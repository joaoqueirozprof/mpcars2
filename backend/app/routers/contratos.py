import math
from datetime import datetime, timedelta
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
    Multa,
    ProrrogacaoContrato,
    Quilometragem,
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
    data_fim: datetime
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
    desconto: Optional[float] = None
    tipo: Optional[str] = "cliente"


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
    desconto: Optional[float] = None
    tipo: Optional[str] = None


class ContratoFinalizeRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    km_final: Optional[float] = None
    quilometragem_final: Optional[float] = None
    km_atual_veiculo: Optional[float] = None
    combustivel_retorno: Optional[str] = None
    valor_avarias: Optional[float] = None
    desconto: Optional[float] = None
    observacoes: Optional[str] = None
    data_finalizacao: Optional[datetime] = None


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
    km_inicial: Optional[float] = None,
    km_final: Optional[float] = None,
    km_livres: Optional[float] = None,
    valor_km_excedente: Optional[float] = None,
    valor_avarias: Optional[float] = None,
    desconto: Optional[float] = None,
) -> float:
    qtd_diarias = _calcular_qtd_diarias(data_inicio, data_fim)
    total_base = qtd_diarias * float(valor_diaria or 0)
    km_excedente = _calcular_km_excedente(km_inicial, km_final, km_livres)
    total_km = km_excedente * float(valor_km_excedente or 0)
    total = total_base + total_km + float(valor_avarias or 0) - float(desconto or 0)
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
        elif key in {"status", "tipo"} and isinstance(value, str):
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
        normalized[key] = None if value == "" else value

    return normalized


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


def _ensure_cliente_exists(db: Session, cliente_id: int):
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente nao encontrado",
        )


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
    contrato_data = _normalize_contrato_payload(
        contrato.model_dump(exclude_unset=True),
        is_create=True,
    )
    _validar_datas(contrato_data["data_inicio"], contrato_data["data_fim"])

    existing = db.query(Contrato).filter(Contrato.numero == contrato_data["numero"]).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Numero de contrato ja existe",
        )

    _ensure_cliente_exists(db, contrato_data["cliente_id"])
    veiculo = _ensure_veiculo_available(db, contrato_data["veiculo_id"])

    if contrato_data.get("km_inicial") is None:
        contrato_data["km_inicial"] = float(veiculo.km_atual or 0)

    if not contrato_data.get("qtd_diarias"):
        contrato_data["qtd_diarias"] = _calcular_qtd_diarias(
            contrato_data["data_inicio"],
            contrato_data["data_fim"],
        )

    if not contrato_data.get("valor_total"):
        contrato_data["valor_total"] = _calcular_valor_total(
            contrato_data["data_inicio"],
            contrato_data["data_fim"],
            float(contrato_data["valor_diaria"]),
            km_inicial=contrato_data.get("km_inicial"),
            km_final=contrato_data.get("km_final"),
            km_livres=contrato_data.get("km_livres"),
            valor_km_excedente=contrato_data.get("valor_km_excedente"),
            valor_avarias=contrato_data.get("valor_avarias"),
            desconto=contrato_data.get("desconto"),
        )

    db_contrato = Contrato(**contrato_data)
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

    update_data = _normalize_contrato_payload(contrato_data.model_dump(exclude_unset=True))

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

    _validar_datas(nova_data_inicio, nova_data_fim)
    _ensure_cliente_exists(db, novo_cliente_id)

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

    if not contrato.qtd_diarias or {"data_inicio", "data_fim"} & set(update_data.keys()):
        contrato.qtd_diarias = _calcular_qtd_diarias(nova_data_inicio, nova_data_fim)

    if "valor_total" not in update_data and (
        {"data_inicio", "data_fim", "valor_diaria", "km_inicial", "km_final", "km_livres", "valor_km_excedente", "valor_avarias", "desconto"}
        & set(update_data.keys())
    ):
        contrato.valor_total = _calcular_valor_total(
            nova_data_inicio,
            nova_data_fim,
            float(novo_valor_diaria or 0),
            km_inicial=contrato.km_inicial,
            km_final=contrato.km_final,
            km_livres=contrato.km_livres,
            valor_km_excedente=contrato.valor_km_excedente,
            valor_avarias=contrato.valor_avarias,
            desconto=contrato.desconto,
        )

    db.flush()
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
    if "desconto" in finalize_data:
        contrato.desconto = finalize_data.get("desconto")
    if finalize_data.get("observacoes"):
        contrato.observacoes = _append_observacao(
            contrato.observacoes,
            finalize_data.get("observacoes"),
            "Encerramento",
        )

    data_base_cobranca = max(contrato.data_fim, data_finalizacao)
    contrato.qtd_diarias = _calcular_qtd_diarias(contrato.data_inicio, data_base_cobranca)
    contrato.valor_total = _calcular_valor_total(
        contrato.data_inicio,
        data_base_cobranca,
        float(contrato.valor_diaria or 0),
        km_inicial=contrato.km_inicial,
        km_final=contrato.km_final,
        km_livres=contrato.km_livres,
        valor_km_excedente=contrato.valor_km_excedente,
        valor_avarias=contrato.valor_avarias,
        desconto=contrato.desconto,
    )
    contrato.status = "finalizado"
    contrato.data_finalizacao = data_finalizacao

    db.flush()
    db.add(
        CheckinCheckout(
            contrato_id=contrato.id,
            tipo="devolucao",
            data_hora=data_finalizacao,
            km=contrato.km_final if contrato.km_final is not None else veiculo.km_atual,
            nivel_combustivel=contrato.combustivel_retorno,
            avarias=finalize_data.get("observacoes"),
        )
    )
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
    contrato.qtd_diarias = _calcular_qtd_diarias(contrato.data_inicio, data_nova)
    if contrato.valor_diaria:
        contrato.valor_total = _calcular_valor_total(
            contrato.data_inicio,
            data_nova,
            float(contrato.valor_diaria),
            km_inicial=contrato.km_inicial,
            km_final=contrato.km_final,
            km_livres=contrato.km_livres,
            valor_km_excedente=contrato.valor_km_excedente,
            valor_avarias=contrato.valor_avarias,
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
