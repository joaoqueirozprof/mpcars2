from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import and_
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import date
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.pagination import paginate
from app.models.user import User
from app.models import (
    Cliente, Empresa, Contrato, Reserva, Multa, MotoristaEmpresa,
    Quilometragem, DespesaContrato, ProrrogacaoContrato, CheckinCheckout,
    UsoVeiculoEmpresa,
)
from app.services.activity_logger import log_activity


router = APIRouter(prefix="/clientes", tags=["Clientes"])


class ClienteBase(BaseModel):
    nome: str
    cpf: str
    rg: Optional[str] = None
    data_nascimento: Optional[date] = None
    telefone: Optional[str] = None
    email: Optional[EmailStr] = None
    endereco_residencial: Optional[str] = None
    numero_residencial: Optional[str] = None
    complemento_residencial: Optional[str] = None
    cidade_residencial: Optional[str] = None
    estado_residencial: Optional[str] = None
    cep_residencial: Optional[str] = None
    endereco_comercial: Optional[str] = None
    numero_comercial: Optional[str] = None
    complemento_comercial: Optional[str] = None
    cidade_comercial: Optional[str] = None
    estado_comercial: Optional[str] = None
    cep_comercial: Optional[str] = None
    numero_cnh: Optional[str] = None
    validade_cnh: Optional[date] = None
    categoria_cnh: Optional[str] = None
    hotel_apartamento: Optional[str] = None
    empresa_id: Optional[int] = None


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(BaseModel):
    nome: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[EmailStr] = None
    numero_cnh: Optional[str] = None
    validade_cnh: Optional[date] = None
    categoria_cnh: Optional[str] = None
    hotel_apartamento: Optional[str] = None
    score: Optional[int] = None
    ativo: Optional[bool] = None


class ClienteResponse(ClienteBase):
    id: int
    score: int
    ativo: bool

    class Config:
        from_attributes = True


@router.get("/")
def list_clientes(
    page: int = 1,
    limit: int = 50,
    search: Optional[str] = None,
    tipo: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all clients with pagination."""
    query = db.query(Cliente)

    # Filter by tipo (pf/pj)
    if tipo == "pf":
        query = query.filter(Cliente.empresa_id == None)
    elif tipo == "pj":
        query = query.filter(Cliente.empresa_id != None)

    return paginate(
        query=query,
        page=page,
        limit=limit,
        search=search,
        search_fields=["nome", "cpf", "email", "telefone"],
        model=Cliente,
    )


@router.get("/search", response_model=List[ClienteResponse])
def search_clientes(
    q: str = "",
    ativo: Optional[bool] = None,
    estado: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Advanced client search."""
    query = db.query(Cliente)

    if q:
        query = query.filter(
            (Cliente.nome.ilike(f"%{q}%"))
            | (Cliente.cpf.ilike(f"%{q}%"))
            | (Cliente.email.ilike(f"%{q}%"))
        )

    if ativo is not None:
        query = query.filter(Cliente.ativo == ativo)

    if estado:
        query = query.filter(Cliente.estado_residencial == estado)

    return query.limit(100).all()


@router.get("/score/{cliente_id}")
def get_cliente_score(
    cliente_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get client score."""
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado"
        )
    return {"score": cliente.score, "cliente_id": cliente_id}


@router.get("/empresa/{cliente_id}")
def get_cliente_empresa(
    cliente_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get client's company information."""
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado"
        )

    if cliente.empresa_id:
        empresa = db.query(Empresa).filter(Empresa.id == cliente.empresa_id).first()
        return empresa
    return None


@router.post("/", response_model=ClienteResponse)
def create_cliente(
    cliente: ClienteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Create a new client."""
    existing = db.query(Cliente).filter(Cliente.cpf == cliente.cpf).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="CPF já cadastrado"
        )

    db_cliente = Cliente(**cliente.model_dump())
    db.add(db_cliente)
    db.commit()
    db.refresh(db_cliente)
    log_activity(db, current_user, "CRIAR", "Cliente", f"Cliente {db_cliente.nome} criado", db_cliente.id, request)
    return db_cliente


@router.get("/{cliente_id}", response_model=ClienteResponse)
def get_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific client."""
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado"
        )
    return cliente


@router.put("/{cliente_id}", response_model=ClienteResponse)
def update_cliente(
    cliente_id: int,
    cliente_data: ClienteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Update a client."""
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado"
        )

    update_data = cliente_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(cliente, key, value)

    db.commit()
    db.refresh(cliente)
    log_activity(db, current_user, "EDITAR", "Cliente", f"Cliente {cliente.nome} editado", cliente_id, request)
    return cliente


@router.delete("/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Delete a client and all related records (CASCADE handles dependents)."""
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cliente nao encontrado"
        )

    # Block deletion if client has active contracts
    contratos_ativos = db.query(Contrato).filter(
        (Contrato.cliente_id == cliente_id) & (Contrato.status == "ativo")
    ).count()
    if contratos_ativos > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cliente possui {contratos_ativos} contrato(s) ativo(s). Finalize-os antes de excluir.",
        )

    # CASCADE in models handles: contratos (and their dependents), reservas, multas, motorista_empresa
    db.delete(cliente)
    db.commit()
    log_activity(db, current_user, "EXCLUIR", "Cliente", f"Cliente {cliente.nome} excluido", cliente_id, request)
