"""
Endpoints para búsqueda inteligente de productos
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.schemas.product import ProductSearchResult, ProductWithPrice
from app.services.product_service import ProductService
import sys
import os
from decimal import Decimal
import re

router = APIRouter()


def parse_price(price_str: str) -> Decimal:
    """
    Parsea un string de precio a Decimal
    Maneja formatos:
    - "$1.990" -> 1990
    - "CLP 1,090" -> 1090
    - "$1.990,50" -> 1990.50
    """
    if not price_str:
        return Decimal("0")
    
    # Remover "CLP" y símbolos de moneda
    cleaned = price_str.replace('CLP', '').replace('$', '').strip()
    
    # Detectar formato: si tiene punto Y coma, el punto es separador de miles
    if '.' in cleaned and ',' in cleaned:
        # Formato: 1.990,50 -> remover puntos, coma es decimal
        cleaned = cleaned.replace('.', '').replace(',', '.')
    elif ',' in cleaned:
        # Formato chileno: 1,090 -> remover coma (es separador de miles)
        cleaned = cleaned.replace(',', '')
    elif '.' in cleaned:
        # Verificar si el punto es separador de miles o decimal
        # Si hay más de 3 dígitos después del punto, es separador de miles
        parts = cleaned.split('.')
        if len(parts) == 2 and len(parts[1]) == 3:
            # Es separador de miles: 1.990 -> 1990
            cleaned = cleaned.replace('.', '')
        # Si son 1-2 dígitos, es decimal: 19.90 -> 19.90
    
    try:
        return Decimal(cleaned)
    except:
        return Decimal("0")


@router.get("/products/search", response_model=ProductSearchResult)
async def search_product(
    q: str = Query(..., description="Nombre del producto a buscar"),
    db: Session = Depends(get_db)
):
    """
    Búsqueda inteligente de productos
    
    Flujo:
    1. Busca el producto en products_catalog por nombre (fuzzy match)
    2. Si existe en catálogo, busca precios scrapeados en products
    3. Si no hay precios, activa scraping con Google Shopping
    4. Guarda resultados en products + prices
    5. Retorna productos agrupados por tienda
    
    Args:
        q: Nombre del producto (ej: "Leche Soprole Entera Natural 1 L")
        db: Sesión de base de datos
        
    Returns:
        ProductSearchResult con productos y precios por tienda
    """
    print(f"\n=== BÚSQUEDA INTELIGENTE ===")
    print(f"Query: {q}")
    
    # 1. Buscar en products_catalog
    catalog_product = ProductService.search_catalog_by_name(db, q)
    
    if not catalog_product:
        print(f"❌ Producto no encontrado en catálogo")
        return ProductSearchResult(
            catalog_id="00000000-0000-0000-0000-000000000000",
            catalog_name=q,
            products=[],
            total_stores=0,
            was_scraped=False
        )
    
    print(f"✅ Encontrado en catálogo: {catalog_product['name']}")
    
    # 2. Buscar precios scrapeados
    existing_products = ProductService.get_products_by_catalog_id(
        db, 
        catalog_product['id']
    )
    
    was_scraped = False
    
    # 3. Si no hay productos scrapeados, activar scraper
    if not existing_products:
        print(f"⚠️  No hay precios scrapeados, activando Google Shopping...")
        
        # Importar el scraper
        scraper_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '../../../simplify-scraper')
        )
        if scraper_path not in sys.path:
            sys.path.append(scraper_path)
        
        from scrapers.google_shopping import scrape_google_shopping
        
        # Ejecutar scraping
        scraping_results = await scrape_google_shopping(catalog_product['name'])
        
        print(f"📦 Resultados del scraping: {len(scraping_results)} tiendas")
        
        # 4. Guardar resultados en la BD
        for result in scraping_results:
            if not result['encontrado']:
                continue
            
            # Buscar o crear la tienda automáticamente
            store = ProductService.get_store_by_name_or_create(
                db, 
                result['retailer'],
                result['url']
            )
            
            # Parsear precio
            price = parse_price(result['precio'])
            
            if price <= 0:
                print(f"⚠️  Precio inválido para {result['retailer']}: {result['precio']}")
                continue
            
            # Crear producto
            product = ProductService.create_product(
                db=db,
                catalog_id=catalog_product['id'],
                store_id=store['id'],
                url=result['url'],
                price=price
            )
            
            print(f"✅ Guardado: {store['name']} - ${price}")
            
            # Crear/actualizar precio
            ProductService.create_or_update_price(
                db=db,
                product_id=product['id'],
                price=price,
                in_stock=True
            )
        
        # Volver a buscar los productos ahora que están guardados
        existing_products = ProductService.get_products_by_catalog_id(
            db,
            catalog_product['id']
        )
        
        was_scraped = True
    else:
        print(f"✅ Se encontraron {len(existing_products)} productos scrapeados")
    
    # 5. Formatear respuesta
    products_with_prices = []
    for prod in existing_products:
        products_with_prices.append(ProductWithPrice(
            id=prod['id'],
            catalog_id=prod['catalog_id'],
            store_id=prod['store_id'],
            url=prod['url'],
            current_price=prod['current_price'],
            active=prod['active'],
            created_at=prod['created_at'],
            updated_at=prod['updated_at'],
            last_scraped_at=prod['last_scraped_at'],
            price=prod['price'],
            store_name=prod['store_name'],
            catalog_name=catalog_product['name']
        ))
    
    result = ProductSearchResult(
        catalog_id=catalog_product['id'],
        catalog_name=catalog_product['name'],
        catalog_sku=catalog_product.get('sku'),
        brand_name=catalog_product.get('brand_name'),
        category_name=catalog_product.get('category_name'),
        products=products_with_prices,
        total_stores=len(products_with_prices),
        was_scraped=was_scraped
    )
    
    print(f"✅ Retornando {len(products_with_prices)} productos")
    print(f"================================\n")
    
    return result


@router.get("/products", response_model=list[ProductWithPrice])
async def get_all_products(db: Session = Depends(get_db)):
    """
    Obtiene todos los productos scrapeados con sus precios y detalles
    
    Returns:
        Lista de productos con precios, tienda, catálogo, marca y categoría
    """
    query = text("""
        SELECT 
            p.id,
            p.catalog_id,
            p.store_id,
            p.url,
            p.current_price,
            p.active,
            p.created_at,
            p.updated_at,
            p.last_scraped_at,
            p.category_id,
            -- Store info
            s.name as store_name,
            s.active as store_active,
            -- Catalog info
            pc.name as catalog_name,
            pc.sku as catalog_sku,
            -- Brand info
            b.name as brand_name,
            -- Category info
            c.name as category_name,
            -- Price info
            pr.id as price_id,
            pr.price,
            pr.original_price,
            pr.discount_percentage,
            pr.currency,
            pr.in_stock,
            pr.created_at as price_created_at,
            pr.updated_at as price_updated_at
        FROM products p
        LEFT JOIN stores s ON p.store_id = s.id
        LEFT JOIN products_catalog pc ON p.catalog_id = pc.id
        LEFT JOIN brands b ON pc.brand_id = b.id
        LEFT JOIN categories c ON p.category_id = c.id
        LEFT JOIN prices pr ON pr.product_id = p.id
        WHERE p.active = true
        ORDER BY 
            pc.name,
            s.active DESC,
            pr.price ASC NULLS LAST
    """)
    
    results = db.execute(query).fetchall()
    
    products = []
    for row in results:
        product = ProductWithPrice(
            id=row.id,
            catalog_id=row.catalog_id,
            store_id=row.store_id,
            category_id=row.category_id,
            url=row.url,
            current_price=row.current_price,
            active=row.active,
            created_at=row.created_at,
            updated_at=row.updated_at,
            last_scraped_at=row.last_scraped_at,
            store_name=row.store_name,
            catalog_name=row.catalog_name,
            price=None
        )
        
        # Add price if exists
        if row.price_id:
            from app.schemas.product import PriceResponse
            product.price = PriceResponse(
                id=row.price_id,
                product_id=row.id,
                price=row.price,
                original_price=row.original_price,
                discount_percentage=row.discount_percentage,
                currency=row.currency,
                in_stock=row.in_stock,
                created_at=row.price_created_at,
                updated_at=row.price_updated_at
            )
        
        # Add extra info for display
        product.store_active = row.store_active
        product.catalog_sku = row.catalog_sku
        product.brand_name = row.brand_name
        product.category_name = row.category_name
        
        products.append(product)
    
    return products
