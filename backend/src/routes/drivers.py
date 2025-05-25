from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List
from ..models.radio import Driver
from ..services.openf1_service import OpenF1Service
from ..utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/drivers", tags=["drivers"])

# Dependency injection
async def get_openf1_service():
    service = OpenF1Service()
    try:
        yield service
    finally:
        await service.close()

@router.get("/", response_model=List[Driver])
async def get_drivers(
    session_key: Optional[int] = Query(None, description="Filtrar por sessão"),
    openf1_service: OpenF1Service = Depends(get_openf1_service)
):
    """Lista todos os pilotos disponíveis"""
    try:
        drivers = await openf1_service.get_drivers(session_key=session_key)
        
        # Ordena por número do piloto
        drivers.sort(key=lambda x: x.driver_number)
        
        return drivers
        
    except Exception as e:
        logger.error(f"Erro ao buscar pilotos: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.get("/{driver_number}", response_model=Driver)
async def get_driver_by_number(
    driver_number: int,
    session_key: Optional[int] = Query(None, description="Sessão específica"),
    openf1_service: OpenF1Service = Depends(get_openf1_service)
):
    """Busca informações de um piloto específico"""
    try:
        drivers = await openf1_service.get_drivers(session_key=session_key)
        driver = next((d for d in drivers if d.driver_number == driver_number), None)
        
        if not driver:
            raise HTTPException(
                status_code=404, 
                detail=f"Piloto com número {driver_number} não encontrado"
            )
        
        return driver
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar piloto {driver_number}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.get("/{driver_number}/stats")
async def get_driver_radio_stats(
    driver_number: int,
    session_key: Optional[int] = Query(None, description="Filtrar por sessão"),
    meeting_key: Optional[int] = Query(None, description="Filtrar por reunião"),
    openf1_service: OpenF1Service = Depends(get_openf1_service)
):
    """Retorna estatísticas de rádio de um piloto"""
    try:
        # Busca todos os rádios do piloto
        radios = await openf1_service.get_team_radio(
            driver_number=driver_number,
            session_key=session_key,
            meeting_key=meeting_key
        )
        
        # Busca informações do piloto
        drivers = await openf1_service.get_drivers(session_key=session_key)
        driver = next((d for d in drivers if d.driver_number == driver_number), None)
        
        if not driver:
            raise HTTPException(
                status_code=404,
                detail=f"Piloto com número {driver_number} não encontrado"
            )
        
        # Calcula estatísticas
        total_radios = len(radios)
        
        # Agrupa por sessão
        sessions_with_radios = {}
        for radio in radios:
            session_key = radio.session_key
            if session_key not in sessions_with_radios:
                sessions_with_radios[session_key] = []
            sessions_with_radios[session_key].append(radio)
        
        # Estatísticas por sessão
        session_stats = []
        for sk, session_radios in sessions_with_radios.items():
            session_stats.append({
                "session_key": sk,
                "radio_count": len(session_radios),
                "first_radio": min(r.date for r in session_radios).isoformat(),
                "last_radio": max(r.date for r in session_radios).isoformat()
            })
        
        session_stats.sort(key=lambda x: x["session_key"], reverse=True)
        
        return {
            "driver": driver,
            "total_radios": total_radios,
            "sessions_count": len(sessions_with_radios),
            "session_stats": session_stats,
            "latest_radio": max(r.date for r in radios).isoformat() if radios else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar estatísticas do piloto {driver_number}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")