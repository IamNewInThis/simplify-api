"""
Manufacturers API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.models.manufacturer import Manufacturer
from app.models.brand import Brand
from app.schemas.manufacturer import ManufacturerCreate, ManufacturerUpdate, ManufacturerResponse, ManufacturerWithBrands

router = APIRouter()


@router.get("/manufacturers", response_model=List[ManufacturerResponse])
def get_manufacturers(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = Query(None, description="Search by manufacturer name"),
    country: Optional[str] = Query(None, description="Filter by country"),
    db: Session = Depends(get_db)
):
    """
    Get all manufacturers with optional filters
    """
    query = db.query(Manufacturer)
    
    if search:
        query = query.filter(Manufacturer.name.ilike(f"%{search}%"))
    
    if country:
        query = query.filter(Manufacturer.country.ilike(f"%{country}%"))
    
    manufacturers = query.offset(skip).limit(limit).all()
    return manufacturers


@router.get("/manufacturers/with-brands", response_model=List[ManufacturerWithBrands])
def get_manufacturers_with_brands(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get all manufacturers with brand count
    """
    manufacturers = db.query(
        Manufacturer,
        func.count(Brand.id).label('brand_count')
    ).outerjoin(Brand).group_by(Manufacturer.id).offset(skip).limit(limit).all()
    
    result = []
    for manufacturer, brand_count in manufacturers:
        manufacturer_dict = {
            "id": manufacturer.id,
            "name": manufacturer.name,
            "tax_id": manufacturer.tax_id,
            "country": manufacturer.country,
            "website": manufacturer.website,
            "main_business_line": manufacturer.main_business_line,
            "logo_url": manufacturer.logo_url,
            "created_at": manufacturer.created_at,
            "updated_at": manufacturer.updated_at,
            "brand_count": brand_count,
        }
        result.append(manufacturer_dict)
    
    return result


@router.get("/manufacturers/{manufacturer_id}", response_model=ManufacturerResponse)
def get_manufacturer(
    manufacturer_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get a specific manufacturer by ID
    """
    manufacturer = db.query(Manufacturer).filter(Manufacturer.id == manufacturer_id).first()
    
    if not manufacturer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Manufacturer with id {manufacturer_id} not found"
        )
    
    return manufacturer


@router.post("/manufacturers", response_model=ManufacturerResponse, status_code=status.HTTP_201_CREATED)
def create_manufacturer(
    manufacturer: ManufacturerCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new manufacturer
    """
    # Check if name already exists
    existing = db.query(Manufacturer).filter(Manufacturer.name == manufacturer.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Manufacturer with name '{manufacturer.name}' already exists"
        )
    
    # Check if tax_id already exists (if provided)
    if manufacturer.tax_id:
        existing_tax = db.query(Manufacturer).filter(Manufacturer.tax_id == manufacturer.tax_id).first()
        if existing_tax:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Manufacturer with tax ID '{manufacturer.tax_id}' already exists"
            )
    
    # Create new manufacturer
    db_manufacturer = Manufacturer(**manufacturer.model_dump())
    db.add(db_manufacturer)
    db.commit()
    db.refresh(db_manufacturer)
    
    return db_manufacturer


@router.put("/manufacturers/{manufacturer_id}", response_model=ManufacturerResponse)
def update_manufacturer(
    manufacturer_id: UUID,
    manufacturer: ManufacturerUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a manufacturer
    """
    db_manufacturer = db.query(Manufacturer).filter(Manufacturer.id == manufacturer_id).first()
    
    if not db_manufacturer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Manufacturer with id {manufacturer_id} not found"
        )
    
    # Check if new name conflicts with existing manufacturer
    if manufacturer.name and manufacturer.name != db_manufacturer.name:
        existing = db.query(Manufacturer).filter(Manufacturer.name == manufacturer.name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Manufacturer with name '{manufacturer.name}' already exists"
            )
    
    # Check if new tax_id conflicts with existing manufacturer
    if manufacturer.tax_id and manufacturer.tax_id != db_manufacturer.tax_id:
        existing_tax = db.query(Manufacturer).filter(Manufacturer.tax_id == manufacturer.tax_id).first()
        if existing_tax:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Manufacturer with tax ID '{manufacturer.tax_id}' already exists"
            )
    
    # Update fields
    update_data = manufacturer.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_manufacturer, field, value)
    
    db.commit()
    db.refresh(db_manufacturer)
    
    return db_manufacturer


@router.delete("/manufacturers/{manufacturer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_manufacturer(
    manufacturer_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Delete a manufacturer
    """
    db_manufacturer = db.query(Manufacturer).filter(Manufacturer.id == manufacturer_id).first()
    
    if not db_manufacturer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Manufacturer with id {manufacturer_id} not found"
        )
    
    # Check if manufacturer has brands
    brand_count = db.query(Brand).filter(Brand.manufacturer_id == manufacturer_id).count()
    if brand_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete manufacturer '{db_manufacturer.name}' because it has {brand_count} associated brand(s). Please remove or reassign the brands first."
        )
    
    db.delete(db_manufacturer)
    db.commit()
    
    return None
