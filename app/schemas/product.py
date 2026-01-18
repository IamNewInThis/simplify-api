"""
Schemas para productos (products) y precios (prices)
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID
from decimal import Decimal


class PriceBase(BaseModel):
    """Base schema para precios"""
    price: Decimal
    original_price: Optional[Decimal] = None
    discount_percentage: Optional[Decimal] = None
    currency: str = "CLP"
    in_stock: bool = True


class PriceCreate(PriceBase):
    """Schema para crear un precio"""
    product_id: UUID


class PriceResponse(PriceBase):
    """Schema para respuesta de precio"""
    id: UUID
    product_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProductBase(BaseModel):
    """Base schema para productos"""
    url: str
    current_price: Optional[Decimal] = None
    active: bool = True


class ProductCreate(ProductBase):
    """Schema para crear un producto"""
    catalog_id: UUID
    store_id: UUID


class ProductResponse(ProductBase):
    """Schema para respuesta de producto"""
    id: UUID
    catalog_id: UUID
    store_id: UUID
    category_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    last_scraped_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProductWithPrice(ProductResponse):
    """Producto con su precio actual"""
    price: Optional[PriceResponse] = None
    store_name: Optional[str] = None
    store_active: Optional[bool] = None
    catalog_name: Optional[str] = None
    catalog_sku: Optional[str] = None
    brand_name: Optional[str] = None
    category_name: Optional[str] = None


class ProductSearchResult(BaseModel):
    """Resultado de búsqueda de producto"""
    catalog_id: UUID
    catalog_name: str
    catalog_sku: Optional[str] = None
    brand_name: Optional[str] = None
    category_name: Optional[str] = None
    products: list[ProductWithPrice] = []
    total_stores: int = 0
    was_scraped: bool = False  # Indica si se activó el scraper
