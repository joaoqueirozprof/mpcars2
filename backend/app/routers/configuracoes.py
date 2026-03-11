from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from app.core.database import get_db
from app.core.deps import get_current_user, require_page_access
from app.models.user import User
from app.models import Configuracao


router = APIRouter(
    prefix="/configuracoes",
    tags=["Configurações"],
    dependencies=[Depends(require_page_access("configuracoes"))],
)


class ConfiguracaoResponse(BaseModel):
    id: int
    chave: str
    valor: str

    class Config:
        from_attributes = True


class ConfiguracaoBatch(BaseModel):
    items: List[dict]


@router.get("/", response_model=List[ConfiguracaoResponse])
def get_all_configuracoes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all configurations."""
    return db.query(Configuracao).all()


# IMPORTANT: batch/update MUST come before /{chave} to avoid being caught by the parameterized route
@router.put("/batch/update")
def update_batch_configuracoes(
    batch: ConfiguracaoBatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update multiple configurations at once - loads all configs in 1 query."""
    # Load all existing configs in a single query instead of N queries
    all_configs = db.query(Configuracao).all()
    config_map = {c.chave: c for c in all_configs}

    for item in batch.items:
        chave = item.get("chave")
        valor = item.get("valor")
        if not chave:
            continue
        if chave in config_map:
            config_map[chave].valor = valor
        else:
            new_config = Configuracao(chave=chave, valor=valor)
            db.add(new_config)
            config_map[chave] = new_config

    db.commit()
    return {"status": "atualizado"}


@router.post("/", response_model=ConfiguracaoResponse)
def create_configuracao(
    chave: str,
    valor: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new configuration."""
    existing = db.query(Configuracao).filter(Configuracao.chave == chave).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Chave já existe"
        )

    config = Configuracao(chave=chave, valor=valor)
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


@router.get("/{chave}", response_model=ConfiguracaoResponse)
def get_configuracao(
    chave: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific configuration by key."""
    config = db.query(Configuracao).filter(Configuracao.chave == chave).first()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Configuração não encontrada"
        )
    return config


@router.put("/{chave}", response_model=ConfiguracaoResponse)
def update_configuracao(
    chave: str,
    valor: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a configuration by key."""
    config = db.query(Configuracao).filter(Configuracao.chave == chave).first()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Configuração não encontrada"
        )

    config.valor = valor
    db.commit()
    db.refresh(config)
    return config
