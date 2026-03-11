from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_admin_user, get_current_user
from app.core.security import get_password_hash, validate_password_strength
from app.models.user import ALL_PAGES, ActivityLog, User
from app.services.activity_logger import log_activity


router = APIRouter(prefix="/usuarios", tags=["UsuÃ¡rios"])

VALID_PROFILES = {"admin", "user"}


class UsuarioCreate(BaseModel):
    email: EmailStr
    password: str
    nome: str
    perfil: str = "user"
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
    nova_senha: str


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
    if normalized not in VALID_PROFILES:
        raise HTTPException(status_code=400, detail="Perfil invalido")
    return normalized


def _normalize_pages(perfil: str, pages: Optional[List[str]]) -> List[str]:
    if perfil == "admin":
        return list(ALL_PAGES)

    if not pages:
        return []

    normalized = []
    for page in pages:
        if page in ALL_PAGES and page not in normalized:
            normalized.append(page)
    return normalized


def _serialize_user(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "nome": user.nome,
        "perfil": user.perfil,
        "ativo": user.ativo,
        "permitted_pages": user.permitted_pages or (ALL_PAGES if user.perfil == "admin" else []),
        "data_cadastro": user.data_cadastro,
    }


def _active_admin_count(db: Session) -> int:
    return db.query(User).filter(User.perfil == "admin", User.ativo == True).count()


@router.get("/", response_model=List[UsuarioResponse])
def listar_usuarios(
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """List all users (admin only)."""
    users = db.query(User).order_by(User.id).all()
    return [_serialize_user(user) for user in users]


@router.post("/", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
def criar_usuario(
    data: UsuarioCreate,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """Create a new user (admin only)."""
    normalized_email = data.email.lower()
    existing = db.query(User).filter(User.email == normalized_email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email jÃ¡ cadastrado",
        )

    try:
        validate_password_strength(data.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    perfil = _normalize_profile(data.perfil) or "user"
    valid_pages = _normalize_pages(perfil, data.permitted_pages)

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
        f"Criou usuÃ¡rio: {new_user.nome} ({new_user.email})",
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
    """Update user info and permissions (admin only)."""
    user = db.query(User).filter(User.id == usuario_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="UsuÃ¡rio nÃ£o encontrado")

    changes = []
    if data.nome is not None and data.nome != user.nome:
        changes.append(f"nome: {user.nome} -> {data.nome}")
        user.nome = data.nome

    if data.email is not None and data.email.lower() != user.email:
        normalized_email = data.email.lower()
        existing = db.query(User).filter(User.email == normalized_email, User.id != usuario_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email jÃ¡ em uso")
        changes.append(f"email: {user.email} -> {normalized_email}")
        user.email = normalized_email

    if data.perfil is not None and data.perfil != user.perfil:
        novo_perfil = _normalize_profile(data.perfil)
        if user.perfil == "admin" and novo_perfil != "admin" and user.ativo and _active_admin_count(db) <= 1:
            raise HTTPException(status_code=400, detail="Nao e possivel remover o ultimo administrador ativo")
        changes.append(f"perfil: {user.perfil} -> {novo_perfil}")
        user.perfil = novo_perfil

    if data.permitted_pages is not None:
        valid_pages = _normalize_pages(user.perfil, data.permitted_pages)
        user.permitted_pages = valid_pages
        changes.append(f"permissoes atualizadas ({len(valid_pages)} paginas)")
    elif data.perfil is not None:
        user.permitted_pages = _normalize_pages(user.perfil, user.permitted_pages)

    db.commit()
    db.refresh(user)

    if changes:
        log_activity(
            db,
            admin,
            "EDITAR",
            "usuarios",
            f"Editou usuÃ¡rio {user.nome}: {', '.join(changes)}",
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
    """Activate/deactivate a user (admin only)."""
    user = db.query(User).filter(User.id == usuario_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="UsuÃ¡rio nÃ£o encontrado")

    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="NÃ£o Ã© possÃ­vel desativar a si mesmo")

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
        f"{status_text.capitalize()} usuÃ¡rio: {user.nome}",
        user.id,
        request,
    )

    return _serialize_user(user)


@router.post("/{usuario_id}/reset-senha")
def reset_senha(
    usuario_id: int,
    data: ResetSenhaRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """Admin resets another user's password."""
    user = db.query(User).filter(User.id == usuario_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="UsuÃ¡rio nÃ£o encontrado")

    try:
        validate_password_strength(data.nova_senha)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    user.hashed_password = get_password_hash(data.nova_senha)
    db.commit()

    log_activity(
        db,
        admin,
        "EDITAR",
        "usuarios",
        f"Resetou senha do usuÃ¡rio: {user.nome}",
        user.id,
        request,
    )

    return {"status": "Senha alterada com sucesso"}


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
    admin: User = Depends(get_admin_user),
):
    """List activity logs with filters (admin only)."""
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
    current_user: User = Depends(get_current_user),
):
    """List all available page slugs."""
    return {"pages": ALL_PAGES}
