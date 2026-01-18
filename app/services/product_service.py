"""
Servicio para gestión de productos y precios
"""
from sqlalchemy.orm import Session
from sqlalchemy import text, select
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from decimal import Decimal


class ProductService:
    """Servicio para operaciones con productos"""
    
    @staticmethod
    def search_catalog_by_name(db: Session, product_name: str) -> Optional[dict]:
        """
        Busca un producto en el catálogo por nombre (fuzzy match)
        
        Args:
            db: Sesión de base de datos
            product_name: Nombre del producto a buscar
            
        Returns:
            dict con información del producto del catálogo o None
        """
        query = text("""
            SELECT 
                pc.id,
                pc.name,
                pc.sku,
                pc.brand_id,
                b.name as brand_name,
                pc.category_id,
                c.name as category_name
            FROM products_catalog pc
            LEFT JOIN brands b ON pc.brand_id = b.id
            LEFT JOIN categories c ON pc.category_id = c.id
            WHERE 
                pc.active = true
                AND similarity(pc.name, :search_term) > 0.3
            ORDER BY similarity(pc.name, :search_term) DESC
            LIMIT 1
        """)
        
        result = db.execute(query, {"search_term": product_name}).fetchone()
        
        if result:
            return {
                "id": result.id,
                "name": result.name,
                "sku": result.sku,
                "brand_id": result.brand_id,
                "brand_name": result.brand_name,
                "category_id": result.category_id,
                "category_name": result.category_name
            }
        return None
    
    @staticmethod
    def get_products_by_catalog_id(db: Session, catalog_id: UUID) -> List[dict]:
        """
        Obtiene todos los productos scrapeados para un catalog_id
        
        Args:
            db: Sesión de base de datos
            catalog_id: ID del producto en el catálogo
            
        Returns:
            Lista de productos con precios por tienda
        """
        query = text("""
            SELECT 
                p.id,
                p.catalog_id,
                p.store_id,
                s.name as store_name,
                s.active as store_active,
                p.url,
                p.current_price,
                p.active,
                p.created_at,
                p.updated_at,
                p.last_scraped_at,
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
            LEFT JOIN prices pr ON pr.product_id = p.id
            WHERE p.catalog_id = :catalog_id
            AND p.active = true
            ORDER BY 
                s.active DESC,
                pr.price ASC NULLS LAST
        """)
        
        results = db.execute(query, {"catalog_id": str(catalog_id)}).fetchall()
        
        products = []
        for row in results:
            product = {
                "id": row.id,
                "catalog_id": row.catalog_id,
                "store_id": row.store_id,
                "store_name": row.store_name,
                "store_active": row.store_active,
                "url": row.url,
                "current_price": row.current_price,
                "active": row.active,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
                "last_scraped_at": row.last_scraped_at,
                "price": None
            }
            
            if row.price_id:
                product["price"] = {
                    "id": row.price_id,
                    "product_id": row.id,
                    "price": row.price,
                    "original_price": row.original_price,
                    "discount_percentage": row.discount_percentage,
                    "currency": row.currency,
                    "in_stock": row.in_stock,
                    "created_at": row.price_created_at,
                    "updated_at": row.price_updated_at
                }
            
            products.append(product)
        
        return products
    
    @staticmethod
    def get_store_by_name(db: Session, store_name: str) -> Optional[dict]:
        """
        Busca una tienda por nombre con fuzzy match mejorado
        
        Busca por:
        1. Nombre exacto
        2. Nombre contenido (ej: "Acuenta" en "Super Bodega Acuenta")
        3. Similarity > 0.3 (más tolerante)
        """
        # Limpiar el nombre de búsqueda
        clean_search = store_name.strip().lower()
        
        query = text("""
            SELECT id, name, base_url
            FROM stores
            WHERE 
                active = true
                AND (
                    LOWER(name) = :exact_match
                    OR LOWER(name) LIKE :partial_match
                    OR LOWER(:search_name) LIKE '%' || LOWER(name) || '%'
                    OR similarity(name, :search_name) > 0.3
                )
            ORDER BY 
                CASE 
                    WHEN LOWER(name) = :exact_match THEN 1
                    WHEN LOWER(name) LIKE :partial_match THEN 2
                    WHEN LOWER(:search_name) LIKE '%' || LOWER(name) || '%' THEN 3
                    ELSE 4
                END,
                similarity(name, :search_name) DESC
            LIMIT 1
        """)
        
        result = db.execute(query, {
            "exact_match": clean_search,
            "partial_match": f"%{clean_search}%",
            "search_name": store_name
        }).fetchone()
        
        if result:
            return {
                "id": result.id,
                "name": result.name,
                "base_url": result.base_url
            }
        return None
    
    @staticmethod
    def create_product(
        db: Session,
        catalog_id: UUID,
        store_id: UUID,
        url: str,
        price: Optional[Decimal] = None
    ) -> dict:
        """
        Crea un producto en la tabla products copiando category_id desde catalog
        
        Args:
            db: Sesión de base de datos
            catalog_id: ID del producto en catálogo
            store_id: ID de la tienda
            url: URL del producto en la tienda
            price: Precio actual (opcional)
            
        Returns:
            dict con el producto creado
        """
        query = text("""
            INSERT INTO products (catalog_id, store_id, category_id, url, current_price, last_scraped_at)
            SELECT 
                :catalog_id,
                :store_id,
                pc.category_id,
                :url,
                :price,
                :scraped_at
            FROM products_catalog pc
            WHERE pc.id = :catalog_id
            ON CONFLICT (catalog_id, store_id) 
            DO UPDATE SET 
                url = EXCLUDED.url,
                current_price = EXCLUDED.current_price,
                last_scraped_at = EXCLUDED.last_scraped_at,
                updated_at = NOW()
            RETURNING id, catalog_id, store_id, category_id, url, current_price, created_at, updated_at, last_scraped_at
        """)
        
        result = db.execute(query, {
            "catalog_id": str(catalog_id),
            "store_id": str(store_id),
            "url": url,
            "price": float(price) if price else None,
            "scraped_at": datetime.now()
        }).fetchone()
        
        db.commit()
        
        return {
            "id": result.id,
            "catalog_id": result.catalog_id,
            "store_id": result.store_id,
            "category_id": result.category_id,
            "url": result.url,
            "current_price": result.current_price,
            "created_at": result.created_at,
            "updated_at": result.updated_at,
            "last_scraped_at": result.last_scraped_at
        }
    
    @staticmethod
    def create_or_update_price(
        db: Session,
        product_id: UUID,
        price: Decimal,
        original_price: Optional[Decimal] = None,
        discount_percentage: Optional[Decimal] = None,
        in_stock: bool = True
    ) -> dict:
        """
        Crea o actualiza el precio de un producto
        
        Args:
            db: Sesión de base de datos
            product_id: ID del producto
            price: Precio actual
            original_price: Precio original (opcional)
            discount_percentage: Porcentaje de descuento (opcional)
            in_stock: Si está en stock
            
        Returns:
            dict con el precio creado/actualizado
        """
        query = text("""
            INSERT INTO prices (product_id, price, original_price, discount_percentage, in_stock)
            VALUES (:product_id, :price, :original_price, :discount_percentage, :in_stock)
            ON CONFLICT (product_id)
            DO UPDATE SET
                price = EXCLUDED.price,
                original_price = EXCLUDED.original_price,
                discount_percentage = EXCLUDED.discount_percentage,
                in_stock = EXCLUDED.in_stock,
                updated_at = NOW()
            RETURNING id, product_id, price, original_price, discount_percentage, currency, in_stock, created_at, updated_at
        """)
        
        result = db.execute(query, {
            "product_id": str(product_id),
            "price": float(price),
            "original_price": float(original_price) if original_price else None,
            "discount_percentage": float(discount_percentage) if discount_percentage else None,
            "in_stock": in_stock
        }).fetchone()
        
        db.commit()
        
        return {
            "id": result.id,
            "product_id": result.product_id,
            "price": result.price,
            "original_price": result.original_price,
            "discount_percentage": result.discount_percentage,
            "currency": result.currency,
            "in_stock": result.in_stock,
            "created_at": result.created_at,
            "updated_at": result.updated_at
        }
    
    @staticmethod
    def create_store(db: Session, name: str, base_url: str = "") -> dict:
        """
        Crea una nueva tienda automáticamente como "pendiente de validación"
        Si ya existe con ese nombre, retorna la existente
        
        Args:
            db: Sesión de base de datos
            name: Nombre de la tienda
            base_url: URL base (opcional)
            
        Returns:
            dict con la tienda creada o existente
        """
        # Primero intentar buscarla por nombre exacto
        existing = ProductService.get_store_by_name(db, name)
        if existing:
            return existing
        
        # Si no existe, crear con ON CONFLICT para evitar duplicados
        query = text("""
            INSERT INTO stores (name, base_url, active)
            VALUES (:name, :base_url, false)
            ON CONFLICT (name) DO UPDATE 
            SET updated_at = NOW()
            RETURNING id, name, base_url, active, created_at
        """)
        
        result = db.execute(query, {
            "name": name,
            "base_url": base_url or f"https://{name.lower().replace(' ', '')}.cl"
        }).fetchone()
        
        db.commit()
        
        return {
            "id": result.id,
            "name": result.name,
            "base_url": result.base_url,
            "active": result.active,
            "created_at": result.created_at
        }
    
    @staticmethod
    def get_store_by_name_or_create(db: Session, store_name: str, store_url: str = "") -> dict:
        """
        Busca una tienda por nombre o la crea si no existe
        
        Args:
            db: Sesión de base de datos
            store_name: Nombre de la tienda
            store_url: URL de la tienda (para extraer base_url)
            
        Returns:
            dict con la tienda encontrada o creada
        """
        # Intentar encontrar la tienda
        store = ProductService.get_store_by_name(db, store_name)
        
        if store:
            return store
        
        # Si no existe, crearla como inactiva (pendiente de validación)
        print(f"⚠️  Tienda no encontrada: '{store_name}' - Creando automáticamente...")
        
        # Extraer base_url del URL del producto si está disponible
        base_url = ""
        if store_url:
            import re
            match = re.match(r'(https?://[^/]+)', store_url)
            if match:
                base_url = match.group(1)
        
        new_store = ProductService.create_store(db, store_name, base_url)
        print(f"✅ Tienda creada (inactiva): {new_store['name']} - ID: {new_store['id']}")
        
        return new_store
