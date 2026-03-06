from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.pagination import paginate
from app.models.user import User
from app.models import Multa, Veiculo, Contrato, Cliente


router = APIRouter(prefix="/multas", tags=["Multas"])


class MultaBase(BaseModel):
    veiculo_id: int
    contrato_id: Optional[int] = None
    cliente_id: Optional[int] = None
    data_infracao: date
    valor: float
    pontos: int
    gravidade: str
    responsavel: Optional[str] = None


class MultaCreate(MultaBase):
    pass


class MultaUpdate(BaseModel):
    valor: Optional[float] = None
    status: Optional[str] = None
    responsavel: Optional[str] = None


class MultaResponse(MultaBase):
    id: int
    status: str

    class Config:
        from_attributes = True


@router.get("/")
def list_multas(
    page: int = 1,
    limit: int = 50,
    search: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all fines with pagination."""
    query = db.query(Multa).options(joinedload(Multa.veiculo), joinedload(Multa.cliente))
    return paginate(
        query=query,
        page=page,
        limit=limit,
        search=search,
        search_fields=["responsavel", "gravidade"],
        model=Multa,
        status_filter=status,
    )


@router.post("/", response_model=MultaResponse)
def create_multa(
    multa: MultaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new fine."""
    veiculo = db.query(Veiculo).filter(Veiculo.id == multa.veiculo_id).first()
    if not veiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Veículo não encontrado"
        )

    db_multa = Multa(**multa.model_dump())
    if not db_multa.responsavel:
        db_multa.responsavel = current_user.email
    db.add(db_multa)
    db.commit()
    db.refresh(db_multa)
    return db_multa


@router.get("/{multa_id}", response_model=MultaResponse)
def get_multa(
    multa_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific fine."""
    multa = db.query(Multa).filter(Multa.id == multa_id).first()
    if not multa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Multa não encontrada"
        )
    return multa


@router.put("/{multa_id}", response_model=MultaResponse)
def update_multa(
    multa_id: int,
    multa_data: MultaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a fine."""
    multa = db.query(Multa).filter(Multa.id == multa_id).first()
    if not multa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Multa não encontrada"
        )

    update_data = multa_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(multa, key, value)

    db.commit()
    db.refresh(multa)
    return multa


@router.post("/{multa_id}/pagar")
def pagar_multa(
    multa_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a fine as paid."""
    multa = db.query(Multa).filter(Multa.id == multa_id).first()
    if not multa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Multa não encontrada"
        )

    multa.status = "pago"
    db.commit()
    db.refresh(multa)
    return multa


@router.get("/resumo")
def get_multas_resumo(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get fines summary."""
    total_multas = db.query(Multa).count()
    multas_pendentes = db.query(Multa).filter(Multa.status == "pendente").count()
    total_valor = sum(float(m.valor) for m in db.query(Multa).all() if m.valor)

    return {
        "total_multas": total_multas,
        "multas_pendentes": multas_pendentes,
        "total_valor": total_valor,
    }


@router.get("/veiculo/{veiculo_id}", response_model=List[MultaResponse])
def get_multas_veiculo(
    veiculo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get fines for a vehicle."""
    multas = db.query(Multa).filter(Multa.veiculo_id == veiculo_id).all()
    return multas


@router.delete("/{multa_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_multa(
    multa_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a fine."""
    multa = db.query(Multa).filter(Multa.id == multa_id).first()
    if not multa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Multa não encontrada"
        )
    db.delete(multa)
    db.commit()
