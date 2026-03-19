"""Base router with generic CRUD operations."""
from typing import Any, Generic, TypeVar, Optional, List, Type
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import inspect

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.pagination import paginate
from app.models.user import User

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseRouter(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Generic CRUD router for SQLAlchemy models."""

    def __init__(
        self,
        model: Type[ModelType],
        create_schema: Type[CreateSchemaType],
        update_schema: Type[UpdateSchemaType],
        prefix: str,
        tags: List[str],
        dependencies: Optional[List] = None,
        get_relationships: Optional[bool] = False,
    ):
        self.model = model
        self.create_schema = create_schema
        self.update_schema = update_schema
        self.prefix = prefix
        self.tags = tags
        self.dependencies = dependencies or []
        self.get_relationships = get_relationships

        self.router = APIRouter(
            prefix=prefix,
            tags=tags,
            dependencies=dependencies,
        )

        self._setup_routes()

    def _get_relationships(self, model) -> List[str]:
        """Get relationship names for a model."""
        try:
            mapper = inspect(type(model))
            return [rel.key for rel in mapper.relationships]
        except Exception:
            return []

    def _setup_routes(self):
        """Setup CRUD routes."""
        model = self.model

        @self.router.get("/", name=f"list_{model.__tablename__}")
        def list_items(
            page: int = Query(1, ge=1),
            limit: int = Query(50, ge=1, le=100),
            search: Optional[str] = None,
            status_filter: Optional[str] = None,
            db: Session = Depends(get_db),
            current_user: User = Depends(get_current_user),
        ):
            """List all items with pagination."""
            query = db.query(model)

            if self.get_relationships:
                relationships = self._get_relationships(model)
                for rel in relationships:
                    query = query.options(joinedload(getattr(model, rel)))

            search_fields = self._get_search_fields()

            return paginate(
                query=query,
                page=page,
                limit=limit,
                search=search,
                search_fields=search_fields,
                model=model,
                status_filter=status_filter,
            )

        @self.router.get("/{item_id}", name=f"get_{model.__tablename__}")
        def get_item(
            item_id: int,
            db: Session = Depends(get_db),
            current_user: User = Depends(get_current_user),
        ):
            """Get a single item by ID."""
            query = db.query(model)

            if self.get_relationships:
                relationships = self._get_relationships(model)
                for rel in relationships:
                    query = query.options(joinedload(getattr(model, rel)))

            item = query.filter(model.id == item_id).first()

            if not item:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"{model.__tablename__.capitalize()} not found",
                )

            return item

        @self.router.post("/", name=f"create_{model.__tablename__}", status_code=status.HTTP_201_CREATED)
        def create_item(
            item_data: CreateSchemaType,
            db: Session = Depends(get_db),
            current_user: User = Depends(get_current_user),
        ):
            """Create a new item."""
            item_dict = item_data.model_dump(exclude_unset=True)

            item = model(**item_dict)
            db.add(item)
            db.commit()
            db.refresh(item)

            return item

        @self.router.put("/{item_id}", name=f"update_{model.__tablename__}")
        def update_item(
            item_id: int,
            item_data: UpdateSchemaType,
            db: Session = Depends(get_db),
            current_user: User = Depends(get_current_user),
        ):
            """Update an item."""
            item = db.query(model).filter(model.id == item_id).first()

            if not item:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"{model.__tablename__.capitalize()} not found",
                )

            item_dict = item_data.model_dump(exclude_unset=True)

            for key, value in item_dict.items():
                setattr(item, key, value)

            db.commit()
            db.refresh(item)

            return item

        @self.router.delete("/{item_id}", name=f"delete_{model.__tablename__}", status_code=status.HTTP_204_NO_CONTENT)
        def delete_item(
            item_id: int,
            db: Session = Depends(get_db),
            current_user: User = Depends(get_current_user),
        ):
            """Delete an item."""
            item = db.query(model).filter(model.id == item_id).first()

            if not item:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"{model.__tablename__.capitalize()} not found",
                )

            db.delete(item)
            db.commit()

            return None

    def _get_search_fields(self) -> List[str]:
        """Get searchable fields. Override in subclasses."""
        return ["nome", "descricao", "razao_social"]


def create_crud_router(
    model: Type[ModelType],
    create_schema: Type[CreateSchemaType],
    update_schema: Type[UpdateSchemaType],
    prefix: str,
    tags: List[str],
    dependencies: Optional[List] = None,
    get_relationships: bool = False,
) -> APIRouter:
    """Factory function to create a CRUD router."""
    base = BaseRouter(
        model=model,
        create_schema=create_schema,
        update_schema=update_schema,
        prefix=prefix,
        tags=tags,
        dependencies=dependencies,
        get_relationships=get_relationships,
    )
    return base.router
