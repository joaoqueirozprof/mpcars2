from datetime import datetime, timedelta
from typing import Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy import func as sqlfunc
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import get_current_user, require_page_access
from app.core.cache import cache_service
from app.models import (
    AlertaHistorico,
    Cliente,
    Contrato,
    DespesaContrato,
    DespesaLoja,
    DespesaVeiculo,
    IpvaRegistro,
    LancamentoFinanceiro,
    Manutencao,
    Multa,
    Reserva,
    Seguro,
    Veiculo,
)
from app.models.user import User


router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
    dependencies=[Depends(require_page_access("dashboard"))],
)


def _normalize_urgencia(urgencia: str) -> str:
    normalized = (urgencia or "info").lower()
    if normalized in {"critico", "critica"}:
        return "critica"
    if normalized == "atencao":
        return "atencao"
    return "info"


def _month_start(reference: datetime, months_ago: int = 0) -> datetime:
    year = reference.year
    month = reference.month - months_ago
    while month <= 0:
        month += 12
        year -= 1
    return reference.replace(
        year=year,
        month=month,
        day=1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )


def _month_label(reference: datetime) -> str:
    return reference.strftime("%m/%y")


def _build_month_windows(reference: datetime, total: int = 6) -> List[dict]:
    windows = []
    for months_ago in range(total - 1, -1, -1):
        start = _month_start(reference, months_ago)
        end = _month_start(start + timedelta(days=32))
        windows.append(
            {
                "start": start,
                "end": end,
                "label": _month_label(start),
                "receita": 0.0,
                "despesa": 0.0,
            }
        )
    return windows


def _bucket_value(windows: List[dict], when: datetime, field: str, value: float) -> None:
    if when is None:
        return

    for window in windows:
        if window["start"] <= when < window["end"]:
            window[field] += float(value or 0)
            return


def _serialize_contract(contrato: Contrato) -> dict:
    return {
        "id": str(contrato.id),
        "numero": contrato.numero,
        "cliente_id": str(contrato.cliente_id),
        "veiculo_id": str(contrato.veiculo_id),
        "data_inicio": contrato.data_inicio.isoformat() if contrato.data_inicio else None,
        "data_fim": contrato.data_fim.isoformat() if contrato.data_fim else None,
        "data_finalizacao": (
            contrato.data_finalizacao.isoformat() if contrato.data_finalizacao else None
        ),
        "quilometragem_inicial": float(contrato.km_inicial or 0),
        "quilometragem_final": (
            float(contrato.km_final) if contrato.km_final is not None else None
        ),
        "valor_diaria": float(contrato.valor_diaria or 0),
        "valor_total": float(contrato.valor_total or 0),
        "status": contrato.status,
        "observacoes": contrato.observacoes or "",
        "cliente": {"nome": contrato.cliente.nome} if contrato.cliente else None,
        "veiculo": {
            "marca": contrato.veiculo.marca,
            "modelo": contrato.veiculo.modelo,
            "placa": contrato.veiculo.placa,
            "km_atual": float(contrato.veiculo.km_atual or 0),
        }
        if contrato.veiculo
        else None,
    }


def _build_fallback_alertas(
    contratos_atrasados: List[Contrato],
    proximos_vencimentos: List[dict],
    now: datetime,
) -> List[dict]:
    alertas = []

    for contrato in contratos_atrasados[:4]:
        dias_atraso = max((now.date() - contrato.data_fim.date()).days, 0)
        alertas.append(
            {
                "id": "contrato-atrasado-{}".format(contrato.id),
                "tipo": "contrato",
                "titulo": "Contrato {} em atraso".format(contrato.numero),
                "descricao": "{} dia(s) de atraso na devolucao".format(dias_atraso),
                "urgencia": "critica",
            }
        )

    for item in proximos_vencimentos[:4]:
        alertas.append(
            {
                "id": "vencimento-{}-{}".format(item["tipo"], item["id"]),
                "tipo": item["tipo"].lower(),
                "titulo": item["titulo"],
                "descricao": "Vencimento previsto para {}".format(item["data_vencimento"]),
                "urgencia": "atencao",
            }
        )

    return alertas


def _build_proximos_vencimentos(db: Session, now: datetime) -> List[dict]:
    limite = now + timedelta(days=30)
    itens = []

    contratos = (
        db.query(Contrato)
        .options(joinedload(Contrato.cliente), joinedload(Contrato.veiculo))
        .filter(
            Contrato.status == "ativo",
            Contrato.data_fim >= now,
            Contrato.data_fim <= limite,
        )
        .order_by(Contrato.data_fim.asc())
        .limit(5)
        .all()
    )
    for contrato in contratos:
        cliente_nome = contrato.cliente.nome if contrato.cliente else "Cliente"
        itens.append(
            {
                "id": str(contrato.id),
                "titulo": "Contrato {} - {}".format(contrato.numero, cliente_nome),
                "data_vencimento": contrato.data_fim.isoformat(),
                "tipo": "Contrato",
            }
        )

    seguros = (
        db.query(Seguro)
        .options(joinedload(Seguro.veiculo))
        .filter(
            Seguro.status == "ativo",
            Seguro.data_fim >= now.date(),
            Seguro.data_fim <= limite.date(),
        )
        .order_by(Seguro.data_fim.asc())
        .limit(3)
        .all()
    )
    for seguro in seguros:
        veiculo_nome = (
            "{} {}".format(seguro.veiculo.marca, seguro.veiculo.modelo).strip()
            if seguro.veiculo
            else "Veiculo"
        )
        itens.append(
            {
                "id": "seguro-{}".format(seguro.id),
                "titulo": "Seguro {} - {}".format(seguro.numero_apolice or seguro.id, veiculo_nome),
                "data_vencimento": datetime.combine(seguro.data_fim, datetime.min.time()).isoformat(),
                "tipo": "Seguro",
            }
        )

    ipvas = (
        db.query(IpvaRegistro)
        .options(joinedload(IpvaRegistro.veiculo))
        .filter(
            IpvaRegistro.status == "pendente",
            IpvaRegistro.data_vencimento >= now.date(),
            IpvaRegistro.data_vencimento <= limite.date(),
        )
        .order_by(IpvaRegistro.data_vencimento.asc())
        .limit(3)
        .all()
    )
    for ipva in ipvas:
        placa = ipva.veiculo.placa if ipva.veiculo else "Veiculo"
        itens.append(
            {
                "id": "ipva-{}".format(ipva.id),
                "titulo": "IPVA {} - {}".format(ipva.ano_referencia, placa),
                "data_vencimento": datetime.combine(
                    ipva.data_vencimento, datetime.min.time()
                ).isoformat(),
                "tipo": "IPVA",
            }
        )

    manutencoes = (
        db.query(Manutencao)
        .options(joinedload(Manutencao.veiculo))
        .filter(
            Manutencao.status.in_(["pendente", "agendada"]),
            Manutencao.data_proxima.isnot(None),
            Manutencao.data_proxima >= now.date(),
            Manutencao.data_proxima <= limite.date(),
        )
        .order_by(Manutencao.data_proxima.asc())
        .limit(3)
        .all()
    )
    for manutencao in manutencoes:
        placa = manutencao.veiculo.placa if manutencao.veiculo else "Veiculo"
        itens.append(
            {
                "id": "manutencao-{}".format(manutencao.id),
                "titulo": "{} - {}".format(manutencao.descricao or "Manutencao", placa),
                "data_vencimento": datetime.combine(
                    manutencao.data_proxima, datetime.min.time()
                ).isoformat(),
                "tipo": "Manutencao",
            }
        )

    itens.sort(key=lambda item: item["data_vencimento"])
    return itens[:8]


def _build_agenda_hoje(db: Session, now: datetime) -> List[dict]:
    inicio_dia = now.replace(hour=0, minute=0, second=0, microsecond=0)
    fim_dia = inicio_dia + timedelta(days=1)
    agenda = []

    reservas = (
        db.query(Reserva)
        .options(joinedload(Reserva.cliente), joinedload(Reserva.veiculo))
        .filter(
            Reserva.status.in_(["pendente", "confirmada"]),
            Reserva.data_inicio >= inicio_dia,
            Reserva.data_inicio < fim_dia,
        )
        .order_by(Reserva.data_inicio.asc())
        .limit(4)
        .all()
    )
    for reserva in reservas:
        cliente_nome = reserva.cliente.nome if reserva.cliente else "Cliente"
        placa = reserva.veiculo.placa if reserva.veiculo else "Veiculo"
        agenda.append(
            {
                "id": "reserva-{}".format(reserva.id),
                "tipo": "Reserva",
                "titulo": "Reserva para retirada",
                "descricao": "{} • {}".format(cliente_nome, placa),
                "horario": reserva.data_inicio.isoformat() if reserva.data_inicio else None,
                "urgencia": "atencao" if reserva.status == "pendente" else "info",
                "rota": "/reservas",
            }
        )

    retiradas = (
        db.query(Contrato)
        .options(joinedload(Contrato.cliente), joinedload(Contrato.veiculo))
        .filter(
            Contrato.data_inicio >= inicio_dia,
            Contrato.data_inicio < fim_dia,
        )
        .order_by(Contrato.data_inicio.asc())
        .limit(4)
        .all()
    )
    for contrato in retiradas:
        cliente_nome = contrato.cliente.nome if contrato.cliente else "Cliente"
        placa = contrato.veiculo.placa if contrato.veiculo else "Veiculo"
        agenda.append(
            {
                "id": "retirada-{}".format(contrato.id),
                "tipo": "Retirada",
                "titulo": "Contrato {} inicia hoje".format(contrato.numero),
                "descricao": "{} • {}".format(cliente_nome, placa),
                "horario": contrato.data_inicio.isoformat() if contrato.data_inicio else None,
                "urgencia": "info",
                "rota": "/contratos",
            }
        )

    devolucoes = (
        db.query(Contrato)
        .options(joinedload(Contrato.cliente), joinedload(Contrato.veiculo))
        .filter(
            Contrato.status == "ativo",
            Contrato.data_fim >= inicio_dia,
            Contrato.data_fim < fim_dia,
        )
        .order_by(Contrato.data_fim.asc())
        .limit(4)
        .all()
    )
    for contrato in devolucoes:
        cliente_nome = contrato.cliente.nome if contrato.cliente else "Cliente"
        placa = contrato.veiculo.placa if contrato.veiculo else "Veiculo"
        agenda.append(
            {
                "id": "devolucao-{}".format(contrato.id),
                "tipo": "Devolucao",
                "titulo": "Contrato {} fecha hoje".format(contrato.numero),
                "descricao": "{} • {}".format(cliente_nome, placa),
                "horario": contrato.data_fim.isoformat() if contrato.data_fim else None,
                "urgencia": "critica" if contrato.data_fim and contrato.data_fim <= now else "atencao",
                "rota": "/contratos",
            }
        )

    manutencoes = (
        db.query(Manutencao)
        .options(joinedload(Manutencao.veiculo))
        .filter(
            Manutencao.status.in_(["pendente", "agendada", "em_andamento"]),
            Manutencao.data_proxima.isnot(None),
            Manutencao.data_proxima >= inicio_dia.date(),
            Manutencao.data_proxima < fim_dia.date(),
        )
        .order_by(Manutencao.data_proxima.asc())
        .limit(3)
        .all()
    )
    for manutencao in manutencoes:
        placa = manutencao.veiculo.placa if manutencao.veiculo else "Veiculo"
        horario = datetime.combine(manutencao.data_proxima, datetime.min.time())
        agenda.append(
            {
                "id": "manutencao-hoje-{}".format(manutencao.id),
                "tipo": "Manutencao",
                "titulo": manutencao.descricao or "Manutencao agendada",
                "descricao": "{} • {}".format(placa, manutencao.oficina or "Oficina a definir"),
                "horario": horario.isoformat(),
                "urgencia": "atencao",
                "rota": "/manutencoes",
            }
        )

    agenda.sort(key=lambda item: item["horario"] or "")
    return agenda[:8]


@router.get("/")
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    del current_user

    cache_key = "dashboard:main"
    cached_data = cache_service.get(cache_key)
    if cached_data is not None:
        return cached_data

    now = datetime.now()
    inicio_mes = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    inicio_mes_anterior = _month_start(inicio_mes, 1)
    windows = _build_month_windows(now, total=6)
    inicio_serie = windows[0]["start"]

    total_veiculos = (
        db.query(sqlfunc.count(Veiculo.id)).filter(Veiculo.ativo.is_(True)).scalar() or 0
    )
    veiculos_alugados = (
        db.query(sqlfunc.count(Veiculo.id))
        .filter(Veiculo.ativo.is_(True), Veiculo.status == "alugado")
        .scalar()
        or 0
    )
    veiculos_disponiveis = (
        db.query(sqlfunc.count(Veiculo.id))
        .filter(Veiculo.ativo.is_(True), Veiculo.status == "disponivel")
        .scalar()
        or 0
    )
    veiculos_manutencao = (
        db.query(sqlfunc.count(Veiculo.id))
        .filter(Veiculo.ativo.is_(True), Veiculo.status == "manutencao")
        .scalar()
        or 0
    )
    total_clientes = (
        db.query(sqlfunc.count(Cliente.id)).filter(Cliente.ativo.is_(True)).scalar() or 0
    )
    contratos_ativos = (
        db.query(sqlfunc.count(Contrato.id)).filter(Contrato.status == "ativo").scalar() or 0
    )
    reservas_pendentes = (
        db.query(sqlfunc.count(Reserva.id)).filter(Reserva.status == "pendente").scalar() or 0
    )
    reservas_confirmadas = (
        db.query(sqlfunc.count(Reserva.id)).filter(Reserva.status == "confirmada").scalar() or 0
    )
    manutencoes_abertas = (
        db.query(sqlfunc.count(Manutencao.id))
        .filter(Manutencao.status.in_(["pendente", "agendada", "em_andamento"]))
        .scalar()
        or 0
    )
    inicio_dia = now.replace(hour=0, minute=0, second=0, microsecond=0)
    fim_dia = inicio_dia + timedelta(days=1)
    retiradas_hoje = (
        db.query(sqlfunc.count(Contrato.id))
        .filter(Contrato.data_inicio >= inicio_dia, Contrato.data_inicio < fim_dia)
        .scalar()
        or 0
    )
    devolucoes_hoje = (
        db.query(sqlfunc.count(Contrato.id))
        .filter(Contrato.status == "ativo", Contrato.data_fim >= inicio_dia, Contrato.data_fim < fim_dia)
        .scalar()
        or 0
    )

    contratos_mes = (
        db.query(Contrato)
        .filter(Contrato.data_criacao >= inicio_serie)
        .all()
    )
    despesas_contrato = (
        db.query(DespesaContrato)
        .filter(DespesaContrato.data_registro >= inicio_serie)
        .all()
    )
    despesas_veiculo = (
        db.query(DespesaVeiculo)
        .filter(DespesaVeiculo.data >= inicio_serie)
        .all()
    )
    despesas_loja = (
        db.query(DespesaLoja)
        .filter(DespesaLoja.data >= inicio_serie)
        .all()
    )
    lancamentos = (
        db.query(LancamentoFinanceiro)
        .filter(LancamentoFinanceiro.data >= inicio_serie.date())
        .all()
    )

    for contrato in contratos_mes:
        _bucket_value(
            windows,
            contrato.data_criacao,
            "receita",
            float(contrato.valor_total or 0),
        )

    for despesa in despesas_contrato:
        _bucket_value(
            windows,
            despesa.data_registro,
            "despesa",
            float(despesa.valor or 0),
        )

    for despesa in despesas_veiculo:
        _bucket_value(windows, despesa.data, "despesa", float(despesa.valor or 0))

    for despesa in despesas_loja:
        _bucket_value(windows, despesa.data, "despesa", float(despesa.valor or 0))

    for lancamento in lancamentos:
        when = datetime.combine(lancamento.data, datetime.min.time())
        bucket = "receita" if lancamento.tipo == "receita" else "despesa"
        if lancamento.status != "cancelado":
            _bucket_value(windows, when, bucket, float(lancamento.valor or 0))

    receita_mensal = next(
        (window["receita"] for window in windows if window["label"] == _month_label(inicio_mes)),
        0.0,
    )
    receita_mes_anterior = next(
        (
            window["receita"]
            for window in windows
            if window["label"] == _month_label(inicio_mes_anterior)
        ),
        0.0,
    )
    ticket_medio = round(receita_mensal / contratos_ativos, 2) if contratos_ativos else 0.0
    taxa_ocupacao = round((veiculos_alugados / total_veiculos) * 100, 1) if total_veiculos else 0.0
    variacao_receita_mensal = 0.0
    if receita_mes_anterior > 0:
        variacao_receita_mensal = round(
            ((receita_mensal - receita_mes_anterior) / receita_mes_anterior) * 100,
            1,
        )

    top_clientes_query = (
        db.query(
            Cliente.nome.label("nome"),
            sqlfunc.count(Contrato.id).label("contratos"),
            sqlfunc.coalesce(sqlfunc.sum(Contrato.valor_total), 0).label("valor_total"),
        )
        .join(Contrato, Contrato.cliente_id == Cliente.id)
        .filter(Cliente.ativo.is_(True))
        .group_by(Cliente.id, Cliente.nome)
        .order_by(sqlfunc.coalesce(sqlfunc.sum(Contrato.valor_total), 0).desc())
        .limit(5)
        .all()
    )
    top_clientes = [
        {
            "nome": row.nome,
            "contratos": int(row.contratos or 0),
            "valor_total": float(row.valor_total or 0),
        }
        for row in top_clientes_query
    ]

    top_veiculos_query = (
        db.query(
            Veiculo.placa.label("placa"),
            Veiculo.modelo.label("modelo"),
            sqlfunc.count(Contrato.id).label("alugadas"),
            sqlfunc.coalesce(sqlfunc.sum(Contrato.valor_total), 0).label("receita"),
        )
        .outerjoin(Contrato, Contrato.veiculo_id == Veiculo.id)
        .filter(Veiculo.ativo.is_(True))
        .group_by(Veiculo.id, Veiculo.placa, Veiculo.modelo)
        .order_by(sqlfunc.count(Contrato.id).desc(), Veiculo.placa.asc())
        .limit(5)
        .all()
    )
    top_veiculos = [
        {
            "placa": row.placa,
            "modelo": row.modelo,
            "alugadas": int(row.alugadas or 0),
            "receita": float(row.receita or 0),
        }
        for row in top_veiculos_query
    ]

    contratos_atrasados_query = (
        db.query(Contrato)
        .options(joinedload(Contrato.cliente), joinedload(Contrato.veiculo))
        .filter(Contrato.status == "ativo", Contrato.data_fim < now)
        .order_by(Contrato.data_fim.asc())
        .limit(5)
        .all()
    )
    contratos_atrasados = [_serialize_contract(item) for item in contratos_atrasados_query]

    proximos_vencimentos = _build_proximos_vencimentos(db, now)
    agenda_hoje = _build_agenda_hoje(db, now)

    alertas_rows = (
        db.query(AlertaHistorico)
        .filter(AlertaHistorico.resolvido.is_(False))
        .order_by(AlertaHistorico.data_criacao.desc())
        .limit(10)
        .all()
    )
    alertas = [
        {
            "id": str(alerta.id),
            "tipo": alerta.tipo_alerta or alerta.entidade_tipo or "alerta",
            "titulo": alerta.titulo,
            "descricao": alerta.descricao,
            "urgencia": _normalize_urgencia(alerta.urgencia),
        }
        for alerta in alertas_rows
    ]
    if not alertas:
        alertas = _build_fallback_alertas(contratos_atrasados_query, proximos_vencimentos, now)

    return {
        "total_veiculos": int(total_veiculos),
        "veiculos_alugados": int(veiculos_alugados),
        "veiculos_disponiveis": int(veiculos_disponiveis),
        "veiculos_manutencao": int(veiculos_manutencao),
        "total_clientes": int(total_clientes),
        "contratos_ativos": int(contratos_ativos),
        "reservas_pendentes": int(reservas_pendentes),
        "reservas_confirmadas": int(reservas_confirmadas),
        "manutencoes_abertas": int(manutencoes_abertas),
        "retiradas_hoje": int(retiradas_hoje),
        "devolucoes_hoje": int(devolucoes_hoje),
        "receita_mensal": round(receita_mensal, 2),
        "taxa_ocupacao": taxa_ocupacao,
        "ticket_medio": ticket_medio,
        "variacao_receita_mensal": variacao_receita_mensal,
        "receita_vs_despesas": [
            {
                "mes": window["label"],
                "receita": round(window["receita"], 2),
                "despesa": round(window["despesa"], 2),
            }
            for window in windows
        ],
        "top_clientes": top_clientes,
        "top_veiculos": top_veiculos,
        "alertas": alertas,
        "contratos_atrasados": contratos_atrasados,
        "proximos_vencimentos": proximos_vencimentos,
        "agenda_hoje": agenda_hoje,
    }

    cache_service.set(cache_key, result, ttl=300)
    return result


@router.get("/consolidado")
def get_consolidado(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    del current_user
    total_contratos = db.query(sqlfunc.count(Contrato.id)).scalar() or 0
    contratos_ativos = (
        db.query(sqlfunc.count(Contrato.id)).filter(Contrato.status == "ativo").scalar() or 0
    )
    total_veiculos = db.query(sqlfunc.count(Veiculo.id)).scalar() or 0
    veiculos_disponiveis = (
        db.query(sqlfunc.count(Veiculo.id)).filter(Veiculo.status == "disponivel").scalar()
        or 0
    )
    total_clientes = db.query(sqlfunc.count(Cliente.id)).scalar() or 0
    total_multas = db.query(sqlfunc.count(Multa.id)).scalar() or 0

    return {
        "total_contratos": total_contratos,
        "total_veiculos": total_veiculos,
        "total_clientes": total_clientes,
        "total_multas": total_multas,
        "contratos_ativos": contratos_ativos,
        "veiculos_disponiveis": veiculos_disponiveis,
    }


@router.get("/metricas")
def get_metricas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dashboard = get_dashboard(db=db, current_user=current_user)
    return {
        "contratos_mes": len(dashboard["contratos_atrasados"]),
        "taxa_ocupacao": dashboard["taxa_ocupacao"],
        "receita_mes": dashboard["receita_mensal"],
        "clientes": dashboard["total_clientes"],
    }


@router.get("/alertas")
def get_alertas(
    urgencia: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    del current_user
    query = db.query(AlertaHistorico).filter(AlertaHistorico.resolvido.is_(False))
    if urgencia:
        urgencias = {urgencia, urgencia.replace("critica", "critico")}
        query = query.filter(AlertaHistorico.urgencia.in_(list(urgencias)))
    return query.order_by(AlertaHistorico.data_criacao.desc()).all()


@router.get("/tops")
def get_tops(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dashboard = get_dashboard(db=db, current_user=current_user)
    return {
        "top_veiculos": dashboard["top_veiculos"],
        "top_clientes": dashboard["top_clientes"],
    }


@router.get("/previsao")
def get_previsao(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dashboard = get_dashboard(db=db, current_user=current_user)
    despesas_mes_atual = sum(
        item["despesa"] for item in dashboard["receita_vs_despesas"][-1:]
    )
    return {
        "previsao_receita": dashboard["receita_mensal"],
        "receita_mes_atual": dashboard["receita_mensal"],
        "receita_mes_passado": dashboard["receita_vs_despesas"][-2]["receita"]
        if len(dashboard["receita_vs_despesas"]) > 1
        else 0,
        "despesa_mes_atual": despesas_mes_atual,
        "taxa_crescimento": dashboard["variacao_receita_mensal"],
    }


@router.get("/atrasados")
def get_atrasados(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_dashboard(db=db, current_user=current_user)["contratos_atrasados"]


@router.get("/vencimentos")
def get_vencimentos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_dashboard(db=db, current_user=current_user)["proximos_vencimentos"]


@router.get("/graficos")
def get_graficos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dashboard = get_dashboard(db=db, current_user=current_user)
    return {
        "contratos_por_status": {
            "ativo": dashboard["contratos_ativos"],
            "finalizado": 0,
        },
        "veiculos_por_status": {
            "disponivel": dashboard["veiculos_disponiveis"],
            "alugado": dashboard["veiculos_alugados"],
            "manutencao": 0,
        },
        "receita_vs_despesas": dashboard["receita_vs_despesas"],
    }
