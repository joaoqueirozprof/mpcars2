from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_page_access
from app.models import (
    CheckinCheckout,
    Cliente,
    Contrato,
    DespesaContrato,
    DespesaLoja,
    DespesaNF,
    DespesaVeiculo,
    Empresa,
    IpvaRegistro,
    LancamentoFinanceiro,
    Manutencao,
    Multa,
    RelatorioNF,
    Seguro,
    ProrrogacaoContrato,
    Quilometragem,
    UsoVeiculoEmpresa,
    Veiculo,
)
from app.models.user import User
from app.services.activity_logger import log_activity
from app.services.export_service import ExportService
from app.services.pdf_service import PDFService


router = APIRouter(
    prefix="/financeiro",
    tags=["Financeiro"],
    dependencies=[Depends(require_page_access("financeiro"))],
)


class DespesaContratoCreate(BaseModel):
    contrato_id: int
    tipo: str
    descricao: str
    valor: float


class DespesaVeiculoCreate(BaseModel):
    veiculo_id: int
    descricao: str
    valor: float
    km: Optional[float] = None
    pneu: bool = False


class DespesaLojaCreate(BaseModel):
    mes: int
    ano: int
    descricao: str
    valor: float


class LancamentoFinanceiroBase(BaseModel):
    model_config = ConfigDict(extra="ignore")

    tipo: str
    categoria: str
    descricao: str
    valor: float
    data: date
    status: str = "pendente"


class LancamentoFinanceiroCreate(LancamentoFinanceiroBase):
    pass


class LancamentoFinanceiroUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    tipo: Optional[str] = None
    categoria: Optional[str] = None
    descricao: Optional[str] = None
    valor: Optional[float] = None
    data: Optional[date] = None
    status: Optional[str] = None


def _parse_date_range(
    *,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    mes: Optional[int] = None,
    ano: Optional[int] = None,
):
    start_date = None
    end_date = None

    if data_inicio:
        start_date = datetime.strptime(data_inicio, "%Y-%m-%d").date()
    if data_fim:
        end_date = datetime.strptime(data_fim, "%Y-%m-%d").date()

    if mes and ano:
        start_date = date(ano, mes, 1)
        if mes == 12:
            end_date = date(ano + 1, 1, 1)
        else:
            end_date = date(ano, mes + 1, 1)

    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Data inicial nao pode ser maior que a data final",
        )

    return start_date, end_date


def _record_in_period(record_date: Optional[str], start_date: Optional[date], end_date: Optional[date]) -> bool:
    if not start_date and not end_date:
        return True
    if not record_date:
        return False

    current = datetime.fromisoformat(record_date).date()
    if start_date and current < start_date:
        return False
    if end_date and current >= end_date:
        return False
    return True


def _vehicle_label(veiculo: Optional[Veiculo]) -> str:
    if not veiculo:
        return "Veiculo nao identificado"
    parts = [veiculo.placa]
    modelo = " ".join(part for part in [veiculo.marca, veiculo.modelo] if part)
    if modelo:
        parts.append(modelo)
    return " - ".join(parts)


def _append_manual_records(records: list, db: Session):
    lancamentos = db.query(LancamentoFinanceiro).all()
    for lancamento in lancamentos:
        records.append(
            {
                "id": f"fm-{lancamento.id}",
                "data": lancamento.data.isoformat() if lancamento.data else None,
                "tipo": lancamento.tipo,
                "categoria": lancamento.categoria,
                "descricao": lancamento.descricao,
                "valor": float(lancamento.valor) if lancamento.valor else 0.0,
                "status": lancamento.status,
                "origem_tipo": "manual",
            }
        )


def _merge_date_with_existing(date_value: Optional[date], current_value: Optional[datetime]) -> Optional[datetime]:
    if date_value is None:
        return current_value

    current_time = current_value.time() if current_value else datetime.min.time()
    return datetime.combine(date_value, current_time)


def _parse_finance_category_suffix(category: Optional[str], fallback: Optional[str] = None) -> Optional[str]:
    if not category:
        return fallback

    if "/" in category:
        _, suffix = category.split("/", 1)
        cleaned_suffix = suffix.strip().lower()
        return cleaned_suffix or fallback

    cleaned_category = category.strip().lower()
    return cleaned_category or fallback


def _normalize_source_status(record_id: str, status_value: Optional[str], current_status: Optional[str] = None) -> Optional[str]:
    if status_value is None:
        return current_status

    normalized = str(status_value).lower()
    prefix = record_id.split("-", 1)[0]

    if prefix == "mt":
        if normalized == "pago":
            return "concluida"
        if normalized == "cancelado":
            return "cancelada"
        if current_status in {"pendente", "agendada", "em_andamento"}:
            return current_status
        return "agendada"

    if prefix in {"ip", "sg"}:
        return "pago" if normalized == "pago" else "pendente"

    if prefix == "ml":
        if normalized == "pago":
            return "pago"
        if normalized == "cancelado":
            return "recurso"
        return "pendente"

    return normalized


def _serialize_updated_finance_record(record_id: str, obj, db: Session) -> dict:
    prefix = record_id.split("-", 1)[0]

    if prefix == "fm":
        return {
            "id": f"fm-{obj.id}",
            "data": obj.data.isoformat() if obj.data else None,
            "tipo": obj.tipo,
            "categoria": obj.categoria,
            "descricao": obj.descricao,
            "valor": float(obj.valor or 0.0),
            "status": obj.status,
            "origem_tipo": "manual",
        }

    if prefix == "dc":
        return {
            "id": f"dc-{obj.id}",
            "data": obj.data_registro.isoformat() if obj.data_registro else None,
            "tipo": "despesa",
            "categoria": obj.tipo or "Contrato",
            "descricao": obj.descricao,
            "valor": float(obj.valor or 0.0),
            "status": "pago",
            "origem_tipo": "despesa_contrato",
            "contrato_id": str(obj.contrato_id) if obj.contrato_id else None,
        }

    if prefix == "dv":
        return {
            "id": f"dv-{obj.id}",
            "data": obj.data.isoformat() if obj.data else None,
            "tipo": "despesa",
            "categoria": obj.tipo or "Veiculo",
            "descricao": obj.descricao,
            "valor": float(obj.valor or 0.0),
            "status": "pago",
            "origem_tipo": "despesa_veiculo",
            "veiculo_id": str(obj.veiculo_id) if obj.veiculo_id else None,
        }

    if prefix == "dl":
        return {
            "id": f"dl-{obj.id}",
            "data": obj.data.isoformat() if obj.data else None,
            "tipo": "despesa",
            "categoria": obj.categoria or "Loja",
            "descricao": obj.descricao,
            "valor": float(obj.valor or 0.0),
            "status": "pago",
            "origem_tipo": "despesa_loja",
        }

    if prefix == "mt":
        veiculo = db.query(Veiculo).filter(Veiculo.id == obj.veiculo_id).first() if obj.veiculo_id else None
        return {
            "id": f"mt-{obj.id}",
            "data": (
                obj.data_realizada.isoformat()
                if obj.data_realizada
                else obj.data_proxima.isoformat()
                if obj.data_proxima
                else None
            ),
            "tipo": "despesa",
            "categoria": "Manutencao / {}".format((obj.tipo or "pendente").title()),
            "descricao": f"{obj.descricao} | {_vehicle_label(veiculo)}" if veiculo else obj.descricao,
            "valor": float(obj.custo or 0.0),
            "status": "pago" if obj.status == "concluida" else "pendente",
            "veiculo_id": str(obj.veiculo_id) if obj.veiculo_id else None,
            "origem_tipo": "manutencao",
        }

    if prefix == "ip":
        veiculo = db.query(Veiculo).filter(Veiculo.id == obj.veiculo_id).first() if obj.veiculo_id else None
        return {
            "id": f"ip-{obj.id}",
            "data": (
                obj.data_pagamento.isoformat()
                if obj.data_pagamento
                else obj.data_vencimento.isoformat()
                if obj.data_vencimento
                else None
            ),
            "tipo": "despesa",
            "categoria": "IPVA",
            "descricao": f"IPVA {obj.ano_referencia or ''} | {_vehicle_label(veiculo)}".strip(),
            "valor": float(obj.valor_ipva or obj.valor_pago or 0.0),
            "status": "pago" if obj.status == "pago" else "pendente",
            "veiculo_id": str(obj.veiculo_id) if obj.veiculo_id else None,
            "origem_tipo": "ipva",
        }

    if prefix == "sg":
        veiculo = db.query(Veiculo).filter(Veiculo.id == obj.veiculo_id).first() if obj.veiculo_id else None
        return {
            "id": f"sg-{obj.id}",
            "data": obj.data_inicio.isoformat() if obj.data_inicio else None,
            "tipo": "despesa",
            "categoria": "Seguro",
            "descricao": f"{obj.seguradora or 'Seguro'} - {obj.numero_apolice or 'sem apolice'} | {_vehicle_label(veiculo)}" if veiculo else (obj.seguradora or "Seguro"),
            "valor": float(obj.valor or 0.0),
            "status": "pago" if obj.status == "pago" else "pendente",
            "veiculo_id": str(obj.veiculo_id) if obj.veiculo_id else None,
            "origem_tipo": "seguro",
        }

    if prefix == "ml":
        veiculo = db.query(Veiculo).filter(Veiculo.id == obj.veiculo_id).first() if obj.veiculo_id else None
        return {
            "id": f"ml-{obj.id}",
            "data": (
                obj.data_pagamento.isoformat()
                if obj.data_pagamento
                else obj.data_vencimento.isoformat()
                if obj.data_vencimento
                else obj.data_infracao.isoformat()
                if obj.data_infracao
                else None
            ),
            "tipo": "despesa",
            "categoria": "Multa",
            "descricao": f"{obj.descricao or 'Multa'} | {_vehicle_label(veiculo)}" if veiculo else (obj.descricao or "Multa"),
            "valor": float(obj.valor or 0.0),
            "status": "pago" if obj.status == "pago" else "pendente",
            "veiculo_id": str(obj.veiculo_id) if obj.veiculo_id else None,
            "contrato_id": str(obj.contrato_id) if obj.contrato_id else None,
            "origem_tipo": "multa",
        }

    raise HTTPException(status_code=400, detail="Tipo de registro desconhecido")


def _contrato_payment_status(contrato: Contrato) -> str:
    if contrato.status_pagamento:
        return str(contrato.status_pagamento).lower()
    if contrato.status == "finalizado":
        return "pago"
    return "pendente"


def _serialize_contrato_record(contrato: Contrato, cliente_nome: str) -> dict:
    payment_status = _contrato_payment_status(contrato)
    data_referencia = (
        contrato.data_pagamento.isoformat()
        if contrato.data_pagamento
        else contrato.data_vencimento_pagamento.isoformat()
        if contrato.data_vencimento_pagamento
        else contrato.data_finalizacao.isoformat()
        if contrato.data_finalizacao
        else contrato.data_criacao.isoformat()
        if contrato.data_criacao
        else None
    )
    forma_pagamento = contrato.forma_pagamento
    categoria = "Locacao"
    if forma_pagamento:
        categoria = "Locacao / {}".format(forma_pagamento.title())

    return {
        "id": f"c-{contrato.id}",
        "data": data_referencia,
        "tipo": "receita",
        "categoria": categoria,
        "descricao": f"Contrato #{contrato.numero} - {cliente_nome}",
        "valor": float(contrato.valor_total) if contrato.valor_total else 0.0,
        "valor_recebido": float(contrato.valor_recebido or 0.0),
        "status": payment_status,
        "contrato_id": str(contrato.id),
        "veiculo_id": str(contrato.veiculo_id) if contrato.veiculo_id else None,
        "origem_tipo": "contrato",
        "forma_pagamento": forma_pagamento,
        "data_pagamento": contrato.data_pagamento.isoformat() if contrato.data_pagamento else None,
        "data_vencimento_pagamento": (
            contrato.data_vencimento_pagamento.isoformat()
            if contrato.data_vencimento_pagamento
            else None
        ),
    }


def _relatorio_nf_total(relatorio: RelatorioNF, uso: Optional[UsoVeiculoEmpresa]) -> float:
    valor_base = float(uso.valor_diaria_empresa or 0) if uso else 0.0
    valor_extra = float(relatorio.valor_total_extra or 0)
    return round(valor_base + valor_extra, 2)


def _serialize_relatorio_nf_record(
    relatorio: RelatorioNF,
    uso: Optional[UsoVeiculoEmpresa],
    veiculo: Optional[Veiculo],
    empresa: Optional[Empresa],
) -> dict:
    periodo_inicio = relatorio.periodo_inicio.strftime("%d/%m/%Y") if relatorio.periodo_inicio else "-"
    periodo_fim = relatorio.periodo_fim.strftime("%d/%m/%Y") if relatorio.periodo_fim else "-"
    referencia = (
        relatorio.periodo_fim.isoformat()
        if relatorio.periodo_fim
        else relatorio.data_criacao.isoformat()
        if relatorio.data_criacao
        else None
    )
    km_texto = float(relatorio.km_percorrida or 0)
    km_excedente = float(relatorio.km_excedente or 0)
    empresa_nome = empresa.nome if empresa else "Empresa"
    veiculo_nome = _vehicle_label(veiculo)
    return {
        "id": f"nf-{relatorio.id}",
        "data": referencia,
        "tipo": "receita",
        "categoria": "Faturamento empresa",
        "descricao": (
            f"NF {empresa_nome} | {veiculo_nome} | Periodo {periodo_inicio} a {periodo_fim} | "
            f"KM {km_texto:,.1f} | Excedente {km_excedente:,.1f}"
        ),
        "valor": _relatorio_nf_total(relatorio, uso),
        "valor_recebido": 0.0,
        "status": "pendente",
        "veiculo_id": str(relatorio.veiculo_id) if relatorio.veiculo_id else None,
        "origem_tipo": "nf_empresa",
    }


@router.get("/")
def list_financeiro(
    page: int = 1,
    limit: int = 50,
    tipo: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    mes: Optional[int] = None,
    ano: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get paginated financial records (consolidated view)."""
    del current_user
    start_date, end_date = _parse_date_range(
        data_inicio=data_inicio,
        data_fim=data_fim,
        mes=mes,
        ano=ano,
    )
    records = []

    contratos = db.query(Contrato).all()
    for contrato in contratos:
        if str(contrato.tipo or "").lower() == "empresa":
            continue
        cliente = db.query(Cliente).filter(Cliente.id == contrato.cliente_id).first() if contrato.cliente_id else None
        cliente_nome = cliente.nome if cliente else "Desconhecido"
        records.append(
            {
                "id": f"c-{contrato.id}",
                "data": contrato.data_criacao.isoformat() if contrato.data_criacao else None,
                "tipo": "receita",
                "categoria": "Locação",
                "descricao": f"Contrato #{contrato.numero} - {cliente_nome}",
                "valor": float(contrato.valor_total) if contrato.valor_total else 0.0,
                "status": "pago" if contrato.status == "finalizado" else "pendente",
            }
        )

    relatorios_nf = db.query(RelatorioNF).all()
    uso_ids = [relatorio.uso_id for relatorio in relatorios_nf if relatorio.uso_id]
    usos_empresa = {}
    empresas = {}
    veiculos_nf = {}
    if uso_ids:
        for uso in db.query(UsoVeiculoEmpresa).filter(UsoVeiculoEmpresa.id.in_(uso_ids)).all():
            usos_empresa[uso.id] = uso
        empresa_ids = [uso.empresa_id for uso in usos_empresa.values() if uso.empresa_id]
        veiculo_ids = [uso.veiculo_id for uso in usos_empresa.values() if uso.veiculo_id]
        if empresa_ids:
            for empresa in db.query(Empresa).filter(Empresa.id.in_(empresa_ids)).all():
                empresas[empresa.id] = empresa
        if veiculo_ids:
            for veiculo in db.query(Veiculo).filter(Veiculo.id.in_(veiculo_ids)).all():
                veiculos_nf[veiculo.id] = veiculo

    for relatorio in relatorios_nf:
        uso = usos_empresa.get(relatorio.uso_id)
        empresa = empresas.get(relatorio.empresa_id) if relatorio.empresa_id else None
        veiculo = veiculos_nf.get(relatorio.veiculo_id) if relatorio.veiculo_id else None
        records.append(_serialize_relatorio_nf_record(relatorio, uso, veiculo, empresa))

    despesas_contrato = db.query(DespesaContrato).all()
    for despesa in despesas_contrato:
        records.append(
            {
                "id": f"dc-{despesa.id}",
                "data": despesa.data_registro.isoformat() if despesa.data_registro else None,
                "tipo": "despesa",
                "categoria": despesa.tipo or "Contrato",
                "descricao": despesa.descricao,
                "valor": float(despesa.valor) if despesa.valor else 0.0,
                "status": "pago",
            }
        )

    despesas_veiculo = db.query(DespesaVeiculo).all()
    for despesa in despesas_veiculo:
        records.append(
            {
                "id": f"dv-{despesa.id}",
                "data": despesa.data.isoformat() if despesa.data else None,
                "tipo": "despesa",
                "categoria": despesa.tipo or "Veículo",
                "descricao": despesa.descricao,
                "valor": float(despesa.valor) if despesa.valor else 0.0,
                "status": "pago",
            }
        )

    despesas_loja = db.query(DespesaLoja).all()
    for despesa in despesas_loja:
        records.append(
            {
                "id": f"dl-{despesa.id}",
                "data": despesa.data.isoformat() if despesa.data else None,
                "tipo": "despesa",
                "categoria": despesa.categoria or "Loja",
                "descricao": despesa.descricao,
                "valor": float(despesa.valor) if despesa.valor else 0.0,
                "status": "pago",
            }
        )

    manutencoes = db.query(Manutencao).all()
    for manutencao in manutencoes:
        veiculo = db.query(Veiculo).filter(Veiculo.id == manutencao.veiculo_id).first() if manutencao.veiculo_id else None
        records.append(
            {
                "id": f"mt-{manutencao.id}",
                "data": (
                    manutencao.data_realizada.isoformat()
                    if manutencao.data_realizada
                    else manutencao.updated_at.isoformat()
                    if manutencao.updated_at
                    else manutencao.data_criacao.isoformat()
                    if manutencao.data_criacao
                    else None
                ),
                "tipo": "despesa",
                "categoria": f"Manutencao / {manutencao.tipo.title()}",
                "descricao": f"{manutencao.descricao} | {_vehicle_label(veiculo)}" if veiculo else manutencao.descricao,
                "valor": float(manutencao.custo) if manutencao.custo else 0.0,
                "status": "pago" if manutencao.status == "concluida" else "pendente",
                "veiculo_id": str(manutencao.veiculo_id) if manutencao.veiculo_id else None,
                "origem_tipo": "manutencao",
            }
        )

    seguros = db.query(Seguro).all()
    for seguro in seguros:
        veiculo = db.query(Veiculo).filter(Veiculo.id == seguro.veiculo_id).first() if seguro.veiculo_id else None
        records.append(
            {
                "id": f"sg-{seguro.id}",
                "data": seguro.data_inicio.isoformat() if seguro.data_inicio else None,
                "tipo": "despesa",
                "categoria": "Seguro",
                "descricao": f"{seguro.seguradora or 'Seguro'} - {seguro.numero_apolice or 'sem apolice'} | {_vehicle_label(veiculo)}" if veiculo else (seguro.seguradora or "Seguro"),
                "valor": float(seguro.valor) if seguro.valor else 0.0,
                "status": "pago" if seguro.status == "ativo" else "pendente",
                "veiculo_id": str(seguro.veiculo_id) if seguro.veiculo_id else None,
                "origem_tipo": "seguro",
            }
        )

    registros_ipva = db.query(IpvaRegistro).all()
    for registro in registros_ipva:
        veiculo = db.query(Veiculo).filter(Veiculo.id == registro.veiculo_id).first() if registro.veiculo_id else None
        records.append(
            {
                "id": f"ip-{registro.id}",
                "data": registro.data_pagamento.isoformat() if registro.data_pagamento else registro.data_vencimento.isoformat() if registro.data_vencimento else None,
                "tipo": "despesa",
                "categoria": "IPVA",
                "descricao": f"IPVA {registro.ano_referencia or ''} | {_vehicle_label(veiculo)}".strip(),
                "valor": float(registro.valor_ipva or registro.valor_pago or 0.0),
                "status": "pago" if registro.status == "pago" else "pendente",
                "veiculo_id": str(registro.veiculo_id) if registro.veiculo_id else None,
                "origem_tipo": "ipva",
            }
        )

    multas = db.query(Multa).all()
    for multa in multas:
        veiculo = db.query(Veiculo).filter(Veiculo.id == multa.veiculo_id).first() if multa.veiculo_id else None
        records.append(
            {
                "id": f"ml-{multa.id}",
                "data": multa.data_pagamento.isoformat() if multa.data_pagamento else multa.data_infracao.isoformat() if multa.data_infracao else None,
                "tipo": "despesa",
                "categoria": "Multa",
                "descricao": f"{multa.descricao or 'Multa'} | {_vehicle_label(veiculo)}" if veiculo else (multa.descricao or "Multa"),
                "valor": float(multa.valor) if multa.valor else 0.0,
                "status": "pago" if multa.status == "pago" else "pendente",
                "veiculo_id": str(multa.veiculo_id) if multa.veiculo_id else None,
                "contrato_id": str(multa.contrato_id) if multa.contrato_id else None,
                "origem_tipo": "multa",
            }
        )

    _append_manual_records(records, db)

    for index, record in enumerate(records):
        record_id = str(record.get("id", ""))
        if not record_id.startswith("c-"):
            continue

        contrato_id = int(record_id.split("-", 1)[1])
        contrato = next((item for item in contratos if item.id == contrato_id), None)
        if not contrato:
            continue

        cliente = (
            db.query(Cliente).filter(Cliente.id == contrato.cliente_id).first()
            if contrato.cliente_id
            else None
        )
        cliente_nome = cliente.nome if cliente else "Desconhecido"
        records[index] = _serialize_contrato_record(contrato, cliente_nome)

    if tipo:
        records = [record for record in records if record["tipo"] == tipo]

    if status:
        records = [record for record in records if record["status"] == status]

    if search:
        term = search.strip().lower()
        records = [
            record
            for record in records
            if term in str(record.get("descricao", "")).lower()
            or term in str(record.get("categoria", "")).lower()
        ]

    records = [record for record in records if _record_in_period(record.get("data"), start_date, end_date)]

    records.sort(key=lambda item: item["data"] or "", reverse=True)

    total = len(records)
    start = (page - 1) * limit
    end = start + limit

    return {
        "data": records[start:end],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
    }


@router.get("/resumo")
def get_resumo(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get financial summary."""
    contratos = db.query(Contrato).all()
    total_receita = sum(
        float(contrato.valor_total)
        for contrato in contratos
        if contrato.valor_total and str(contrato.tipo or "").lower() != "empresa"
    )
    total_receita_recebida = sum(
        float(contrato.valor_total or 0)
        if _contrato_payment_status(contrato) == "pago"
        else float(contrato.valor_recebido or 0)
        for contrato in contratos
        if contrato.valor_total and str(contrato.tipo or "").lower() != "empresa"
    )
    total_receita_pendente = max(total_receita - total_receita_recebida, 0.0)
    relatorios_nf = db.query(RelatorioNF).all()
    uso_ids = [relatorio.uso_id for relatorio in relatorios_nf if relatorio.uso_id]
    usos_empresa = {}
    if uso_ids:
        for uso in db.query(UsoVeiculoEmpresa).filter(UsoVeiculoEmpresa.id.in_(uso_ids)).all():
            usos_empresa[uso.id] = uso
    total_receita_nf = sum(
        _relatorio_nf_total(relatorio, usos_empresa.get(relatorio.uso_id))
        for relatorio in relatorios_nf
    )

    total_despesa_contrato = sum(
        float(despesa.valor) for despesa in db.query(DespesaContrato).all() if despesa.valor
    )
    total_despesa_veiculo = sum(
        float(despesa.valor) for despesa in db.query(DespesaVeiculo).all() if despesa.valor
    )
    total_despesa_loja = sum(
        float(despesa.valor) for despesa in db.query(DespesaLoja).all() if despesa.valor
    )
    total_manutencao = sum(
        float(manutencao.custo) for manutencao in db.query(Manutencao).all() if manutencao.custo
    )
    total_seguros = sum(
        float(seguro.valor) for seguro in db.query(Seguro).all() if seguro.valor
    )
    total_ipva = sum(
        float(ipva.valor_ipva or ipva.valor_pago or 0) for ipva in db.query(IpvaRegistro).all()
    )
    total_multas = sum(
        float(multa.valor) for multa in db.query(Multa).all() if multa.valor
    )

    total_manual_receita = sum(
        float(lancamento.valor)
        for lancamento in db.query(LancamentoFinanceiro).filter(LancamentoFinanceiro.tipo == "receita").all()
        if lancamento.valor
    )
    total_manual_receita_recebida = sum(
        float(lancamento.valor)
        for lancamento in db.query(LancamentoFinanceiro)
        .filter(LancamentoFinanceiro.tipo == "receita", LancamentoFinanceiro.status == "pago")
        .all()
        if lancamento.valor
    )
    total_manual_despesa = sum(
        float(lancamento.valor)
        for lancamento in db.query(LancamentoFinanceiro).filter(LancamentoFinanceiro.tipo == "despesa").all()
        if lancamento.valor
    )

    total_receita += total_manual_receita + total_receita_nf
    total_receita_recebida += total_manual_receita_recebida
    total_receita_pendente = max(total_receita - total_receita_recebida, 0.0)
    total_despesa = (
        total_despesa_contrato
        + total_despesa_veiculo
        + total_despesa_loja
        + total_manutencao
        + total_seguros
        + total_ipva
        + total_multas
        + total_manual_despesa
    )
    lucro = total_receita - total_despesa
    saldo_realizado = total_receita_recebida - total_despesa

    return {
        "total_receita": total_receita,
        "total_receita_recebida": total_receita_recebida,
        "total_receita_pendente": total_receita_pendente,
        "total_despesa": total_despesa,
        "lucro": lucro,
        "saldo_realizado": saldo_realizado,
        "despesa_contrato": total_despesa_contrato,
        "despesa_veiculo": total_despesa_veiculo,
        "despesa_loja": total_despesa_loja + total_manual_despesa,
        "despesa_manutencao": total_manutencao,
        "despesa_seguro": total_seguros,
        "despesa_ipva": total_ipva,
        "despesa_multa": total_multas,
        "receita_nf_empresa": total_receita_nf,
    }


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_lancamento_financeiro(
    lancamento: LancamentoFinanceiroCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Create a manual financial record for the finance dashboard."""
    db_lancamento = LancamentoFinanceiro(**lancamento.model_dump())
    db.add(db_lancamento)
    db.commit()
    db.refresh(db_lancamento)
    log_activity(
        db,
        current_user,
        "CRIAR",
        "LancamentoFinanceiro",
        f"Lançamento financeiro criado: {db_lancamento.descricao}",
        db_lancamento.id,
        request,
    )
    return {
        "id": f"fm-{db_lancamento.id}",
        "data": db_lancamento.data.isoformat(),
        "tipo": db_lancamento.tipo,
        "categoria": db_lancamento.categoria,
        "descricao": db_lancamento.descricao,
        "valor": float(db_lancamento.valor),
        "status": db_lancamento.status,
    }


@router.put("/{record_id}")
@router.patch("/{record_id}")
def update_lancamento_financeiro(
    record_id: str,
    lancamento_data: LancamentoFinanceiroUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Update finance records directly from the consolidated finance view."""
    update_data = lancamento_data.model_dump(exclude_unset=True)
    prefix, id_str = record_id.split("-", 1) if "-" in record_id else ("", "")
    if not prefix or not id_str.isdigit():
        raise HTTPException(status_code=400, detail="ID inválido")

    real_id = int(id_str)

    if prefix == "fm":
        obj = db.query(LancamentoFinanceiro).filter(LancamentoFinanceiro.id == real_id).first()
        if not obj:
            raise HTTPException(status_code=404, detail="Registro não encontrado")
        for key, value in update_data.items():
            setattr(obj, key, value)
    elif prefix == "dc":
        obj = db.query(DespesaContrato).filter(DespesaContrato.id == real_id).first()
        if not obj:
            raise HTTPException(status_code=404, detail="Registro não encontrado")
        if "categoria" in update_data:
            obj.tipo = update_data["categoria"]
        if "descricao" in update_data:
            obj.descricao = update_data["descricao"]
        if "valor" in update_data:
            obj.valor = update_data["valor"]
        if "data" in update_data:
            obj.data_registro = _merge_date_with_existing(update_data["data"], obj.data_registro)
    elif prefix == "dv":
        obj = db.query(DespesaVeiculo).filter(DespesaVeiculo.id == real_id).first()
        if not obj:
            raise HTTPException(status_code=404, detail="Registro não encontrado")
        if "categoria" in update_data:
            obj.tipo = update_data["categoria"]
        if "descricao" in update_data:
            obj.descricao = update_data["descricao"]
        if "valor" in update_data:
            obj.valor = update_data["valor"]
        if "data" in update_data:
            obj.data = _merge_date_with_existing(update_data["data"], obj.data)
    elif prefix == "dl":
        obj = db.query(DespesaLoja).filter(DespesaLoja.id == real_id).first()
        if not obj:
            raise HTTPException(status_code=404, detail="Registro não encontrado")
        if "categoria" in update_data:
            obj.categoria = update_data["categoria"]
        if "descricao" in update_data:
            obj.descricao = update_data["descricao"]
        if "valor" in update_data:
            obj.valor = update_data["valor"]
        if "data" in update_data:
            merged_date = _merge_date_with_existing(update_data["data"], obj.data)
            obj.data = merged_date
            if merged_date:
                obj.mes = merged_date.month
                obj.ano = merged_date.year
    elif prefix == "mt":
        obj = db.query(Manutencao).filter(Manutencao.id == real_id).first()
        if not obj:
            raise HTTPException(status_code=404, detail="Registro não encontrado")
        if "categoria" in update_data:
            obj.tipo = _parse_finance_category_suffix(update_data["categoria"], obj.tipo)
        if "descricao" in update_data:
            obj.descricao = update_data["descricao"]
        if "valor" in update_data:
            obj.custo = update_data["valor"]
        obj.status = _normalize_source_status(record_id, update_data.get("status"), obj.status)
        if "data" in update_data:
            if obj.status == "concluida":
                obj.data_realizada = update_data["data"]
            else:
                obj.data_proxima = update_data["data"]
    elif prefix == "ip":
        obj = db.query(IpvaRegistro).filter(IpvaRegistro.id == real_id).first()
        if not obj:
            raise HTTPException(status_code=404, detail="Registro não encontrado")
        if "valor" in update_data:
            obj.valor_ipva = update_data["valor"]
            if obj.status == "pago":
                obj.valor_pago = update_data["valor"]
        obj.status = _normalize_source_status(record_id, update_data.get("status"), obj.status)
        if "data" in update_data:
            if obj.status == "pago":
                obj.data_pagamento = update_data["data"]
                obj.valor_pago = float(obj.valor_ipva or update_data.get("valor") or obj.valor_pago or 0)
            else:
                obj.data_vencimento = update_data["data"]
    elif prefix == "sg":
        obj = db.query(Seguro).filter(Seguro.id == real_id).first()
        if not obj:
            raise HTTPException(status_code=404, detail="Registro nÃ£o encontrado")
        if "descricao" in update_data:
            obj.seguradora = update_data["descricao"]
        if "valor" in update_data:
            obj.valor = update_data["valor"]
        obj.status = _normalize_source_status(record_id, update_data.get("status"), obj.status)
        if "data" in update_data:
            obj.data_inicio = update_data["data"]
    elif prefix == "ml":
        obj = db.query(Multa).filter(Multa.id == real_id).first()
        if not obj:
            raise HTTPException(status_code=404, detail="Registro não encontrado")
        if "descricao" in update_data:
            obj.descricao = update_data["descricao"]
        if "valor" in update_data:
            obj.valor = update_data["valor"]
        obj.status = _normalize_source_status(record_id, update_data.get("status"), obj.status)
        if "data" in update_data:
            if obj.status == "pago":
                obj.data_pagamento = update_data["data"]
            else:
                obj.data_vencimento = update_data["data"]
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A edição ainda não está disponível para este tipo de lançamento.",
        )

    db.commit()
    db.refresh(obj)
    log_activity(
        db,
        current_user,
        "EDITAR",
        "Financeiro",
        f"Lançamento financeiro editado: {record_id}",
        real_id,
        request,
    )
    return _serialize_updated_finance_record(record_id, obj, db)


@router.post("/despesa-contrato")
def criar_despesa_contrato(
    despesa: DespesaContratoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Create expense for contract."""
    contrato = db.query(Contrato).filter(Contrato.id == despesa.contrato_id).first()
    if not contrato:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contrato não encontrado"
        )

    db_despesa = DespesaContrato(
        contrato_id=despesa.contrato_id,
        tipo=despesa.tipo,
        descricao=despesa.descricao,
        valor=despesa.valor,
        responsavel=current_user.email,
    )
    db.add(db_despesa)
    db.commit()
    db.refresh(db_despesa)
    log_activity(
        db,
        current_user,
        "CRIAR",
        "DespesaContrato",
        f"Despesa de contrato criada: {despesa.descricao}",
        db_despesa.id,
        request,
    )
    return db_despesa


@router.post("/despesa-veiculo")
def criar_despesa_veiculo(
    despesa: DespesaVeiculoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Create expense for vehicle."""
    db_despesa = DespesaVeiculo(
        veiculo_id=despesa.veiculo_id,
        descricao=despesa.descricao,
        valor=despesa.valor,
        km=despesa.km,
        pneu=despesa.pneu,
    )
    db.add(db_despesa)
    db.commit()
    db.refresh(db_despesa)
    log_activity(
        db,
        current_user,
        "CRIAR",
        "DespesaVeiculo",
        f"Despesa de veículo criada: {despesa.descricao}",
        db_despesa.id,
        request,
    )
    return db_despesa


@router.post("/despesa-loja")
def criar_despesa_loja(
    despesa: DespesaLojaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Create shop expense."""
    db_despesa = DespesaLoja(
        mes=despesa.mes,
        ano=despesa.ano,
        descricao=despesa.descricao,
        valor=despesa.valor,
    )
    db.add(db_despesa)
    db.commit()
    db.refresh(db_despesa)
    log_activity(
        db,
        current_user,
        "CRIAR",
        "DespesaLoja",
        f"Despesa de loja criada: {despesa.descricao}",
        db_despesa.id,
        request,
    )
    return db_despesa


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_registro_financeiro(
    record_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Delete a financial record by composite id."""
    parts = record_id.split("-", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="ID inválido")

    prefix, id_str = parts
    try:
        real_id = int(id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID inválido")

    if prefix == "dc":
        obj = db.query(DespesaContrato).filter(DespesaContrato.id == real_id).first()
    elif prefix == "dv":
        obj = db.query(DespesaVeiculo).filter(DespesaVeiculo.id == real_id).first()
    elif prefix == "dl":
        obj = db.query(DespesaLoja).filter(DespesaLoja.id == real_id).first()
    elif prefix == "fm":
        obj = db.query(LancamentoFinanceiro).filter(LancamentoFinanceiro.id == real_id).first()
    elif prefix == "c":
        contrato = db.query(Contrato).filter(Contrato.id == real_id).first()
        if not contrato:
            raise HTTPException(status_code=404, detail="Registro não encontrado")
        db.query(Quilometragem).filter(Quilometragem.contrato_id == real_id).delete(synchronize_session=False)
        db.query(DespesaContrato).filter(DespesaContrato.contrato_id == real_id).delete(synchronize_session=False)
        db.query(ProrrogacaoContrato).filter(ProrrogacaoContrato.contrato_id == real_id).delete(synchronize_session=False)
        db.query(CheckinCheckout).filter(CheckinCheckout.contrato_id == real_id).delete(synchronize_session=False)
        db.query(UsoVeiculoEmpresa).filter(UsoVeiculoEmpresa.contrato_id == real_id).update(
            {UsoVeiculoEmpresa.contrato_id: None},
            synchronize_session=False,
        )
        db.query(Multa).filter(Multa.contrato_id == real_id).delete(synchronize_session=False)
        obj = contrato
    else:
        raise HTTPException(status_code=400, detail="Tipo de registro desconhecido")

    if not obj:
        raise HTTPException(status_code=404, detail="Registro não encontrado")

    db.delete(obj)
    db.commit()
    log_activity(
        db,
        current_user,
        "EXCLUIR",
        "Financeiro",
        f"Registro financeiro {record_id} excluído",
        real_id,
        request,
    )


@router.get("/faturamento")
def get_faturamento(
    mes: Optional[int] = None,
    ano: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get billing information."""
    query = db.query(Contrato)

    if mes and ano:
        start = datetime(ano, mes, 1)
        if mes == 12:
            end = datetime(ano + 1, 1, 1)
        else:
            end = datetime(ano, mes + 1, 1)

        query = query.filter(Contrato.data_criacao >= start, Contrato.data_criacao < end)

    contratos = query.all()
    total = sum(float(contrato.valor_total) for contrato in contratos if contrato.valor_total)

    return {"total_faturamento": total, "quantidade_contratos": len(contratos)}


@router.get("/relatorio")
def get_relatorio_avancado(
    data_inicio: str,
    data_fim: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get advanced financial report."""
    try:
        inicio = datetime.strptime(data_inicio, "%Y-%m-%d")
        fim = datetime.strptime(data_fim, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Formato de data inválido"
        )

    contratos = db.query(Contrato).filter(
        Contrato.data_criacao.between(inicio, fim)
    ).all()

    return {
        "periodo": {"inicio": data_inicio, "fim": data_fim},
        "total_contratos": len(contratos),
        "total_receita": sum(
            float(contrato.valor_total) for contrato in contratos if contrato.valor_total
        ),
        "contratos": contratos,
    }


@router.get("/exportar/xlsx")
def exportar_contratos_xlsx(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export contracts to XLSX."""
    buffer = ExportService.export_contratos_xlsx(db)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=contratos.xlsx"},
    )


@router.get("/exportar/csv")
def exportar_contratos_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export contracts to CSV."""
    buffer = ExportService.export_contratos_csv(db)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=contratos.csv"},
    )


@router.get("/relatorio-pdf")
def get_relatorio_pdf(
    data_inicio: str,
    data_fim: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate financial report PDF."""
    pdf_buffer = PDFService.generate_relatorio_financeiro_pdf(db, data_inicio, data_fim)
    return StreamingResponse(
        iter([pdf_buffer.getvalue()]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=relatorio_financeiro_{data_inicio}_{data_fim}.pdf"},
    )
