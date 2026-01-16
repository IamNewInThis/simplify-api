"""
Store schemas
"""
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
from datetime import datetime
from uuid import UUID


class StoreBase(BaseModel):
    """Base store schema"""
    name: str = Field(..., min_length=1, max_length=255, description="Store name")
    base_url: str = Field(..., description="Store base URL")
    active: bool = Field(True, description="Store status")


class StoreCreate(StoreBase):
    """Schema for creating a store"""
    pass


class StoreUpdate(BaseModel):
    """Schema for updating a store"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    base_url: Optional[str] = None
    active: Optional[bool] = None


class StoreResponse(StoreBase):
    """Schema for store response"""
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
