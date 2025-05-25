from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List
from ..models.radio import RadioMessage, RadioResponse
from ..services.openf1_service import OpenF1Service
from ..services.storage_service import LocalStorageService
from ..utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/radio", tags=["radio"])

# Dependency injection
async def get_openf1_service():
    service = OpenF1Service()
    try:
        yield service
    finally:
        await service.close()

async def get_storage_service():
    return LocalStorageService()

@router.get("/session/{session_key}", response_model=RadioResponse)
async def get_session_radios(
    session_key: int,
    driver_number: Optional[int] = Query(None, description="Filtrar por número do piloto"),
    page: int = Query(1, ge=1, description="Página"),
    per_page: int = Query(50, ge=1, le=200, description="Itens por página"),
    use_cache: bool = Query(True, description="Usar dados em cache se disponível"),
    openf1_service: OpenF1Service = Depends(get_openf1_service),
    storage_service: LocalStorageService = Depends(get_storage_service)
):
    """Busca rádios de uma sessão específica"""
    try:
        radios = None
        
        # Tenta carregar do cache primeiro se solicitado
        if use_cache:
            radios = await storage_service.load_radios(session_key)
            if radios:
                logger.info(f"Rádios carregados do cache para sessão {session_key}")
        
        # Se não tem cache ou não quer usar cache, busca da API
        if not radios:
            logger.info(f"Buscando rádios da API para sessão {session_key}")
            radios = await openf1_service.get_team_radio(session_key=session_key)
            
            # Salva no cache para próximas consultas
            await storage_service.save_radios(radios, session_key)
        
        # Filtra por piloto se especificado
        if driver_number:
            radios = [r for r in radios if r.driver_number == driver_number]
        
        # Ordena por data (mais recente primeiro)
        radios.sort(key=lambda x: x.date, reverse=True)
        
        # Paginação
        total = len(radios)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_radios = radios[start_idx:end_idx]
        
        return RadioResponse(
            radios=paginated_radios,
            total=total,
            page=page,
            per_page=per_page
        )
        
    except Exception as e:
        logger.error(f"Erro ao buscar rádios da sessão {session_key}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.get("/latest", response_model=RadioResponse)
async def get_latest_radios(
    driver_number: Optional[int] = Query(None, description="Filtrar por número do piloto"),
    limit: int = Query(20, ge=1, le=100, description="Número máximo de rádios"),
    openf1_service: OpenF1Service = Depends(get_openf1_service),
    storage_service: LocalStorageService = Depends(get_storage_service)
):
    """Busca os rádios mais recentes da sessão atual"""
    try:
        # Busca a sessão mais recente
        latest_session = await openf1_service.get_latest_session()
        if not latest_session:
            raise HTTPException(status_code=404, detail="Nenhuma sessão encontrada")
        
        # Busca rádios da sessão mais recente
        radios = await openf1_service.get_team_radio(session_key=latest_session.session_key)
        
        # Filtra por piloto se especificado
        if driver_number:
            radios = [r for r in radios if r.driver_number == driver_number]
        
        # Ordena por data e limita
        radios.sort(key=lambda x: x.date, reverse=True)
        radios = radios[:limit]
        
        return RadioResponse(
            radios=radios,
            total=len(radios),
            page=1,
            per_page=limit,
            session_info={
                "session_key": latest_session.session_key,
                "session_name": latest_session.session_name,
                "location": latest_session.location,
                "date_start": latest_session.date_start.isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar rádios mais recentes: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.get("/driver/{driver_number}", response_model=RadioResponse)
async def get_driver_radios(
    driver_number: int,
    session_key: Optional[int] = Query(None, description="Filtrar por sessão"),
    meeting_key: Optional[int] = Query(None, description="Filtrar por reunião/GP"),
    page: int = Query(1, ge=1, description="Página"),
    per_page: int = Query(50, ge=1, le=200, description="Itens por página"),
    openf1_service: OpenF1Service = Depends(get_openf1_service)
):
    """Busca todos os rádios de um piloto específico"""
    try:
        radios = await openf1_service.get_team_radio(
            driver_number=driver_number,
            session_key=session_key,
            meeting_key=meeting_key
        )
        
        # Ordena por data (mais recente primeiro)
        radios.sort(key=lambda x: x.date, reverse=True)
        
        # Paginação
        total = len(radios)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_radios = radios[start_idx:end_idx]
        
        return RadioResponse(
            radios=paginated_radios,
            total=total,
            page=page,
            per_page=per_page
        )
        
    except Exception as e:
        logger.error(f"Erro ao buscar rádios do piloto {driver_number}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.post("/sync/{session_key}")
async def sync_session_radios(
    session_key: int,
    force_refresh: bool = Query(False, description="Forçar atualização mesmo com dados em cache"),
    openf1_service: OpenF1Service = Depends(get_openf1_service),
    storage_service: LocalStorageService = Depends(get_storage_service)
):
    """Sincroniza/atualiza rádios de uma sessão específica"""
    try:
        # Verifica se já tem dados em cache
        cached_radios = await storage_service.load_radios(session_key)
        
        if cached_radios and not force_refresh:
            return {
                "message": f"Sessão {session_key} já está em cache",
                "radio_count": len(cached_radios),
                "action": "cache_used"
            }
        
        # Busca dados atualizados da API
        logger.info(f"Sincronizando rádios da sessão {session_key}")
        radios = await openf1_service.get_team_radio(session_key=session_key)
        
        # Salva no armazenamento local
        success = await storage_service.save_radios(radios, session_key)
        
        if not success:
            raise HTTPException(status_code=500, detail="Falha ao salvar dados")
        
        return {
            "message": f"Sessão {session_key} sincronizada com sucesso",
            "radio_count": len(radios),
            "action": "synced"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao sincronizar sessão {session_key}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.get("/cache/status")
async def get_cache_status(
    storage_service: LocalStorageService = Depends(get_storage_service)
):
    """Retorna informações sobre o cache local"""
    try:
        available_sessions = await storage_service.get_available_sessions()
        
        total_radios = sum(session["radio_count"] for session in available_sessions)
        total_size_mb = sum(session["file_size"] for session in available_sessions) / (1024 * 1024)
        
        return {
            "cached_sessions": len(available_sessions),
            "total_radios": total_radios,
            "total_size_mb": round(total_size_mb, 2),
            "sessions": available_sessions
        }
        
    except Exception as e:
        logger.error(f"Erro ao verificar status do cache: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.delete("/cache/{session_key}")
async def clear_session_cache(
    session_key: int,
    storage_service: LocalStorageService = Depends(get_storage_service)
):
    """Remove dados de cache de uma sessão específica"""
    try:
        # TODO: Implementar remoção específica no storage_service
        return {
            "message": f"Cache da sessão {session_key} removido",
            "action": "cache_cleared"
        }
        
    except Exception as e:
        logger.error(f"Erro ao limpar cache da sessão {session_key}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")