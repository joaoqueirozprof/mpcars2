from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict
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
    km_final: Optional[float] = None
    quilometragem_final: Optional[float] = None
    valor_diaria: float
    valor_total: Optional[float] = None
    status: str = "ativo"
    observacoes: Optional[str] = None


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
    km_final: Optional[float] = None
    quilometragem_final: Optional[float] = None
    valor_diaria: Optional[float] = None
    valor_total: Optional[float] = None
    status: Optional[str] = None
    observacoes: Optional[str] = None


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
            detail="Data de início deve ser anterior à data de fim",
        )


def _calcular_valor_total(data_inicio: datetime, data_fim: datetime, valor_diaria: float) -> float:
    dias = max(1, (data_fim - data_inicio).days)
    return round(dias * valor_diaria, 2)


def _normalize_contrato_payload(payload: dict, is_create: bool = False) -> dict:
    data = dict(payload)

    if data.get("km_inicial") is None and data.get("quilometragem_inicial") is not None:
        data["km_inicial"] = data.pop("quilometragem_inicial")
    else:
        data.pop("quilometragem_inicial", None)

    if data.get("km_final") is None and data.get("quilometragem_final") is not None:
        data["km_final"] = data.pop("quilometragem_final")
    else:
        data.pop("quilometragem_final", None)

    if is_create and not data.get("numero"):
        data["numero"] = _generate_numero_contrato()

    normalized = {}
    for key, value in data.items():
        normalized[key] = None if value == "" else value

    return normalized


def _ensure_cliente_exists(db: Session, cliente_id: int):
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado"
        )


def _ensure_veiculo_available(db: Session, veiculo_id: int, contrato_id: Optional[int] = None) -> Veiculo:
    veiculo = db.query(Veiculo).filter(Veiculo.id == veiculo_id).first()
    if not veiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Veículo não encontrado"
        )

    contrato_ativo = db.query(Contrato).filter(
        Contrato.veiculo_id == veiculo_id,
        Contrato.status == "ativo",
        Contrato.id != contrato_id,
    ).first()
    if contrato_ativo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Veículo já possui contrato ativo (#{})".format(contrato_ativo.numero),
        )

    if contrato_id is None and veiculo.status not in {"disponivel", "reservado"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Veículo não está disponível (status atual: {})".format(veiculo.status),
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
    query = db.query(Contrato).options(joinedload(Contrato.cliente), joinedload(Contrato.veiculo))
    return paginate(
        query=query,
        page=page,
        limit=limit,
        search=search,
        search_fields=["numero"],
        model=Contrato,
        status_filter=status_filter,
    )


@router.get("/atrasados", response_model=List[ContratoResponse])
def get_atrasados(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get overdue contracts."""
    agora = datetime.now()
    contratos = db.query(Contrato).filter(
        (Contrato.data_fim < agora) & (Contrato.status == "ativo")
    ).all()
    return contratos


@router.get("/vencimentos", response_model=List[ContratoResponse])
def get_vencimentos(
    dias: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get contracts expiring within specified days."""
    from datetime import timedelta

    agora = datetime.now()
    fim = agora + timedelta(days=dias)
    contratos = db.query(Contrato).filter(
        (Contrato.data_fim.between(agora, fim)) & (Contrato.status == "ativo")
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
            detail="Número de contrato já existe",
        )

    _ensure_cliente_exists(db, contrato_data["cliente_id"])
    veiculo = _ensure_veiculo_available(db, contrato_data["veiculo_id"])

    if not contrato_data.get("valor_total"):
        contrato_data["valor_total"] = _calcular_valor_total(
            contrato_data["data_inicio"],
            contrato_data["data_fim"],
            float(contrato_data["valor_diaria"]),
        )

    db_contrato = Contrato(**contrato_data)
    db.add(db_contrato)
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
    contrato = db.query(Contrato).filter(Contrato.id == contrato_id).first()
    if not contrato:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contrato não encontrado"
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
            status_code=status.HTTP_404_NOT_FOUND, detail="Contrato não encontrado"
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
                detail="Número de contrato já existe",
            )

    novo_cliente_id = update_data.get("cliente_id", contrato.cliente_id)
    novo_veiculo_id = update_data.get("veiculo_id", contrato.veiculo_id)
    nova_data_inicio = update_data.get("data_inicio", contrato.data_inicio)
    nova_data_fim = update_data.get("data_fim", contrato.data_fim)
    novo_status = update_data.get("status", contrato.status)
    novo_valor_diaria = update_data.get("valor_diaria", contrato.valor_diaria)

    _validar_datas(nova_data_inicio, nova_data_fim)
    _ensure_cliente_exists(db, novo_cliente_id)

    if novo_status == "ativo":
        _ensure_veiculo_available(db, novo_veiculo_id, contrato_id=contrato_id)

    veiculo_antigo_id = contrato.veiculo_id

    for key, value in update_data.items():
        setattr(contrato, key, value)

    if (
        "valor_total" not in update_data
        and (
            "data_inicio" in update_data
            or "data_fim" in update_data
            or "valor_diaria" in update_data
        )
    ):
        contrato.valor_total = _calcular_valor_total(
            nova_data_inicio,
            nova_data_fim,
            float(novo_valor_diaria),
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


@router.post("/{contrato_id}/finalizar")
def finalizar_contrato(
    contrato_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Finalize a contract."""
    contrato = db.query(Contrato).filter(Contrato.id == contrato_id).first()
    if not contrato:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contrato não encontrado"
        )

    contrato.status = "finalizado"
    contrato.data_finalizacao = datetime.now()
    db.flush()
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


@router.post("/{contrato_id}/prorrogar")
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
            status_code=status.HTTP_404_NOT_FOUND, detail="Contrato não encontrado"
        )

    if data_nova <= contrato.data_fim:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nova data deve ser posterior à data de fim atual",
        )

    prorrogacao = ProrrogacaoContrato(
        contrato_id=contrato_id,
        data_anterior=contrato.data_fim,
        data_nova=data_nova,
        motivo=motivo,
    )
    db.add(prorrogacao)

    contrato.data_fim = data_nova
    if contrato.valor_diaria:
        contrato.valor_total = _calcular_valor_total(
            contrato.data_inicio,
            data_nova,
            float(contrato.valor_diaria),
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
    contrato = db.query(Contrato).filter(Contrato.id == contrato_id).first()
    if not contrato:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contrato não encontrado"
        )

    pdf_buffer = PDFService.generate_contrato_pdf(db, contrato_id)
    pdf_buffer.seek(0)
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="contrato_{}.pdf"'.format(contrato.numero)},
    )


@router.get("/{contrato_id}/despesas", response_model=List[DespesaContratoResponse])
def get_contrato_despesas(
    contrato_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get expenses for a contract."""
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
            status_code=status.HTTP_404_NOT_FOUND, detail="Contrato não encontrado"
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
            status_code=status.HTTP_404_NOT_FOUND, detail="Contrato não encontrado"
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
        "Contrato {} excluído".format(numero),
        contrato_id,
        request,
    )
