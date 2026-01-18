from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import scraping, categories, brands, manufacturers, stores, products_catalog, products

app = FastAPI(
    title="Simplify API",
    description="API para extracción y análisis de datos de retail",
    version="0.1.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(scraping.router, prefix="/api", tags=["scraping"])
app.include_router(categories.router, prefix="/api", tags=["categories"])
app.include_router(brands.router, prefix="/api", tags=["brands"])
app.include_router(manufacturers.router, prefix="/api", tags=["manufacturers"])
app.include_router(stores.router, prefix="/api", tags=["stores"])
app.include_router(products_catalog.router, prefix="/api", tags=["products-catalog"])
app.include_router(products.router, prefix="/api", tags=["products"])


@app.get("/")
async def root():
    """
    Endpoint de prueba
    """
    return {
        "message": "Simplify API",
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    """
    Health check
    """
    return {"status": "healthy"}
