"""
Manufacturer model
"""
from sqlalchemy import Column, String, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from app.core.database import Base


class Manufacturer(Base):
    """Manufacturer model"""
    __tablename__ = "manufacturers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False, index=True)
    tax_id = Column(String(100), unique=True, nullable=True)
    country = Column(String(100), nullable=True)
    logo_url = Column(Text, nullable=True)
    website = Column(Text, nullable=True)
    main_business_line = Column(String(255), nullable=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    brands = relationship("Brand", back_populates="manufacturer")
