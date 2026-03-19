from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool, QueuePool
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings


DATABASE_URL = settings.database_url_for_runtime


def _get_pool_settings():
    """Get pool settings based on environment."""
    if DATABASE_URL.startswith("sqlite"):
        return {
            "connect_args": {"check_same_thread": False},
            "poolclass": StaticPool,
        }

    base_settings = {
        "pool_pre_ping": True,
        "echo": settings.ENVIRONMENT == "development",
    }

    if settings.is_production:
        base_settings.update({
            "pool_size": 20,
            "max_overflow": 30,
            "pool_recycle": 1800,
            "pool_timeout": 30,
        })
    elif settings.is_staging:
        base_settings.update({
            "pool_size": 15,
            "max_overflow": 20,
            "pool_recycle": 3600,
        })
    else:
        base_settings.update({
            "pool_size": 5,
            "max_overflow": 10,
        })

    return base_settings


engine_kwargs = _get_pool_settings()

engine = create_engine(
    DATABASE_URL,
    **engine_kwargs,
)


@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Log new database connections in development."""
    if settings.ENVIRONMENT == "development":
        connection_record.info["pid"] = id(dbapi_conn)


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
