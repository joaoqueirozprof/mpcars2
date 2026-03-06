"""Pagination helper for all routers."""
from typing import Optional
from sqlalchemy.orm import Query
import math


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
        pass

    return result


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
    from sqlalchemy import or_

    # Apply search filter
    if search and search_fields and model:
        search_conditions = []
        for field_name in search_fields:
            field = getattr(model, field_name, None)
            if field is not None:
                search_conditions.append(field.ilike(f"%{search}%"))
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
