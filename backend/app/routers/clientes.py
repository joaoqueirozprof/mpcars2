from datetime import date
import re
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, EmailStr
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.pagination import paginate
from app.models import (
    CheckinCheckout,
    Cliente,
    Contrato,
    DespesaContrato,
    Empresa,
    MotoristaEmpresa,
    Multa,
    ProrrogacaoContrato,
    Quilometragem,
    Reserva,
    UsoVeiculoEmpresa,
)
from app.models.user import User
from app.services.activity_logger import log_activity


router = APIRouter(prefix="/clientes", tags=["Clientes"])


class ClienteBase(BaseModel):
    model_config = ConfigDict(extra="ignore")

    nome: str
    cpf: Optional[str] = None
    cpf_cnpj: Optional[str] = None
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
    endereco: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    cep: Optional[str] = None
    tipo: Optional[str] = None
    empresa_id: Optional[int] = None


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    nome: Optional[str] = None
    cpf: Optional[str] = None
    cpf_cnpj: Optional[str] = None
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
    endereco: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    cep: Optional[str] = None
    empresa_id: Optional[int] = None
    tipo: Optional[str] = None
    score: Optional[int] = None
    ativo: Optional[bool] = None


class ClienteResponse(ClienteBase):
    id: int
    score: int
    ativo: bool

    class Config:
        from_attributes = True


def _clean_digits(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None

    digits = re.sub(r"\D", "", value)
    return digits or None


def _normalize_cliente_payload(payload: dict) -> dict:
    data = dict(payload)

    cpf = data.pop("cpf", None) or data.pop("cpf_cnpj", None)
    if cpf is not None:
        data["cpf"] = _clean_digits(cpf)

    field_aliases = {
        "endereco": "endereco_residencial",
        "cidade": "cidade_residencial",
        "estado": "estado_residencial",
        "cep": "cep_residencial",
    }
    for legacy, canonical in field_aliases.items():
        legacy_value = data.pop(legacy, None)
        if data.get(canonical) in (None, "") and legacy_value not in (None, ""):
            data[canonical] = legacy_value

    if "cep_residencial" in data:
        data["cep_residencial"] = _clean_digits(data.get("cep_residencial"))

    if "telefone" in data:
        data["telefone"] = _clean_digits(data.get("telefone"))

    if data.get("empresa_id") == "":
        data["empresa_id"] = None

    data.pop("tipo", None)

    normalized = {}
    for key, value in data.items():
        normalized[key] = None if value == "" else value

    return normalized


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

    tipo_normalizado = {
        "pessoa_fisica": "pf",
        "pessoa_juridica": "pj",
    }.get(tipo or "", tipo)

    if tipo_normalizado == "pf":
        query = query.filter(Cliente.empresa_id == None)
    elif tipo_normalizado == "pj":
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
    cliente_data = _normalize_cliente_payload(cliente.model_dump(exclude_unset=True))
    if not cliente_data.get("cpf"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="CPF é obrigatório",
        )

    existing = db.query(Cliente).filter(Cliente.cpf == cliente_data["cpf"]).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="CPF já cadastrado"
        )

    db_cliente = Cliente(**cliente_data)
    db.add(db_cliente)
    db.commit()
    db.refresh(db_cliente)
    log_activity(
        db,
        current_user,
        "CRIAR",
        "Cliente",
        f"Cliente {db_cliente.nome} criado",
        db_cliente.id,
        request,
    )
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
@router.patch("/{cliente_id}", response_model=ClienteResponse)
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

    update_data = _normalize_cliente_payload(cliente_data.model_dump(exclude_unset=True))
    if "cpf" in update_data and update_data["cpf"]:
        existing = db.query(Cliente).filter(
            Cliente.cpf == update_data["cpf"],
            Cliente.id != cliente_id,
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CPF já cadastrado",
            )

    for key, value in update_data.items():
        setattr(cliente, key, value)

    db.commit()
    db.refresh(cliente)
    log_activity(
        db,
        current_user,
        "EDITAR",
        "Cliente",
        f"Cliente {cliente.nome} editado",
        cliente_id,
        request,
    )
    return cliente


@router.delete("/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Delete a client and related records without relying on DB cascades."""
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado"
        )

    contratos_ativos = db.query(Contrato.id).filter(
        (Contrato.cliente_id == cliente_id) & (Contrato.status == "ativo")
    ).count()
    if contratos_ativos > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cliente possui {contratos_ativos} contrato(s) ativo(s). Finalize-os antes de excluir.",
        )

    contrato_ids = [
        contrato_id
        for (contrato_id,) in db.query(Contrato.id).filter(
            Contrato.cliente_id == cliente_id
        ).all()
    ]

    if contrato_ids:
        db.query(Quilometragem).filter(
            Quilometragem.contrato_id.in_(contrato_ids)
        ).delete(synchronize_session=False)
        db.query(DespesaContrato).filter(
            DespesaContrato.contrato_id.in_(contrato_ids)
        ).delete(synchronize_session=False)
        db.query(ProrrogacaoContrato).filter(
            ProrrogacaoContrato.contrato_id.in_(contrato_ids)
        ).delete(synchronize_session=False)
        db.query(CheckinCheckout).filter(
            CheckinCheckout.contrato_id.in_(contrato_ids)
        ).delete(synchronize_session=False)
        db.query(UsoVeiculoEmpresa).filter(
            UsoVeiculoEmpresa.contrato_id.in_(contrato_ids)
        ).update({UsoVeiculoEmpresa.contrato_id: None}, synchronize_session=False)
        db.query(Multa).filter(
            Multa.contrato_id.in_(contrato_ids)
        ).delete(synchronize_session=False)
        db.query(Contrato).filter(
            Contrato.id.in_(contrato_ids)
        ).delete(synchronize_session=False)

    db.query(Reserva).filter(
        Reserva.cliente_id == cliente_id
    ).delete(synchronize_session=False)
    db.query(Multa).filter(
        Multa.cliente_id == cliente_id
    ).delete(synchronize_session=False)
    db.query(MotoristaEmpresa).filter(
        MotoristaEmpresa.cliente_id == cliente_id
    ).delete(synchronize_session=False)

    cliente_nome = cliente.nome
    db.delete(cliente)
    db.commit()
    log_activity(
        db,
        current_user,
        "EXCLUIR",
        "Cliente",
        f"Cliente {cliente_nome} excluído",
        cliente_id,
        request,
    )
