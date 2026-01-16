"""
Category schemas
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID
import re


class CategoryBase(BaseModel):
    """Base category schema"""
    name: str = Field(..., min_length=1, max_length=255, description="Category name")
    slug: str = Field(..., min_length=1, max_length=255, description="URL-friendly slug")
    description: Optional[str] = Field(None, description="Category description")
    parent_id: Optional[UUID] = Field(None, description="Parent category ID")
    active: bool = Field(True, description="Category status")


class CategoryCreate(BaseModel):
    """Schema for creating a category"""
    name: str = Field(..., min_length=1, max_length=255, description="Category name")
    slug: Optional[str] = Field(None, description="URL-friendly slug (auto-generated if not provided)")
    description: Optional[str] = Field(None, description="Category description")
    parent_id: Optional[UUID] = Field(None, description="Parent category ID")
    active: bool = Field(True, description="Category status")
    
    def model_post_init(self, __context):
        """Generate slug from name if not provided"""
        if not self.slug:
            # Convert to lowercase and replace spaces/special chars with hyphens
            slug = self.name.lower()
            slug = re.sub(r'[^\w\s-]', '', slug)  # Remove special chars
            slug = re.sub(r'[-\s]+', '-', slug)    # Replace spaces with hyphens
            slug = slug.strip('-')                  # Remove leading/trailing hyphens
            self.slug = slug


class CategoryUpdate(BaseModel):
    """Schema for updating a category"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    slug: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    parent_id: Optional[UUID] = None
    active: Optional[bool] = None


class CategoryResponse(CategoryBase):
    """Schema for category response"""
    id: UUID
    product_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CategoryWithChildren(CategoryResponse):
    """Schema for category with children"""
    children: list['CategoryWithChildren'] = []

    class Config:
        from_attributes = True
