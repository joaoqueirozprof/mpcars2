from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.pagination import paginate
from app.models import Cliente, Contrato, Reserva, Veiculo
from app.models.user import User


router = APIRouter(prefix="/reservas", tags=["Reservas"])


class ReservaBase(BaseModel):
    model_config = ConfigDict(extra="ignore")

    cliente_id: int
    veiculo_id: int
    data_inicio: datetime
    data_fim: datetime
    valor_estimado: Optional[float] = None


class ReservaCreate(ReservaBase):
    pass


class ReservaUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    data_inicio: Optional[datetime] = None
    data_fim: Optional[datetime] = None
    status: Optional[str] = None
    valor_estimado: Optional[float] = None


class ReservaResponse(ReservaBase):
    id: int
    status: str

    class Config:
        from_attributes = True


def _normalize_reserva_status(status_value: Optional[str]) -> Optional[str]:
    status_map = {
        "ativa": "pendente",
        "pendente": "pendente",
        "confirmada": "confirmada",
        "convertida": "convertida",
        "cancelada": "cancelada",
    }
    return status_map.get(status_value, status_value)


def _verificar_conflitos_periodo(
    db: Session,
    veiculo_id: int,
    data_inicio: datetime,
    data_fim: datetime,
    excluir_reserva_id: Optional[int] = None,
):
    """Verifica conflitos com reservas e contratos ativos no período."""
    query_reservas = db.query(Reserva).filter(
        (Reserva.veiculo_id == veiculo_id)
        & (Reserva.data_inicio <= data_fim)
        & (Reserva.data_fim >= data_inicio)
        & (Reserva.status.in_(["pendente", "confirmada"]))
    )
    if excluir_reserva_id:
        query_reservas = query_reservas.filter(Reserva.id != excluir_reserva_id)

    conflito_reserva = query_reservas.first()
    if conflito_reserva:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Veículo já reservado no período (reserva #{})".format(conflito_reserva.id),
        )

    conflito_contrato = db.query(Contrato).filter(
        (Contrato.veiculo_id == veiculo_id)
        & (Contrato.data_inicio <= data_fim)
        & (Contrato.data_fim >= data_inicio)
        & (Contrato.status == "ativo")
    ).first()
    if conflito_contrato:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Veículo possui contrato ativo no período (contrato #{})".format(conflito_contrato.numero),
        )


@router.get("/")
def list_reservas(
    page: int = 1,
    limit: int = 50,
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all reservations with pagination."""
    query = db.query(Reserva).options(joinedload(Reserva.cliente), joinedload(Reserva.veiculo))

    status_normalizado = _normalize_reserva_status(status_filter)
    if status_filter == "ativa":
        query = query.filter(Reserva.status.in_(["pendente", "confirmada"]))
        status_normalizado = None

    return paginate(
        query=query,
        page=page,
        limit=limit,
        model=Reserva,
        status_filter=status_normalizado,
    )


@router.get("/agenda")
def get_agenda_reservas(
    veiculo_id: Optional[int] = None,
    cliente_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get reservations calendar/agenda."""
    query = db.query(Reserva)
    if veiculo_id:
        query = query.filter(Reserva.veiculo_id == veiculo_id)
    if cliente_id:
        query = query.filter(Reserva.cliente_id == cliente_id)
    return query.all()


@router.post("/", response_model=ReservaResponse)
def create_reserva(
    reserva: ReservaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new reservation."""
    if reserva.data_inicio >= reserva.data_fim:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Data de início deve ser anterior à data de fim",
        )

    cliente = db.query(Cliente).filter(Cliente.id == reserva.cliente_id).first()
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado"
        )

    veiculo = db.query(Veiculo).filter(Veiculo.id == reserva.veiculo_id).first()
    if not veiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Veículo não encontrado"
        )

    _verificar_conflitos_periodo(db, reserva.veiculo_id, reserva.data_inicio, reserva.data_fim)

    db_reserva = Reserva(**reserva.model_dump())
    db.add(db_reserva)
    db.commit()
    db.refresh(db_reserva)
    return db_reserva


@router.get("/{reserva_id}", response_model=ReservaResponse)
def get_reserva(
    reserva_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific reservation."""
    reserva = db.query(Reserva).filter(Reserva.id == reserva_id).first()
    if not reserva:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reserva não encontrada"
        )
    return reserva


@router.put("/{reserva_id}", response_model=ReservaResponse)
@router.patch("/{reserva_id}", response_model=ReservaResponse)
def update_reserva(
    reserva_id: int,
    reserva_data: ReservaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a reservation."""
    reserva = db.query(Reserva).filter(Reserva.id == reserva_id).first()
    if not reserva:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reserva não encontrada"
        )

    update_data = reserva_data.model_dump(exclude_unset=True)
    if "status" in update_data:
        update_data["status"] = _normalize_reserva_status(update_data["status"])

    new_inicio = update_data.get("data_inicio", reserva.data_inicio)
    new_fim = update_data.get("data_fim", reserva.data_fim)
    if "data_inicio" in update_data or "data_fim" in update_data:
        if new_inicio >= new_fim:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Data de início deve ser anterior à data de fim",
            )
        _verificar_conflitos_periodo(
            db,
            reserva.veiculo_id,
            new_inicio,
            new_fim,
            excluir_reserva_id=reserva_id,
        )

    for key, value in update_data.items():
        setattr(reserva, key, value)

    db.commit()
    db.refresh(reserva)
    return reserva


@router.post("/{reserva_id}/confirmar")
def confirmar_reserva(
    reserva_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Confirm a reservation."""
    reserva = db.query(Reserva).filter(Reserva.id == reserva_id).first()
    if not reserva:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reserva não encontrada"
        )

    reserva.status = "confirmada"
    db.commit()
    db.refresh(reserva)
    return reserva


@router.post("/{reserva_id}/converter")
def converter_para_contrato(
    reserva_id: int,
    valor_diaria: float,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Convert a reservation to a contract."""
    reserva = db.query(Reserva).filter(Reserva.id == reserva_id).first()
    if not reserva:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reserva não encontrada"
        )

    if reserva.status != "confirmada":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apenas reservas confirmadas podem ser convertidas",
        )

    dias = max(1, (reserva.data_fim - reserva.data_inicio).days)
    valor_total = round(dias * valor_diaria, 2)

    contrato = Contrato(
        numero="RES-{}-{}".format(reserva_id, datetime.now().strftime("%Y%m%d%H%M%S")),
        cliente_id=reserva.cliente_id,
        veiculo_id=reserva.veiculo_id,
        data_inicio=reserva.data_inicio,
        data_fim=reserva.data_fim,
        valor_diaria=valor_diaria,
        valor_total=valor_total,
        status="ativo",
    )
    db.add(contrato)
    reserva.status = "convertida"

    veiculo = db.query(Veiculo).filter(Veiculo.id == reserva.veiculo_id).first()
    if veiculo:
        veiculo.status = "alugado"

    db.commit()
    db.refresh(contrato)
    return contrato


@router.delete("/{reserva_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reserva(
    reserva_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a reservation."""
    reserva = db.query(Reserva).filter(Reserva.id == reserva_id).first()
    if not reserva:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reserva não encontrada"
        )
    db.delete(reserva)
    db.commit()
