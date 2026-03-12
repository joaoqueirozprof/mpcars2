from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import case, func as sqlfunc
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import get_current_user, require_page_access
from app.core.pagination import paginate
from app.models import Contrato, Manutencao, Veiculo
from app.models.user import User


router = APIRouter(
    prefix="/manutencoes",
    tags=["Manutenções"],
    dependencies=[Depends(require_page_access("manutencoes"))],
)


OPEN_MAINTENANCE_STATUSES = {"pendente", "agendada", "em_andamento"}
URGENCY_RANK = {"info": 0, "atencao": 1, "critica": 2}


class ManutencaoBase(BaseModel):
    model_config = ConfigDict(extra="ignore")

    veiculo_id: int
    tipo: str
    descricao: str
    km_realizada: Optional[float] = None
    km_proxima: Optional[float] = None
    data_realizada: Optional[date] = None
    data_proxima: Optional[date] = None
    custo: Optional[float] = None
    oficina: Optional[str] = None
    data_manutencao: Optional[date] = None
    valor: Optional[float] = None
    quilometragem: Optional[float] = None
    status: Optional[str] = None


class ManutencaoCreate(ManutencaoBase):
    pass


class ManutencaoUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    tipo: Optional[str] = None
    descricao: Optional[str] = None
    data_realizada: Optional[date] = None
    data_proxima: Optional[date] = None
    custo: Optional[float] = None
    km_realizada: Optional[float] = None
    km_proxima: Optional[float] = None
    oficina: Optional[str] = None
    status: Optional[str] = None
    data_manutencao: Optional[date] = None
    valor: Optional[float] = None
    quilometragem: Optional[float] = None


class ManutencaoResponse(ManutencaoBase):
    id: int
    status: str

    class Config:
        from_attributes = True


def _normalize_manutencao_status(status_value: Optional[str]) -> Optional[str]:
    status_map = {
        "em_progresso": "em_andamento",
        "pendente": "pendente",
        "concluida": "concluida",
        "cancelada": "cancelada",
        "agendada": "agendada",
    }
    return status_map.get(status_value, status_value)


def _normalize_manutencao_payload(payload: dict) -> dict:
    data = dict(payload)

    data_manutencao = data.pop("data_manutencao", None)
    if data.get("data_realizada") in (None, "") and data_manutencao is not None:
        data["data_realizada"] = data_manutencao
    if data.get("data_proxima") in (None, "") and data_manutencao is not None:
        data["data_proxima"] = data_manutencao

    valor = data.pop("valor", None)
    if data.get("custo") in (None, "") and valor is not None:
        data["custo"] = valor

    quilometragem = data.pop("quilometragem", None)
    if data.get("km_realizada") in (None, "") and quilometragem is not None:
        data["km_realizada"] = quilometragem
    if data.get("km_proxima") in (None, "") and quilometragem is not None:
        data["km_proxima"] = quilometragem

    if "status" in data:
        data["status"] = _normalize_manutencao_status(data["status"])

    normalized = {}
    for key, value in data.items():
        normalized[key] = None if value == "" else value

    return normalized


def _is_open_maintenance(status_value: Optional[str]) -> bool:
    normalized = _normalize_manutencao_status(status_value)
    return normalized in OPEN_MAINTENANCE_STATUSES


def _resolve_maintenance_urgency(
    manutencao: Manutencao,
    *,
    reference_date: Optional[date] = None,
) -> tuple[str, Optional[int], Optional[float]]:
    today = reference_date or datetime.now().date()
    urgency = "info"
    dias_restantes = None
    km_restante = None

    if not _is_open_maintenance(manutencao.status):
        return urgency, dias_restantes, km_restante

    if manutencao.data_proxima:
        dias_restantes = (manutencao.data_proxima - today).days
        if dias_restantes < 0:
            urgency = "critica"
        elif dias_restantes <= 7 and URGENCY_RANK[urgency] < URGENCY_RANK["atencao"]:
            urgency = "atencao"

    if manutencao.km_proxima is not None and manutencao.veiculo:
        km_atual = float(manutencao.veiculo.km_atual or 0)
        km_restante = float(manutencao.km_proxima or 0) - km_atual
        if km_restante <= 0:
            urgency = "critica"
        elif km_restante <= 500 and URGENCY_RANK[urgency] < URGENCY_RANK["atencao"]:
            urgency = "atencao"

    return urgency, dias_restantes, km_restante


def _serialize_manutencao_alerta(
    manutencao: Manutencao,
    *,
    reference_date: Optional[date] = None,
) -> Optional[dict]:
    if not _is_open_maintenance(manutencao.status):
        return None

    today = reference_date or datetime.now().date()
    urgency, dias_restantes, km_restante = _resolve_maintenance_urgency(
        manutencao,
        reference_date=today,
    )
    placa = manutencao.veiculo.placa if manutencao.veiculo else "Veiculo"
    km_atual = float(manutencao.veiculo.km_atual or 0) if manutencao.veiculo else None

    details = []
    if dias_restantes is not None:
        if dias_restantes < 0:
            details.append("atrasada ha {} dia(s)".format(abs(dias_restantes)))
        elif dias_restantes == 0:
            details.append("vence hoje")
        else:
            details.append("vence em {} dia(s)".format(dias_restantes))

    if km_restante is not None:
        if km_restante <= 0:
            details.append("km vencido em {}".format(abs(int(round(km_restante)))))
        else:
            details.append("faltam {} km".format(int(round(km_restante))))

    if not details:
        details.append("ordem aberta aguardando programacao")

    return {
        "id": str(manutencao.id),
        "tipo": "manutencao",
        "titulo": "{} - {}".format(manutencao.descricao or "Manutencao", placa),
        "descricao": " | ".join(details),
        "urgencia": urgency,
        "status": manutencao.status,
        "placa": placa,
        "oficina": manutencao.oficina,
        "data_proxima": manutencao.data_proxima.isoformat() if manutencao.data_proxima else None,
        "km_proxima": float(manutencao.km_proxima) if manutencao.km_proxima is not None else None,
        "km_atual": km_atual,
        "km_restante": km_restante,
        "dias_restantes": dias_restantes,
        "rota": "/manutencoes",
    }


def _sync_vehicle_maintenance_status(db: Session, veiculo: Optional[Veiculo]) -> None:
    if not veiculo or veiculo.status == "inativo":
        return

    has_open_maintenance = (
        db.query(Manutencao.id)
        .filter(
            Manutencao.veiculo_id == veiculo.id,
            Manutencao.status.in_(tuple(OPEN_MAINTENANCE_STATUSES)),
        )
        .first()
        is not None
    )

    has_active_contract = (
        db.query(Contrato.id)
        .filter(Contrato.veiculo_id == veiculo.id, Contrato.status == "ativo")
        .first()
        is not None
    )

    if has_open_maintenance:
        if veiculo.status != "alugado":
            veiculo.status = "manutencao"
        return

    if veiculo.status == "manutencao":
        veiculo.status = "alugado" if has_active_contract else "disponivel"


@router.get("/")
def list_manutencoes(
    page: int = 1,
    limit: int = 50,
    search: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    tipo: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all maintenance records with pagination."""
    query = db.query(Manutencao).options(joinedload(Manutencao.veiculo))
    extra = {}
    if tipo:
        extra["tipo"] = tipo

    status_normalizado = _normalize_manutencao_status(status_filter)

    return paginate(
        query=query,
        page=page,
        limit=limit,
        search=search,
        search_fields=["descricao", "oficina"],
        model=Manutencao,
        status_filter=status_normalizado,
        extra_filters=extra if extra else None,
    )


@router.post("/", response_model=ManutencaoResponse)
def create_manutencao(
    manutencao: ManutencaoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new maintenance record."""
    manutencao_data = _normalize_manutencao_payload(manutencao.model_dump(exclude_unset=True))

    veiculo = db.query(Veiculo).filter(Veiculo.id == manutencao_data["veiculo_id"]).first()
    if not veiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Veículo não encontrado"
        )

    db_manutencao = Manutencao(**manutencao_data)
    db.add(db_manutencao)
    db.flush()
    _sync_vehicle_maintenance_status(db, veiculo)
    db.commit()
    db.refresh(db_manutencao)
    return db_manutencao


@router.get("/pendentes")
def get_manutencoes_pendentes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get pending maintenance records."""
    return (
        db.query(Manutencao)
        .filter(Manutencao.status.in_(tuple(OPEN_MAINTENANCE_STATUSES)))
        .all()
    )


@router.get("/resumo")
def get_manutencoes_resumo(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get maintenance summary."""
    agora = datetime.now().date()
    manutencoes = (
        db.query(Manutencao)
        .options(joinedload(Manutencao.veiculo))
        .order_by(Manutencao.data_proxima.asc(), Manutencao.id.desc())
        .all()
    )
    alertas = [
        alerta
        for alerta in (
            _serialize_manutencao_alerta(manutencao, reference_date=agora)
            for manutencao in manutencoes
        )
        if alerta is not None
    ]
    alertas.sort(
        key=lambda alerta: (
            -URGENCY_RANK.get(alerta["urgencia"], 0),
            alerta["dias_restantes"] if alerta["dias_restantes"] is not None else 9999,
            alerta["km_restante"] if alerta["km_restante"] is not None else 999999,
        )
    )

    result = db.query(
        sqlfunc.count(Manutencao.id).label("total"),
        sqlfunc.count(
            case((Manutencao.status.in_(tuple(OPEN_MAINTENANCE_STATUSES)), 1))
        ).label("abertas"),
        sqlfunc.count(case((Manutencao.status == "pendente", 1))).label("pendentes"),
        sqlfunc.count(case((Manutencao.status == "agendada", 1))).label("agendadas"),
        sqlfunc.count(case((Manutencao.status == "em_andamento", 1))).label("em_andamento"),
        sqlfunc.coalesce(sqlfunc.sum(Manutencao.custo), 0).label("total_custo"),
        sqlfunc.count(
            case(
                (
                    (Manutencao.data_proxima.isnot(None))
                    & (Manutencao.data_proxima.between(agora, agora + timedelta(days=30)))
                    & (Manutencao.status.in_(tuple(OPEN_MAINTENANCE_STATUSES))),
                    1,
                )
            )
        ).label("vencendo_30d"),
        sqlfunc.count(
            case(
                (
                    (Manutencao.data_proxima.isnot(None))
                    & (Manutencao.data_proxima < agora)
                    & (Manutencao.status.in_(tuple(OPEN_MAINTENANCE_STATUSES))),
                    1,
                )
            )
        ).label("vencidas_data"),
    ).first()

    vencidas_por_km = sum(
        1
        for alerta in alertas
        if alerta["km_restante"] is not None and alerta["km_restante"] <= 0
    )
    criticas = sum(1 for alerta in alertas if alerta["urgencia"] == "critica")

    return {
        "total_manutencoes": result.total or 0,
        "manutencoes_abertas": result.abertas or 0,
        "manutencoes_pendentes": result.pendentes or 0,
        "manutencoes_agendadas": result.agendadas or 0,
        "manutencoes_em_andamento": result.em_andamento or 0,
        "total_custo": float(result.total_custo or 0),
        "vencendo_em_30_dias": result.vencendo_30d or 0,
        "vencidas_por_data": result.vencidas_data or 0,
        "vencidas_por_km": vencidas_por_km,
        "criticas": criticas,
        "alertas": alertas[:6],
    }


@router.get("/alerta-km/{veiculo_id}")
def get_alerta_km(
    veiculo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get kilometer alert for vehicle."""
    veiculo = db.query(Veiculo).filter(Veiculo.id == veiculo_id).first()
    if not veiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Veículo não encontrado"
        )

    km_atual = veiculo.km_atual or 0
    manutencoes = db.query(Manutencao).filter(
        (Manutencao.veiculo_id == veiculo_id)
        & (Manutencao.status.in_(tuple(OPEN_MAINTENANCE_STATUSES)))
        & (Manutencao.km_proxima.isnot(None))
        & (Manutencao.km_proxima <= km_atual)
    ).all()

    return [
        {
            "manutencao_id": manutencao.id,
            "tipo": manutencao.tipo,
            "km_prevista": manutencao.km_proxima,
            "km_atual": km_atual,
            "km_restante": manutencao.km_proxima - km_atual,
        }
        for manutencao in manutencoes
    ]


@router.get("/{manutencao_id}", response_model=ManutencaoResponse)
def get_manutencao(
    manutencao_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific maintenance record."""
    manutencao = (
        db.query(Manutencao)
        .options(joinedload(Manutencao.veiculo))
        .filter(Manutencao.id == manutencao_id)
        .first()
    )
    if not manutencao:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Manutenção não encontrada"
        )
    return manutencao


@router.put("/{manutencao_id}", response_model=ManutencaoResponse)
@router.patch("/{manutencao_id}", response_model=ManutencaoResponse)
def update_manutencao(
    manutencao_id: int,
    manutencao_data: ManutencaoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a maintenance record."""
    manutencao = (
        db.query(Manutencao)
        .options(joinedload(Manutencao.veiculo))
        .filter(Manutencao.id == manutencao_id)
        .first()
    )
    if not manutencao:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Manutenção não encontrada"
        )

    previous_vehicle = manutencao.veiculo
    update_data = _normalize_manutencao_payload(manutencao_data.model_dump(exclude_unset=True))
    for key, value in update_data.items():
        setattr(manutencao, key, value)

    if manutencao.status == "concluida" and manutencao.data_realizada is None:
        manutencao.data_realizada = datetime.now().date()

    current_vehicle = previous_vehicle
    if "veiculo_id" in update_data and update_data["veiculo_id"] != getattr(previous_vehicle, "id", None):
        current_vehicle = db.query(Veiculo).filter(Veiculo.id == manutencao.veiculo_id).first()

    if manutencao.km_realizada is not None and current_vehicle:
        current_vehicle.km_atual = max(
            float(current_vehicle.km_atual or 0),
            float(manutencao.km_realizada),
        )

    db.flush()
    _sync_vehicle_maintenance_status(db, previous_vehicle)
    if current_vehicle is not previous_vehicle:
        _sync_vehicle_maintenance_status(db, current_vehicle)

    db.commit()
    db.refresh(manutencao)
    return manutencao


@router.post("/{manutencao_id}/completar", response_model=ManutencaoResponse)
def completar_manutencao(
    manutencao_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark maintenance as completed."""
    manutencao = (
        db.query(Manutencao)
        .options(joinedload(Manutencao.veiculo))
        .filter(Manutencao.id == manutencao_id)
        .first()
    )
    if not manutencao:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Manutenção não encontrada"
        )

    manutencao.status = "concluida"
    manutencao.data_realizada = datetime.now().date()
    if manutencao.veiculo:
        manutencao.km_realizada = max(
            float(manutencao.km_realizada or 0),
            float(manutencao.veiculo.km_atual or 0),
        )
        manutencao.veiculo.km_atual = max(
            float(manutencao.veiculo.km_atual or 0),
            float(manutencao.km_realizada or 0),
        )
    db.flush()
    _sync_vehicle_maintenance_status(db, manutencao.veiculo)
    db.commit()
    db.refresh(manutencao)
    return manutencao


@router.delete("/{manutencao_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_manutencao(
    manutencao_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a maintenance record."""
    manutencao = db.query(Manutencao).filter(Manutencao.id == manutencao_id).first()
    if not manutencao:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Manutenção não encontrada"
        )
    veiculo = manutencao.veiculo
    db.delete(manutencao)
    db.flush()
    _sync_vehicle_maintenance_status(db, veiculo)
    db.commit()
