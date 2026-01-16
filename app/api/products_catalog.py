"""
Products Catalog API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.models.product_catalog import ProductCatalog
from app.models.brand import Brand
from app.models.category import Category
from app.schemas.product_catalog import (
    ProductCatalogCreate, 
    ProductCatalogUpdate, 
    ProductCatalogResponse,
    ProductCatalogWithDetails
)

router = APIRouter()


@router.get("/products-catalog", response_model=List[ProductCatalogResponse])
def get_products(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = False,
    search: Optional[str] = Query(None, description="Search by product name or SKU"),
    brand_id: Optional[UUID] = Query(None, description="Filter by brand"),
    category_id: Optional[UUID] = Query(None, description="Filter by category"),
    db: Session = Depends(get_db)
):
    """
    Get all products with optional filters
    """
    query = db.query(ProductCatalog)
    
    if active_only:
        query = query.filter(ProductCatalog.active == True)
    
    if search:
        query = query.filter(
            (ProductCatalog.name.ilike(f"%{search}%")) |
            (ProductCatalog.sku.ilike(f"%{search}%"))
        )
    
    if brand_id:
        query = query.filter(ProductCatalog.brand_id == brand_id)
    
    if category_id:
        query = query.filter(ProductCatalog.category_id == category_id)
    
    products = query.offset(skip).limit(limit).all()
    return products


@router.get("/products-catalog/with-details", response_model=List[ProductCatalogWithDetails])
def get_products_with_details(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = False,
    db: Session = Depends(get_db)
):
    """
    Get all products with brand and category information
    """
    query = db.query(ProductCatalog).options(
        joinedload(ProductCatalog.brand),
        joinedload(ProductCatalog.category)
    )
    
    if active_only:
        query = query.filter(ProductCatalog.active == True)
    
    products = query.offset(skip).limit(limit).all()
    
    # Transform to include brand and category names
    result = []
    for product in products:
        product_dict = {
            "id": product.id,
            "name": product.name,
            "sku": product.sku,
            "brand_id": product.brand_id,
            "category_id": product.category_id,
            "attributes": product.attributes,
            "active": product.active,
            "image_url": product.image_url,
            "created_at": product.created_at,
            "updated_at": product.updated_at,
            "brand_name": product.brand.name if product.brand else None,
            "category_name": product.category.name if product.category else None,
        }
        result.append(product_dict)
    
    return result


@router.get("/products-catalog/{product_id}", response_model=ProductCatalogResponse)
def get_product(
    product_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get a specific product by ID
    """
    product = db.query(ProductCatalog).filter(ProductCatalog.id == product_id).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {product_id} not found"
        )
    
    return product


@router.post("/products-catalog", response_model=ProductCatalogResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    product: ProductCatalogCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new product
    """
    # Check if SKU already exists (if provided)
    if product.sku:
        existing = db.query(ProductCatalog).filter(ProductCatalog.sku == product.sku).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product with SKU '{product.sku}' already exists"
            )
    
    # If brand_id is provided, verify it exists
    if product.brand_id:
        brand = db.query(Brand).filter(Brand.id == product.brand_id).first()
        if not brand:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Brand with id {product.brand_id} not found"
            )
    
    # If category_id is provided, verify it exists
    if product.category_id:
        category = db.query(Category).filter(Category.id == product.category_id).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category with id {product.category_id} not found"
            )
    
    # Create new product
    db_product = ProductCatalog(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    
    return db_product


@router.put("/products-catalog/{product_id}", response_model=ProductCatalogResponse)
def update_product(
    product_id: UUID,
    product: ProductCatalogUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a product
    """
    db_product = db.query(ProductCatalog).filter(ProductCatalog.id == product_id).first()
    
    if not db_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {product_id} not found"
        )
    
    # Check if new SKU conflicts with existing product
    if product.sku and product.sku != db_product.sku:
        existing = db.query(ProductCatalog).filter(ProductCatalog.sku == product.sku).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product with SKU '{product.sku}' already exists"
            )
    
    # If brand_id is being updated, verify it exists
    if product.brand_id is not None:
        brand = db.query(Brand).filter(Brand.id == product.brand_id).first()
        if not brand:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Brand with id {product.brand_id} not found"
            )
    
    # If category_id is being updated, verify it exists
    if product.category_id is not None:
        category = db.query(Category).filter(Category.id == product.category_id).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category with id {product.category_id} not found"
            )
    
    # Update fields
    update_data = product.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_product, field, value)
    
    db.commit()
    db.refresh(db_product)
    
    return db_product


@router.delete("/products-catalog/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Delete a product
    """
    db_product = db.query(ProductCatalog).filter(ProductCatalog.id == product_id).first()
    
    if not db_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {product_id} not found"
        )
    
    # TODO: Add check for associated store products when products table is implemented
    
    db.delete(db_product)
    db.commit()
    
    return None
