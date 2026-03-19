import hashlib
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, EmailStr
from sqlalchemy.orm import Session

from app.core.config import settings

try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    _auth_limiter = Limiter(key_func=get_remote_address)
except ImportError:
    _auth_limiter = None
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import (
    create_access_token,
    get_password_hash,
    validate_password_strength,
    verify_password,
)
from app.models.user import User, get_profile_pages
from app.services.activity_logger import log_activity


router = APIRouter(prefix="/auth", tags=["Auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    nome: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: str
    nome: str
    perfil: str
    ativo: bool
    permitted_pages: Optional[List[str]] = None

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class ChangePasswordRequest(BaseModel):
    senha_atual: str
    senha_nova: str


class PasswordResetTokenRequest(BaseModel):
    token: str


class PasswordResetCompleteRequest(BaseModel):
    token: str
    senha_nova: str


class ProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    nome: Optional[str] = None
    email: Optional[EmailStr] = None


def _get_user_pages(user: User) -> list:
    return get_profile_pages(user.perfil, user.permitted_pages)


def _hash_reset_token(token: str) -> str:
    return hashlib.sha256((token or "").encode("utf-8")).hexdigest()


def _serialize_user(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "nome": user.nome,
        "perfil": user.perfil,
        "ativo": user.ativo,
        "permitted_pages": _get_user_pages(user),
    }


# Simple login rate limiter: max 10 attempts per minute per IP
_login_attempts: dict = {}

def _check_login_rate(ip: str) -> bool:
    import time
    now = time.time()
    # Clean old entries
    cutoff = now - 60
    _login_attempts[ip] = [t for t in _login_attempts.get(ip, []) if t > cutoff]
    if len(_login_attempts.get(ip, [])) >= 10:
        return False
    _login_attempts.setdefault(ip, []).append(now)
    return True


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, req: Request, db: Session = Depends(get_db)):
    """Login with email and password. Rate limited to 10/minute per IP."""
    client_ip = req.client.host if req.client else "unknown"
    if not _check_login_rate(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de login. Aguarde 1 minuto.",
        )
    normalized_email = request.email.lower()
    user = db.query(User).filter(User.email == normalized_email).first()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha invÃ¡lidos",
        )
    if not user.ativo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="UsuÃ¡rio inativo",
        )

    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})

    log_activity(
        db,
        user,
        "LOGIN",
        "auth",
        f"Login realizado: {user.nome}",
        request=req,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": _serialize_user(user),
    }


@router.post("/register", response_model=TokenResponse)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user when public sign-up is enabled."""
    if not settings.ALLOW_PUBLIC_REGISTRATION:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cadastro publico desabilitado. Solicite um administrador.",
        )

    normalized_email = request.email.lower()
    existing_user = db.query(User).filter(User.email == normalized_email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email jÃ¡ cadastrado",
        )

    try:
        validate_password_strength(request.password)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    new_user = User(
        email=normalized_email,
        hashed_password=get_password_hash(request.password),
        nome=request.nome,
        perfil="operador",
        ativo=True,
        permitted_pages=get_profile_pages("operador"),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    access_token = create_access_token(
        data={"sub": str(new_user.id), "email": new_user.email}
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return _serialize_user(current_user)


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(current_user: User = Depends(get_current_user)):
    """Refresh access token."""
    access_token = create_access_token(
        data={"sub": str(current_user.id), "email": current_user.email}
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.put("/change-password")
def change_password(
    request: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Change current user password."""
    if not verify_password(request.senha_atual, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha atual incorreta",
        )

    if request.senha_atual == request.senha_nova:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A nova senha deve ser diferente da senha atual",
        )

    try:
        validate_password_strength(request.senha_nova)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    current_user.hashed_password = get_password_hash(request.senha_nova)
    db.commit()
    return {"status": "senha alterada com sucesso"}


@router.put("/profile", response_model=UserResponse)
def update_profile(
    profile_data: ProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update current user profile."""
    update_data = profile_data.model_dump(exclude_unset=True)

    if update_data.get("nome"):
        current_user.nome = update_data["nome"]

    if update_data.get("email"):
        normalized_email = update_data["email"].lower()
        existing = db.query(User).filter(
            User.email == normalized_email,
            User.id != current_user.id,
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email jÃ¡ em uso por outro usuÃ¡rio",
            )
        current_user.email = normalized_email

    db.commit()
    db.refresh(current_user)
    return _serialize_user(current_user)


@router.post("/password-reset/validate")
def validate_password_reset_token(
    request: PasswordResetTokenRequest,
    db: Session = Depends(get_db),
):
    hashed_token = _hash_reset_token(request.token)
    user = db.query(User).filter(User.password_reset_token_hash == hashed_token).first()

    if not user or not user.password_reset_expires_at:
        raise HTTPException(status_code=400, detail="Link de recuperacao invalido")

    if user.password_reset_expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
        raise HTTPException(status_code=400, detail="Link de recuperacao expirado")

    return {
        "status": "ok",
        "usuario": {
            "nome": user.nome,
            "email": user.email,
        },
        "expires_at": user.password_reset_expires_at,
    }


@router.post("/password-reset/complete")
def complete_password_reset(
    request: PasswordResetCompleteRequest,
    db: Session = Depends(get_db),
):
    hashed_token = _hash_reset_token(request.token)
    user = db.query(User).filter(User.password_reset_token_hash == hashed_token).first()

    if not user or not user.password_reset_expires_at:
        raise HTTPException(status_code=400, detail="Link de recuperacao invalido")

    if user.password_reset_expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
        raise HTTPException(status_code=400, detail="Link de recuperacao expirado")

    try:
        validate_password_strength(request.senha_nova)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    user.hashed_password = get_password_hash(request.senha_nova)
    user.password_reset_token_hash = None
    user.password_reset_expires_at = None
    user.password_reset_requested_at = None
    db.commit()

    return {
        "status": "Senha redefinida com sucesso",
        "next_step": "Faça login com a nova senha.",
    }
