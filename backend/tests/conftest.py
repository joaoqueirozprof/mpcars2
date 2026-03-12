import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


BACKEND_DIR = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(BACKEND_DIR))

os.environ["ENVIRONMENT"] = "test"
os.environ["TESTING"] = "true"
os.environ["SEED_ON_STARTUP"] = "false"
os.environ["RUN_LEGACY_COLUMN_MIGRATIONS"] = "false"
os.environ["ALLOW_PUBLIC_REGISTRATION"] = "false"
os.environ["SECRET_KEY"] = "test-secret-key-with-at-least-32-chars"
os.environ["TEST_DATABASE_URL"] = "sqlite://"

from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import ALL_PAGES, User  # noqa: E402


def create_user(
    db_session,
    *,
    email: str,
    password: str = "SenhaForte123",
    nome: str = "Usuario Teste",
    perfil: str = "user",
    permitted_pages=None,
    ativo: bool = True,
):
    pages = list(ALL_PAGES) if perfil == "admin" else list(permitted_pages or [])
    user = User(
        email=email.lower(),
        hashed_password=get_password_hash(password),
        nome=nome,
        perfil=perfil,
        ativo=ativo,
        permitted_pages=pages,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(autouse=True)
def reset_database():
    engine.dispose()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    try:
        yield
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def login_as(client):
    def _login(email: str, password: str):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert response.status_code == 200, response.text
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _login


@pytest.fixture
def user_factory(db_session):
    def _create_user(**kwargs):
        return create_user(db_session, **kwargs)

    return _create_user


@pytest.fixture
def admin_user(db_session):
    return create_user(
        db_session,
        email="admin@example.org",
        password="AdminSeguro123",
        nome="Administrador",
        perfil="admin",
    )


@pytest.fixture
def admin_headers(login_as, admin_user):
    return login_as(admin_user.email, "AdminSeguro123")
