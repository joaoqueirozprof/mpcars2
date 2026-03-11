from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc, union_all, literal, cast, String, DateTime, Float, text
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import math
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models import (
    Contrato,
    DespesaContrato,
    DespesaVeiculo,
    DespesaLoja,
    Cliente,
)
from app.services.pdf_service import PDFService
from app.services.export_service import ExportService
from app.services.activity_logger import log_activity


router = APIRouter(prefix="/financeiro", tags=["Financeiro"])


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


@router.get("/")
def list_financeiro(
    page: int = 1,
    limit: int = 50,
    tipo: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get paginated financial records using SQL UNION ALL instead of loading everything into Python."""

    # Build UNION ALL query for consolidated view
    # Each subquery produces: id, data, tipo, categoria, descricao, valor, status
    q_contratos = (
        db.query(
            (literal("c-") + cast(Contrato.id, String)).label("id"),
            Contrato.data_criacao.label("data"),
            literal("receita").label("tipo"),
            literal("Locação").label("categoria"),
            (literal("Contrato #") + Contrato.numero).label("descricao"),
            sqlfunc.coalesce(Contrato.valor_total, 0).label("valor"),
            sqlfunc.IF(Contrato.status == "finalizado", literal("pago"), literal("pendente")).label("status_fin") if hasattr(sqlfunc, 'IF') else
            sqlfunc.cast(
                sqlfunc.coalesce(None, literal("pendente")), String
            ).label("status_fin"),
        )
    )

    # For PostgreSQL, use CASE WHEN instead of IF
    q_receitas = db.query(
        (literal("c-") + cast(Contrato.id, String)).label("record_id"),
        Contrato.data_criacao.label("data"),
        literal("receita").label("tipo"),
        literal("Locação").label("categoria"),
        Contrato.numero.label("descricao"),
        sqlfunc.coalesce(cast(Contrato.valor_total, Float), 0).label("valor"),
        text("CASE WHEN contratos.status = 'finalizado' THEN 'pago' ELSE 'pendente' END").label("status_fin"),
    )

    q_desp_contrato = db.query(
        (literal("dc-") + cast(DespesaContrato.id, String)).label("record_id"),
        DespesaContrato.data_criacao.label("data"),
        literal("despesa").label("tipo"),
        sqlfunc.coalesce(DespesaContrato.tipo, literal("Contrato")).label("categoria"),
        DespesaContrato.descricao.label("descricao"),
        sqlfunc.coalesce(cast(DespesaContrato.valor, Float), 0).label("valor"),
        literal("pago").label("status_fin"),
    )

    q_desp_veiculo = db.query(
        (literal("dv-") + cast(DespesaVeiculo.id, String)).label("record_id"),
        DespesaVeiculo.data_criacao.label("data"),
        literal("despesa").label("tipo"),
        literal("Veículo").label("categoria"),
        DespesaVeiculo.descricao.label("descricao"),
        sqlfunc.coalesce(cast(DespesaVeiculo.valor, Float), 0).label("valor"),
        literal("pago").label("status_fin"),
    )

    q_desp_loja = db.query(
        (literal("dl-") + cast(DespesaLoja.id, String)).label("record_id"),
        DespesaLoja.data_criacao.label("data"),
        literal("despesa").label("tipo"),
        literal("Loja").label("categoria"),
        DespesaLoja.descricao.label("descricao"),
        sqlfunc.coalesce(cast(DespesaLoja.valor, Float), 0).label("valor"),
        literal("pago").label("status_fin"),
    )

    # Build UNION ALL
    combined = union_all(
        q_receitas,
        q_desp_contrato,
        q_desp_veiculo,
        q_desp_loja,
    ).alias("financeiro")

    # Apply filters
    query = db.query(combined)

    if tipo:
        query = query.filter(combined.c.tipo == tipo)
    if status:
        query = query.filter(combined.c.status_fin == status)

    # Get total count
    total = query.count()

    # Order and paginate in SQL
    results = (
        query
        .order_by(combined.c.data.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    # Format results
    data = []
    for r in results:
        data.append({
            "id": r.record_id,
            "data": r.data.isoformat() if r.data else None,
            "tipo": r.tipo,
            "categoria": r.categoria,
            "descricao": r.descricao,
            "valor": float(r.valor) if r.valor else 0.0,
            "status": r.status_fin,
        })

    return {
        "data": data,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": math.ceil(total / limit) if limit > 0 else 1,
    }


@router.get("/resumo")
def get_resumo(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get financial summary - using SQL SUM instead of Python loops."""
    total_receita = float(db.query(
        sqlfunc.coalesce(sqlfunc.sum(Contrato.valor_total), 0)
    ).scalar())

    total_despesa_contrato = float(db.query(
        sqlfunc.coalesce(sqlfunc.sum(DespesaContrato.valor), 0)
    ).scalar())

    total_despesa_veiculo = float(db.query(
        sqlfunc.coalesce(sqlfunc.sum(DespesaVeiculo.valor), 0)
    ).scalar())

    total_despesa_loja = float(db.query(
        sqlfunc.coalesce(sqlfunc.sum(DespesaLoja.valor), 0)
    ).scalar())

    total_despesa = total_despesa_contrato + total_despesa_veiculo + total_despesa_loja
    lucro = total_receita - total_despesa

    return {
        "total_receita": total_receita,
        "total_despesa": total_despesa,
        "lucro": lucro,
        "despesa_contrato": total_despesa_contrato,
        "despesa_veiculo": total_despesa_veiculo,
        "despesa_loja": total_despesa_loja,
    }


@router.post("/despesa-contrato")
def criar_despesa_contrato(
    despesa: DespesaContratoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Create expense for contract."""
    contrato = db.query(Contrato).filter(
        Contrato.id == despesa.contrato_id
    ).first()
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
    log_activity(db, current_user, "CRIAR", "DespesaContrato", "Despesa de contrato criada: {}".format(despesa.descricao), db_despesa.id, request)
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
    log_activity(db, current_user, "CRIAR", "DespesaVeiculo", "Despesa de veículo criada: {}".format(despesa.descricao), db_despesa.id, request)
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
    log_activity(db, current_user, "CRIAR", "DespesaLoja", "Despesa de loja criada: {}".format(despesa.descricao), db_despesa.id, request)
    return db_despesa


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_registro_financeiro(
    record_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Delete a financial record by composite id (e.g. c-1, dc-5, dv-3, dl-2).

    CORRIGIDO: Com CASCADE nos models, a deleção de contrato não precisa mais
    de 30+ linhas de delete manual - o banco cuida automaticamente.
    """
    parts = record_id.split("-", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="ID invalido")

    prefix, id_str = parts
    try:
        real_id = int(id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID invalido")

    if prefix == "dc":
        obj = db.query(DespesaContrato).filter(DespesaContrato.id == real_id).first()
    elif prefix == "dv":
        obj = db.query(DespesaVeiculo).filter(DespesaVeiculo.id == real_id).first()
    elif prefix == "dl":
        obj = db.query(DespesaLoja).filter(DespesaLoja.id == real_id).first()
    elif prefix == "c":
        # With CASCADE configured in models, deleting contrato auto-deletes dependents
        obj = db.query(Contrato).filter(Contrato.id == real_id).first()
    else:
        raise HTTPException(status_code=400, detail="Tipo de registro desconhecido")

    if not obj:
        raise HTTPException(status_code=404, detail="Registro nao encontrado")

    db.delete(obj)
    db.commit()
    log_activity(db, current_user, "EXCLUIR", "Financeiro", "Registro financeiro {} excluído".format(record_id), real_id, request)


@router.get("/faturamento")
def get_faturamento(
    mes: Optional[int] = None,
    ano: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get billing information - using SQL SUM."""
    query = db.query(
        sqlfunc.coalesce(sqlfunc.sum(Contrato.valor_total), 0).label("total"),
        sqlfunc.count(Contrato.id).label("qtd"),
    )

    if mes and ano:
        start = datetime(ano, mes, 1)
        if mes == 12:
            end = datetime(ano + 1, 1, 1)
        else:
            end = datetime(ano, mes + 1, 1)
        query = query.filter(Contrato.data_criacao >= start, Contrato.data_criacao < end)

    result = query.one()
    return {"total_faturamento": float(result.total), "quantidade_contratos": result.qtd}


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

    if inicio > fim:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="data_inicio deve ser anterior a data_fim"
        )

    contratos = db.query(Contrato).filter(
        Contrato.data_criacao.between(inicio, fim)
    ).all()

    total_receita = float(db.query(
        sqlfunc.coalesce(sqlfunc.sum(Contrato.valor_total), 0)
    ).filter(Contrato.data_criacao.between(inicio, fim)).scalar())

    return {
        "periodo": {"inicio": data_inicio, "fim": data_fim},
        "total_contratos": len(contratos),
        "total_receita": total_receita,
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
        headers={"Content-Disposition": "attachment; filename=relatorio_financeiro_{}_{}.pdf".format(data_inicio, data_fim)},
    )
