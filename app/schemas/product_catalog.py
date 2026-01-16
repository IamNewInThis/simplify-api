"""
Product Catalog schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class ProductCatalogBase(BaseModel):
    """Base product catalog schema"""
    name: str = Field(..., min_length=1, max_length=500, description="Product name")
    sku: Optional[str] = Field(None, max_length=100, description="Product SKU")
    brand_id: Optional[UUID] = Field(None, description="Brand ID")
    category_id: Optional[UUID] = Field(None, description="Category ID")
    attributes: Optional[Dict[str, Any]] = Field(None, description="Product attributes as JSON")
    active: bool = Field(True, description="Product status")


class ProductCatalogCreate(ProductCatalogBase):
    """Schema for creating a product"""
    pass


class ProductCatalogUpdate(BaseModel):
    """Schema for updating a product"""
    name: Optional[str] = Field(None, min_length=1, max_length=500)
    sku: Optional[str] = Field(None, max_length=100)
    brand_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    attributes: Optional[Dict[str, Any]] = None
    active: Optional[bool] = None


class ProductCatalogResponse(ProductCatalogBase):
    """Schema for product response"""
    id: UUID
    image_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProductCatalogWithDetails(ProductCatalogResponse):
    """Schema for product with brand and category details"""
    brand_name: Optional[str] = None
    category_name: Optional[str] = None

    class Config:
        from_attributes = True
