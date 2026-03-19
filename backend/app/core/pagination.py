"""Pagination helper for all routers."""
import logging
from typing import Optional
from sqlalchemy.orm import Query
import math


def strip_html(value: str) -> str:
    """Remove HTML tags from user input to prevent stored XSS."""
    import re
    return re.sub(r'<[^>]+>', '', value).strip() if value else value


def escape_like(value: str) -> str:
    """Escape LIKE wildcard characters in user input."""
    return value.replace("%", r"\%").replace("_", r"\_")


def _apply_legacy_aliases(item, result: dict) -> dict:
    """Expose compatibility aliases expected by the current frontend."""
    table_name = getattr(item, "__tablename__", "")

    if table_name == "clientes":
        result["cpf_cnpj"] = result.get("cpf")
        result["endereco"] = result.get("endereco_residencial")
        result["cidade"] = result.get("cidade_residencial")
        result["estado"] = result.get("estado_residencial")
        result["cep"] = result.get("cep_residencial")
        result["tipo"] = "pessoa_juridica" if result.get("empresa_id") else "pessoa_fisica"

    elif table_name == "empresas":
        result["responsavel"] = result.get("contato_principal")

    elif table_name == "veiculos":
        result["quilometragem"] = result.get("km_atual", 0)
        result["data_compra"] = result.get("data_aquisicao")
        result.setdefault("observacoes", "")

    elif table_name == "contratos":
        result["quilometragem_inicial"] = result.get("km_inicial")
        result["quilometragem_final"] = result.get("km_final")

    elif table_name == "manutencoes":
        result["data_manutencao"] = result.get("data_realizada") or result.get("data_proxima")
        result["valor"] = result.get("custo")
        result["quilometragem"] = result.get("km_realizada") or result.get("km_proxima")
        result["status_original"] = result.get("status")

        if result.get("status") == "em_andamento":
            result["status"] = "em_progresso"
        elif result.get("status") == "agendada":
            result["status"] = "pendente"

    elif table_name == "reservas":
        result["data_reserva"] = result.get("data_criacao")
        status = result.get("status")
        result["status_original"] = status
        if status in {"pendente", "confirmada"}:
            result["status"] = "ativa"

    return result


def _serialize_item(item) -> dict:
    """Serialize a SQLAlchemy model instance to dict, including nested relationships."""
    if item is None:
        return None

    result = {}
    # Get column values
    for column in item.__table__.columns:
        value = getattr(item, column.name)
        # Convert Decimal to float for JSON serialization
        if hasattr(value, 'as_integer_ratio'):  # Decimal/float
            value = float(value)
        elif hasattr(value, 'isoformat'):  # datetime/date
            value = value.isoformat()
        result[column.name] = value

    # Get relationship values (only one level deep)
    from sqlalchemy import inspect as sa_inspect
    try:
        mapper = sa_inspect(type(item))
        for rel in mapper.relationships:
            rel_name = rel.key
            # Only serialize if already loaded (don't trigger lazy load for nested)
            if rel_name in item.__dict__:
                related = getattr(item, rel_name)
                if related is not None:
                    rel_dict = {}
                    for col in related.__table__.columns:
                        val = getattr(related, col.name)
                        if hasattr(val, 'as_integer_ratio'):
                            val = float(val)
                        elif hasattr(val, 'isoformat'):
                            val = val.isoformat()
                        rel_dict[col.name] = val
                    result[rel_name] = rel_dict
                else:
                    result[rel_name] = None
    except Exception:
        logging.getLogger(__name__).debug("Pagination serialization error", exc_info=True)

    return _apply_legacy_aliases(item, result)


def paginate(
    query: Query,
    page: int = 1,
    limit: int = 50,
    search: Optional[str] = None,
    search_fields: list = None,
    model=None,
    status_filter: Optional[str] = None,
    status_field: str = "status",
    extra_filters: dict = None,
) -> dict:
    """
    Apply pagination, search, and filters to a SQLAlchemy query.
    Returns dict matching PaginatedResponse format.
    """
    # Clamp page and limit to valid values
    page = max(1, page)
    limit = max(1, min(limit, 500))

    from sqlalchemy import or_

    # Apply search filter
    if search and search_fields and model:
        search_conditions = []
        for field_name in search_fields:
            field = getattr(model, field_name, None)
            if field is not None:
                search_conditions.append(field.ilike(f"%{escape_like(search)}%"))
        if search_conditions:
            query = query.filter(or_(*search_conditions))

    # Apply status filter
    if status_filter and model:
        field = getattr(model, status_field, None)
        if field is not None:
            query = query.filter(field == status_filter)

    # Apply extra filters
    if extra_filters and model:
        for field_name, value in extra_filters.items():
            if value is not None:
                field = getattr(model, field_name, None)
                if field is not None:
                    query = query.filter(field == value)

    # Get total count
    total = query.count()

    # Calculate pagination
    total_pages = math.ceil(total / limit) if limit > 0 else 1
    offset = (page - 1) * limit

    # Get paginated data
    items = query.offset(offset).limit(limit).all()

    # Serialize items with nested relationships
    serialized = [_serialize_item(item) for item in items]

    return {
        "data": serialized,
        "total": total,
        "page": page,
        "limit": limit,
        "totalPages": total_pages,
    }
