from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func as sqlfunc
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from app.core.database import get_db
from app.core.deps import get_current_user, require_page_access
from app.core.pagination import paginate
from app.models.user import User
from app.models import Multa, Veiculo, Contrato, Cliente


router = APIRouter(
    prefix="/multas",
    tags=["Multas"],
    dependencies=[Depends(require_page_access("multas"))],
)


class MultaBase(BaseModel):
    veiculo_id: int
    numero_infracao: Optional[str] = None
    data_infracao: Optional[date] = None
    valor: float
    data_vencimento: Optional[date] = None
    data_pagamento: Optional[date] = None
    status: Optional[str] = "pendente"
    descricao: Optional[str] = None


class MultaCreate(MultaBase):
    pass


class MultaUpdate(BaseModel):
    numero_infracao: Optional[str] = None
    data_infracao: Optional[date] = None
    valor: Optional[float] = None
    data_vencimento: Optional[date] = None
    data_pagamento: Optional[date] = None
    status: Optional[str] = None
    descricao: Optional[str] = None


class MultaResponse(BaseModel):
    id: int
    veiculo_id: int
    numero_infracao: Optional[str] = None
    data_infracao: Optional[date] = None
    valor: Optional[float] = None
    data_vencimento: Optional[date] = None
    data_pagamento: Optional[date] = None
    status: str = "pendente"
    descricao: Optional[str] = None

    class Config:
        from_attributes = True


# === Fixed path routes FIRST ===


@router.get("/")
def list_multas(
    page: int = 1,
    limit: int = 50,
    search: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
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
        status_filter=status_filter,
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

    if multa.valor <= 0:
        raise HTTPException(status_code=400, detail="Valor da multa deve ser maior que zero")

    db_multa = Multa(**multa.model_dump())
    if not db_multa.responsavel:
        db_multa.responsavel = current_user.email
    db.add(db_multa)
    db.commit()
    db.refresh(db_multa)
    return db_multa


@router.get("/resumo")
def get_multas_resumo(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get fines summary - SQL aggregation instead of loading all records."""
    result = db.query(
        sqlfunc.count(Multa.id).label("total"),
        sqlfunc.count(sqlfunc.nullif(Multa.status != "pendente", True)).label("pendentes"),
        sqlfunc.coalesce(sqlfunc.sum(Multa.valor), 0).label("total_valor"),
        sqlfunc.coalesce(
            sqlfunc.sum(sqlfunc.case((Multa.status == "pendente", Multa.valor), else_=0)), 0
        ).label("valor_pendente"),
    ).first()

    return {
        "total_multas": result.total,
        "multas_pendentes": result.pendentes,
        "total_valor": float(result.total_valor),
        "valor_pendente": float(result.valor_pendente),
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


# === Parameterized routes AFTER ===


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


@router.patch("/{multa_id}", response_model=MultaResponse)
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
    multa.data_pagamento = datetime.now().date()
    db.commit()
    db.refresh(multa)
    return multa


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
