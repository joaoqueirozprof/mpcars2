from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func as sqlfunc
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime, timedelta
from app.core.database import get_db
from app.core.deps import get_current_user, require_page_access
from app.core.pagination import paginate
from app.models.user import User
from app.models import Seguro, ParcelaSeguro, Veiculo


router = APIRouter(
    prefix="/seguros",
    tags=["Seguros"],
    dependencies=[Depends(require_page_access("seguros"))],
)


class ParcelaInput(BaseModel):
    valor: float
    vencimento: date


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
    parcelas: Optional[List[ParcelaInput]] = None


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


def _sync_seguro_status(db: Session, seguro_id: int):
    """Sincroniza o status do seguro baseado nas parcelas.

    CORRIGIDO: Quando todas as parcelas estão pagas, o seguro
    deve refletir isso. Também verifica vencimento.
    """
    seguro = db.query(Seguro).filter(Seguro.id == seguro_id).first()
    if not seguro:
        return

    total_parcelas = db.query(sqlfunc.count(ParcelaSeguro.id)).filter(
        ParcelaSeguro.seguro_id == seguro_id
    ).scalar() or 0

    parcelas_pagas = db.query(sqlfunc.count(ParcelaSeguro.id)).filter(
        ParcelaSeguro.seguro_id == seguro_id,
        ParcelaSeguro.status == "pago",
    ).scalar() or 0

    if total_parcelas > 0 and parcelas_pagas == total_parcelas:
        # Todas as parcelas pagas
        if seguro.data_fim and seguro.data_fim < date.today():
            seguro.status = "vencido"
        else:
            seguro.status = "ativo"  # Parcelas pagas, ainda vigente
    elif seguro.data_fim and seguro.data_fim < date.today():
        seguro.status = "vencido"


# === Fixed path routes FIRST (before /{seguro_id}) ===


@router.get("/")
def list_seguros(
    page: int = 1,
    limit: int = 50,
    search: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
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
        status_filter=status_filter,
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

    # Validar datas
    if seguro.data_inicio >= seguro.data_fim:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Data de início deve ser anterior à data de fim",
        )

    existing = db.query(Seguro).filter(
        Seguro.numero_apolice == seguro.numero_apolice
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Número de apólice já cadastrado",
        )

    db_seguro = Seguro(**seguro.model_dump(exclude={'parcelas'}))
    db.add(db_seguro)
    db.commit()
    db.refresh(db_seguro)

    # Create installments - use client-specified parcelas if provided
    if seguro.parcelas and len(seguro.parcelas) > 0:
        for i, p in enumerate(seguro.parcelas, 1):
            parcela = ParcelaSeguro(
                seguro_id=db_seguro.id,
                veiculo_id=seguro.veiculo_id,
                numero_parcela=i,
                valor=p.valor,
                vencimento=p.vencimento,
            )
            db.add(parcela)
    else:
        # Auto-calculate parcelas
        qtd = seguro.qtd_parcelas if seguro.qtd_parcelas and seguro.qtd_parcelas > 0 else 1
        dias_entre = (seguro.data_fim - seguro.data_inicio).days
        dias_por_parcela = max(1, dias_entre // qtd)
        valor_parcela = round(seguro.valor / qtd, 2)

        for i in range(1, qtd + 1):
            vencimento = seguro.data_inicio + timedelta(days=dias_por_parcela * i)
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


@router.get("/vencendo/proximos")
def get_seguros_vencendo(
    dias: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get insurance policies expiring soon."""
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
    """Get insurance summary - using SQL SUM instead of Python loops."""
    total_seguros = db.query(sqlfunc.count(Seguro.id)).scalar() or 0
    seguros_ativos = db.query(sqlfunc.count(Seguro.id)).filter(Seguro.status == "ativo").scalar() or 0
    total_valor = float(db.query(
        sqlfunc.coalesce(sqlfunc.sum(Seguro.valor), 0)
    ).scalar())

    # Adicionar info de parcelas pendentes
    parcelas_pendentes = db.query(sqlfunc.count(ParcelaSeguro.id)).filter(
        ParcelaSeguro.status == "pendente"
    ).scalar() or 0
    valor_parcelas_pendentes = float(db.query(
        sqlfunc.coalesce(sqlfunc.sum(ParcelaSeguro.valor), 0)
    ).filter(ParcelaSeguro.status == "pendente").scalar())

    return {
        "total_seguros": total_seguros,
        "seguros_ativos": seguros_ativos,
        "total_valor": total_valor,
        "parcelas_pendentes": parcelas_pendentes,
        "valor_parcelas_pendentes": valor_parcelas_pendentes,
    }


# === Parameterized routes AFTER fixed paths ===


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


@router.patch("/{seguro_id}", response_model=SeguroResponse)
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
    ).order_by(ParcelaSeguro.numero_parcela).all()
    return parcelas


@router.post("/{parcela_id}/pagar")
def pagar_parcela(
    parcela_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark an installment as paid.

    CORRIGIDO: Agora sincroniza o status do seguro pai quando
    todas as parcelas estão pagas.
    """
    parcela = db.query(ParcelaSeguro).filter(ParcelaSeguro.id == parcela_id).first()
    if not parcela:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Parcela não encontrada"
        )

    parcela.status = "pago"
    parcela.data_pagamento = datetime.now().date()

    # Sync status do seguro pai
    _sync_seguro_status(db, parcela.seguro_id)

    db.commit()
    db.refresh(parcela)
    return parcela


@router.delete("/{seguro_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_seguro(
    seguro_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an insurance policy.

    CORRIGIDO: Com CASCADE configurado, as parcelas são deletadas automaticamente.
    """
    seguro = db.query(Seguro).filter(Seguro.id == seguro_id).first()
    if not seguro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Seguro não encontrado"
        )
    db.query(ParcelaSeguro).filter(
        ParcelaSeguro.seguro_id == seguro_id
    ).delete(synchronize_session=False)
    db.delete(seguro)
    db.commit()
