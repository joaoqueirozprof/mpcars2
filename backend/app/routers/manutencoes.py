from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import case, func as sqlfunc
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.pagination import paginate
from app.models import Manutencao, Veiculo
from app.models.user import User


router = APIRouter(prefix="/manutencoes", tags=["Manutenções"])


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
    db.commit()
    db.refresh(db_manutencao)
    return db_manutencao


@router.get("/pendentes")
def get_manutencoes_pendentes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get pending maintenance records."""
    return db.query(Manutencao).filter(Manutencao.status == "pendente").all()


@router.get("/resumo")
def get_manutencoes_resumo(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get maintenance summary."""
    agora = datetime.now().date()

    result = db.query(
        sqlfunc.count(Manutencao.id).label("total"),
        sqlfunc.count(
            case((Manutencao.status == "pendente", 1))
        ).label("pendentes"),
        sqlfunc.coalesce(sqlfunc.sum(Manutencao.custo), 0).label("total_custo"),
        sqlfunc.count(
            case(
                (
                    (Manutencao.data_proxima.isnot(None))
                    & (Manutencao.data_proxima.between(agora, agora + timedelta(days=30)))
                    & (Manutencao.status == "pendente"),
                    1,
                )
            )
        ).label("vencendo_30d"),
    ).first()

    return {
        "total_manutencoes": result.total or 0,
        "manutencoes_pendentes": result.pendentes or 0,
        "total_custo": float(result.total_custo or 0),
        "vencendo_em_30_dias": result.vencendo_30d or 0,
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
        & (Manutencao.status == "pendente")
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
    manutencao = db.query(Manutencao).filter(Manutencao.id == manutencao_id).first()
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
    manutencao = db.query(Manutencao).filter(Manutencao.id == manutencao_id).first()
    if not manutencao:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Manutenção não encontrada"
        )

    update_data = _normalize_manutencao_payload(manutencao_data.model_dump(exclude_unset=True))
    for key, value in update_data.items():
        setattr(manutencao, key, value)

    db.commit()
    db.refresh(manutencao)
    return manutencao


@router.post("/{manutencao_id}/completar")
def completar_manutencao(
    manutencao_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark maintenance as completed."""
    manutencao = db.query(Manutencao).filter(Manutencao.id == manutencao_id).first()
    if not manutencao:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Manutenção não encontrada"
        )

    manutencao.status = "concluida"
    manutencao.data_realizada = datetime.now().date()
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
    db.delete(manutencao)
    db.commit()
