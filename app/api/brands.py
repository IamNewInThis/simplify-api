"""
Brands API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List, Optional, Dict
from uuid import UUID
import sys
import os
import re

from app.core.database import get_db
from app.models.brand import Brand
from app.models.manufacturer import Manufacturer
from app.models.product_catalog import ProductCatalog
from app.models.category import Category
from app.schemas.brand import BrandCreate, BrandUpdate, BrandResponse, BrandWithManufacturer

router = APIRouter()


# Mapeo de palabras clave a categorías (nombres en inglés para BD)
# Formato: 'Nombre Categoría BD': ['palabras', 'clave', 'en', 'español']
CATEGORY_KEYWORDS = {
    'Yogurt': ['yogurt', 'yoghurt', 'yogur'],
    'Milk': ['leche'],
    'Cheese': ['queso'],
    'Butter & Margarine': ['mantequilla'],
    'Desserts': ['postre', 'flan', 'manjarate', 'sémola', 'semola', 'creme caramel'],
    'Beverages': ['probiótico', 'probiotico', 'uno multifruta', 'bebida lactea'],
    'Cream': ['crema'],
    'Ice Cream': ['helado', 'ice cream'],
}

# Parent category para nuevas categorías de lácteos
DAIRY_PARENT_SLUG = 'dairy'


def get_or_create_category(db: Session, category_name: str) -> Category:
    """Obtiene una categoría existente o la crea si no existe."""
    slug = re.sub(r'[^a-z0-9]+', '-', category_name.lower()).strip('-')

    # Buscar categoría existente por nombre o slug (case insensitive)
    category = db.query(Category).filter(
        (func.lower(Category.name) == category_name.lower()) |
        (Category.slug == slug)
    ).first()

    if not category:
        # Buscar parent "Dairy & Chilled Food" para categorías de lácteos
        parent_id = None
        dairy_categories = ['yogurt', 'milk', 'cheese', 'butter & margarine', 'cream', 'desserts']
        if category_name.lower() in dairy_categories:
            dairy_parent = db.query(Category).filter(Category.slug == DAIRY_PARENT_SLUG).first()
            if dairy_parent:
                parent_id = dairy_parent.id

        # Crear nueva categoría
        category = Category(
            name=category_name,
            slug=slug,
            parent_id=parent_id,
            active=True
        )
        db.add(category)
        db.flush()  # Para obtener el ID sin hacer commit
        print(f"  [CAT] Nueva categoría creada: {category_name} (parent: {'Dairy' if parent_id else 'None'})")

    return category


def detect_category_from_name(product_name: str, db: Session, brand_id: UUID = None) -> Optional[UUID]:
    """
    Detecta la categoría de un producto basándose en:
    1. Productos similares de la misma marca
    2. Palabras clave en el nombre
    """
    product_name_lower = product_name.lower()

    # 1. Buscar productos similares de la misma marca que ya tengan categoría
    if brand_id:
        # Extraer primera palabra significativa del producto (ej: "Yogurt", "Leche")
        first_words = product_name.split()[:2]  # Primeras 2 palabras

        for word in first_words:
            if len(word) > 3:  # Ignorar palabras muy cortas
                similar_product = db.query(ProductCatalog).filter(
                    ProductCatalog.brand_id == brand_id,
                    ProductCatalog.category_id.isnot(None),
                    ProductCatalog.name.ilike(f"{word}%")
                ).first()

                if similar_product:
                    print(f"  [CAT] Categoría inferida de producto similar: {similar_product.name}")
                    return similar_product.category_id

    # 2. Mapeo por palabras clave
    for category_name, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in product_name_lower:
                category = get_or_create_category(db, category_name)
                return category.id

    return None


@router.get("/brands/search")
async def search_brand_catalog(
    q: str = Query(..., description="Nombre de la marca a buscar"),
    create_products: bool = Query(True, description="Crear productos en el catálogo automáticamente"),
    db: Session = Depends(get_db)
):
    """
    Busca productos de una marca en Jumbo.cl y opcionalmente los crea en el catálogo.

    Args:
        q: Nombre de la marca (ej: "Soprole", "Nestle")
        create_products: Si True, crea los productos encontrados en product_catalog

    Returns:
        dict: Estado del scraping, productos encontrados y creados
    """
    print(f"\n=== BÚSQUEDA DE CATÁLOGO POR MARCA ===")
    print(f"Marca: {q}")

    # Importar el scraper de Jumbo
    scraper_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '../../../simplify-scraper')
    )
    if scraper_path not in sys.path:
        sys.path.append(scraper_path)

    from scrapers.jumbo_catalog import scrape_jumbo_catalog

    # Ejecutar scraping
    result = await scrape_jumbo_catalog(q)

    print(f"Resultado: {result['status']}")

    # Si el scraping fue exitoso y se deben crear productos
    if result['status'] == 'success' and create_products and result.get('products'):
        print(f"\n=== CREANDO PRODUCTOS EN CATÁLOGO ===")

        # Buscar o crear la marca
        brand = db.query(Brand).filter(Brand.name.ilike(q)).first()
        brand_id = brand.id if brand else None

        if brand:
            print(f"Marca encontrada: {brand.name} (ID: {brand.id})")
        else:
            print(f"Marca '{q}' no encontrada en BD, productos se crearán sin brand_id")

        created_count = 0
        skipped_count = 0
        created_products = []

        for product in result['products']:
            # Verificar si el producto ya existe (por nombre exacto)
            existing = db.query(ProductCatalog).filter(
                ProductCatalog.name == product['name']
            ).first()

            if existing:
                print(f"  [SKIP] Ya existe: {product['name']}")
                skipped_count += 1
                continue

            # Detectar categoría
            category_id = detect_category_from_name(product['name'], db, brand_id)

            # Crear el producto
            new_product = ProductCatalog(
                name=product['name'],
                sku=f"JUMBO-{product['jumbo_id']}",  # SKU basado en ID de Jumbo
                brand_id=brand_id,
                category_id=category_id,
                image_url=product.get('image_url'),
                attributes={
                    'jumbo_id': product['jumbo_id'],
                    'jumbo_url': product['url'],
                    'jumbo_price': product['price'],
                    'source': 'jumbo_scraper'
                },
                active=True
            )

            db.add(new_product)
            created_count += 1

            # Obtener nombre de categoría para el log
            cat_name = None
            if category_id:
                cat = db.query(Category).filter(Category.id == category_id).first()
                cat_name = cat.name if cat else None

            created_products.append({
                'name': product['name'],
                'sku': f"JUMBO-{product['jumbo_id']}",
                'category': cat_name
            })
            print(f"  [NEW] Creado: {product['name']} -> Categoría: {cat_name or 'Sin categoría'}")

        # Commit todos los productos
        db.commit()

        print(f"\n=== RESUMEN ===")
        print(f"Productos creados: {created_count}")
        print(f"Productos omitidos (ya existían): {skipped_count}")
        print(f"================================\n")

        # Agregar info al resultado
        result['created_count'] = created_count
        result['skipped_count'] = skipped_count
        result['created_products'] = created_products

    return result


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
