"""
Endpoints para scraping usando Google Shopping
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

router = APIRouter()


class ScrapeRequest(BaseModel):
    """Request para iniciar scraping"""
    product_name: str


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


@router.post("/scrape/google-shopping", response_model=MultiScrapeResponse)
async def scrape_google_shopping_endpoint(request: ScrapeRequest):
    """
    Endpoint para scrapear un producto en Google Shopping.
    Obtiene precios de múltiples retailers en una sola búsqueda.
    
    VENTAJA: Más rápido y preciso que scrapear cada sitio individualmente.
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
