"""
Brands API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.models.brand import Brand
from app.models.manufacturer import Manufacturer
from app.schemas.brand import BrandCreate, BrandUpdate, BrandResponse, BrandWithManufacturer

router = APIRouter()


@router.get("/brands", response_model=List[BrandResponse])
def get_brands(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = False,
    search: Optional[str] = Query(None, description="Search by brand name"),
    manufacturer_id: Optional[UUID] = Query(None, description="Filter by manufacturer"),
    db: Session = Depends(get_db)
):
    """
    Get all brands with optional filters
    """
    query = db.query(Brand)
    
    if active_only:
        query = query.filter(Brand.active == True)
    
    if search:
        query = query.filter(Brand.name.ilike(f"%{search}%"))
    
    if manufacturer_id:
        query = query.filter(Brand.manufacturer_id == manufacturer_id)
    
    brands = query.offset(skip).limit(limit).all()
    return brands


@router.get("/brands/with-manufacturer", response_model=List[BrandWithManufacturer])
def get_brands_with_manufacturer(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = False,
    db: Session = Depends(get_db)
):
    """
    Get all brands with manufacturer information
    """
    query = db.query(Brand).options(joinedload(Brand.manufacturer))
    
    if active_only:
        query = query.filter(Brand.active == True)
    
    brands = query.offset(skip).limit(limit).all()
    
    # Transform to include manufacturer info
    result = []
    for brand in brands:
        brand_dict = {
            "id": brand.id,
            "name": brand.name,
            "manufacturer_id": brand.manufacturer_id,
            "active": brand.active,
            "product_count": brand.product_count,
            "logo_url": brand.logo_url,
            "created_at": brand.created_at,
            "updated_at": brand.updated_at,
            "manufacturer_name": brand.manufacturer.name if brand.manufacturer else None,
            "manufacturer_country": brand.manufacturer.country if brand.manufacturer else None,
        }
        result.append(brand_dict)
    
    return result


@router.get("/brands/{brand_id}", response_model=BrandResponse)
def get_brand(
    brand_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get a specific brand by ID
    """
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Brand with id {brand_id} not found"
        )
    
    return brand


@router.post("/brands", response_model=BrandResponse, status_code=status.HTTP_201_CREATED)
def create_brand(
    brand: BrandCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new brand
    """
    # Check if name already exists
    existing = db.query(Brand).filter(Brand.name == brand.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Brand with name '{brand.name}' already exists"
        )
    
    # If manufacturer_id is provided, verify it exists
    if brand.manufacturer_id:
        manufacturer = db.query(Manufacturer).filter(Manufacturer.id == brand.manufacturer_id).first()
        if not manufacturer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Manufacturer with id {brand.manufacturer_id} not found"
            )
    
    # Create new brand
    db_brand = Brand(**brand.model_dump())
    db.add(db_brand)
    db.commit()
    db.refresh(db_brand)
    
    return db_brand


@router.put("/brands/{brand_id}", response_model=BrandResponse)
def update_brand(
    brand_id: UUID,
    brand: BrandUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a brand
    """
    db_brand = db.query(Brand).filter(Brand.id == brand_id).first()
    
    if not db_brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Brand with id {brand_id} not found"
        )
    
    # Check if new name conflicts with existing brand
    if brand.name and brand.name != db_brand.name:
        existing = db.query(Brand).filter(Brand.name == brand.name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Brand with name '{brand.name}' already exists"
            )
    
    # If manufacturer_id is being updated, verify it exists
    if brand.manufacturer_id is not None:
        manufacturer = db.query(Manufacturer).filter(Manufacturer.id == brand.manufacturer_id).first()
        if not manufacturer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Manufacturer with id {brand.manufacturer_id} not found"
            )
    
    # Update fields
    update_data = brand.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_brand, field, value)
    
    db.commit()
    db.refresh(db_brand)
    
    return db_brand


@router.delete("/brands/{brand_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_brand(
    brand_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Delete a brand
    """
    db_brand = db.query(Brand).filter(Brand.id == brand_id).first()
    
    if not db_brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Brand with id {brand_id} not found"
        )
    
    # Check if brand has products
    if db_brand.product_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete brand '{db_brand.name}' because it has {db_brand.product_count} associated products. Please deactivate it instead."
        )
    
    db.delete(db_brand)
    db.commit()
    
    return None
