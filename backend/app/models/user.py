from typing import Iterable, List, Optional

from sqlalchemy import Column, Integer, String, Boolean, DateTime, func, JSON
from app.core.database import Base


ALL_PAGES = [
    "dashboard", "clientes", "veiculos", "contratos", "empresas",
    "financeiro", "seguros", "ipva", "multas", "manutencoes",
    "reservas", "despesas-loja", "relatorios", "configuracoes", "usuarios",
    "governanca",
]

ASSIGNABLE_PAGES = [
    "dashboard", "clientes", "veiculos", "contratos", "empresas",
    "financeiro", "seguros", "ipva", "multas", "manutencoes",
    "reservas", "despesas-loja", "relatorios", "configuracoes",
]

VALID_USER_PROFILES = {"admin", "gerente", "operador", "owner", "user"}

DEFAULT_PAGES_BY_PROFILE = {
    "gerente": [
        "dashboard",
        "clientes",
        "veiculos",
        "contratos",
        "empresas",
        "financeiro",
        "seguros",
        "ipva",
        "multas",
        "manutencoes",
        "reservas",
        "despesas-loja",
        "relatorios",
        "governanca",
    ],
    "operador": [
        "dashboard",
        "clientes",
        "veiculos",
        "contratos",
        "reservas",
    ],
}


def normalize_assignable_pages(pages: Optional[Iterable[str]]) -> List[str]:
    if not pages:
        return []

    normalized: List[str] = []
    for page in pages:
        slug = (page or "").strip()
        if slug in ASSIGNABLE_PAGES and slug not in normalized:
            normalized.append(slug)
    return normalized


def get_profile_pages(perfil: str, custom_pages: Optional[Iterable[str]] = None) -> List[str]:
    normalized_profile = (perfil or "operador").strip().lower()
    if normalized_profile == "user":
        normalized_profile = "operador"

    if normalized_profile == "admin":
        return list(ALL_PAGES)

    if normalized_profile == "owner":
        return list(ALL_PAGES)

    source_pages = (
        normalize_assignable_pages(custom_pages)
        if custom_pages is not None
        else DEFAULT_PAGES_BY_PROFILE.get(normalized_profile, [])
    )

    normalized_pages = normalize_assignable_pages(source_pages)
    if normalized_profile == "gerente" and "governanca" not in normalized_pages:
        normalized_pages.append("governanca")

    return normalized_pages


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    nome = Column(String, nullable=False)
    perfil = Column(String, default="admin")
    ativo = Column(Boolean, default=True)
    permitted_pages = Column(JSON, default=list)
    password_reset_token_hash = Column(String, nullable=True)
    password_reset_expires_at = Column(DateTime, nullable=True)
    password_reset_requested_at = Column(DateTime, nullable=True)
    data_cadastro = Column(DateTime, server_default=func.now())


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, nullable=True)
    usuario_nome = Column(String)
    usuario_email = Column(String)
    acao = Column(String)  # LOGIN, CRIAR, EDITAR, EXCLUIR, VISUALIZAR
    recurso = Column(String)  # clientes, veiculos, contratos, etc.
    recurso_id = Column(Integer, nullable=True)
    descricao = Column(String)
    ip_address = Column(String)
    timestamp = Column(DateTime, server_default=func.now())
