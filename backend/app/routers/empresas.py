from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.pagination import paginate
from app.models.user import User
from app.models import Empresa, MotoristaEmpresa, Cliente, UsoVeiculoEmpresa, Veiculo, DespesaNF


router = APIRouter(prefix="/empresas", tags=["Empresas"])


class EmpresaBase(BaseModel):
    nome: str
    cnpj: str
    razao_social: str
    endereco: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    cep: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None
    contato_principal: Optional[str] = None


class EmpresaCreate(EmpresaBase):
    pass


class EmpresaUpdate(BaseModel):
    nome: Optional[str] = None
    razao_social: Optional[str] = None
    endereco: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None
    contato_principal: Optional[str] = None
    ativo: Optional[bool] = None


class EmpresaResponse(EmpresaBase):
    id: int
    ativo: bool
    data_cadastro: datetime

    class Config:
        from_attributes = True


class MotoristaEmpresaResponse(BaseModel):
    id: int
    empresa_id: int
    cliente_id: int
    cargo: Optional[str] = None
    ativo: bool
    data_vinculo: datetime

    class Config:
        from_attributes = True


@router.get("/")
def list_empresas(
    page: int = 1,
    limit: int = 50,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all companies with pagination."""
    query = db.query(Empresa)
    return paginate(
        query=query,
        page=page,
        limit=limit,
        search=search,
        search_fields=["nome", "cnpj", "razao_social"],
        model=Empresa,
    )


@router.post("/", response_model=EmpresaResponse)
def create_empresa(
    empresa: EmpresaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new company."""
    existing = db.query(Empresa).filter(Empresa.cnpj == empresa.cnpj).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="CNPJ já cadastrado"
        )

    db_empresa = Empresa(**empresa.model_dump())
    db.add(db_empresa)
    db.commit()
    db.refresh(db_empresa)
    return db_empresa


@router.get("/{empresa_id}", response_model=EmpresaResponse)
def get_empresa(
    empresa_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific company."""
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada"
        )
    return empresa


@router.put("/{empresa_id}", response_model=EmpresaResponse)
def update_empresa(
    empresa_id: int,
    empresa_data: EmpresaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a company."""
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada"
        )

    update_data = empresa_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(empresa, key, value)

    db.commit()
    db.refresh(empresa)
    return empresa


@router.delete("/{empresa_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_empresa(
    empresa_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a company."""
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada"
        )
    db.delete(empresa)
    db.commit()


@router.get("/{empresa_id}/motoristas", response_model=List[MotoristaEmpresaResponse])
def get_empresa_motoristas(
    empresa_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get drivers associated with a company."""
    motoristas = db.query(MotoristaEmpresa).filter(
        MotoristaEmpresa.empresa_id == empresa_id
    ).all()
    return motoristas


@router.post("/{empresa_id}/motoristas")
def add_empresa_motorista(
    empresa_id: int,
    cliente_id: int,
    cargo: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a driver to a company."""
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada"
        )

    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado"
        )

    motorista = MotoristaEmpresa(
        empresa_id=empresa_id, cliente_id=cliente_id, cargo=cargo
    )
    db.add(motorista)
    db.commit()
    db.refresh(motorista)
    return motorista


@router.get("/{empresa_id}/performance")
def get_empresa_performance(
    empresa_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get performance metrics for a company."""
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada"
        )

    return {
        "empresa_id": empresa_id,
        "total_motoristas": db.query(MotoristaEmpresa).filter(
            MotoristaEmpresa.empresa_id == empresa_id
        ).count(),
        "motoristas_ativos": db.query(MotoristaEmpresa).filter(
            (MotoristaEmpresa.empresa_id == empresa_id)
            & (MotoristaEmpresa.ativo == True)
        ).count(),
    }


@router.get("/{empresa_id}/faturamento")
def get_empresa_faturamento(
    empresa_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get billing information for a company."""
    from app.models import Contrato

    contratos = db.query(Contrato).filter(
        Contrato.cliente_id.in_(
            db.query(Cliente.id).filter(Cliente.empresa_id == empresa_id)
        )
    ).all()

    total_faturamento = sum(
        float(c.valor_total) for c in contratos if c.valor_total
    )

    return {
        "empresa_id": empresa_id,
        "total_contratos": len(contratos),
        "total_faturamento": total_faturamento,
    }


# ============================================================
# USO VEÍCULO EMPRESA (Veículos locados para empresas)
# ============================================================


class UsoVeiculoCreate(BaseModel):
    veiculo_id: int
    empresa_id: int
    contrato_id: Optional[int] = None
    km_inicial: Optional[float] = None
    data_inicio: Optional[str] = None
    data_fim: Optional[str] = None
    km_referencia: Optional[float] = None
    valor_km_extra: Optional[float] = None
    valor_diaria_empresa: Optional[float] = None


class UsoVeiculoUpdate(BaseModel):
    km_final: Optional[float] = None
    km_percorrido: Optional[float] = None
    data_fim: Optional[str] = None
    km_referencia: Optional[float] = None
    valor_km_extra: Optional[float] = None
    valor_diaria_empresa: Optional[float] = None
    status: Optional[str] = None


@router.get("/{empresa_id}/usos")
def list_usos_empresa(
    empresa_id: int,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all vehicle usage records for a company."""
    query = db.query(UsoVeiculoEmpresa).filter(UsoVeiculoEmpresa.empresa_id == empresa_id)
    if status_filter:
        query = query.filter(UsoVeiculoEmpresa.status == status_filter)

    usos = query.order_by(UsoVeiculoEmpresa.data_criacao.desc()).all()

    result = []
    for uso in usos:
        veiculo = db.query(Veiculo).filter(Veiculo.id == uso.veiculo_id).first()
        km_percorrido = uso.km_percorrido or (
            (uso.km_final - uso.km_inicial) if uso.km_final and uso.km_inicial else None
        )
        km_excedente = 0
        valor_excedente = 0
        if km_percorrido and uso.km_referencia and km_percorrido > uso.km_referencia:
            km_excedente = km_percorrido - uso.km_referencia
            valor_excedente = float(km_excedente * float(uso.valor_km_extra or 0))

        result.append({
            "id": uso.id,
            "veiculo_id": uso.veiculo_id,
            "empresa_id": uso.empresa_id,
            "contrato_id": uso.contrato_id,
            "placa": veiculo.placa if veiculo else None,
            "modelo": veiculo.modelo if veiculo else None,
            "marca": veiculo.marca if veiculo else None,
            "km_inicial": uso.km_inicial,
            "km_final": uso.km_final,
            "km_percorrido": km_percorrido,
            "km_referencia": uso.km_referencia,
            "valor_km_extra": float(uso.valor_km_extra) if uso.valor_km_extra else None,
            "valor_diaria_empresa": float(uso.valor_diaria_empresa) if uso.valor_diaria_empresa else None,
            "km_excedente": km_excedente,
            "valor_excedente": valor_excedente,
            "data_inicio": uso.data_inicio.isoformat() if uso.data_inicio else None,
            "data_fim": uso.data_fim.isoformat() if uso.data_fim else None,
            "status": uso.status,
        })

    return result


@router.post("/{empresa_id}/usos")
def create_uso_veiculo(
    empresa_id: int,
    uso_data: UsoVeiculoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new vehicle usage record for a company."""
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa nao encontrada")

    veiculo = db.query(Veiculo).filter(Veiculo.id == uso_data.veiculo_id).first()
    if not veiculo:
        raise HTTPException(status_code=404, detail="Veiculo nao encontrado")

    uso = UsoVeiculoEmpresa(
        veiculo_id=uso_data.veiculo_id,
        empresa_id=empresa_id,
        contrato_id=uso_data.contrato_id,
        km_inicial=uso_data.km_inicial or (veiculo.km_atual or 0),
        km_referencia=uso_data.km_referencia,
        valor_km_extra=uso_data.valor_km_extra,
        valor_diaria_empresa=uso_data.valor_diaria_empresa,
        status="ativo",
    )
    if uso_data.data_inicio:
        uso.data_inicio = datetime.fromisoformat(uso_data.data_inicio)
    else:
        uso.data_inicio = datetime.now()
    if uso_data.data_fim:
        uso.data_fim = datetime.fromisoformat(uso_data.data_fim)

    db.add(uso)
    db.commit()
    db.refresh(uso)
    return {"id": uso.id, "message": "Uso de veiculo criado com sucesso"}


@router.put("/usos/{uso_id}")
def update_uso_veiculo(
    uso_id: int,
    uso_data: UsoVeiculoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a vehicle usage record (set km, close, etc)."""
    uso = db.query(UsoVeiculoEmpresa).filter(UsoVeiculoEmpresa.id == uso_id).first()
    if not uso:
        raise HTTPException(status_code=404, detail="Uso nao encontrado")

    update_data = uso_data.model_dump(exclude_unset=True)
    if "data_fim" in update_data and update_data["data_fim"]:
        update_data["data_fim"] = datetime.fromisoformat(update_data["data_fim"])

    for key, value in update_data.items():
        setattr(uso, key, value)

    db.commit()
    db.refresh(uso)
    return {"id": uso.id, "message": "Uso atualizado com sucesso"}


@router.delete("/usos/{uso_id}", status_code=204)
def delete_uso_veiculo(
    uso_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a vehicle usage record."""
    uso = db.query(UsoVeiculoEmpresa).filter(UsoVeiculoEmpresa.id == uso_id).first()
    if not uso:
        raise HTTPException(status_code=404, detail="Uso nao encontrado")
    db.delete(uso)
    db.commit()
