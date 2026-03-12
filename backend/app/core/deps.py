from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import get_profile_pages


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    """Get the current authenticated user from JWT token."""
    from app.models.user import User

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        subject = payload.get("sub")
        if subject is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = None
    if str(subject).isdigit():
        user = db.query(User).filter(User.id == int(subject)).first()

    if user is None:
        user = db.query(User).filter(User.email == str(subject).lower()).first()

    if user is None:
        raise credentials_exception

    if not user.ativo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo",
        )

    return user


def get_admin_user(
    current_user=Depends(get_current_user),
):
    """Require admin user. Returns 403 if user is not admin."""
    if current_user.perfil != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores",
        )
    return current_user


def get_ops_user(
    current_user=Depends(get_current_user),
):
    """Allow platform admin or backup owner to access governance tools."""
    if current_user.perfil not in {"admin", "owner"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores da plataforma",
        )
    return current_user


def require_page_access(page_slug: str):
    def dependency(current_user=Depends(get_current_user)):
        permitted_pages = get_profile_pages(current_user.perfil, current_user.permitted_pages)
        if page_slug not in permitted_pages:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario sem permissao para acessar esta area",
            )

        return current_user

    return dependency
