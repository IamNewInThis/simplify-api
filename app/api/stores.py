"""
Stores API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.models.store import Store
from app.schemas.store import StoreCreate, StoreUpdate, StoreResponse

router = APIRouter()


@router.get("/stores", response_model=List[StoreResponse])
def get_stores(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = False,
    search: Optional[str] = Query(None, description="Search by store name"),
    db: Session = Depends(get_db)
):
    """
    Get all stores with optional filters
    """
    query = db.query(Store)
    
    if active_only:
        query = query.filter(Store.active == True)
    
    if search:
        query = query.filter(Store.name.ilike(f"%{search}%"))
    
    stores = query.offset(skip).limit(limit).all()
    return stores


@router.get("/stores/{store_id}", response_model=StoreResponse)
def get_store(
    store_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get a specific store by ID
    """
    store = db.query(Store).filter(Store.id == store_id).first()
    
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Store with id {store_id} not found"
        )
    
    return store


@router.post("/stores", response_model=StoreResponse, status_code=status.HTTP_201_CREATED)
def create_store(
    store: StoreCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new store
    """
    # Check if name already exists
    existing = db.query(Store).filter(Store.name == store.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Store with name '{store.name}' already exists"
        )
    
    # Create new store
    db_store = Store(**store.model_dump())
    db.add(db_store)
    db.commit()
    db.refresh(db_store)
    
    return db_store


@router.put("/stores/{store_id}", response_model=StoreResponse)
def update_store(
    store_id: UUID,
    store: StoreUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a store
    """
    db_store = db.query(Store).filter(Store.id == store_id).first()
    
    if not db_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Store with id {store_id} not found"
        )
    
    # Check if new name conflicts with existing store
    if store.name and store.name != db_store.name:
        existing = db.query(Store).filter(Store.name == store.name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Store with name '{store.name}' already exists"
            )
    
    # Update fields
    update_data = store.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_store, field, value)
    
    db.commit()
    db.refresh(db_store)
    
    return db_store


@router.delete("/stores/{store_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_store(
    store_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Delete a store
    """
    db_store = db.query(Store).filter(Store.id == store_id).first()
    
    if not db_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Store with id {store_id} not found"
        )
    
    # TODO: Add check for associated products when products table is implemented
    
    db.delete(db_store)
    db.commit()
    
    return None
