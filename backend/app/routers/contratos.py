import math
from datetime import date, datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import get_current_user, require_page_access
from app.core.pagination import paginate
from app.models import (
    CheckinCheckout,
    Cliente,
    Contrato,
    DespesaContrato,
    Empresa,
    Multa,
    ProrrogacaoContrato,
    Quilometragem,
    RelatorioNF,
    UsoVeiculoEmpresa,
    Veiculo,
)
from app.models.user import User
from app.services.activity_logger import log_activity
from app.services.pdf_service import PDFService


router = APIRouter(
    prefix="/contratos",
    tags=["Contratos"],
    dependencies=[Depends(require_page_access("contratos"))],
)


class ContratoBase(BaseModel):
    model_config = ConfigDict(extra="ignore")

    numero: Optional[str] = None
    cliente_id: int
    veiculo_id: int
    data_inicio: datetime
    data_fim: Optional[datetime] = None
    km_inicial: Optional[float] = None
    quilometragem_inicial: Optional[float] = None
    km_atual_veiculo: Optional[float] = None
    km_final: Optional[float] = None
    quilometragem_final: Optional[float] = None
    valor_diaria: float
    valor_total: Optional[float] = None
    status: str = "ativo"
    observacoes: Optional[str] = None
    hora_saida: Optional[str] = None
    combustivel_saida: Optional[str] = None
    combustivel_retorno: Optional[str] = None
    km_livres: Optional[float] = None
    qtd_diarias: Optional[int] = None
    valor_hora_extra: Optional[float] = None
    valor_km_excedente: Optional[float] = None
    valor_avarias: Optional[float] = None
    taxa_combustivel: Optional[float] = None
    taxa_limpeza: Optional[float] = None
    taxa_higienizacao: Optional[float] = None
    taxa_pneus: Optional[float] = None
    taxa_acessorios: Optional[float] = None
    valor_franquia_seguro: Optional[float] = None
    taxa_administrativa: Optional[float] = None
    desconto: Optional[float] = None
    status_pagamento: Optional[str] = "pendente"
    forma_pagamento: Optional[str] = None
    data_vencimento_pagamento: Optional[date] = None
    data_pagamento: Optional[date] = None
    valor_recebido: Optional[float] = None
    tipo: Optional[str] = "cliente"
    vigencia_indeterminada: Optional[bool] = False
    empresa_uso_id: Optional[int] = None
    empresa_id: Optional[int] = None
    force_override: Optional[bool] = False
    force_motivo: Optional[str] = None


class ContratoCreate(ContratoBase):
    pass


class ContratoUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    numero: Optional[str] = None
    cliente_id: Optional[int] = None
    veiculo_id: Optional[int] = None
    data_inicio: Optional[datetime] = None
    data_fim: Optional[datetime] = None
    km_inicial: Optional[float] = None
    quilometragem_inicial: Optional[float] = None
    km_atual_veiculo: Optional[float] = None
    km_final: Optional[float] = None
    quilometragem_final: Optional[float] = None
    valor_diaria: Optional[float] = None
    valor_total: Optional[float] = None
    status: Optional[str] = None
    observacoes: Optional[str] = None
    hora_saida: Optional[str] = None
    combustivel_saida: Optional[str] = None
    combustivel_retorno: Optional[str] = None
    km_livres: Optional[float] = None
    qtd_diarias: Optional[int] = None
    valor_hora_extra: Optional[float] = None
    valor_km_excedente: Optional[float] = None
    valor_avarias: Optional[float] = None
    taxa_combustivel: Optional[float] = None
    taxa_limpeza: Optional[float] = None
    taxa_higienizacao: Optional[float] = None
    taxa_pneus: Optional[float] = None
    taxa_acessorios: Optional[float] = None
    valor_franquia_seguro: Optional[float] = None
    taxa_administrativa: Optional[float] = None
    desconto: Optional[float] = None
    status_pagamento: Optional[str] = None
    forma_pagamento: Optional[str] = None
    data_vencimento_pagamento: Optional[date] = None
    data_pagamento: Optional[date] = None
    valor_recebido: Optional[float] = None
    tipo: Optional[str] = None
    vigencia_indeterminada: Optional[bool] = None
    empresa_uso_id: Optional[int] = None
    empresa_id: Optional[int] = None


class ContratoFinalizeRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    km_final: Optional[float] = None
    quilometragem_final: Optional[float] = None
    km_atual_veiculo: Optional[float] = None
    combustivel_retorno: Optional[str] = None
    itens_checklist: Optional[dict] = None
    valor_avarias: Optional[float] = None
    taxa_combustivel: Optional[float] = None
    taxa_limpeza: Optional[float] = None
    taxa_higienizacao: Optional[float] = None
    taxa_pneus: Optional[float] = None
    taxa_acessorios: Optional[float] = None
    valor_franquia_seguro: Optional[float] = None
    taxa_administrativa: Optional[float] = None
    desconto: Optional[float] = None
    status_pagamento: Optional[str] = None
    forma_pagamento: Optional[str] = None
    data_vencimento_pagamento: Optional[date] = None
    data_pagamento: Optional[date] = None
    valor_recebido: Optional[float] = None
    observacoes: Optional[str] = None
    data_finalizacao: Optional[datetime] = None


class ContratoPaymentUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    status_pagamento: Optional[str] = None
    forma_pagamento: Optional[str] = None
    data_vencimento_pagamento: Optional[date] = None
    data_pagamento: Optional[date] = None
    valor_recebido: Optional[float] = None


class ContratoEmpresaCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    empresa_id: int
    uso_ids: List[int]
    data_inicio: datetime
    observacoes: Optional[str] = None
    force_override: bool = False
    force_motivo: Optional[str] = None


class EmpresaPeriodoCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    uso_id: int
    periodo_inicio: date
    periodo_fim: date
    km_percorrida: float


class ContratoResponse(ContratoBase):
    id: int
    data_criacao: datetime
    data_finalizacao: Optional[datetime] = None

    class Config:
        from_attributes = True


class DespesaContratoResponse(BaseModel):
    id: int
    tipo: str
    descricao: str
    valor: float
    data_registro: datetime

    class Config:
        from_attributes = True


def _generate_numero_contrato() -> str:
    return "CTR-{}".format(datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3])


def _validar_datas(data_inicio: datetime, data_fim: datetime):
    if data_inicio >= data_fim:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Data de inicio deve ser anterior a data de fim",
        )


def _resolver_data_fim(
    data_inicio: datetime,
    data_fim: Optional[datetime],
    *,
    tipo: Optional[str] = None,
    vigencia_indeterminada: bool = False,
) -> datetime:
    if data_fim:
        return data_fim

    if vigencia_indeterminada or str(tipo or "").lower() == "empresa":
        return data_inicio + timedelta(days=3650)

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Data final obrigatoria para contratos com prazo definido",
    )


def _calcular_qtd_diarias(data_inicio: datetime, data_fim: datetime) -> int:
    total_seconds = max((data_fim - data_inicio).total_seconds(), 0)
    return max(1, math.ceil(total_seconds / 86400))


def _calcular_km_excedente(
    km_inicial: Optional[float],
    km_final: Optional[float],
    km_livres: Optional[float],
) -> float:
    if km_inicial is None or km_final is None:
        return 0.0

    km_rodado = max(float(km_final) - float(km_inicial), 0.0)
    franquia = float(km_livres or 0)
    return max(km_rodado - franquia, 0.0)


def _calcular_valor_total(
    data_inicio: datetime,
    data_fim: datetime,
    valor_diaria: float,
    *,
    tipo: Optional[str] = None,
    km_inicial: Optional[float] = None,
    km_final: Optional[float] = None,
    km_livres: Optional[float] = None,
    valor_km_excedente: Optional[float] = None,
    valor_avarias: Optional[float] = None,
    taxa_combustivel: Optional[float] = None,
    taxa_limpeza: Optional[float] = None,
    taxa_higienizacao: Optional[float] = None,
    taxa_pneus: Optional[float] = None,
    taxa_acessorios: Optional[float] = None,
    valor_franquia_seguro: Optional[float] = None,
    taxa_administrativa: Optional[float] = None,
    desconto: Optional[float] = None,
) -> float:
    qtd_diarias = _calcular_qtd_diarias(data_inicio, data_fim)
    total_base = float(valor_diaria or 0) if str(tipo or "").lower() == "empresa" else qtd_diarias * float(valor_diaria or 0)
    km_excedente = _calcular_km_excedente(km_inicial, km_final, km_livres)
    total_km = km_excedente * float(valor_km_excedente or 0)
    total_taxas = sum(
        float(valor or 0)
        for valor in (
            valor_avarias,
            taxa_combustivel,
            taxa_limpeza,
            taxa_higienizacao,
            taxa_pneus,
            taxa_acessorios,
            valor_franquia_seguro,
            taxa_administrativa,
        )
    )
    total = total_base + total_km + total_taxas - float(desconto or 0)
    return round(max(total, 0.0), 2)


def _normalize_contrato_payload(payload: dict, is_create: bool = False) -> dict:
    data = dict(payload)

    if data.get("km_inicial") is None and data.get("quilometragem_inicial") is not None:
        data["km_inicial"] = data.pop("quilometragem_inicial")
    else:
        data.pop("quilometragem_inicial", None)

    if data.get("km_inicial") is None and data.get("km_atual_veiculo") is not None:
        data["km_inicial"] = data.pop("km_atual_veiculo")
    else:
        data.pop("km_atual_veiculo", None)

    if data.get("km_final") is None and data.get("quilometragem_final") is not None:
        data["km_final"] = data.pop("quilometragem_final")
    else:
        data.pop("quilometragem_final", None)

    if is_create and not data.get("numero"):
        data["numero"] = _generate_numero_contrato()

    normalized = {}
    for key, value in data.items():
        if value == "":
            normalized[key] = None
        elif key in {"status", "tipo", "status_pagamento"} and isinstance(value, str):
            normalized[key] = value.lower()
        else:
            normalized[key] = value

    return normalized


def _normalize_finalizacao_payload(payload: dict) -> dict:
    data = dict(payload)

    if data.get("km_final") is None and data.get("quilometragem_final") is not None:
        data["km_final"] = data.pop("quilometragem_final")
    else:
        data.pop("quilometragem_final", None)

    if data.get("km_final") is None and data.get("km_atual_veiculo") is not None:
        data["km_final"] = data.pop("km_atual_veiculo")
    else:
        data.pop("km_atual_veiculo", None)

    normalized = {}
    for key, value in data.items():
        if value == "":
            normalized[key] = None
        elif key == "status_pagamento" and isinstance(value, str):
            normalized[key] = value.lower()
        else:
            normalized[key] = value

    return normalized


def _status_pagamento_atual(contrato: Contrato) -> str:
    if contrato.status_pagamento:
        return str(contrato.status_pagamento).lower()
    if contrato.status == "finalizado":
        return "pago"
    return "pendente"


def _apply_payment_details(
    contrato: Contrato,
    payment_data: dict,
    *,
    reference_date: Optional[datetime] = None,
) -> None:
    data = dict(payment_data or {})
    allowed_status = {"pendente", "pago", "cancelado"}
    current_status = _status_pagamento_atual(contrato)
    next_status = current_status

    if data.get("status_pagamento"):
        next_status = str(data["status_pagamento"]).lower()
        if next_status not in allowed_status:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Status de pagamento invalido",
            )

    if "forma_pagamento" in data:
        contrato.forma_pagamento = data.get("forma_pagamento")
    if "data_vencimento_pagamento" in data:
        contrato.data_vencimento_pagamento = data.get("data_vencimento_pagamento")
    if "data_pagamento" in data:
        contrato.data_pagamento = data.get("data_pagamento")
    if "valor_recebido" in data:
        contrato.valor_recebido = data.get("valor_recebido")

    contrato.status_pagamento = next_status
    default_due_date = (
        reference_date.date()
        if reference_date
        else contrato.data_finalizacao.date()
        if contrato.data_finalizacao
        else contrato.data_fim.date()
        if contrato.data_fim
        else datetime.now().date()
    )

    if not contrato.data_vencimento_pagamento:
        contrato.data_vencimento_pagamento = default_due_date

    if next_status == "pago":
        if not contrato.data_pagamento:
            contrato.data_pagamento = (
                reference_date.date() if reference_date else datetime.now().date()
            )
        if contrato.valor_recebido is None or float(contrato.valor_recebido or 0) <= 0:
            contrato.valor_recebido = float(contrato.valor_total or 0)
    elif next_status == "cancelado":
        if contrato.valor_recebido is None:
            contrato.valor_recebido = 0


def _append_observacao(existing_value: Optional[str], extra_value: Optional[str], titulo: str) -> Optional[str]:
    if not extra_value:
        return existing_value

    extra_value = extra_value.strip()
    if not extra_value:
        return existing_value

    bloco = "[{}] {}".format(titulo, extra_value)
    if not existing_value:
        return bloco
    return "{}\n{}".format(existing_value.strip(), bloco)


def _ensure_cliente_exists(db: Session, cliente_id: int) -> Cliente:
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente nao encontrado",
        )
    return cliente


def _resolve_cliente_contrato(
    db: Session,
    *,
    tipo: Optional[str],
    cliente_id: Optional[int] = None,
    empresa_id: Optional[int] = None,
) -> Cliente:
    if str(tipo or "").lower() != "empresa":
        if cliente_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cliente obrigatorio para criar contrato",
            )
        return _ensure_cliente_exists(db, cliente_id)

    target_empresa_id = empresa_id
    if not target_empresa_id and cliente_id:
        cliente_existente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        if cliente_existente and cliente_existente.empresa_id:
            return cliente_existente

        empresa_existente = db.query(Empresa).filter(Empresa.id == cliente_id).first()
        if empresa_existente:
            target_empresa_id = empresa_existente.id

    if not target_empresa_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empresa obrigatoria para criar contrato corporativo",
        )

    empresa = db.query(Empresa).filter(Empresa.id == target_empresa_id).first()
    if not empresa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa nao encontrada",
        )

    cliente = (
        db.query(Cliente)
        .filter(Cliente.empresa_id == target_empresa_id)
        .order_by(Cliente.id.asc())
        .first()
    )
    if cliente:
        return cliente

    cpf_base = "".join(ch for ch in str(empresa.cnpj or "") if ch.isdigit()) or f"empresa-{empresa.id}"
    cpf = cpf_base
    if db.query(Cliente).filter(Cliente.cpf == cpf).first():
        cpf = f"{cpf_base}-{empresa.id}"

    cliente = Cliente(
        nome=empresa.nome,
        cpf=cpf,
        telefone=empresa.telefone,
        email=None,
        empresa_id=empresa.id,
        ativo=True,
    )
    db.add(cliente)
    db.flush()
    return cliente


def _sincronizar_uso_empresa(
    db: Session,
    contrato: Contrato,
    cliente: Cliente,
    *,
    empresa_uso_id: Optional[int] = None,
    encerrar: bool = False,
):
    empresa_id = getattr(cliente, "empresa_id", None)
    if contrato.tipo != "empresa" or not empresa_id:
        return

    uso = None
    if empresa_uso_id:
        uso = (
            db.query(UsoVeiculoEmpresa)
            .filter(
                UsoVeiculoEmpresa.id == empresa_uso_id,
                UsoVeiculoEmpresa.empresa_id == empresa_id,
            )
            .first()
        )
    if not uso and contrato.id:
        uso = (
            db.query(UsoVeiculoEmpresa)
            .filter(UsoVeiculoEmpresa.contrato_id == contrato.id)
            .first()
        )
    if not uso:
        uso = (
            db.query(UsoVeiculoEmpresa)
            .filter(
                UsoVeiculoEmpresa.empresa_id == empresa_id,
                UsoVeiculoEmpresa.veiculo_id == contrato.veiculo_id,
                UsoVeiculoEmpresa.status == "ativo",
            )
            .order_by(UsoVeiculoEmpresa.data_criacao.desc())
            .first()
        )

    if not uso:
        uso = UsoVeiculoEmpresa(
            empresa_id=empresa_id,
            veiculo_id=contrato.veiculo_id,
            status="ativo",
        )
        db.add(uso)

    uso.empresa_id = empresa_id
    uso.veiculo_id = contrato.veiculo_id
    uso.contrato_id = contrato.id
    uso.km_inicial = float(contrato.km_inicial or 0)
    uso.km_referencia = float(contrato.km_livres or 0) if contrato.km_livres is not None else uso.km_referencia
    uso.valor_km_extra = contrato.valor_km_excedente
    uso.valor_diaria_empresa = contrato.valor_diaria
    uso.data_inicio = contrato.data_inicio

    if encerrar:
        uso.km_final = float(contrato.km_final or uso.km_final or contrato.km_inicial or 0)
        if uso.km_inicial is not None and uso.km_final is not None:
            uso.km_percorrido = max(float(uso.km_final) - float(uso.km_inicial), 0.0)
        uso.data_fim = contrato.data_finalizacao or contrato.data_fim
        uso.status = "finalizado"
    else:
        uso.data_fim = None if contrato.status == "ativo" else (contrato.data_finalizacao or contrato.data_fim)
        uso.status = "ativo" if contrato.status == "ativo" else "finalizado"


def _ensure_veiculo_available(
    db: Session,
    veiculo_id: int,
    contrato_id: Optional[int] = None,
) -> Veiculo:
    veiculo = db.query(Veiculo).filter(Veiculo.id == veiculo_id).first()
    if not veiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Veiculo nao encontrado",
        )

    contrato_ativo = db.query(Contrato).filter(
        Contrato.veiculo_id == veiculo_id,
        Contrato.status == "ativo",
        Contrato.id != contrato_id,
    ).first()
    if contrato_ativo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Veiculo ja possui contrato ativo (#{})".format(contrato_ativo.numero),
        )

    if contrato_id is None and veiculo.status not in {"disponivel", "reservado"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Veiculo nao esta disponivel (status atual: {})".format(veiculo.status),
        )

    return veiculo


def _recalcular_status_veiculo(db: Session, veiculo_id: int):
    veiculo = db.query(Veiculo).filter(Veiculo.id == veiculo_id).first()
    if not veiculo:
        return

    contratos_ativos = db.query(Contrato).filter(
        Contrato.veiculo_id == veiculo_id,
        Contrato.status == "ativo",
    ).count()
    veiculo.status = "alugado" if contratos_ativos > 0 else "disponivel"


@router.get("/")
def list_contratos(
    page: int = 1,
    limit: int = 50,
    search: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all contracts with pagination."""
    del current_user

    query = (
        db.query(Contrato)
        .options(joinedload(Contrato.cliente), joinedload(Contrato.veiculo))
        .join(Cliente, Cliente.id == Contrato.cliente_id)
        .join(Veiculo, Veiculo.id == Contrato.veiculo_id)
        .order_by(Contrato.data_criacao.desc())
    )

    if search:
        search_term = "%{}%".format(search.strip())
        query = query.filter(
            or_(
                Contrato.numero.ilike(search_term),
                Cliente.nome.ilike(search_term),
                Veiculo.placa.ilike(search_term),
                Veiculo.marca.ilike(search_term),
                Veiculo.modelo.ilike(search_term),
            )
        )

    if status_filter:
        if status_filter == "atraso":
            query = query.filter(
                Contrato.status == "ativo",
                Contrato.data_fim < datetime.now(),
            )
        else:
            query = query.filter(Contrato.status == status_filter)

    return paginate(query=query, page=page, limit=limit)


@router.get("/atrasados", response_model=List[ContratoResponse])
def get_atrasados(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get overdue contracts."""
    del current_user
    agora = datetime.now()
    contratos = db.query(Contrato).filter(
        Contrato.data_fim < agora,
        Contrato.status == "ativo",
    ).all()
    return contratos


@router.get("/vencimentos", response_model=List[ContratoResponse])
def get_vencimentos(
    dias: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get contracts expiring within specified days."""
    del current_user
    agora = datetime.now()
    fim = agora + timedelta(days=dias)
    contratos = db.query(Contrato).filter(
        Contrato.data_fim.between(agora, fim),
        Contrato.status == "ativo",
    ).all()
    return contratos


@router.post("/", response_model=ContratoResponse)
def create_contrato(
    contrato: ContratoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Create a new contract."""
    raw_payload = contrato.model_dump(exclude_unset=True)
    vigencia_indeterminada = bool(raw_payload.pop("vigencia_indeterminada", False))
    empresa_uso_id = raw_payload.pop("empresa_uso_id", None)
    empresa_id = raw_payload.pop("empresa_id", None)
    force_override = bool(raw_payload.pop("force_override", False))
    force_motivo = raw_payload.pop("force_motivo", None)
    contrato_data = _normalize_contrato_payload(
        raw_payload,
        is_create=True,
    )
    contrato_data["data_fim"] = _resolver_data_fim(
        contrato_data["data_inicio"],
        contrato_data.get("data_fim"),
        tipo=contrato_data.get("tipo"),
        vigencia_indeterminada=vigencia_indeterminada,
    )
    _validar_datas(contrato_data["data_inicio"], contrato_data["data_fim"])

    existing = db.query(Contrato).filter(Contrato.numero == contrato_data["numero"]).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Numero de contrato ja existe",
        )

    cliente = _resolve_cliente_contrato(
        db,
        tipo=contrato_data.get("tipo"),
        cliente_id=contrato_data.get("cliente_id"),
        empresa_id=empresa_id,
    )
    contrato_data["cliente_id"] = cliente.id
    veiculo = _ensure_veiculo_available(db, contrato_data["veiculo_id"])

    # Check empresa uso conflict for PF contracts
    if str(contrato_data.get("tipo") or "").lower() != "empresa":
        uso_empresa_ativo = db.query(UsoVeiculoEmpresa).filter(
            UsoVeiculoEmpresa.veiculo_id == contrato_data["veiculo_id"],
            UsoVeiculoEmpresa.status == "ativo"
        ).first()
        if uso_empresa_ativo:
            if not force_override:
                empresa_info = db.query(Empresa).filter(Empresa.id == uso_empresa_ativo.empresa_id).first()
                raise HTTPException(
                    status_code=409,
                    detail="Veiculo vinculado a empresa {} com uso ativo. Envie force_override=true com motivo para prosseguir.".format(
                        empresa_info.nome if empresa_info else uso_empresa_ativo.empresa_id
                    )
                )
            if force_motivo:
                contrato_data["observacoes"] = _append_observacao(
                    contrato_data.get("observacoes"),
                    force_motivo,
                    "OVERRIDE - Veiculo com vinculo empresa"
                )

    if contrato_data.get("km_inicial") is None:
        contrato_data["km_inicial"] = float(veiculo.km_atual or 0)

    if not contrato_data.get("qtd_diarias"):
        contrato_data["qtd_diarias"] = (
            1
            if str(contrato_data.get("tipo") or "").lower() == "empresa"
            else _calcular_qtd_diarias(
                contrato_data["data_inicio"],
                contrato_data["data_fim"],
            )
        )

    if not contrato_data.get("valor_total"):
        contrato_data["valor_total"] = _calcular_valor_total(
            contrato_data["data_inicio"],
            contrato_data["data_fim"],
            float(contrato_data["valor_diaria"]),
            tipo=contrato_data.get("tipo"),
            km_inicial=contrato_data.get("km_inicial"),
            km_final=contrato_data.get("km_final"),
            km_livres=contrato_data.get("km_livres"),
            valor_km_excedente=contrato_data.get("valor_km_excedente"),
            valor_avarias=contrato_data.get("valor_avarias"),
            taxa_combustivel=contrato_data.get("taxa_combustivel"),
            taxa_limpeza=contrato_data.get("taxa_limpeza"),
            taxa_higienizacao=contrato_data.get("taxa_higienizacao"),
            taxa_pneus=contrato_data.get("taxa_pneus"),
            taxa_acessorios=contrato_data.get("taxa_acessorios"),
            valor_franquia_seguro=contrato_data.get("valor_franquia_seguro"),
            taxa_administrativa=contrato_data.get("taxa_administrativa"),
            desconto=contrato_data.get("desconto"),
        )

    db_contrato = Contrato(**contrato_data)
    _apply_payment_details(
        db_contrato,
        contrato_data,
        reference_date=contrato_data["data_fim"],
    )
    db.add(db_contrato)
    db.flush()

    db.add(
        CheckinCheckout(
            contrato_id=db_contrato.id,
            tipo="retirada",
            km=db_contrato.km_inicial,
            nivel_combustivel=db_contrato.combustivel_saida,
            itens_checklist=veiculo.checklist or {},
        )
    )
    veiculo.status = "alugado"
    _sincronizar_uso_empresa(
        db,
        db_contrato,
        cliente,
        empresa_uso_id=empresa_uso_id,
    )

    db.commit()
    db.refresh(db_contrato)
    log_activity(
        db,
        current_user,
        "CRIAR",
        "Contrato",
        "Contrato {} criado".format(db_contrato.numero),
        db_contrato.id,
        request,
    )
    return db_contrato


@router.get("/verificar-veiculo/{veiculo_id}")
def verificar_veiculo_disponibilidade(
    veiculo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check if a vehicle has active empresa links or contracts."""
    del current_user
    veiculo = db.query(Veiculo).filter(Veiculo.id == veiculo_id).first()
    if not veiculo:
        raise HTTPException(status_code=404, detail="Veiculo nao encontrado")

    # Check active empresa uso
    uso_ativo = db.query(UsoVeiculoEmpresa).filter(
        UsoVeiculoEmpresa.veiculo_id == veiculo_id,
        UsoVeiculoEmpresa.status == "ativo"
    ).first()

    # Check active contrato
    contrato_ativo = db.query(Contrato).filter(
        Contrato.veiculo_id == veiculo_id,
        Contrato.status == "ativo"
    ).first()

    # Also check if vehicle is linked to empresa contracts via UsoVeiculoEmpresa.contrato_id
    uso_com_contrato = None
    if uso_ativo and uso_ativo.contrato_id:
        uso_com_contrato = db.query(Contrato).filter(
            Contrato.id == uso_ativo.contrato_id,
            Contrato.status == "ativo"
        ).first()

    empresa_nome = None
    if uso_ativo:
        empresa = db.query(Empresa).filter(Empresa.id == uso_ativo.empresa_id).first()
        empresa_nome = empresa.nome if empresa else None

    return {
        "veiculo_id": veiculo_id,
        "placa": veiculo.placa,
        "disponivel": uso_ativo is None and contrato_ativo is None,
        "uso_empresa_ativo": {
            "uso_id": uso_ativo.id,
            "empresa_id": uso_ativo.empresa_id,
            "empresa_nome": empresa_nome,
            "contrato_id": uso_ativo.contrato_id,
            "data_inicio": uso_ativo.data_inicio.isoformat() if uso_ativo and uso_ativo.data_inicio else None,
        } if uso_ativo else None,
        "contrato_ativo": {
            "contrato_id": contrato_ativo.id,
            "numero": contrato_ativo.numero,
            "tipo": contrato_ativo.tipo,
            "cliente_id": contrato_ativo.cliente_id,
        } if contrato_ativo else None,
        "contrato_empresa_ativo": {
            "contrato_id": uso_com_contrato.id,
            "numero": uso_com_contrato.numero,
        } if uso_com_contrato else None,
    }


@router.post("/empresa", response_model=ContratoResponse)
def create_contrato_empresa(
    payload: ContratoEmpresaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Create an empresa contract with multiple vehicles."""
    if not payload.uso_ids:
        raise HTTPException(400, "Selecione pelo menos um veiculo")

    empresa = db.query(Empresa).filter(Empresa.id == payload.empresa_id).first()
    if not empresa:
        raise HTTPException(404, "Empresa nao encontrada")

    # Validate all usos exist and belong to this empresa
    usos = []
    total_valor_mensal = 0.0
    primary_veiculo = None

    for uso_id in payload.uso_ids:
        uso = db.query(UsoVeiculoEmpresa).filter(
            UsoVeiculoEmpresa.id == uso_id,
            UsoVeiculoEmpresa.empresa_id == payload.empresa_id,
            UsoVeiculoEmpresa.status == "ativo"
        ).first()
        if not uso:
            raise HTTPException(400, "Uso de veiculo {} nao encontrado ou nao pertence a empresa".format(uso_id))

        veiculo = db.query(Veiculo).filter(Veiculo.id == uso.veiculo_id).first()
        if not veiculo:
            raise HTTPException(404, "Veiculo nao encontrado para uso {}".format(uso_id))

        # Check if vehicle already has an active non-empresa contract
        if not payload.force_override:
            contrato_conflito = db.query(Contrato).filter(
                Contrato.veiculo_id == uso.veiculo_id,
                Contrato.status == "ativo",
                Contrato.tipo != "empresa"
            ).first()
            if contrato_conflito:
                raise HTTPException(
                    status_code=409,
                    detail="Veiculo {} ({}) possui contrato ativo #{} para pessoa fisica. Use force_override=true com motivo.".format(
                        veiculo.placa, veiculo.marca + " " + veiculo.modelo, contrato_conflito.numero
                    )
                )

        usos.append((uso, veiculo))
        total_valor_mensal += float(uso.valor_diaria_empresa or 0)
        if primary_veiculo is None:
            primary_veiculo = veiculo

    # Resolve/create client for empresa
    cliente = _resolve_cliente_contrato(db, tipo="empresa", cliente_id=None, empresa_id=payload.empresa_id)

    # Build observacoes with force motivo if applicable
    obs = payload.observacoes or ""
    if payload.force_override and payload.force_motivo:
        obs = "[OVERRIDE] {}\n{}".format(payload.force_motivo, obs).strip()

    # Create the contract
    contrato = Contrato(
        numero=_generate_numero_contrato(),
        cliente_id=cliente.id,
        veiculo_id=primary_veiculo.id,  # Primary vehicle (first selected)
        data_inicio=payload.data_inicio,
        data_fim=payload.data_inicio + timedelta(days=3650),  # Indeterminate
        km_inicial=float(primary_veiculo.km_atual or 0),
        valor_diaria=total_valor_mensal,
        valor_total=total_valor_mensal,
        tipo="empresa",
        status="ativo",
        qtd_diarias=1,
        observacoes=obs or None,
        status_pagamento="pendente",
    )
    db.add(contrato)
    db.flush()

    # Link all UsoVeiculoEmpresa to this contrato
    for uso, veiculo in usos:
        uso.contrato_id = contrato.id
        veiculo.status = "alugado"

    # Create checkin record
    db.add(CheckinCheckout(
        contrato_id=contrato.id,
        tipo="retirada",
        km=contrato.km_inicial,
        nivel_combustivel=None,
        itens_checklist=primary_veiculo.checklist or {},
    ))

    db.commit()
    db.refresh(contrato)
    log_activity(db, current_user, "CRIAR", "Contrato", "Contrato empresa {} criado com {} veiculo(s)".format(contrato.numero, len(usos)), contrato.id, request)
    return contrato


@router.get("/{contrato_id}/empresa-detalhes")
def get_contrato_empresa_detalhes(
    contrato_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get full empresa contract details with all vehicles and periods."""
    del current_user
    contrato = db.query(Contrato).filter(Contrato.id == contrato_id).first()
    if not contrato:
        raise HTTPException(404, "Contrato nao encontrado")
    if str(contrato.tipo or "").strip("'\"").lower() != "empresa":
        raise HTTPException(400, "Este contrato nao e do tipo empresa")

    cliente = contrato.cliente
    empresa_id = cliente.empresa_id if cliente else None
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first() if empresa_id else None

    # Get all UsoVeiculoEmpresa linked to this contract
    usos = db.query(UsoVeiculoEmpresa).filter(
        UsoVeiculoEmpresa.contrato_id == contrato_id
    ).all()

    # If no usos found via contrato_id, try via empresa_id + active status
    if not usos and empresa_id:
        usos = db.query(UsoVeiculoEmpresa).filter(
            UsoVeiculoEmpresa.empresa_id == empresa_id,
            UsoVeiculoEmpresa.veiculo_id == contrato.veiculo_id,
        ).all()

    veiculos_detalhes = []
    total_mensal = 0.0
    total_km_extra_geral = 0.0

    for uso in usos:
        veiculo = db.query(Veiculo).filter(Veiculo.id == uso.veiculo_id).first()

        # Get all RelatorioNF (periods) for this uso
        relatorios = db.query(RelatorioNF).filter(
            RelatorioNF.uso_id == uso.id
        ).order_by(RelatorioNF.periodo_inicio.desc()).all()

        periodos = []
        for rel in relatorios:
            km_percorrida = float(rel.km_percorrida or 0)
            km_excedente = float(rel.km_excedente or 0)
            valor_km_extra = float(uso.valor_km_extra or 0)
            valor_extra_periodo = km_excedente * valor_km_extra

            periodos.append({
                "id": rel.id,
                "periodo_inicio": rel.periodo_inicio.isoformat() if rel.periodo_inicio else None,
                "periodo_fim": rel.periodo_fim.isoformat() if rel.periodo_fim else None,
                "km_percorrida": km_percorrida,
                "km_referencia": float(uso.km_referencia or 0),
                "km_excedente": km_excedente,
                "valor_km_extra_unitario": valor_km_extra,
                "valor_extra_periodo": round(valor_extra_periodo, 2),
                "valor_total_extra_registrado": float(rel.valor_total_extra or 0),
                "valor_mensal": float(uso.valor_diaria_empresa or 0),
                "valor_total_periodo": round(float(uso.valor_diaria_empresa or 0) + valor_extra_periodo, 2),
            })

        total_km_extra_uso = sum(p["valor_extra_periodo"] for p in periodos)
        total_mensal += float(uso.valor_diaria_empresa or 0)
        total_km_extra_geral += total_km_extra_uso

        veiculos_detalhes.append({
            "uso_id": uso.id,
            "veiculo_id": uso.veiculo_id,
            "placa": veiculo.placa if veiculo else None,
            "marca": veiculo.marca if veiculo else None,
            "modelo": veiculo.modelo if veiculo else None,
            "ano": veiculo.ano if veiculo else None,
            "km_atual": float(veiculo.km_atual or 0) if veiculo else 0,
            "km_inicial": float(uso.km_inicial or 0),
            "km_referencia": float(uso.km_referencia or 0),
            "valor_km_extra": float(uso.valor_km_extra or 0),
            "valor_mensal": float(uso.valor_diaria_empresa or 0),
            "status_uso": uso.status,
            "data_inicio_uso": uso.data_inicio.isoformat() if uso.data_inicio else None,
            "data_fim_uso": uso.data_fim.isoformat() if uso.data_fim else None,
            "total_periodos": len(periodos),
            "total_km_extra_valor": round(total_km_extra_uso, 2),
            "periodos": periodos,
        })

    return {
        "contrato": {
            "id": contrato.id,
            "numero": contrato.numero,
            "status": contrato.status,
            "data_inicio": contrato.data_inicio.isoformat() if contrato.data_inicio else None,
            "data_criacao": contrato.data_criacao.isoformat() if contrato.data_criacao else None,
            "observacoes": contrato.observacoes,
            "status_pagamento": contrato.status_pagamento,
        },
        "empresa": {
            "id": empresa.id,
            "nome": empresa.nome,
            "cnpj": empresa.cnpj,
            "razao_social": empresa.razao_social,
            "telefone": empresa.telefone,
            "email": empresa.email,
            "endereco": empresa.endereco,
            "cidade": empresa.cidade,
            "estado": empresa.estado,
        } if empresa else None,
        "veiculos": veiculos_detalhes,
        "resumo": {
            "total_veiculos": len(veiculos_detalhes),
            "valor_mensal_total": round(total_mensal, 2),
            "total_km_extra_valor": round(total_km_extra_geral, 2),
            "valor_total_geral": round(total_mensal + total_km_extra_geral, 2),
        },
    }


@router.post("/{contrato_id}/empresa-periodo")
def add_empresa_periodo(
    contrato_id: int,
    payload: EmpresaPeriodoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Add a new period entry for a vehicle in an empresa contract."""
    contrato = db.query(Contrato).filter(Contrato.id == contrato_id).first()
    if not contrato:
        raise HTTPException(404, "Contrato nao encontrado")
    if str(contrato.tipo or "").strip("'\"").lower() != "empresa":
        raise HTTPException(400, "Este contrato nao e do tipo empresa")

    uso = db.query(UsoVeiculoEmpresa).filter(
        UsoVeiculoEmpresa.id == payload.uso_id,
        UsoVeiculoEmpresa.contrato_id == contrato_id
    ).first()
    if not uso:
        raise HTTPException(404, "Veiculo nao vinculado a este contrato")

    # Calculate km excedente
    km_referencia = float(uso.km_referencia or 0)
    km_excedente = max(payload.km_percorrida - km_referencia, 0)
    valor_km_extra = float(uso.valor_km_extra or 0)
    valor_total_extra = round(km_excedente * valor_km_extra, 2)

    relatorio = RelatorioNF(
        veiculo_id=uso.veiculo_id,
        empresa_id=uso.empresa_id,
        uso_id=uso.id,
        periodo_inicio=payload.periodo_inicio,
        periodo_fim=payload.periodo_fim,
        km_percorrida=payload.km_percorrida,
        km_excedente=km_excedente,
        valor_total_extra=valor_total_extra,
    )
    db.add(relatorio)

    # Update vehicle km if this period's km is higher
    veiculo = db.query(Veiculo).filter(Veiculo.id == uso.veiculo_id).first()
    if veiculo:
        new_km = float(uso.km_inicial or 0) + payload.km_percorrida
        if new_km > float(veiculo.km_atual or 0):
            veiculo.km_atual = new_km

    # Update contrato valor_total with accumulated km extras
    all_relatorios = db.query(RelatorioNF).filter(
        RelatorioNF.uso_id.in_(
            db.query(UsoVeiculoEmpresa.id).filter(UsoVeiculoEmpresa.contrato_id == contrato_id)
        )
    ).all()
    total_extras = sum(float(r.valor_total_extra or 0) for r in all_relatorios) + valor_total_extra

    # Get all usos for this contract to sum monthly values
    all_usos = db.query(UsoVeiculoEmpresa).filter(UsoVeiculoEmpresa.contrato_id == contrato_id).all()
    total_mensal = sum(float(u.valor_diaria_empresa or 0) for u in all_usos)

    contrato.valor_total = round(total_mensal + total_extras, 2)

    db.commit()
    db.refresh(relatorio)

    log_activity(db, current_user, "CRIAR", "Contrato", "Periodo adicionado ao contrato empresa {}".format(contrato.numero), contrato.id, request)

    return {
        "id": relatorio.id,
        "periodo_inicio": relatorio.periodo_inicio.isoformat(),
        "periodo_fim": relatorio.periodo_fim.isoformat(),
        "km_percorrida": payload.km_percorrida,
        "km_referencia": km_referencia,
        "km_excedente": km_excedente,
        "valor_km_extra_unitario": valor_km_extra,
        "valor_total_extra": valor_total_extra,
        "valor_mensal": float(uso.valor_diaria_empresa or 0),
        "valor_total_periodo": round(float(uso.valor_diaria_empresa or 0) + valor_total_extra, 2),
    }


@router.get("/{contrato_id}", response_model=ContratoResponse)
def get_contrato(
    contrato_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific contract."""
    del current_user
    contrato = db.query(Contrato).filter(Contrato.id == contrato_id).first()
    if not contrato:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contrato nao encontrado",
        )
    return contrato


@router.put("/{contrato_id}", response_model=ContratoResponse)
@router.patch("/{contrato_id}", response_model=ContratoResponse)
def update_contrato(
    contrato_id: int,
    contrato_data: ContratoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Update a contract."""
    contrato = db.query(Contrato).filter(Contrato.id == contrato_id).first()
    if not contrato:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contrato nao encontrado",
        )

    raw_payload = contrato_data.model_dump(exclude_unset=True)
    vigencia_indeterminada = raw_payload.pop("vigencia_indeterminada", None)
    empresa_uso_id = raw_payload.pop("empresa_uso_id", None)
    empresa_id = raw_payload.pop("empresa_id", None)
    update_data = _normalize_contrato_payload(raw_payload)

    if "numero" in update_data and update_data["numero"]:
        existing = db.query(Contrato).filter(
            Contrato.numero == update_data["numero"],
            Contrato.id != contrato_id,
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Numero de contrato ja existe",
            )

    novo_cliente_id = update_data.get("cliente_id", contrato.cliente_id)
    novo_veiculo_id = update_data.get("veiculo_id", contrato.veiculo_id)
    nova_data_inicio = update_data.get("data_inicio", contrato.data_inicio)
    nova_data_fim = update_data.get("data_fim", contrato.data_fim)
    novo_status = update_data.get("status", contrato.status)
    novo_valor_diaria = update_data.get("valor_diaria", contrato.valor_diaria)

    nova_data_fim = _resolver_data_fim(
        nova_data_inicio,
        nova_data_fim,
        tipo=update_data.get("tipo", contrato.tipo),
        vigencia_indeterminada=bool(vigencia_indeterminada),
    )
    update_data["data_fim"] = nova_data_fim
    _validar_datas(nova_data_inicio, nova_data_fim)
    cliente = _resolve_cliente_contrato(
        db,
        tipo=update_data.get("tipo", contrato.tipo),
        cliente_id=novo_cliente_id,
        empresa_id=empresa_id,
    )
    update_data["cliente_id"] = cliente.id

    veiculo_destino = None
    if novo_status == "ativo":
        veiculo_destino = _ensure_veiculo_available(
            db,
            novo_veiculo_id,
            contrato_id=contrato_id,
        )

    if "veiculo_id" in update_data and "km_inicial" not in update_data and veiculo_destino:
        update_data["km_inicial"] = float(veiculo_destino.km_atual or 0)

    veiculo_antigo_id = contrato.veiculo_id

    for key, value in update_data.items():
        setattr(contrato, key, value)

    if not contrato.qtd_diarias or {"data_inicio", "data_fim", "tipo"} & set(update_data.keys()):
        contrato.qtd_diarias = (
            1
            if str(contrato.tipo or "").lower() == "empresa"
            else _calcular_qtd_diarias(nova_data_inicio, nova_data_fim)
        )

    if "valor_total" not in update_data and (
        {
            "data_inicio",
            "data_fim",
            "valor_diaria",
            "km_inicial",
            "km_final",
            "km_livres",
            "valor_km_excedente",
            "valor_avarias",
            "taxa_combustivel",
            "taxa_limpeza",
            "taxa_higienizacao",
            "taxa_pneus",
            "taxa_acessorios",
            "valor_franquia_seguro",
            "taxa_administrativa",
            "desconto",
        }
        & set(update_data.keys())
    ):
        contrato.valor_total = _calcular_valor_total(
            nova_data_inicio,
            nova_data_fim,
            float(novo_valor_diaria or 0),
            tipo=contrato.tipo,
            km_inicial=contrato.km_inicial,
            km_final=contrato.km_final,
            km_livres=contrato.km_livres,
            valor_km_excedente=contrato.valor_km_excedente,
            valor_avarias=contrato.valor_avarias,
            taxa_combustivel=contrato.taxa_combustivel,
            taxa_limpeza=contrato.taxa_limpeza,
            taxa_higienizacao=contrato.taxa_higienizacao,
            taxa_pneus=contrato.taxa_pneus,
            taxa_acessorios=contrato.taxa_acessorios,
            valor_franquia_seguro=contrato.valor_franquia_seguro,
            taxa_administrativa=contrato.taxa_administrativa,
            desconto=contrato.desconto,
        )

    _apply_payment_details(
        contrato,
        update_data,
        reference_date=contrato.data_finalizacao or contrato.data_fim,
    )

    db.flush()
    _sincronizar_uso_empresa(
        db,
        contrato,
        cliente,
        empresa_uso_id=empresa_uso_id,
        encerrar=contrato.status != "ativo",
    )
    _recalcular_status_veiculo(db, veiculo_antigo_id)
    _recalcular_status_veiculo(db, contrato.veiculo_id)

    db.commit()
    db.refresh(contrato)
    log_activity(
        db,
        current_user,
        "EDITAR",
        "Contrato",
        "Contrato {} editado".format(contrato.numero),
        contrato_id,
        request,
    )
    return contrato


@router.post("/{contrato_id}/encerrar", response_model=ContratoResponse)
@router.post("/{contrato_id}/finalizar", response_model=ContratoResponse)
def finalizar_contrato(
    contrato_id: int,
    payload: Optional[ContratoFinalizeRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Finalize a contract and register the vehicle return."""
    contrato = db.query(Contrato).filter(Contrato.id == contrato_id).first()
    if not contrato:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contrato nao encontrado",
        )

    if contrato.status != "ativo":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Somente contratos ativos podem ser encerrados",
        )

    veiculo = db.query(Veiculo).filter(Veiculo.id == contrato.veiculo_id).first()
    if not veiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Veiculo nao encontrado",
        )

    finalize_data = _normalize_finalizacao_payload(
        (payload or ContratoFinalizeRequest()).model_dump(exclude_unset=True)
    )
    data_finalizacao = finalize_data.get("data_finalizacao") or datetime.now()
    km_final = finalize_data.get("km_final")
    checklist_retorno = finalize_data.get("itens_checklist")

    if isinstance(checklist_retorno, dict):
        checklist_retorno = {
            str(chave): bool(valor)
            for chave, valor in checklist_retorno.items()
        }
    else:
        checklist_retorno = None

    if km_final is not None and contrato.km_inicial is not None and float(km_final) < float(contrato.km_inicial):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="KM atual nao pode ser menor que o KM de retirada",
        )

    if km_final is not None:
        contrato.km_final = float(km_final)
        veiculo.km_atual = float(km_final)

    if "combustivel_retorno" in finalize_data:
        contrato.combustivel_retorno = finalize_data.get("combustivel_retorno")
    if "valor_avarias" in finalize_data:
        contrato.valor_avarias = finalize_data.get("valor_avarias")
    if "taxa_combustivel" in finalize_data:
        contrato.taxa_combustivel = finalize_data.get("taxa_combustivel")
    if "taxa_limpeza" in finalize_data:
        contrato.taxa_limpeza = finalize_data.get("taxa_limpeza")
    if "taxa_higienizacao" in finalize_data:
        contrato.taxa_higienizacao = finalize_data.get("taxa_higienizacao")
    if "taxa_pneus" in finalize_data:
        contrato.taxa_pneus = finalize_data.get("taxa_pneus")
    if "taxa_acessorios" in finalize_data:
        contrato.taxa_acessorios = finalize_data.get("taxa_acessorios")
    if "valor_franquia_seguro" in finalize_data:
        contrato.valor_franquia_seguro = finalize_data.get("valor_franquia_seguro")
    if "taxa_administrativa" in finalize_data:
        contrato.taxa_administrativa = finalize_data.get("taxa_administrativa")
    if "desconto" in finalize_data:
        contrato.desconto = finalize_data.get("desconto")
    if finalize_data.get("observacoes"):
        contrato.observacoes = _append_observacao(
            contrato.observacoes,
            finalize_data.get("observacoes"),
            "Encerramento",
        )

    data_base_cobranca = max(contrato.data_fim, data_finalizacao)
    contrato.qtd_diarias = (
        1
        if str(contrato.tipo or "").lower() == "empresa"
        else _calcular_qtd_diarias(contrato.data_inicio, data_base_cobranca)
    )
    contrato.valor_total = _calcular_valor_total(
        contrato.data_inicio,
        data_base_cobranca,
        float(contrato.valor_diaria or 0),
        tipo=contrato.tipo,
        km_inicial=contrato.km_inicial,
        km_final=contrato.km_final,
        km_livres=contrato.km_livres,
        valor_km_excedente=contrato.valor_km_excedente,
        valor_avarias=contrato.valor_avarias,
        taxa_combustivel=contrato.taxa_combustivel,
        taxa_limpeza=contrato.taxa_limpeza,
        taxa_higienizacao=contrato.taxa_higienizacao,
        taxa_pneus=contrato.taxa_pneus,
        taxa_acessorios=contrato.taxa_acessorios,
        valor_franquia_seguro=contrato.valor_franquia_seguro,
        taxa_administrativa=contrato.taxa_administrativa,
        desconto=contrato.desconto,
    )
    contrato.status = "finalizado"
    contrato.data_finalizacao = data_finalizacao
    _apply_payment_details(contrato, finalize_data, reference_date=data_finalizacao)

    db.flush()
    db.add(
        CheckinCheckout(
            contrato_id=contrato.id,
            tipo="devolucao",
            data_hora=data_finalizacao,
            km=contrato.km_final if contrato.km_final is not None else veiculo.km_atual,
            nivel_combustivel=contrato.combustivel_retorno,
            itens_checklist=checklist_retorno or veiculo.checklist or {},
            avarias=finalize_data.get("observacoes"),
        )
    )
    cliente = _ensure_cliente_exists(db, contrato.cliente_id)
    _sincronizar_uso_empresa(db, contrato, cliente, encerrar=True)
    _recalcular_status_veiculo(db, contrato.veiculo_id)

    db.commit()
    db.refresh(contrato)
    log_activity(
        db,
        current_user,
        "EDITAR",
        "Contrato",
        "Contrato {} finalizado".format(contrato.numero),
        contrato_id,
        request,
    )
    return contrato


@router.patch("/{contrato_id}/pagamento", response_model=ContratoResponse)
def atualizar_pagamento_contrato(
    contrato_id: int,
    pagamento_data: ContratoPaymentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    contrato = db.query(Contrato).filter(Contrato.id == contrato_id).first()
    if not contrato:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contrato nao encontrado",
        )

    update_data = _normalize_contrato_payload(
        pagamento_data.model_dump(exclude_unset=True)
    )
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhum dado de pagamento informado",
        )

    _apply_payment_details(
        contrato,
        update_data,
        reference_date=contrato.data_finalizacao or contrato.data_fim or datetime.now(),
    )

    db.commit()
    db.refresh(contrato)
    log_activity(
        db,
        current_user,
        "EDITAR",
        "Contrato",
        "Pagamento do contrato {} atualizado".format(contrato.numero),
        contrato_id,
        request,
    )
    return contrato


@router.post("/{contrato_id}/prorrogar", response_model=ContratoResponse)
def prorrogar_contrato(
    contrato_id: int,
    data_nova: datetime,
    motivo: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Extend a contract."""
    contrato = db.query(Contrato).filter(Contrato.id == contrato_id).first()
    if not contrato:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contrato nao encontrado",
        )

    if data_nova <= contrato.data_fim:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nova data deve ser posterior a data de fim atual",
        )

    prorrogacao = ProrrogacaoContrato(
        contrato_id=contrato_id,
        data_anterior=contrato.data_fim,
        data_nova=data_nova,
        motivo=motivo,
    )
    db.add(prorrogacao)

    contrato.data_fim = data_nova
    contrato.qtd_diarias = (
        1
        if str(contrato.tipo or "").lower() == "empresa"
        else _calcular_qtd_diarias(contrato.data_inicio, data_nova)
    )
    if contrato.valor_diaria:
        contrato.valor_total = _calcular_valor_total(
            contrato.data_inicio,
            data_nova,
            float(contrato.valor_diaria),
            tipo=contrato.tipo,
            km_inicial=contrato.km_inicial,
            km_final=contrato.km_final,
            km_livres=contrato.km_livres,
            valor_km_excedente=contrato.valor_km_excedente,
            valor_avarias=contrato.valor_avarias,
            taxa_combustivel=contrato.taxa_combustivel,
            taxa_limpeza=contrato.taxa_limpeza,
            taxa_higienizacao=contrato.taxa_higienizacao,
            taxa_pneus=contrato.taxa_pneus,
            taxa_acessorios=contrato.taxa_acessorios,
            valor_franquia_seguro=contrato.valor_franquia_seguro,
            taxa_administrativa=contrato.taxa_administrativa,
            desconto=contrato.desconto,
        )

    db.commit()
    db.refresh(contrato)
    log_activity(
        db,
        current_user,
        "EDITAR",
        "Contrato",
        "Contrato {} prorrogado".format(contrato.numero),
        contrato_id,
        request,
    )
    return contrato


@router.get("/{contrato_id}/pdf")
def get_contrato_pdf(
    contrato_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate and download contract PDF."""
    del current_user
    contrato = db.query(Contrato).filter(Contrato.id == contrato_id).first()
    if not contrato:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contrato nao encontrado",
        )

    # Check contract type and generate appropriate PDF
    tipo_clean = str(contrato.tipo or "").strip("'\"").lower()
    if tipo_clean == "empresa":
        from app.services.pdf_contrato import PDFContratoService
        pdf_buffer = PDFContratoService.generate_contrato_empresa_pdf(db, contrato_id)
    else:
        pdf_buffer = PDFService.generate_contrato_pdf(db, contrato_id)

    pdf_buffer.seek(0)
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="contrato_{}.pdf"'.format(
                contrato.numero
            )
        },
    )


@router.get("/{contrato_id}/despesas", response_model=List[DespesaContratoResponse])
def get_contrato_despesas(
    contrato_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get expenses for a contract."""
    del current_user
    despesas = db.query(DespesaContrato).filter(
        DespesaContrato.contrato_id == contrato_id
    ).all()
    return despesas


@router.post("/{contrato_id}/despesas")
def add_contrato_despesa(
    contrato_id: int,
    tipo: str,
    descricao: str,
    valor: float,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Add expense to a contract."""
    contrato = db.query(Contrato).filter(Contrato.id == contrato_id).first()
    if not contrato:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contrato nao encontrado",
        )

    despesa = DespesaContrato(
        contrato_id=contrato_id,
        tipo=tipo,
        descricao=descricao,
        valor=valor,
        responsavel=current_user.email,
    )
    db.add(despesa)
    db.commit()
    db.refresh(despesa)
    log_activity(
        db,
        current_user,
        "CRIAR",
        "DespesaContrato",
        "Despesa de contrato criada: {}".format(descricao),
        despesa.id,
        request,
    )
    return despesa


@router.delete("/{contrato_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contrato(
    contrato_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Delete a contract without relying on DB cascades."""
    contrato = db.query(Contrato).filter(Contrato.id == contrato_id).first()
    if not contrato:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contrato nao encontrado",
        )

    numero = contrato.numero
    veiculo_id = contrato.veiculo_id

    db.query(Quilometragem).filter(
        Quilometragem.contrato_id == contrato_id
    ).delete(synchronize_session=False)
    db.query(DespesaContrato).filter(
        DespesaContrato.contrato_id == contrato_id
    ).delete(synchronize_session=False)
    db.query(ProrrogacaoContrato).filter(
        ProrrogacaoContrato.contrato_id == contrato_id
    ).delete(synchronize_session=False)
    db.query(CheckinCheckout).filter(
        CheckinCheckout.contrato_id == contrato_id
    ).delete(synchronize_session=False)
    db.query(UsoVeiculoEmpresa).filter(
        UsoVeiculoEmpresa.contrato_id == contrato_id
    ).update({UsoVeiculoEmpresa.contrato_id: None}, synchronize_session=False)
    db.query(Multa).filter(
        Multa.contrato_id == contrato_id
    ).delete(synchronize_session=False)

    db.delete(contrato)
    db.flush()
    _recalcular_status_veiculo(db, veiculo_id)

    db.commit()
    log_activity(
        db,
        current_user,
        "EXCLUIR",
        "Contrato",
        "Contrato {} excluido".format(numero),
        contrato_id,
        request,
    )
