"""
Brand schemas
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID
import re


class BrandBase(BaseModel):
    """Base brand schema"""
    name: str = Field(..., min_length=1, max_length=255, description="Brand name")
    manufacturer_id: Optional[UUID] = Field(None, description="Manufacturer ID")
    active: bool = Field(True, description="Brand status")


class BrandCreate(BaseModel):
    """Schema for creating a brand"""
    name: str = Field(..., min_length=1, max_length=255, description="Brand name")
    manufacturer_id: Optional[UUID] = Field(None, description="Manufacturer ID")
    active: bool = Field(True, description="Brand status")


class BrandUpdate(BaseModel):
    """Schema for updating a brand"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    manufacturer_id: Optional[UUID] = None
    active: Optional[bool] = None


class BrandResponse(BrandBase):
    """Schema for brand response"""
    id: UUID
    product_count: int = 0
    logo_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BrandWithManufacturer(BrandResponse):
    """Schema for brand with manufacturer details"""
    manufacturer_name: Optional[str] = None
    manufacturer_country: Optional[str] = None

    class Config:
        from_attributes = True
