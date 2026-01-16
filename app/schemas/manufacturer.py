"""
Manufacturer schemas
"""
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
from datetime import datetime
from uuid import UUID


class ManufacturerBase(BaseModel):
    """Base manufacturer schema"""
    name: str = Field(..., min_length=1, max_length=255, description="Manufacturer name")
    tax_id: Optional[str] = Field(None, max_length=100, description="Tax ID (RUT, NIT, EIN)")
    country: Optional[str] = Field(None, max_length=100, description="Country of origin")
    website: Optional[str] = Field(None, description="Company website")
    main_business_line: Optional[str] = Field(None, max_length=255, description="Main business line")


class ManufacturerCreate(ManufacturerBase):
    """Schema for creating a manufacturer"""
    pass


class ManufacturerUpdate(BaseModel):
    """Schema for updating a manufacturer"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    tax_id: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    website: Optional[str] = None
    main_business_line: Optional[str] = Field(None, max_length=255)


class ManufacturerResponse(ManufacturerBase):
    """Schema for manufacturer response"""
    id: UUID
    logo_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ManufacturerWithBrands(ManufacturerResponse):
    """Schema for manufacturer with brand count"""
    brand_count: int = 0

    class Config:
        from_attributes = True
