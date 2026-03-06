from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime, timedelta
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.pagination import paginate
from app.models.user import User
from app.models import IpvaAliquota, IpvaRegistro, Veiculo


router = APIRouter(prefix="/ipva", tags=["IPVA"])


class IpvaAliquotaBase(BaseModel):
    estado: str
    tipo_veiculo: str
    aliquota: float
    descricao: Optional[str] = None


class IpvaAliquotaCreate(IpvaAliquotaBase):
    pass


class IpvaAliquotaResponse(IpvaAliquotaBase):
    id: int

    class Config:
        from_attributes = True


class IpvaRegistroBase(BaseModel):
    veiculo_id: int
    ano_referencia: int
    valor_venal: float
    aliquota: float
    valor_ipva: float
    data_vencimento: date


class IpvaRegistroCreate(IpvaRegistroBase):
    pass


class IpvaRegistroUpdate(BaseModel):
    valor_pago: Optional[float] = None
    status: Optional[str] = None


class IpvaRegistroResponse(IpvaRegistroBase):
    id: int
    valor_pago: Optional[float] = None
    status: str

    class Config:
        from_attributes = True


@router.get("/aliquotas", response_model=List[IpvaAliquotaResponse])
def list_aliquotas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all IPVA rates."""
    aliquotas = db.query(IpvaAliquota).all()
    return aliquotas


@router.get("/aliquotas/{estado}/{tipo_veiculo}", response_model=IpvaAliquotaResponse)
def get_aliquota(
    estado: str,
    tipo_veiculo: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get IPVA rate for a specific state and vehicle type."""
    aliquota = db.query(IpvaAliquota).filter(
        (IpvaAliquota.estado == estado) & (IpvaAliquota.tipo_veiculo == tipo_veiculo)
    ).first()
    if not aliquota:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Alíquota não encontrada"
        )
    return aliquota


@router.post("/aliquotas", response_model=IpvaAliquotaResponse)
def create_aliquota(
    aliquota: IpvaAliquotaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new IPVA rate."""
    existing = db.query(IpvaAliquota).filter(
        (IpvaAliquota.estado == aliquota.estado)
        & (IpvaAliquota.tipo_veiculo == aliquota.tipo_veiculo)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Alíquota já cadastrada para este estado e tipo de veículo",
        )

    db_aliquota = IpvaAliquota(**aliquota.model_dump())
    db.add(db_aliquota)
    db.commit()
    db.refresh(db_aliquota)
    return db_aliquota


@router.get("/")
def list_ipva(
    page: int = 1,
    limit: int = 50,
    status: Optional[str] = None,
    veiculo_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all IPVA records with pagination (frontend endpoint)."""
    from sqlalchemy.orm import joinedload
    query = db.query(IpvaRegistro).options(joinedload(IpvaRegistro.veiculo))
    extra = {}
    if veiculo_id:
        extra["veiculo_id"] = veiculo_id
    return paginate(
        query=query,
        page=page,
        limit=limit,
        model=IpvaRegistro,
        status_filter=status,
        extra_filters=extra if extra else None,
    )


@router.get("/registros")
def list_registros(
    page: int = 1,
    limit: int = 50,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all IPVA records with pagination."""
    query = db.query(IpvaRegistro)
    return paginate(
        query=query,
        page=page,
        limit=limit,
        model=IpvaRegistro,
        status_filter=status,
    )


@router.post("/registros", response_model=IpvaRegistroResponse)
def create_registro(
    registro: IpvaRegistroCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new IPVA record."""
    veiculo = db.query(Veiculo).filter(Veiculo.id == registro.veiculo_id).first()
    if not veiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Veículo não encontrado"
        )

    db_registro = IpvaRegistro(**registro.model_dump())
    db.add(db_registro)
    db.commit()
    db.refresh(db_registro)
    return db_registro


@router.get("/registros/{registro_id}", response_model=IpvaRegistroResponse)
def get_registro(
    registro_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific IPVA record."""
    registro = db.query(IpvaRegistro).filter(IpvaRegistro.id == registro_id).first()
    if not registro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Registro IPVA não encontrado"
        )
    return registro


@router.put("/registros/{registro_id}", response_model=IpvaRegistroResponse)
def update_registro(
    registro_id: int,
    registro_data: IpvaRegistroUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an IPVA record."""
    registro = db.query(IpvaRegistro).filter(IpvaRegistro.id == registro_id).first()
    if not registro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Registro IPVA não encontrado"
        )

    update_data = registro_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(registro, key, value)

    db.commit()
    db.refresh(registro)
    return registro


@router.post("/registros/{registro_id}/pagar")
def pagar_ipva(
    registro_id: int,
    valor_pago: float,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark IPVA as paid."""
    registro = db.query(IpvaRegistro).filter(IpvaRegistro.id == registro_id).first()
    if not registro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Registro IPVA não encontrado"
        )

    registro.valor_pago = valor_pago
    registro.status = "pago"
    db.commit()
    db.refresh(registro)
    return registro


@router.get("/calcular/{veiculo_id}")
def calcular_ipva(
    veiculo_id: int,
    ano_referencia: int,
    valor_venal: float,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Calculate IPVA for a vehicle."""
    veiculo = db.query(Veiculo).filter(Veiculo.id == veiculo_id).first()
    if not veiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Veículo não encontrado"
        )

    # Get the state from vehicle (would need to be added to vehicle model)
    # For now, use a default state
    estado = "SP"
    tipo_veiculo = "Automovel"

    aliquota_obj = db.query(IpvaAliquota).filter(
        (IpvaAliquota.estado == estado)
        & (IpvaAliquota.tipo_veiculo == tipo_veiculo)
    ).first()

    if not aliquota_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alíquota não encontrada para este veículo",
        )

    aliquota = aliquota_obj.aliquota / 100
    valor_ipva = valor_venal * aliquota

    return {
        "veiculo_id": veiculo_id,
        "ano_referencia": ano_referencia,
        "valor_venal": valor_venal,
        "aliquota": aliquota_obj.aliquota,
        "valor_ipva": valor_ipva,
    }


@router.get("/vencendo")
def get_ipva_vencendo(
    dias: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get IPVA records expiring soon."""
    agora = date.today()
    fim = agora + timedelta(days=dias)

    registros = db.query(IpvaRegistro).filter(
        (IpvaRegistro.data_vencimento.between(agora, fim))
        & (IpvaRegistro.status == "pendente")
    ).all()
    return registros


@router.get("/resumo")
def get_resumo_ipva(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get IPVA summary."""
    total_registros = db.query(IpvaRegistro).count()
    registros_pendentes = db.query(IpvaRegistro).filter(
        IpvaRegistro.status == "pendente"
    ).count()
    total_valor = sum(float(r.valor_ipva) for r in db.query(IpvaRegistro).all())

    return {
        "total_registros": total_registros,
        "registros_pendentes": registros_pendentes,
        "total_valor": total_valor,
    }


@router.delete("/registros/{registro_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_registro(
    registro_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an IPVA record."""
    registro = db.query(IpvaRegistro).filter(IpvaRegistro.id == registro_id).first()
    if not registro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Registro IPVA não encontrado"
        )
    db.delete(registro)
    db.commit()
