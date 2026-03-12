import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_admin_user, get_current_user
from app.core.security import get_password_hash, validate_password_strength
from app.models.user import (
    ASSIGNABLE_PAGES,
    ActivityLog,
    DEFAULT_PAGES_BY_PROFILE,
    User,
    VALID_USER_PROFILES,
    get_profile_pages,
)
from app.services.activity_logger import log_activity


router = APIRouter(prefix="/usuarios", tags=["Usuários"])


class UsuarioCreate(BaseModel):
    email: EmailStr
    password: str
    nome: str
    perfil: str = "operador"
    permitted_pages: List[str] = Field(default_factory=list)


class UsuarioUpdate(BaseModel):
    nome: Optional[str] = None
    email: Optional[EmailStr] = None
    perfil: Optional[str] = None
    permitted_pages: Optional[List[str]] = None


class UsuarioResponse(BaseModel):
    id: int
    email: str
    nome: str
    perfil: str
    ativo: bool
    permitted_pages: List[str]
    data_cadastro: Optional[datetime] = None

    class Config:
        from_attributes = True


class ResetSenhaRequest(BaseModel):
    validade_minutos: int = Field(default=0, ge=0, le=240)


class ActivityLogResponse(BaseModel):
    id: int
    usuario_id: Optional[int] = None
    usuario_nome: Optional[str] = None
    usuario_email: Optional[str] = None
    acao: Optional[str] = None
    recurso: Optional[str] = None
    recurso_id: Optional[int] = None
    descricao: Optional[str] = None
    ip_address: Optional[str] = None
    timestamp: Optional[datetime] = None

    class Config:
        from_attributes = True


def _normalize_profile(perfil: Optional[str]) -> Optional[str]:
    if perfil is None:
        return None

    normalized = perfil.strip().lower()
    if normalized == "user":
        normalized = "operador"
    if normalized not in VALID_USER_PROFILES:
        raise HTTPException(status_code=400, detail="Perfil invalido")
    return normalized


def _normalize_pages(perfil: str, pages: Optional[List[str]]) -> List[str]:
    return get_profile_pages(perfil, pages if pages is not None else None)


def _hash_reset_token(token: str) -> str:
    return hashlib.sha256((token or "").encode("utf-8")).hexdigest()


def _build_password_reset_url(token: str) -> str:
    if settings.PASSWORD_RESET_BASE_URL:
        return f"{settings.PASSWORD_RESET_BASE_URL.rstrip('/')}?token={token}"

    if settings.CORS_ORIGINS:
        return f"{settings.CORS_ORIGINS[0].rstrip('/')}/redefinir-senha?token={token}"

    return f"/redefinir-senha?token={token}"


def _serialize_user(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "nome": user.nome,
        "perfil": user.perfil,
        "ativo": user.ativo,
        "permitted_pages": get_profile_pages(user.perfil, user.permitted_pages),
        "data_cadastro": user.data_cadastro,
    }


def _active_admin_count(db: Session) -> int:
    return db.query(User).filter(User.perfil == "admin", User.ativo == True).count()


def _active_owner_count(db: Session) -> int:
    return db.query(User).filter(User.perfil == "owner", User.ativo == True).count()


def _access_catalog() -> Dict[str, Any]:
    labels = {
        "dashboard": "Dashboard",
        "clientes": "Clientes",
        "veiculos": "Veiculos",
        "contratos": "Contratos",
        "empresas": "Empresas",
        "financeiro": "Financeiro",
        "seguros": "Seguros",
        "ipva": "Licenciamento",
        "multas": "Multas",
        "manutencoes": "Manutencoes",
        "reservas": "Reservas",
        "despesas-loja": "Despesas da loja",
        "relatorios": "Relatorios",
        "configuracoes": "Configuracoes",
    }
    return {
        "profiles": [
            {
                "id": "admin",
                "label": "Administrador",
                "description": "Acesso total a operacao, usuarios e backups. Checklist sensivel de producao e versoes continuam reservados ao admin principal da plataforma.",
                "fixed_pages": get_profile_pages("admin"),
                "manual_selection": False,
            },
            {
                "id": "gerente",
                "label": "Gerente",
                "description": "Cuida da operacao, financeiro e tambem acompanha backups e restauracao basica.",
                "fixed_pages": get_profile_pages("gerente"),
                "manual_selection": True,
            },
            {
                "id": "operador",
                "label": "Operador",
                "description": "Acesso simples para atendimento, reservas, contratos e frota.",
                "fixed_pages": DEFAULT_PAGES_BY_PROFILE["operador"],
                "manual_selection": True,
            },
            {
                "id": "owner",
                "label": "Dono da empresa",
                "description": "Acesso completo da locadora, inclusive usuarios e backups. Itens sensiveis de prontidao e versoes seguem reservados ao admin principal da plataforma.",
                "fixed_pages": get_profile_pages("owner"),
                "manual_selection": False,
            },
        ],
        "assignable_pages": [
            {"slug": slug, "label": labels.get(slug, slug.replace("-", " ").title())}
            for slug in ASSIGNABLE_PAGES
        ],
        "hidden_pages": ["usuarios", "governanca"],
    }


@router.get("/catalogo-acesso")
def obter_catalogo_acesso(
    _: User = Depends(get_admin_user),
):
    return _access_catalog()


@router.get("/", response_model=List[UsuarioResponse])
def listar_usuarios(
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    users = db.query(User).order_by(User.id).all()
    return [_serialize_user(user) for user in users]


@router.post("/", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
def criar_usuario(
    data: UsuarioCreate,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    normalized_email = data.email.lower()
    existing = db.query(User).filter(User.email == normalized_email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email ja cadastrado")

    try:
        validate_password_strength(data.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    perfil = _normalize_profile(data.perfil) or "operador"
    if perfil == "owner" and _active_owner_count(db) >= 1:
        raise HTTPException(
            status_code=400,
            detail="Ja existe um usuario dono da empresa ativo. Edite o acesso atual em vez de criar outro.",
        )

    valid_pages = _normalize_pages(perfil, data.permitted_pages or None)

    new_user = User(
        email=normalized_email,
        hashed_password=get_password_hash(data.password),
        nome=data.nome,
        perfil=perfil,
        ativo=True,
        permitted_pages=valid_pages,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    log_activity(
        db,
        admin,
        "CRIAR",
        "usuarios",
        f"Criou usuario: {new_user.nome} ({new_user.email}) [{perfil}]",
        new_user.id,
        request,
    )

    return _serialize_user(new_user)


@router.put("/{usuario_id}", response_model=UsuarioResponse)
def atualizar_usuario(
    usuario_id: int,
    data: UsuarioUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    user = db.query(User).filter(User.id == usuario_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")

    changes: List[str] = []

    if data.nome is not None and data.nome != user.nome:
        changes.append(f"nome: {user.nome} -> {data.nome}")
        user.nome = data.nome

    if data.email is not None and data.email.lower() != user.email:
        normalized_email = data.email.lower()
        existing = (
            db.query(User)
            .filter(User.email == normalized_email, User.id != usuario_id)
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="Email ja em uso")
        changes.append(f"email: {user.email} -> {normalized_email}")
        user.email = normalized_email

    if data.perfil is not None and data.perfil != user.perfil:
        novo_perfil = _normalize_profile(data.perfil)
        if user.perfil == "admin" and novo_perfil != "admin" and user.ativo and _active_admin_count(db) <= 1:
            raise HTTPException(status_code=400, detail="Nao e possivel remover o ultimo administrador ativo")
        if novo_perfil == "owner" and user.perfil != "owner" and _active_owner_count(db) >= 1:
            raise HTTPException(status_code=400, detail="Ja existe um usuario dono da empresa ativo")
        changes.append(f"perfil: {user.perfil} -> {novo_perfil}")
        user.perfil = novo_perfil

    if data.permitted_pages is not None:
        valid_pages = _normalize_pages(user.perfil, data.permitted_pages or None)
        user.permitted_pages = valid_pages
        changes.append(f"permissoes atualizadas ({len(valid_pages)} paginas)")
    elif data.perfil is not None:
        user.permitted_pages = _normalize_pages(user.perfil, None)

    db.commit()
    db.refresh(user)

    if changes:
        log_activity(
            db,
            admin,
            "EDITAR",
            "usuarios",
            f"Editou usuario {user.nome}: {', '.join(changes)}",
            user.id,
            request,
        )

    return _serialize_user(user)


@router.patch("/{usuario_id}/toggle", response_model=UsuarioResponse)
def toggle_usuario(
    usuario_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    user = db.query(User).filter(User.id == usuario_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")

    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Nao e possivel desativar a si mesmo")

    if user.perfil == "admin" and user.ativo and _active_admin_count(db) <= 1:
        raise HTTPException(status_code=400, detail="Nao e possivel desativar o ultimo administrador ativo")

    user.ativo = not user.ativo
    db.commit()
    db.refresh(user)

    status_text = "ativou" if user.ativo else "desativou"
    log_activity(
        db,
        admin,
        "EDITAR",
        "usuarios",
        f"{status_text.capitalize()} usuario: {user.nome}",
        user.id,
        request,
    )

    return _serialize_user(user)


@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_usuario(
    usuario_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    user = db.query(User).filter(User.id == usuario_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")

    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Nao e possivel excluir a propria conta")

    if user.perfil == "admin" and user.ativo and _active_admin_count(db) <= 1:
        raise HTTPException(status_code=400, detail="Nao e possivel excluir o ultimo administrador ativo")

    deleted_id = user.id
    deleted_name = user.nome
    deleted_email = user.email
    deleted_profile = user.perfil

    db.delete(user)
    db.commit()

    log_activity(
        db,
        admin,
        "EXCLUIR",
        "usuarios",
        f"Excluiu usuario: {deleted_name} ({deleted_email}) [{deleted_profile}]",
        deleted_id,
        request,
    )

    return None


@router.post("/{usuario_id}/reset-senha")
def reset_senha(
    usuario_id: int,
    data: ResetSenhaRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    user = db.query(User).filter(User.id == usuario_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")

    validity_minutes = data.validade_minutos or settings.PASSWORD_RESET_TOKEN_TTL_MINUTES
    raw_token = secrets.token_urlsafe(32)
    expires_at = (
        datetime.now(timezone.utc) + timedelta(minutes=validity_minutes)
    ).replace(tzinfo=None)

    user.password_reset_token_hash = _hash_reset_token(raw_token)
    user.password_reset_expires_at = expires_at
    user.password_reset_requested_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()

    log_activity(
        db,
        admin,
        "EDITAR",
        "usuarios",
        f"Iniciou recuperacao de senha para o usuario: {user.nome}",
        user.id,
        request,
    )

    return {
        "status": "Link de redefinicao gerado com sucesso",
        "recovery_url": _build_password_reset_url(raw_token),
        "expires_at": expires_at,
        "instructions": "Compartilhe este link apenas com o usuario dono da conta. A nova senha sera definida por ele.",
    }


@router.get("/logs", response_model=List[ActivityLogResponse])
def listar_logs(
    usuario_id: Optional[int] = Query(None),
    acao: Optional[str] = Query(None),
    recurso: Optional[str] = Query(None),
    data_inicio: Optional[str] = Query(None),
    data_fim: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    query = db.query(ActivityLog).order_by(desc(ActivityLog.timestamp))

    if usuario_id:
        query = query.filter(ActivityLog.usuario_id == usuario_id)
    if acao:
        query = query.filter(ActivityLog.acao == acao)
    if recurso:
        query = query.filter(ActivityLog.recurso == recurso)
    if data_inicio:
        try:
            dt = datetime.strptime(data_inicio, "%Y-%m-%d")
            query = query.filter(ActivityLog.timestamp >= dt)
        except ValueError:
            pass
    if data_fim:
        try:
            dt = datetime.strptime(data_fim, "%Y-%m-%d").replace(
                hour=23,
                minute=59,
                second=59,
            )
            query = query.filter(ActivityLog.timestamp <= dt)
        except ValueError:
            pass

    logs = query.offset(offset).limit(limit).all()
    return logs


@router.get("/pages-list")
def listar_paginas(
    _: User = Depends(get_current_user),
):
    return {
        "pages": ASSIGNABLE_PAGES,
        "hidden_pages": ["usuarios", "governanca"],
    }
