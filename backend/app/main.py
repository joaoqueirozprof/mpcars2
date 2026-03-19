from contextlib import asynccontextmanager
import logging
import sys

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
except Exception:  # pragma: no cover - fallback for legacy images without slowapi
    Limiter = None
    RateLimitExceeded = None

    def get_remote_address(request: Request):  # type: ignore[override]
        return request.client.host if request.client else "unknown"

from app.core.config import settings
from app.core.database import Base, engine
from app.core.exceptions import register_exception_handlers
from app.core.versioning import get_version_info, version_middleware, APIVersion
from app.models import (  # noqa: F401 - import models so SQLAlchemy registers metadata
    AlertaHistorico,
    AuditLog,
    CheckinCheckout,
    Cliente,
    Configuracao,
    Contrato,
    DespesaContrato,
    DespesaLoja,
    DespesaNF,
    DespesaOperacional,
    DespesaVeiculo,
    Documento,
    Empresa,
    IpvaAliquota,
    IpvaParcela,
    IpvaRegistro,
    LancamentoFinanceiro,
    Manutencao,
    MotoristaEmpresa,
    Multa,
    ParcelaSeguro,
    ProrrogacaoContrato,
    Quilometragem,
    RelatorioNF,
    Reserva,
    Seguro,
    UsoVeiculoEmpresa,
    Veiculo,
)
from app.models.user import ActivityLog, User  # noqa: F401
from app.routers import (
    auth,
    clientes,
    configuracoes,
    contratos,
    dashboard,
    despesas_loja,
    empresas,
    financeiro,
    ipva,
    manutencoes,
    multas,
    ops,
    relatorios,
    reservas,
    seguros,
    usuarios,
    veiculos,
)

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute", "20/second"]) if Limiter else None


def setup_logging():
    """Configure structured logging for the application."""
    log_level = logging.DEBUG if settings.ENVIRONMENT == "development" else logging.INFO

    logging.basicConfig(
        level=log_level,
        format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "name": "%(name)s", "message": "%(message)s"}',
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )

    if settings.ENVIRONMENT == "production":
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("uvicorn.error").setLevel(logging.INFO)


setup_logging()


def run_startup_tasks() -> None:
    """Create tables, apply compatibility patches, and optionally seed data."""
    Base.metadata.create_all(bind=engine)

    # Safe compatibility patch for production data: keep historical installs working
    # even when the DB was created before new optional columns were introduced.
    from sqlalchemy import inspect, text

    with engine.connect() as conn:
        inspector = inspect(engine)
        if "veiculos" in inspector.get_table_names():
            veiculos_columns = [column["name"] for column in inspector.get_columns("veiculos")]
            if "observacoes" not in veiculos_columns:
                conn.execute(text("ALTER TABLE veiculos ADD COLUMN observacoes TEXT"))
                conn.commit()

    if settings.RUN_LEGACY_COLUMN_MIGRATIONS and not settings.is_production:
        logger.warning("Running legacy column migrations - this should only happen in development")

        with engine.connect() as conn:
            inspector = inspect(engine)

            if "veiculos" in inspector.get_table_names():
                columns = [column["name"] for column in inspector.get_columns("veiculos")]
                if "foto_url" not in columns:
                    conn.execute(text("ALTER TABLE veiculos ADD COLUMN foto_url VARCHAR"))
                    conn.commit()

            if "multas" in inspector.get_table_names():
                columns = [column["name"] for column in inspector.get_columns("multas")]
                if "numero_infracao" not in columns:
                    conn.execute(
                        text("ALTER TABLE multas ADD COLUMN numero_infracao VARCHAR")
                    )
                    conn.commit()
                if "data_vencimento" not in columns:
                    conn.execute(text("ALTER TABLE multas ADD COLUMN data_vencimento DATE"))
                    conn.commit()

            if "ipva_registro" in inspector.get_table_names():
                columns = [
                    column["name"] for column in inspector.get_columns("ipva_registro")
                ]
                if "qtd_parcelas" not in columns:
                    conn.execute(
                        text("ALTER TABLE ipva_registro ADD COLUMN qtd_parcelas INTEGER")
                    )
                    conn.commit()

            if "users" in inspector.get_table_names():
                columns = [column["name"] for column in inspector.get_columns("users")]
                if "permitted_pages" not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN permitted_pages JSON"))
                    conn.commit()
                if "password_reset_token_hash" not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN password_reset_token_hash VARCHAR"))
                    conn.commit()
                if "password_reset_expires_at" not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN password_reset_expires_at TIMESTAMP"))
                    conn.commit()
                if "password_reset_requested_at" not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN password_reset_requested_at TIMESTAMP"))
                    conn.commit()

        try:
            from add_columns_migration import run_migration

            run_migration()
        except Exception as exc:
            logger.warning(f"Migration note: {exc}")

    if settings.SEED_ON_STARTUP:
        from app.core.database import SessionLocal
        from app.services.seed import seed_database

        db = SessionLocal()
        try:
            seed_database(db)
        finally:
            db.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info(f"Starting MPCARS2 in {settings.ENVIRONMENT} mode")
    run_startup_tasks()
    yield
    logger.info("Shutting down MPCARS2")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="2.0.0",
    description="MPCARS - Sistema de Gerenciamento de Aluguel de Veiculos",
    lifespan=lifespan,
    docs_url="/docs" if settings.should_enable_docs else None,
    redoc_url="/redoc" if settings.should_enable_docs else None,
    openapi_url="/openapi.json" if settings.should_enable_docs else None,
)

app = register_exception_handlers(app)

if limiter is not None:
    app.state.limiter = limiter


@app.middleware("http")
async def add_version_middleware(request: Request, call_next):
    """Add API versioning headers to responses."""
    return await version_middleware(request, call_next)


if RateLimitExceeded is not None:
    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
        return JSONResponse(
            status_code=429,
            content={
                "detail": "Too many requests. Please try again later.",
                "retry_after": exc.detail,
            },
        )


if settings.TRUSTED_HOSTS:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.TRUSTED_HOSTS)


def _get_cors_origins() -> list[str]:
    """Get CORS origins based on environment."""
    if settings.is_production:
        production_origins = [
            "https://mpcars.com.br",
            "https://www.mpcars.com.br",
        ]
        configured_origins = [o.strip() for o in settings.CORS_ORIGINS if (o or "").strip()]
        return list(dict.fromkeys(production_origins + configured_origins))
    return settings.CORS_ORIGINS or ["*"]


cors_origins = _get_cors_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)

    if settings.SECURITY_HEADERS_ENABLED:
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

        forwarded_proto = request.headers.get("x-forwarded-proto", request.url.scheme)
        if forwarded_proto == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

    return response


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests for security monitoring."""
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Client: {request.client.host if request.client else 'Unknown'}"
    )
    response = await call_next(request)
    return response


@app.get("/health")
def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "version": "2.0.0",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/api/info")
def api_info():
    """Get API version information."""
    return get_version_info()


@app.get("/security/headers")
def security_headers_check():
    """Verify security headers are properly configured."""
    return {
        "security_headers_enabled": settings.SECURITY_HEADERS_ENABLED,
        "rate_limiting_enabled": settings.RATE_LIMIT_ENABLED,
        "docs_enabled": settings.should_enable_docs,
        "cors_origins": cors_origins if not settings.is_production else "restricted",
    }


app.include_router(auth.router, prefix=settings.API_V1_PREFIX, tags=["Auth"])
app.include_router(clientes.router, prefix=settings.API_V1_PREFIX, tags=["Clientes"])
app.include_router(veiculos.router, prefix=settings.API_V1_PREFIX, tags=["Veiculos"])
app.include_router(contratos.router, prefix=settings.API_V1_PREFIX, tags=["Contratos"])
app.include_router(empresas.router, prefix=settings.API_V1_PREFIX, tags=["Empresas"])
app.include_router(dashboard.router, prefix=settings.API_V1_PREFIX, tags=["Dashboard"])
app.include_router(financeiro.router, prefix=settings.API_V1_PREFIX, tags=["Financeiro"])
app.include_router(
    configuracoes.router, prefix=settings.API_V1_PREFIX, tags=["Configuracoes"]
)
app.include_router(seguros.router, prefix=settings.API_V1_PREFIX, tags=["Seguros"])
app.include_router(multas.router, prefix=settings.API_V1_PREFIX, tags=["Multas"])
app.include_router(
    manutencoes.router, prefix=settings.API_V1_PREFIX, tags=["Manutencoes"]
)
app.include_router(reservas.router, prefix=settings.API_V1_PREFIX, tags=["Reservas"])
app.include_router(relatorios.router, prefix=settings.API_V1_PREFIX, tags=["Relatorios"])
app.include_router(ipva.router, prefix=settings.API_V1_PREFIX, tags=["IPVA"])
app.include_router(
    despesas_loja.router, prefix=settings.API_V1_PREFIX, tags=["Despesas Loja"]
)
app.include_router(usuarios.router, prefix=settings.API_V1_PREFIX, tags=["Usuarios"])
app.include_router(ops.router, prefix=settings.API_V1_PREFIX, tags=["Operacao"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
