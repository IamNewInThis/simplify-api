"""
Database configuration
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Database URL - usando psycopg (driver nativo de PostgreSQL para SQLAlchemy 2.0+)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://simplify_user:simplify_password@localhost:5432/simplify"
)

# Cambiar postgresql:// a postgresql+psycopg:// para usar psycopg3
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

# Create engine
engine = create_engine(DATABASE_URL, echo=True)

# Session local
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


# Dependency
def get_db():
    """
    Dependency to get database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
