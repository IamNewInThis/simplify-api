"""
Categories API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryResponse, CategoryWithChildren

router = APIRouter()


@router.get("/categories", response_model=List[CategoryResponse])
def get_categories(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = False,
    db: Session = Depends(get_db)
):
    """
    Get all categories
    """
    query = db.query(Category)
    
    if active_only:
        query = query.filter(Category.active == True)
    
    categories = query.offset(skip).limit(limit).all()
    return categories


@router.get("/categories/tree", response_model=List[CategoryWithChildren])
def get_categories_tree(
    db: Session = Depends(get_db)
):
    """
    Get categories as a tree structure (only root categories with their children)
    """
    # Get only root categories (parent_id is NULL)
    root_categories = db.query(Category).filter(Category.parent_id == None).all()
    return root_categories


@router.get("/categories/{category_id}", response_model=CategoryResponse)
def get_category(
    category_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get a specific category by ID
    """
    category = db.query(Category).filter(Category.id == category_id).first()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category with id {category_id} not found"
        )
    
    return category


@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    category: CategoryCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new category
    """
    # Check if slug already exists
    existing = db.query(Category).filter(Category.slug == category.slug).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category with slug '{category.slug}' already exists"
        )
    
    # If parent_id is provided, verify it exists
    if category.parent_id:
        parent = db.query(Category).filter(Category.id == category.parent_id).first()
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Parent category with id {category.parent_id} not found"
            )
    
    # Create new category
    db_category = Category(**category.model_dump())
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    
    return db_category


@router.put("/categories/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: UUID,
    category: CategoryUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a category
    """
    db_category = db.query(Category).filter(Category.id == category_id).first()
    
    if not db_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category with id {category_id} not found"
        )
    
    # Check if new slug conflicts with existing category
    if category.slug and category.slug != db_category.slug:
        existing = db.query(Category).filter(Category.slug == category.slug).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category with slug '{category.slug}' already exists"
            )
    
    # If parent_id is being updated, verify it exists and prevent circular reference
    if category.parent_id is not None:
        if category.parent_id == category_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category cannot be its own parent"
            )
        parent = db.query(Category).filter(Category.id == category.parent_id).first()
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Parent category with id {category.parent_id} not found"
            )
    
    # Update category
    update_data = category.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_category, key, value)
    
    db.commit()
    db.refresh(db_category)
    
    return db_category


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Delete a category
    """
    db_category = db.query(Category).filter(Category.id == category_id).first()
    
    if not db_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category with id {category_id} not found"
        )
    
    # Check if category has children
    children_count = db.query(Category).filter(Category.parent_id == category_id).count()
    if children_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete category with {children_count} subcategories. Delete or reassign them first."
        )
    
    db.delete(db_category)
    db.commit()
    
    return None
