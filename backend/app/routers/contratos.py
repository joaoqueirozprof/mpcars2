from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.pagination import paginate
from app.models.user import User
from app.models import (
    Contrato,
    Cliente,
    Veiculo,
    DespesaContrato,
    Quilometragem,
    ProrrogacaoContrato,
    CheckinCheckout,
    Multa,
    UsoVeiculoEmpresa,
)
from app.services.pdf_service import PDFService
from app.services.activity_logger import log_activity


router = APIRouter(prefix="/contratos", tags=["Contratos"])


class ContratoBase(BaseModel):
    numero: str
    cliente_id: int
    veiculo_id: int
    data_inicio: datetime
    data_fim: datetime
    km_inicial: Optional[float] = None
    km_final: Optional[float] = None
    valor_diaria: float
    valor_total: Optional[float] = None
    status: str = "ativo"
    observacoes: Optional[str] = None


class ContratoCreate(ContratoBase):
    pass


class ContratoUpdate(BaseModel):
    data_fim: Optional[datetime] = None
    km_final: Optional[float] = None
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


def _validar_datas(data_inicio: datetime, data_fim: datetime):
    """Valida que data_inicio < data_fim."""
    if data_inicio >= data_fim:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Data de início deve ser anterior à data de fim",
        )


def _calcular_valor_total(data_inicio: datetime, data_fim: datetime, valor_diaria: float) -> float:
    """Calcula valor total baseado em dias e diária."""
    dias = max(1, (data_fim - data_inicio).days)
    return round(dias * valor_diaria, 2)


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
    """Create a new contract.

    CORRIGIDO:
    - Validação de datas (data_inicio < data_fim)
    - Auto-cálculo de valor_total se não fornecido
    - Auto-atualiza status do veículo para 'alugado'
    - Verifica se veículo está disponível
    """
    # Validar datas
    _validar_datas(contrato.data_inicio, contrato.data_fim)

    existing = db.query(Contrato).filter(Contrato.numero == contrato.numero).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Número de contrato já existe",
        )

    # Verificar se veículo existe e está disponível
    veiculo = db.query(Veiculo).filter(Veiculo.id == contrato.veiculo_id).first()
    if not veiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Veículo não encontrado"
        )
    if veiculo.status not in ("disponivel", "reservado"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Veículo não está disponível (status atual: {})".format(veiculo.status),
        )

    # Verificar se cliente existe
    cliente = db.query(Cliente).filter(Cliente.id == contrato.cliente_id).first()
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado"
        )

    # Auto-calcular valor_total se não fornecido
    contrato_data = contrato.model_dump()
    if not contrato_data.get("valor_total"):
        contrato_data["valor_total"] = _calcular_valor_total(
            contrato.data_inicio, contrato.data_fim, contrato.valor_diaria
        )

    db_contrato = Contrato(**contrato_data)
    db.add(db_contrato)

    # Atualizar status do veículo para 'alugado'
    veiculo.status = "alugado"

    db.commit()
    db.refresh(db_contrato)
    log_activity(db, current_user, "CRIAR", "Contrato", "Contrato {} criado".format(db_contrato.numero), db_contrato.id, request)
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

    update_data = contrato_data.model_dump(exclude_unset=True)

    # Validar datas se ambas estiverem sendo atualizadas
    new_data_fim = update_data.get("data_fim", contrato.data_fim)
    if new_data_fim and contrato.data_inicio and new_data_fim <= contrato.data_inicio:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Data de fim deve ser posterior à data de início",
        )

    for key, value in update_data.items():
        setattr(contrato, key, value)

    db.commit()
    db.refresh(contrato)
    log_activity(db, current_user, "EDITAR", "Contrato", "Contrato {} editado".format(contrato.numero), contrato_id, request)
    return contrato


@router.post("/{contrato_id}/finalizar")
def finalizar_contrato(
    contrato_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Finalize a contract.

    CORRIGIDO: Agora atualiza o status do veículo para 'disponivel'.
    """
    contrato = db.query(Contrato).filter(Contrato.id == contrato_id).first()
    if not contrato:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contrato não encontrado"
        )

    contrato.status = "finalizado"
    contrato.data_finalizacao = datetime.now()

    # Verificar se o veículo tem outros contratos ativos
    outros_ativos = db.query(Contrato).filter(
        Contrato.veiculo_id == contrato.veiculo_id,
        Contrato.id != contrato_id,
        Contrato.status == "ativo",
    ).count()

    # Se não tem outros contratos ativos, liberar o veículo
    if outros_ativos == 0:
        veiculo = db.query(Veiculo).filter(Veiculo.id == contrato.veiculo_id).first()
        if veiculo and veiculo.status == "alugado":
            veiculo.status = "disponivel"

    db.commit()
    db.refresh(contrato)
    log_activity(db, current_user, "EDITAR", "Contrato", "Contrato {} finalizado".format(contrato.numero), contrato_id, request)
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
    """Extend a contract.

    CORRIGIDO: Agora recalcula qtd_diarias e valor_total proporcionalmente.
    """
    contrato = db.query(Contrato).filter(Contrato.id == contrato_id).first()
    if not contrato:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contrato não encontrado"
        )

    if data_nova <= contrato.data_fim:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nova data deve ser posterior à data de fim atual ({})".format(contrato.data_fim),
        )

    prorrogacao = ProrrogacaoContrato(
        contrato_id=contrato_id,
        data_anterior=contrato.data_fim,
        data_nova=data_nova,
        motivo=motivo,
    )
    db.add(prorrogacao)

    # Recalcular valor_total e qtd_diarias
    contrato.data_fim = data_nova
    if contrato.valor_diaria:
        novo_total = _calcular_valor_total(contrato.data_inicio, data_nova, float(contrato.valor_diaria))
        contrato.valor_total = novo_total

    db.commit()
    db.refresh(contrato)
    log_activity(db, current_user, "EDITAR", "Contrato", "Contrato {} prorrogado até {}".format(contrato.numero, data_nova), contrato_id, request)
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
    log_activity(db, current_user, "CRIAR", "DespesaContrato", "Despesa de contrato criada: {}".format(descricao), despesa.id, request)
    return despesa


@router.delete("/{contrato_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contrato(
    contrato_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Delete a contract.

    CORRIGIDO: Com CASCADE configurado nos models, o banco deleta
    automaticamente todos os registros dependentes.
    Também libera o veículo se não houver outros contratos ativos.
    """
    contrato = db.query(Contrato).filter(Contrato.id == contrato_id).first()
    if not contrato:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contrato não encontrado"
        )

    # Liberar veículo se era o único contrato ativo
    if contrato.status == "ativo":
        outros_ativos = db.query(Contrato).filter(
            Contrato.veiculo_id == contrato.veiculo_id,
            Contrato.id != contrato_id,
            Contrato.status == "ativo",
        ).count()
        if outros_ativos == 0:
            veiculo = db.query(Veiculo).filter(Veiculo.id == contrato.veiculo_id).first()
            if veiculo and veiculo.status == "alugado":
                veiculo.status = "disponivel"

    numero = contrato.numero
    # CASCADE handles dependent deletions automatically
    db.delete(contrato)
    db.commit()
    log_activity(db, current_user, "EXCLUIR", "Contrato", "Contrato {} excluído".format(numero), contrato_id, request)
