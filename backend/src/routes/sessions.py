from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List
from ..models.session import Session, Meeting
from ..services.openf1_service import OpenF1Service
from ..services.storage_service import LocalStorageService
from ..utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/sessions", tags=["sessions"])

# Dependency injection
async def get_openf1_service():
    service = OpenF1Service()
    try:
        yield service
    finally:
        await service.close()

async def get_storage_service():
    return LocalStorageService()

@router.get("/", response_model=List[Session])
async def get_sessions(
    year: Optional[int] = Query(None, description="Filtrar por ano"),
    meeting_key: Optional[int] = Query(None, description="Filtrar por reunião"),
    session_name: Optional[str] = Query(None, description="Filtrar por nome da sessão"),
    use_cache: bool = Query(True, description="Usar dados em cache se disponível"),
    openf1_service: OpenF1Service = Depends(get_openf1_service),
    storage_service: LocalStorageService = Depends(get_storage_service)
):
    """Lista todas as sessões disponíveis"""
    try:
        sessions = None
        
        # Tenta carregar do cache primeiro
        if use_cache and not (meeting_key or session_name):  # Cache geral apenas
            sessions = await storage_service.load_sessions()
            if sessions and year:
                sessions = [s for s in sessions if s.year == year]
        
        # Se não tem cache, busca da API
        if not sessions:
            sessions = await openf1_service.get_sessions(
                meeting_key=meeting_key,
                session_name=session_name,
                year=year
            )
            
            # Salva no cache apenas se for uma busca geral
            if not (meeting_key or session_name):
                await storage_service.save_sessions(sessions)
        
        # Ordena por data (mais recente primeiro)
        sessions.sort(key=lambda x: x.date_start, reverse=True)
        
        return sessions
        
    except Exception as e:
        logger.error(f"Erro ao buscar sessões: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.get("/latest", response_model=Session)
async def get_latest_session(
    openf1_service: OpenF1Service = Depends(get_openf1_service)
):
    """Retorna a sessão mais recente"""
    try:
        session = await openf1_service.get_latest_session()
        if not session:
            raise HTTPException(status_code=404, detail="Nenhuma sessão encontrada")
        
        return session
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar sessão mais recente: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.get("/{session_key}", response_model=Session)
async def get_session_by_key(
    session_key: int,
    openf1_service: OpenF1Service = Depends(get_openf1_service)
):
    """Busca uma sessão específica pela chave"""
    try:
        sessions = await openf1_service.get_sessions()
        session = next((s for s in sessions if s.session_key == session_key), None)
        
        if not session:
            raise HTTPException(status_code=404, detail=f"Sessão {session_key} não encontrada")
        
        return session
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar sessão {session_key}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.get("/{session_key}/summary")
async def get_session_summary(
    session_key: int,
    openf1_service: OpenF1Service = Depends(get_openf1_service)
):
    """Retorna um resumo completo de uma sessão"""
    try:
        summary = await openf1_service.get_session_summary(session_key)
        
        if not summary.get("session"):
            raise HTTPException(status_code=404, detail=f"Sessão {session_key} não encontrada")
        
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar resumo da sessão {session_key}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.get("/meetings/", response_model=List[Meeting])
async def get_meetings(
    year: Optional[int] = Query(None, description="Filtrar por ano"),
    openf1_service: OpenF1Service = Depends(get_openf1_service)
):
    """Lista todas as reuniões (GPs) disponíveis"""
    try:
        meetings = await openf1_service.get_meetings(year=year)
        
        # Ordena por data de início
        meetings.sort(key=lambda x: x.date_start, reverse=True)
        
        return meetings
        
    except Exception as e:
        logger.error(f"Erro ao buscar reuniões: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.get("/meetings/{meeting_key}")
async def get_meeting_sessions(
    meeting_key: int,
    openf1_service: OpenF1Service = Depends(get_openf1_service)
):
    """Lista todas as sessões de uma reunião específica"""
    try:
        sessions = await openf1_service.get_sessions(meeting_key=meeting_key)
        meetings = await openf1_service.get_meetings()
        
        meeting = next((m for m in meetings if m.meeting_key == meeting_key), None)
        if not meeting:
            raise HTTPException(status_code=404, detail=f"Reunião {meeting_key} não encontrada")
        
        # Ordena sessões por data
        sessions.sort(key=lambda x: x.date_start)
        
        return {
            "meeting": meeting,
            "sessions": sessions,
            "session_count": len(sessions)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar sessões da reunião {meeting_key}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")