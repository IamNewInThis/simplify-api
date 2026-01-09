"""
Endpoints para scraping de múltiples retailers
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import asyncio

router = APIRouter()


class ScrapeRequest(BaseModel):
    """Request para iniciar scraping"""
    product_name: str


class ScrapeResponse(BaseModel):
    """Response del scraping"""
    nombre: str
    precio: str
    sku: str
    url: str
    encontrado: bool


class RetailerResult(BaseModel):
    """Resultado de un retailer específico"""
    retailer: str
    nombre: str
    precio: str
    sku: str
    url: str
    encontrado: bool


class MultiScrapeResponse(BaseModel):
    """Response del scraping multi-retailer"""
    results: List[RetailerResult]


@router.post("/scrape/jumbo", response_model=ScrapeResponse)
async def scrape_jumbo(request: ScrapeRequest):
    """
    Endpoint para scrapear un producto de Jumbo.
    
    IMPORTANTE: Este endpoint ejecuta scraping de forma síncrona (puede tardar).
    En el futuro usaremos Celery para hacerlo en background.
    """
    import sys
    import os
    
    print(f"\n=== INICIANDO SCRAPING JUMBO ===")
    print(f"Producto: {request.product_name}")
    
    # Agregar el path del scraper al PYTHONPATH
    scraper_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../simplify-scraper'))
    if scraper_path not in sys.path:
        sys.path.append(scraper_path)
    
    # Importar el scraper
    from scrapers.jumbo import scrape_jumbo_product
    
    # Ejecutar el scraping
    result = await scrape_jumbo_product(request.product_name)
    
    print(f"\n=== RESULTADO DEL SCRAPING JUMBO ===")
    print(f"Nombre: {result['nombre']}")
    print(f"Precio: {result['precio']}")
    print(f"SKU: {result['sku']}")
    print(f"URL: {result['url']}")
    print(f"Encontrado: {result['encontrado']}")
    print(f"================================\n")
    
    return ScrapeResponse(
        nombre=result["nombre"],
        precio=result["precio"],
        sku=result["sku"],
        url=result["url"],
        encontrado=result["encontrado"]
    )


@router.post("/scrape/all", response_model=MultiScrapeResponse)
async def scrape_all_retailers(request: ScrapeRequest):
    """
    Endpoint para scrapear un producto en todos los retailers (Jumbo, Santa Isabel, Líder).
    Ejecuta los scrapers en paralelo para mayor velocidad.
    
    IMPORTANTE: Este endpoint puede tardar hasta 30 segundos.
    """
    import sys
    import os
    
    print(f"\n=== INICIANDO SCRAPING MULTI-RETAILER ===")
    print(f"Producto: {request.product_name}")
    
    # Agregar el path del scraper al PYTHONPATH
    scraper_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../simplify-scraper'))
    if scraper_path not in sys.path:
        sys.path.append(scraper_path)
    
    # Importar los scrapers
    from scrapers.jumbo import scrape_jumbo_product
    from scrapers.santaisabel import scrape_santaisabel_product
    from scrapers.lider import scrape_lider_product
    
    # Ejecutar los 3 scrapers en paralelo
    results = await asyncio.gather(
        scrape_jumbo_product(request.product_name),
        scrape_santaisabel_product(request.product_name),
        scrape_lider_product(request.product_name),
        return_exceptions=True
    )
    
    # Procesar resultados
    final_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            retailer_names = ["Jumbo", "Santa Isabel", "Líder"]
            final_results.append(RetailerResult(
                retailer=retailer_names[i],
                nombre="Error",
                precio="Error",
                sku="Error",
                url="",
                encontrado=False
            ))
        else:
            final_results.append(RetailerResult(**result))
    
    print(f"\n=== RESULTADO MULTI-RETAILER ===")
    for result in final_results:
        print(f"\n{result.retailer}:")
        print(f"  Nombre: {result.nombre}")
        print(f"  Precio: {result.precio}")
        print(f"  SKU: {result.sku}")
        print(f"  Encontrado: {result.encontrado}")
    print(f"================================\n")
    
    return MultiScrapeResponse(results=final_results)


@router.post("/scrape/google-shopping", response_model=MultiScrapeResponse)
async def scrape_google_shopping_endpoint(request: ScrapeRequest):
    """
    Endpoint para scrapear un producto en Google Shopping.
    Obtiene precios de múltiples retailers en una sola búsqueda.
    
    VENTAJA: Más rápido que scrapear cada sitio individualmente.
    Puede obtener hasta 20 vendedores en una sola consulta.
    """
    import sys
    import os
    
    print(f"\n=== INICIANDO SCRAPING GOOGLE SHOPPING ===")
    print(f"Producto: {request.product_name}")
    
    # Agregar el path del scraper al PYTHONPATH
    scraper_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../simplify-scraper'))
    if scraper_path not in sys.path:
        sys.path.append(scraper_path)
    
    # Importar el scraper de Google Shopping
    from scrapers.google_shopping import scrape_google_shopping
    
    # Ejecutar el scraping
    results = await scrape_google_shopping(request.product_name)
    
    # Convertir a RetailerResult
    final_results = [RetailerResult(**result) for result in results]
    
    print(f"\n=== RESULTADO GOOGLE SHOPPING ===")
    print(f"Total de vendedores: {len(final_results)}")
    for result in final_results:
        print(f"  {result.retailer}: {result.precio}")
    print(f"================================\n")
    
    return MultiScrapeResponse(results=final_results)
