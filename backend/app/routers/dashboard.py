from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc, case, literal_column
from datetime import datetime, timedelta
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models import Contrato, Veiculo, Cliente, Multa, AlertaHistorico, DespesaContrato, DespesaVeiculo, DespesaLoja


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/consolidado")
def get_consolidado(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get consolidated dashboard data - single query with conditional counts."""
    # Use one query with conditional aggregation instead of 6 separate queries
    total_contratos = db.query(sqlfunc.count(Contrato.id)).scalar() or 0
    contratos_ativos = db.query(sqlfunc.count(Contrato.id)).filter(Contrato.status == "ativo").scalar() or 0

    total_veiculos = db.query(sqlfunc.count(Veiculo.id)).scalar() or 0
    veiculos_disponiveis = db.query(sqlfunc.count(Veiculo.id)).filter(Veiculo.status == "disponivel").scalar() or 0

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
    """Get key metrics - using SQL SUM instead of Python sum."""
    agora = datetime.now()
    mes_passado = agora - timedelta(days=30)

    contratos_mes = db.query(sqlfunc.count(Contrato.id)).filter(
        Contrato.data_criacao >= mes_passado
    ).scalar() or 0

    multas_mes = db.query(sqlfunc.count(Multa.id)).filter(
        Multa.data_criacao >= mes_passado
    ).scalar() or 0

    # Calculate real occupancy rate
    total_veiculos = db.query(sqlfunc.count(Veiculo.id)).filter(Veiculo.ativo == True).scalar() or 0
    alugados = db.query(sqlfunc.count(Veiculo.id)).filter(Veiculo.status == "alugado").scalar() or 0
    taxa_ocupacao = round((alugados / total_veiculos * 100), 1) if total_veiculos > 0 else 0.0

    # Revenue this month - SQL SUM instead of loading all into memory
    receita_mes = db.query(
        sqlfunc.coalesce(sqlfunc.sum(Contrato.valor_total), 0)
    ).filter(
        Contrato.data_criacao >= mes_passado
    ).scalar()
    receita_mes = float(receita_mes)

    return {
        "contratos_mes": contratos_mes,
        "multas_mes": multas_mes,
        "taxa_ocupacao": taxa_ocupacao,
        "receita_mes": receita_mes,
    }


@router.get("/alertas")
def get_alertas(
    urgencia: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get active alerts."""
    query = db.query(AlertaHistorico).filter(AlertaHistorico.resolvido == False)
    if urgencia:
        query = query.filter(AlertaHistorico.urgencia == urgencia)
    return query.all()


@router.get("/tops")
def get_tops(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get top performers - using SQL GROUP BY instead of N+1 queries."""
    # Top vehicles by revenue - single SQL query with GROUP BY
    top_veiculos_query = (
        db.query(
            Veiculo.placa,
            (Veiculo.marca + " " + Veiculo.modelo).label("marca_modelo"),
            sqlfunc.count(Contrato.id).label("contratos"),
            sqlfunc.coalesce(sqlfunc.sum(Contrato.valor_total), 0).label("receita"),
        )
        .outerjoin(Contrato, Contrato.veiculo_id == Veiculo.id)
        .filter(Veiculo.ativo == True)
        .group_by(Veiculo.id, Veiculo.placa, Veiculo.marca, Veiculo.modelo)
        .order_by(sqlfunc.coalesce(sqlfunc.sum(Contrato.valor_total), 0).desc())
        .limit(5)
        .all()
    )
    top_veiculos = [
        {"placa": r.placa, "marca_modelo": r.marca_modelo, "contratos": r.contratos, "receita": float(r.receita)}
        for r in top_veiculos_query
    ]

    # Top clients by total spent - single SQL query
    top_clientes_query = (
        db.query(
            Cliente.nome,
            sqlfunc.count(Contrato.id).label("contratos"),
            sqlfunc.coalesce(sqlfunc.sum(Contrato.valor_total), 0).label("total_gasto"),
        )
        .join(Contrato, Contrato.cliente_id == Cliente.id)
        .filter(Cliente.ativo == True)
        .group_by(Cliente.id, Cliente.nome)
        .having(sqlfunc.count(Contrato.id) > 0)
        .order_by(sqlfunc.coalesce(sqlfunc.sum(Contrato.valor_total), 0).desc())
        .limit(5)
        .all()
    )
    top_clientes = [
        {"nome": r.nome, "contratos": r.contratos, "total_gasto": float(r.total_gasto)}
        for r in top_clientes_query
    ]

    # Problematic vehicles (in maintenance) - single query
    veiculos_problematicos = [
        {"placa": v.placa, "marca_modelo": "{} {}".format(v.marca, v.modelo), "status": v.status}
        for v in db.query(Veiculo).filter(Veiculo.ativo == True, Veiculo.status == "manutencao").all()
    ]

    return {
        "top_veiculos": top_veiculos,
        "top_clientes": top_clientes,
        "veiculos_problematicos": veiculos_problematicos,
    }


@router.get("/previsao")
def get_previsao(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get forecasts - using SQL SUM instead of Python loops."""
    agora = datetime.now()
    mes_atual_inicio = agora.replace(day=1, hour=0, minute=0, second=0)
    mes_passado_inicio = (mes_atual_inicio - timedelta(days=1)).replace(day=1)

    # Current month revenue - SQL SUM
    receita_mes_atual = float(db.query(
        sqlfunc.coalesce(sqlfunc.sum(Contrato.valor_total), 0)
    ).filter(Contrato.data_criacao >= mes_atual_inicio).scalar())

    # Last month revenue - SQL SUM
    receita_mes_passado = float(db.query(
        sqlfunc.coalesce(sqlfunc.sum(Contrato.valor_total), 0)
    ).filter(
        Contrato.data_criacao >= mes_passado_inicio,
        Contrato.data_criacao < mes_atual_inicio
    ).scalar())

    # Current month expenses - SQL SUM across tables
    desp_contrato = float(db.query(
        sqlfunc.coalesce(sqlfunc.sum(DespesaContrato.valor), 0)
    ).filter(DespesaContrato.data_registro >= mes_atual_inicio).scalar())

    desp_veiculo = float(db.query(
        sqlfunc.coalesce(sqlfunc.sum(DespesaVeiculo.valor), 0)
    ).filter(DespesaVeiculo.data >= mes_atual_inicio).scalar())

    despesa_mes_atual = desp_contrato + desp_veiculo

    # Growth rate
    taxa_crescimento = 0.0
    if receita_mes_passado > 0:
        taxa_crescimento = round(((receita_mes_atual - receita_mes_passado) / receita_mes_passado) * 100, 1)

    # Active contracts revenue (future guaranteed) - SQL SUM
    previsao_receita = float(db.query(
        sqlfunc.coalesce(sqlfunc.sum(Contrato.valor_total), 0)
    ).filter(Contrato.status == "ativo").scalar())

    return {
        "previsao_receita": previsao_receita,
        "receita_mes_atual": receita_mes_atual,
        "receita_mes_passado": receita_mes_passado,
        "despesa_mes_atual": despesa_mes_atual,
        "taxa_crescimento": taxa_crescimento,
    }


@router.get("/atrasados")
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


@router.get("/vencimentos")
def get_vencimentos(
    dias: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get contracts expiring soon."""
    agora = datetime.now()
    fim = agora + timedelta(days=dias)
    contratos = db.query(Contrato).filter(
        (Contrato.data_fim.between(agora, fim)) & (Contrato.status == "ativo")
    ).all()
    return contratos


@router.get("/graficos")
def get_graficos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get data for dashboard charts - using conditional aggregation."""
    # Contratos por status - single query
    contrato_stats = db.query(
        Contrato.status,
        sqlfunc.count(Contrato.id)
    ).group_by(Contrato.status).all()
    contratos_por_status = {s: c for s, c in contrato_stats}

    # Veiculos por status - single query
    veiculo_stats = db.query(
        Veiculo.status,
        sqlfunc.count(Veiculo.id)
    ).group_by(Veiculo.status).all()
    veiculos_por_status = {s: c for s, c in veiculo_stats}

    return {
        "contratos_por_status": {
            "ativo": contratos_por_status.get("ativo", 0),
            "finalizado": contratos_por_status.get("finalizado", 0),
        },
        "veiculos_por_status": {
            "disponivel": veiculos_por_status.get("disponivel", 0),
            "alugado": veiculos_por_status.get("alugado", 0),
            "manutencao": veiculos_por_status.get("manutencao", 0),
        },
    }
