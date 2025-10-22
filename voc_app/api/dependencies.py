"""Shared API dependencies for authentication, pagination, and database sessions."""

from __future__ import annotations

from typing import Annotated, AsyncGenerator

from fastapi import Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from voc_app.config import get_settings
from voc_app.database import _SessionFactory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide database session for request lifecycle."""
    async with _SessionFactory() as session:
        yield session


# Dependency for database session
DatabaseSession = Annotated[AsyncSession, Depends(get_db)]


async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    """Verify API key from request header."""
    settings = get_settings()
    
    # For MVP, use environment-based API key
    # In production, this should query a database of valid keys
    valid_api_key = settings.alert_webhook_url  # Placeholder - should be dedicated API_KEY env var
    
    if not valid_api_key or x_api_key != valid_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    return x_api_key


# Optional API key dependency (for endpoints that may be public)
OptionalAPIKey = Annotated[str | None, Depends(verify_api_key)]


class PaginationParams:
    """Query parameters for pagination."""

    def __init__(
        self,
        skip: int = Query(0, ge=0, description="Number of records to skip"),
        limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return"),
    ):
        self.skip = skip
        self.limit = limit


# Dependency for pagination
Pagination = Annotated[PaginationParams, Depends()]


class SortParams:
    """Query parameters for sorting."""

    def __init__(
        self,
        sort_by: str = Query("created_at", description="Field to sort by"),
        order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    ):
        self.sort_by = sort_by
        self.order = order


# Dependency for sorting
Sorting = Annotated[SortParams, Depends()]
