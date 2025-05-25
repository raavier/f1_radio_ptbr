from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv
from contextlib import asynccontextmanager

from .routes import radio, sessions, drivers
from .utils.logger import get_logger
from .services.storage_service import LocalStorageService

# Carrega variáveis de ambiente
load_dotenv()

logger = get_logger(__name__)

# Configuração de inicialização e finalização da aplicação
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🏎️  Iniciando F1 Radio API...")
    
    # Cria diretórios necessários
    storage_service = LocalStorageService()
    logger.info("📁 Estrutura de armazenamento configurada")
    
    yield
    
    # Shutdown
    logger.info("🏁 Encerrando F1 Radio API")

# Inicializa a aplicação FastAPI
app = FastAPI(
    title="F1 Radio API",
    description="API para capturar e servir rádios da Fórmula 1 via OpenF1",
    version="1.0.0",
    lifespan=lifespan
)

# Configuração CORS para permitir acesso do Flutter
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especifique domínios específicos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registra as rotas
app.include_router(radio.router)
app.include_router(sessions.router)
app.include_router(drivers.router)

# Rota de health check
@app.get("/")
async def root():
    """Endpoint de verificação de saúde da API"""
    return {
        "message": "🏎️ F1 Radio API está funcionando!",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "online"
    }

@app.get("/health")
async def health_check():
    """Endpoint detalhado de saúde"""
    try:
        storage_service = LocalStorageService()
        cache_status = await storage_service.get_available_sessions()
        
        return {
            "status": "healthy",
            "timestamp": "2025-05-24T12:00:00Z",
            "services": {
                "storage": "online",
                "openf1_api": "online"
            },
            "cache": {
                "sessions_cached": len(cache_status),
                "total_radios": sum(s["radio_count"] for s in cache_status)
            }
        }
    except Exception as e:
        logger.error(f"Erro no health check: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )

# Handler global de exceções
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    logger.error(f"HTTP Exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Erro não tratado: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"error": "Erro interno do servidor", "detail": str(exc)}
    )

if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    debug = os.getenv("DEBUG", "True").lower() == "true"
    
    logger.info(f"🚀 Iniciando servidor em {host}:{port}")
    logger.info(f"🔧 Debug mode: {debug}")
    logger.info(f"📖 Documentação disponível em: http://{host}:{port}/docs")
    
    uvicorn.run(
        "src.app:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info" if debug else "warning"
    )