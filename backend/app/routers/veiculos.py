from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import date
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.pagination import paginate
from app.models.user import User
from app.models import Veiculo, DespesaVeiculo, Contrato


router = APIRouter(prefix="/veiculos", tags=["Veículos"])


class VeiculoBase(BaseModel):
    placa: str
    marca: str
    modelo: str
    ano: Optional[int] = None
    cor: Optional[str] = None
    chassis: Optional[str] = None
    renavam: Optional[str] = None
    combustivel: Optional[str] = None
    capacidade_tanque: Optional[float] = None
    km_atual: Optional[float] = 0
    data_aquisicao: Optional[date] = None
    valor_aquisicao: Optional[float] = None


class VeiculoCreate(VeiculoBase):
    pass


class VeiculoUpdate(BaseModel):
    placa: Optional[str] = None
    marca: Optional[str] = None
    modelo: Optional[str] = None
    ano: Optional[int] = None
    cor: Optional[str] = None
    chassis: Optional[str] = None
    renavam: Optional[str] = None
    combustivel: Optional[str] = None
    capacidade_tanque: Optional[float] = None
    km_atual: Optional[float] = None
    data_aquisicao: Optional[date] = None
    valor_aquisicao: Optional[float] = None
    status: Optional[str] = None
    ativo: Optional[bool] = None


class VeiculoResponse(BaseModel):
    id: int
    placa: str
    marca: str
    modelo: str
    ano: Optional[int] = None
    cor: Optional[str] = None
    chassis: Optional[str] = None
    renavam: Optional[str] = None
    combustivel: Optional[str] = None
    capacidade_tanque: Optional[float] = None
    km_atual: Optional[float] = 0
    data_aquisicao: Optional[date] = None
    valor_aquisicao: Optional[float] = None
    status: str = "disponivel"
    ativo: bool = True

    class Config:
        from_attributes = True


@router.get("/")
def list_veiculos(
    page: int = 1,
    limit: int = 1000,
    search: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all vehicles with pagination."""
    query = db.query(Veiculo)
    return paginate(
        query=query,
        page=page,
        limit=limit,
        search=search,
        search_fields=["placa", "marca", "modelo", "cor"],
        model=Veiculo,
        status_filter=status_filter,
    )


@router.get("/search", response_model=List[VeiculoResponse])
def search_veiculos(
    q: str = "",
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search vehicles by plate, brand, or model."""
    query = db.query(Veiculo)

    if q:
        query = query.filter(
            (Veiculo.placa.ilike(f"%{q}%"))
            | (Veiculo.marca.ilike(f"%{q}%"))
            | (Veiculo.modelo.ilike(f"%{q}%"))
        )

    if status:
        query = query.filter(Veiculo.status == status)

    return query.all()


@router.get("/km/{veiculo_id}")
def get_veiculo_km(
    veiculo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current kilometers of a vehicle."""
    veiculo = db.query(Veiculo).filter(Veiculo.id == veiculo_id).first()
    if not veiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Veículo não encontrado"
        )
    return {"veiculo_id": veiculo_id, "km_atual": veiculo.km_atual}


@router.get("/status/{veiculo_id}")
def get_veiculo_status(
    veiculo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get vehicle status."""
    veiculo = db.query(Veiculo).filter(Veiculo.id == veiculo_id).first()
    if not veiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Veículo não encontrado"
        )
    return {"veiculo_id": veiculo_id, "status": veiculo.status}


@router.get("/analise-financeira/{veiculo_id}")
def get_veiculo_financial_analysis(
    veiculo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get financial analysis for a vehicle."""
    veiculo = db.query(Veiculo).filter(Veiculo.id == veiculo_id).first()
    if not veiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Veículo não encontrado"
        )

    despesas = db.query(DespesaVeiculo).filter(
        DespesaVeiculo.veiculo_id == veiculo_id
    ).all()
    total_despesas = sum(float(d.valor) for d in despesas if d.valor)

    return {
        "veiculo_id": veiculo_id,
        "valor_aquisicao": float(veiculo.valor_aquisicao) if veiculo.valor_aquisicao else 0,
        "total_despesas": total_despesas,
        "valor_liquido": (float(veiculo.valor_aquisicao) - total_despesas) if veiculo.valor_aquisicao else -total_despesas,
    }


@router.post("/", response_model=VeiculoResponse)
def create_veiculo(
    veiculo: VeiculoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new vehicle."""
    existing = db.query(Veiculo).filter(Veiculo.placa == veiculo.placa).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Placa já cadastrada"
        )

    db_veiculo = Veiculo(**veiculo.model_dump())
    db.add(db_veiculo)
    db.commit()
    db.refresh(db_veiculo)
    return db_veiculo


@router.get("/{veiculo_id}", response_model=VeiculoResponse)
def get_veiculo(
    veiculo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific vehicle."""
    veiculo = db.query(Veiculo).filter(Veiculo.id == veiculo_id).first()
    if not veiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Veículo não encontrado"
        )
    return veiculo


@router.put("/{veiculo_id}", response_model=VeiculoResponse)
def update_veiculo(
    veiculo_id: int,
    veiculo_data: VeiculoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a vehicle."""
    veiculo = db.query(Veiculo).filter(Veiculo.id == veiculo_id).first()
    if not veiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Veículo não encontrado"
        )

    update_data = veiculo_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(veiculo, key, value)

    db.commit()
    db.refresh(veiculo)
    return veiculo


@router.patch("/{veiculo_id}", response_model=VeiculoResponse)
def patch_veiculo(
    veiculo_id: int,
    veiculo_data: VeiculoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Partially update a vehicle."""
    veiculo = db.query(Veiculo).filter(Veiculo.id == veiculo_id).first()
    if not veiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Veículo não encontrado"
        )

    update_data = veiculo_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(veiculo, key, value)

    db.commit()
    db.refresh(veiculo)
    return veiculo


@router.delete("/{veiculo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_veiculo(
    veiculo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a vehicle."""
    veiculo = db.query(Veiculo).filter(Veiculo.id == veiculo_id).first()
    if not veiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Veículo não encontrado"
        )
    db.delete(veiculo)
    db.commit()
