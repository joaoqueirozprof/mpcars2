from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime, timedelta
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.pagination import paginate
from app.models.user import User
from app.models import Manutencao, Veiculo


router = APIRouter(prefix="/manutencoes", tags=["Manutenções"])


class ManutencaoBase(BaseModel):
    veiculo_id: int
    tipo: str
    descricao: str
    km_realizada: Optional[float] = None
    km_proxima: Optional[float] = None
    data_realizada: Optional[date] = None
    data_proxima: Optional[date] = None
    custo: Optional[float] = None
    oficina: Optional[str] = None


class ManutencaoCreate(ManutencaoBase):
    pass


class ManutencaoUpdate(BaseModel):
    tipo: Optional[str] = None
    descricao: Optional[str] = None
    data_realizada: Optional[date] = None
    data_proxima: Optional[date] = None
    custo: Optional[float] = None
    status: Optional[str] = None


class ManutencaoResponse(ManutencaoBase):
    id: int
    status: str

    class Config:
        from_attributes = True


@router.get("/")
def list_manutencoes(
    page: int = 1,
    limit: int = 50,
    search: Optional[str] = None,
    status: Optional[str] = None,
    tipo: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all maintenance records with pagination."""
    query = db.query(Manutencao).options(joinedload(Manutencao.veiculo))
    extra = {}
    if tipo:
        extra["tipo"] = tipo
    return paginate(
        query=query,
        page=page,
        limit=limit,
        search=search,
        search_fields=["descricao", "oficina"],
        model=Manutencao,
        status_filter=status,
        extra_filters=extra if extra else None,
    )


@router.post("/", response_model=ManutencaoResponse)
def create_manutencao(
    manutencao: ManutencaoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new maintenance record."""
    veiculo = db.query(Veiculo).filter(Veiculo.id == manutencao.veiculo_id).first()
    if not veiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Veículo não encontrado"
        )

    db_manutencao = Manutencao(**manutencao.model_dump())
    db.add(db_manutencao)
    db.commit()
    db.refresh(db_manutencao)
    return db_manutencao


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

    update_data = manutencao_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(manutencao, key, value)

    db.commit()
    db.refresh(manutencao)
    return manutencao


@router.get("/pendentes")
def get_manutencoes_pendentes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get pending maintenance records."""
    manutencoes = db.query(Manutencao).filter(
        Manutencao.status == "pendente"
    ).all()
    return manutencoes


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

    manutencoes = db.query(Manutencao).filter(
        (Manutencao.veiculo_id == veiculo_id) & (Manutencao.status == "pendente")
    ).all()

    alertas = []
    for manu in manutencoes:
        if manu.km_proxima and veiculo.km_atual >= manu.km_proxima:
            alertas.append({
                "manutencao_id": manu.id,
                "tipo": manu.tipo,
                "km_prevista": manu.km_proxima,
                "km_atual": veiculo.km_atual,
                "km_restante": manu.km_proxima - veiculo.km_atual,
            })

    return alertas


@router.get("/resumo")
def get_manutencoes_resumo(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get maintenance summary."""
    total_manutencoes = db.query(Manutencao).count()
    manutencoes_pendentes = db.query(Manutencao).filter(
        Manutencao.status == "pendente"
    ).count()
    total_custo = sum(float(m.custo) for m in db.query(Manutencao).all() if m.custo)

    agora = datetime.now().date()
    vencendo_em_30_dias = db.query(Manutencao).filter(
        (Manutencao.data_proxima.between(agora, agora + timedelta(days=30)))
        & (Manutencao.status == "pendente")
    ).count()

    return {
        "total_manutencoes": total_manutencoes,
        "manutencoes_pendentes": manutencoes_pendentes,
        "total_custo": total_custo,
        "vencendo_em_30_dias": vencendo_em_30_dias,
    }


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

    manutencao.status = "completada"
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
