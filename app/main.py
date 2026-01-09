from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import scraping

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
