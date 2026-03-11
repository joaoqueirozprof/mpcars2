from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, engine
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
    relatorios,
    reservas,
    seguros,
    usuarios,
    veiculos,
)


def run_startup_tasks() -> None:
    """Create tables, apply compatibility patches, and optionally seed data."""
    Base.metadata.create_all(bind=engine)

    if settings.RUN_LEGACY_COLUMN_MIGRATIONS:
        # Keep compatibility patches for existing deployments until every
        # environment is bootstrapped exclusively through Alembic revisions.
        from sqlalchemy import inspect, text

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

        try:
            from add_columns_migration import run_migration

            run_migration()
        except Exception as exc:
            print(f"Migration note: {exc}")

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
    run_startup_tasks()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="2.0.0",
    description="MPCARS - Sistema de Gerenciamento de Aluguel de Veiculos",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok", "version": "2.0.0"}


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
