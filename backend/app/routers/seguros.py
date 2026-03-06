from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.pagination import paginate
from app.models.user import User
from app.models import Seguro, ParcelaSeguro, Veiculo


router = APIRouter(prefix="/seguros", tags=["Seguros"])


class SeguroBase(BaseModel):
    veiculo_id: int
    seguradora: str
    numero_apolice: str
    tipo_seguro: str
    data_inicio: date
    data_fim: date
    valor: float
    valor_franquia: float
    qtd_parcelas: int


class SeguroCreate(SeguroBase):
    pass


class SeguroUpdate(BaseModel):
    seguradora: Optional[str] = None
    tipo_seguro: Optional[str] = None
    data_fim: Optional[date] = None
    valor: Optional[float] = None
    status: Optional[str] = None


class SeguroResponse(SeguroBase):
    id: int
    status: str

    class Config:
        from_attributes = True


class ParcelaResponse(BaseModel):
    id: int
    numero_parcela: int
    valor: float
    vencimento: date
    data_pagamento: Optional[date] = None
    status: str

    class Config:
        from_attributes = True


@router.get("/")
def list_seguros(
    page: int = 1,
    limit: int = 50,
    search: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all insurance policies with pagination."""
    query = db.query(Seguro).options(joinedload(Seguro.veiculo))
    return paginate(
        query=query,
        page=page,
        limit=limit,
        search=search,
        search_fields=["seguradora", "numero_apolice"],
        model=Seguro,
        status_filter=status,
    )


@router.post("/", response_model=SeguroResponse)
def create_seguro(
    seguro: SeguroCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new insurance policy."""
    veiculo = db.query(Veiculo).filter(Veiculo.id == seguro.veiculo_id).first()
    if not veiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Veículo não encontrado"
        )

    existing = db.query(Seguro).filter(
        Seguro.numero_apolice == seguro.numero_apolice
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Número de apólice já cadastrado",
        )

    db_seguro = Seguro(**seguro.model_dump())
    db.add(db_seguro)
    db.commit()
    db.refresh(db_seguro)

    # Create installments
    dias_entre = (seguro.data_fim - seguro.data_inicio).days
    dias_por_parcela = dias_entre // seguro.qtd_parcelas
    valor_parcela = seguro.valor / seguro.qtd_parcelas

    for i in range(1, seguro.qtd_parcelas + 1):
        vencimento = seguro.data_inicio + __import__("datetime").timedelta(
            days=dias_por_parcela * i
        )
        parcela = ParcelaSeguro(
            seguro_id=db_seguro.id,
            veiculo_id=seguro.veiculo_id,
            numero_parcela=i,
            valor=valor_parcela,
            vencimento=vencimento,
        )
        db.add(parcela)

    db.commit()
    return db_seguro


@router.get("/{seguro_id}", response_model=SeguroResponse)
def get_seguro(
    seguro_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific insurance policy."""
    seguro = db.query(Seguro).filter(Seguro.id == seguro_id).first()
    if not seguro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Seguro não encontrado"
        )
    return seguro


@router.put("/{seguro_id}", response_model=SeguroResponse)
def update_seguro(
    seguro_id: int,
    seguro_data: SeguroUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an insurance policy."""
    seguro = db.query(Seguro).filter(Seguro.id == seguro_id).first()
    if not seguro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Seguro não encontrado"
        )

    update_data = seguro_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(seguro, key, value)

    db.commit()
    db.refresh(seguro)
    return seguro


@router.get("/{seguro_id}/parcelas", response_model=List[ParcelaResponse])
def get_seguro_parcelas(
    seguro_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get installments for an insurance policy."""
    seguro = db.query(Seguro).filter(Seguro.id == seguro_id).first()
    if not seguro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Seguro não encontrado"
        )

    parcelas = db.query(ParcelaSeguro).filter(
        ParcelaSeguro.seguro_id == seguro_id
    ).all()
    return parcelas


@router.post("/{parcela_id}/pagar")
def pagar_parcela(
    parcela_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark an installment as paid."""
    parcela = db.query(ParcelaSeguro).filter(ParcelaSeguro.id == parcela_id).first()
    if not parcela:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Parcela não encontrada"
        )

    parcela.status = "pago"
    parcela.data_pagamento = datetime.now().date()
    db.commit()
    db.refresh(parcela)
    return parcela


@router.get("/vencendo/proximos")
def get_seguros_vencendo(
    dias: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get insurance policies expiring soon."""
    from datetime import timedelta

    agora = date.today()
    fim = agora + timedelta(days=dias)

    seguros = db.query(Seguro).filter(
        (Seguro.data_fim.between(agora, fim)) & (Seguro.status == "ativo")
    ).all()
    return seguros


@router.get("/resumo")
def get_seguros_resumo(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get insurance summary."""
    total_seguros = db.query(Seguro).count()
    seguros_ativos = db.query(Seguro).filter(Seguro.status == "ativo").count()
    total_valor = sum(float(s.valor) for s in db.query(Seguro).all() if s.valor)

    return {
        "total_seguros": total_seguros,
        "seguros_ativos": seguros_ativos,
        "total_valor": total_valor,
    }


@router.delete("/{seguro_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_seguro(
    seguro_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an insurance policy."""
    seguro = db.query(Seguro).filter(Seguro.id == seguro_id).first()
    if not seguro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Seguro não encontrado"
        )
    db.delete(seguro)
    db.commit()
