import math
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import get_current_user, require_page_access
from app.core.pagination import paginate
from app.models import CheckinCheckout, Cliente, Contrato, Reserva, Veiculo
from app.models.user import User


router = APIRouter(
    prefix="/reservas",
    tags=["Reservas"],
    dependencies=[Depends(require_page_access("reservas"))],
)


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


class ReservaConvertRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    valor_diaria: float
    tipo: Optional[str] = "cliente"
    hora_saida: Optional[str] = None
    combustivel_saida: Optional[str] = None
    km_livres: Optional[float] = None
    valor_km_excedente: Optional[float] = None
    desconto: Optional[float] = None
    observacoes: Optional[str] = None


class ReservaConvertResponse(BaseModel):
    id: int
    numero: str
    status: str
    valor_total: float


def _normalize_reserva_status(status_value: Optional[str]) -> Optional[str]:
    status_map = {
        "ativa": "pendente",
        "pendente": "pendente",
        "confirmada": "confirmada",
        "convertida": "convertida",
        "cancelada": "cancelada",
    }
    return status_map.get(status_value, status_value)


def _generate_numero_contrato_reserva(reserva_id: int) -> str:
    return "CTR-RES-{}-{}".format(reserva_id, datetime.now().strftime("%Y%m%d%H%M%S"))


def _calcular_qtd_diarias(data_inicio: datetime, data_fim: datetime) -> int:
    total_seconds = max((data_fim - data_inicio).total_seconds(), 0)
    return max(1, math.ceil(total_seconds / 86400))


def _verificar_conflitos_periodo(
    db: Session,
    veiculo_id: int,
    data_inicio: datetime,
    data_fim: datetime,
    excluir_reserva_id: Optional[int] = None,
):
    """Check schedule conflicts with active reservations and contracts."""
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
            detail="Veiculo ja reservado no periodo (reserva #{})".format(conflito_reserva.id),
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
            detail="Veiculo possui contrato ativo no periodo (contrato #{})".format(conflito_contrato.numero),
        )


@router.get("/")
def list_reservas(
    page: int = 1,
    limit: int = 50,
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List reservations with pagination."""
    del current_user
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
    """Get reservation calendar data."""
    del current_user
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
    """Create a reservation."""
    del current_user
    if reserva.data_inicio >= reserva.data_fim:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Data de inicio deve ser anterior a data de fim",
        )

    cliente = db.query(Cliente).filter(Cliente.id == reserva.cliente_id).first()
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente nao encontrado",
        )

    veiculo = db.query(Veiculo).filter(Veiculo.id == reserva.veiculo_id).first()
    if not veiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Veiculo nao encontrado",
        )

    _verificar_conflitos_periodo(db, reserva.veiculo_id, reserva.data_inicio, reserva.data_fim)

    db_reserva = Reserva(**reserva.model_dump())
    db.add(db_reserva)

    # Mark vehicle as reserved if currently available
    if veiculo.status == "disponivel":
        veiculo.status = "reservado"

    db.commit()
    db.refresh(db_reserva)
    return db_reserva


@router.get("/{reserva_id}", response_model=ReservaResponse)
def get_reserva(
    reserva_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single reservation."""
    del current_user
    reserva = db.query(Reserva).filter(Reserva.id == reserva_id).first()
    if not reserva:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reserva nao encontrada",
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
    del current_user
    reserva = db.query(Reserva).filter(Reserva.id == reserva_id).first()
    if not reserva:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reserva nao encontrada",
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
                detail="Data de inicio deve ser anterior a data de fim",
            )
        _verificar_conflitos_periodo(
            db,
            reserva.veiculo_id,
            new_inicio,
            new_fim,
            excluir_reserva_id=reserva_id,
        )

    old_status = reserva.status
    for key, value in update_data.items():
        setattr(reserva, key, value)

    # Free vehicle when reservation is canceled or completed
    if reserva.status in ("cancelada", "concluida") and old_status not in ("cancelada", "concluida"):
        veiculo = db.query(Veiculo).filter(Veiculo.id == reserva.veiculo_id).first()
        if veiculo and veiculo.status == "reservado":
            # Only free if no other active reservations for this vehicle
            other_active = db.query(Reserva).filter(
                Reserva.veiculo_id == reserva.veiculo_id,
                Reserva.id != reserva_id,
                Reserva.status.in_(["pendente", "confirmada"]),
            ).first()
            if not other_active:
                veiculo.status = "disponivel"

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
    del current_user
    reserva = db.query(Reserva).filter(Reserva.id == reserva_id).first()
    if not reserva:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reserva nao encontrada",
        )

    if reserva.status == "convertida":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reserva ja foi convertida em contrato",
        )

    if reserva.status == "cancelada":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reserva cancelada nao pode ser confirmada",
        )

    _verificar_conflitos_periodo(
        db,
        reserva.veiculo_id,
        reserva.data_inicio,
        reserva.data_fim,
        excluir_reserva_id=reserva_id,
    )

    reserva.status = "confirmada"
    db.commit()
    db.refresh(reserva)
    return reserva


@router.post("/{reserva_id}/converter", response_model=ReservaConvertResponse)
def converter_para_contrato(
    reserva_id: int,
    payload: ReservaConvertRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Convert a confirmed reservation into an active contract."""
    del current_user
    reserva = db.query(Reserva).filter(Reserva.id == reserva_id).first()
    if not reserva:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reserva nao encontrada",
        )

    if reserva.status != "confirmada":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apenas reservas confirmadas podem ser convertidas",
        )

    cliente = db.query(Cliente).filter(Cliente.id == reserva.cliente_id).first()
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente nao encontrado",
        )

    veiculo = db.query(Veiculo).filter(Veiculo.id == reserva.veiculo_id).first()
    if not veiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Veiculo nao encontrado",
        )

    _verificar_conflitos_periodo(
        db,
        reserva.veiculo_id,
        reserva.data_inicio,
        reserva.data_fim,
        excluir_reserva_id=reserva_id,
    )

    if veiculo.status not in {"disponivel", "reservado"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Veiculo nao esta disponivel para conversao",
        )

    qtd_diarias = _calcular_qtd_diarias(reserva.data_inicio, reserva.data_fim)
    valor_total = round(
        max((qtd_diarias * float(payload.valor_diaria or 0)) - float(payload.desconto or 0), 0),
        2,
    )

    observacoes = "[Reserva #{}] Conversao de reserva confirmada".format(reserva.id)
    if payload.observacoes:
        observacoes = "{}\n{}".format(observacoes, payload.observacoes.strip())

    contrato = Contrato(
        numero=_generate_numero_contrato_reserva(reserva_id),
        cliente_id=reserva.cliente_id,
        veiculo_id=reserva.veiculo_id,
        data_inicio=reserva.data_inicio,
        data_fim=reserva.data_fim,
        km_inicial=float(veiculo.km_atual or 0),
        valor_diaria=payload.valor_diaria,
        valor_total=valor_total,
        status="ativo",
        hora_saida=payload.hora_saida,
        combustivel_saida=payload.combustivel_saida,
        km_livres=payload.km_livres,
        qtd_diarias=qtd_diarias,
        valor_km_excedente=payload.valor_km_excedente,
        desconto=payload.desconto,
        tipo=(payload.tipo or "cliente").lower(),
        observacoes=observacoes,
    )
    db.add(contrato)
    db.flush()

    db.add(
        CheckinCheckout(
            contrato_id=contrato.id,
            tipo="retirada",
            km=contrato.km_inicial,
            nivel_combustivel=contrato.combustivel_saida,
            itens_checklist=veiculo.checklist or {},
        )
    )
    reserva.status = "convertida"
    veiculo.status = "alugado"

    db.commit()
    db.refresh(contrato)
    return {
        "id": contrato.id,
        "numero": contrato.numero,
        "status": contrato.status,
        "valor_total": float(contrato.valor_total or 0),
    }


@router.delete("/{reserva_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reserva(
    reserva_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a reservation."""
    del current_user
    reserva = db.query(Reserva).filter(Reserva.id == reserva_id).first()
    if not reserva:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reserva nao encontrada",
        )
    db.delete(reserva)
    db.commit()
