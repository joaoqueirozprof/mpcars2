from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.pagination import paginate
from app.models.user import User
from app.models import Reserva, Cliente, Veiculo, Contrato


router = APIRouter(prefix="/reservas", tags=["Reservas"])


class ReservaBase(BaseModel):
    cliente_id: int
    veiculo_id: int
    data_inicio: datetime
    data_fim: datetime
    valor_estimado: Optional[float] = None


class ReservaCreate(ReservaBase):
    pass


class ReservaUpdate(BaseModel):
    data_inicio: Optional[datetime] = None
    data_fim: Optional[datetime] = None
    status: Optional[str] = None
    valor_estimado: Optional[float] = None


class ReservaResponse(ReservaBase):
    id: int
    status: str

    class Config:
        from_attributes = True


@router.get("/")
def list_reservas(
    page: int = 1,
    limit: int = 50,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all reservations with pagination."""
    query = db.query(Reserva).options(joinedload(Reserva.cliente), joinedload(Reserva.veiculo))
    return paginate(
        query=query,
        page=page,
        limit=limit,
        model=Reserva,
        status_filter=status,
    )


@router.post("/", response_model=ReservaResponse)
def create_reserva(
    reserva: ReservaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new reservation."""
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

    # Check if vehicle is available in the period
    conflitos = db.query(Reserva).filter(
        (Reserva.veiculo_id == reserva.veiculo_id)
        & (Reserva.data_inicio <= reserva.data_fim)
        & (Reserva.data_fim >= reserva.data_inicio)
        & (Reserva.status.in_(["pendente", "confirmada"]))
    ).all()

    if conflitos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Veículo não disponível no período selecionado",
        )

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

    # Calculate days and total value
    dias = (reserva.data_fim - reserva.data_inicio).days
    valor_total = dias * valor_diaria

    # Create contract
    contrato = Contrato(
        numero=f"RES-{reserva_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
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

    db.commit()
    db.refresh(contrato)
    return contrato


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

    reservas = query.all()
    return reservas


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
