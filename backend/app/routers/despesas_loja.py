from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.core.database import get_db
from app.core.pagination import escape_like
from app.core.deps import get_current_user, require_page_access
from app.models.user import User
from app.models import DespesaLoja


router = APIRouter(
    prefix="/despesas-loja",
    tags=["Despesas Loja"],
    dependencies=[Depends(require_page_access("despesas-loja"))],
)


# ============================================================
# Schemas
# ============================================================
class DespesaLojaCreate(BaseModel):
    categoria: str
    descricao: str
    valor: float
    mes: int
    ano: int


class DespesaLojaUpdate(BaseModel):
    categoria: Optional[str] = None
    descricao: Optional[str] = None
    valor: Optional[float] = None
    mes: Optional[int] = None
    ano: Optional[int] = None


# ============================================================
# Endpoints
# ============================================================
@router.get("/")
def list_despesas_loja(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    categoria: Optional[str] = None,
    mes: Optional[int] = None,
    ano: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all shop expenses with pagination and filters."""
    query = db.query(DespesaLoja)

    if search:
        query = query.filter(DespesaLoja.descricao.ilike(f"%{escape_like(search)}%"))
    if categoria:
        query = query.filter(DespesaLoja.categoria == categoria)
    if mes:
        query = query.filter(DespesaLoja.mes == mes)
    if ano:
        query = query.filter(DespesaLoja.ano == ano)

    total = query.count()
    despesas = query.order_by(desc(DespesaLoja.ano), desc(DespesaLoja.mes), desc(DespesaLoja.id)).offset((page - 1) * limit).limit(limit).all()

    data = []
    for d in despesas:
        data.append({
            "id": d.id,
            "categoria": d.categoria,
            "descricao": d.descricao,
            "valor": float(d.valor) if d.valor else 0,
            "mes": d.mes,
            "ano": d.ano,
            "data": d.data.isoformat() if d.data else None,
        })

    return {
        "data": data,
        "total": total,
        "page": page,
        "limit": limit,
        "totalPages": max(1, (total + limit - 1) // limit),
    }


@router.get("/resumo")
def resumo_despesas_loja(
    ano: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get summary of shop expenses - SQL GROUP BY instead of Python loop."""
    base_filter = DespesaLoja.ano == ano if ano else True

    # Total
    totais = db.query(
        func.count(DespesaLoja.id).label("qtd"),
        func.coalesce(func.sum(DespesaLoja.valor), 0).label("total"),
    ).filter(base_filter).first()

    # By category - SQL GROUP BY
    cat_rows = db.query(
        func.coalesce(DespesaLoja.categoria, "Outros").label("cat"),
        func.sum(DespesaLoja.valor).label("valor"),
    ).filter(base_filter).group_by(DespesaLoja.categoria).all()
    por_categoria = {row.cat: float(row.valor or 0) for row in cat_rows}

    # By month - SQL GROUP BY
    mes_rows = db.query(
        DespesaLoja.mes,
        DespesaLoja.ano,
        func.sum(DespesaLoja.valor).label("valor"),
    ).filter(base_filter).group_by(DespesaLoja.mes, DespesaLoja.ano).order_by(
        DespesaLoja.ano, DespesaLoja.mes
    ).all()
    por_mes = {f"{row.mes:02d}/{row.ano}": float(row.valor or 0) for row in mes_rows}

    return {
        "total": float(totais.total),
        "por_categoria": por_categoria,
        "por_mes": por_mes,
        "quantidade": totais.qtd,
    }


@router.get("/categorias")
def list_categorias(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all unique categories."""
    categorias = db.query(DespesaLoja.categoria).distinct().all()
    return [c[0] for c in categorias if c[0]]


@router.get("/{despesa_id}")
def get_despesa_loja(
    despesa_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single shop expense."""
    despesa = db.query(DespesaLoja).filter(DespesaLoja.id == despesa_id).first()
    if not despesa:
        raise HTTPException(status_code=404, detail="Despesa nao encontrada")

    return {
        "id": despesa.id,
        "categoria": despesa.categoria,
        "descricao": despesa.descricao,
        "valor": float(despesa.valor) if despesa.valor else 0,
        "mes": despesa.mes,
        "ano": despesa.ano,
        "data": despesa.data.isoformat() if despesa.data else None,
    }


@router.post("/", status_code=201)
def create_despesa_loja(
    data: DespesaLojaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new shop expense."""
    if data.mes < 1 or data.mes > 12:
        raise HTTPException(status_code=400, detail="Mes deve ser entre 1 e 12")
    if data.ano < 2020 or data.ano > 2099:
        raise HTTPException(status_code=400, detail="Ano invalido")
    if data.valor <= 0:
        raise HTTPException(status_code=400, detail="Valor deve ser maior que zero")

    despesa = DespesaLoja(
        categoria=data.categoria,
        descricao=data.descricao,
        valor=data.valor,
        mes=data.mes,
        ano=data.ano,
    )
    db.add(despesa)
    db.commit()
    db.refresh(despesa)

    return {
        "id": despesa.id,
        "categoria": despesa.categoria,
        "descricao": despesa.descricao,
        "valor": float(despesa.valor) if despesa.valor else 0,
        "mes": despesa.mes,
        "ano": despesa.ano,
        "data": despesa.data.isoformat() if despesa.data else None,
    }


@router.put("/{despesa_id}")
@router.patch("/{despesa_id}")
def update_despesa_loja(
    despesa_id: int,
    data: DespesaLojaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a shop expense."""
    despesa = db.query(DespesaLoja).filter(DespesaLoja.id == despesa_id).first()
    if not despesa:
        raise HTTPException(status_code=404, detail="Despesa nao encontrada")

    if data.categoria is not None:
        despesa.categoria = data.categoria
    if data.descricao is not None:
        despesa.descricao = data.descricao
    if data.valor is not None:
        if data.valor <= 0:
            raise HTTPException(status_code=400, detail="Valor deve ser maior que zero")
        despesa.valor = data.valor
    if data.mes is not None:
        if data.mes < 1 or data.mes > 12:
            raise HTTPException(status_code=400, detail="Mes deve ser entre 1 e 12")
        despesa.mes = data.mes
    if data.ano is not None:
        if data.ano < 2020 or data.ano > 2099:
            raise HTTPException(status_code=400, detail="Ano invalido")
        despesa.ano = data.ano

    db.commit()
    db.refresh(despesa)

    return {
        "id": despesa.id,
        "categoria": despesa.categoria,
        "descricao": despesa.descricao,
        "valor": float(despesa.valor) if despesa.valor else 0,
        "mes": despesa.mes,
        "ano": despesa.ano,
        "data": despesa.data.isoformat() if despesa.data else None,
    }


@router.delete("/{despesa_id}", status_code=204)
def delete_despesa_loja(
    despesa_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a shop expense."""
    despesa = db.query(DespesaLoja).filter(DespesaLoja.id == despesa_id).first()
    if not despesa:
        raise HTTPException(status_code=404, detail="Despesa nao encontrada")

    db.delete(despesa)
    db.commit()
