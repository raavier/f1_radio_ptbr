import httpx
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from ..models.radio import RadioMessage, Driver
from ..models.session import Session, Meeting
from ..utils.logger import get_logger
import os

logger = get_logger(__name__)

class OpenF1Service:
    def __init__(self):
        self.base_url = os.getenv("OPENF1_BASE_URL", "https://api.openf1.org/v1")
        self.session = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        """Fecha a sessão HTTP"""
        await self.session.aclose()
    
    async def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> List[Dict]:
        """Faz uma requisição para a API OpenF1"""
        try:
            url = f"{self.base_url}/{endpoint}"
            response = await self.session.get(url, params=params or {})
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Erro HTTP ao acessar {endpoint}: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"Erro ao fazer requisição para {endpoint}: {str(e)}")
            raise
    
    async def get_meetings(self, year: Optional[int] = None) -> List[Meeting]:
        """Busca todas as reuniões (GPs) de uma temporada"""
        params = {}
        if year:
            params["year"] = year
        
        data = await self._make_request("meetings", params)
        return [Meeting(**item) for item in data]
    
    async def get_sessions(self, meeting_key: Optional[int] = None, 
                          session_name: Optional[str] = None,
                          year: Optional[int] = None) -> List[Session]:
        """Busca sessões filtradas por reunião, nome ou ano"""
        params = {}
        if meeting_key:
            params["meeting_key"] = meeting_key
        if session_name:
            params["session_name"] = session_name
        if year:
            params["year"] = year
            
        data = await self._make_request("sessions", params)
        return [Session(**item) for item in data]
    
    async def get_drivers(self, session_key: Optional[int] = None) -> List[Driver]:
        """Busca informações dos pilotos"""
        params = {}
        if session_key:
            params["session_key"] = session_key
            
        data = await self._make_request("drivers", params)
        return [Driver(**item) for item in data]
    
    async def get_team_radio(self, session_key: Optional[int] = None,
                           driver_number: Optional[int] = None,
                           meeting_key: Optional[int] = None) -> List[RadioMessage]:
        """Busca mensagens de rádio da equipe"""
        params = {}
        if session_key:
            params["session_key"] = session_key
        if driver_number:
            params["driver_number"] = driver_number
        if meeting_key:
            params["meeting_key"] = meeting_key
            
        data = await self._make_request("team_radio", params)
        radios = []
        
        for item in data:
            # Converte a string de data para datetime
            if isinstance(item.get("date"), str):
                item["date"] = datetime.fromisoformat(item["date"].replace("Z", "+00:00"))
            radios.append(RadioMessage(**item))
        
        return radios
    
    async def get_latest_session(self) -> Optional[Session]:
        """Busca a sessão mais recente"""
        try:
            # Busca sessões dos últimos 30 dias
            sessions = await self.get_sessions()
            if not sessions:
                return None
            
            # Ordena por data de início (mais recente primeiro)
            sessions.sort(key=lambda x: x.date_start, reverse=True)
            return sessions[0]
        except Exception as e:
            logger.error(f"Erro ao buscar sessão mais recente: {str(e)}")
            return None
    
    async def get_live_radio_feed(self, session_key: int, 
                                 interval: int = 10) -> None:
        """Monitora rádios em tempo real (simulado)"""
        logger.info(f"Iniciando monitoramento de rádios para sessão {session_key}")
        
        last_check = datetime.now()
        
        while True:
            try:
                # Busca rádios desde a última verificação
                radios = await self.get_team_radio(session_key=session_key)
                
                # Filtra apenas rádios novos
                new_radios = [r for r in radios if r.date > last_check]
                
                if new_radios:
                    logger.info(f"Encontrados {len(new_radios)} novos rádios")
                    # Aqui você pode processar os novos rádios
                    # Por exemplo, salvá-los ou enviá-los via WebSocket
                
                last_check = datetime.now()
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Erro no monitoramento de rádios: {str(e)}")
                await asyncio.sleep(interval * 2)  # Espera mais tempo em caso de erro
    
    async def get_session_summary(self, session_key: int) -> Dict[str, Any]:
        """Busca um resumo completo de uma sessão"""
        try:
            # Busca dados em paralelo
            session_task = self.get_sessions()
            drivers_task = self.get_drivers(session_key)
            radios_task = self.get_team_radio(session_key)
            
            sessions, drivers, radios = await asyncio.gather(
                session_task, drivers_task, radios_task
            )
            
            # Encontra a sessão específica
            session = next((s for s in sessions if s.session_key == session_key), None)
            
            return {
                "session": session,
                "drivers": drivers,
                "radios": radios,
                "radio_count": len(radios),
                "drivers_with_radios": len(set(r.driver_number for r in radios if r.driver_number))
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar resumo da sessão {session_key}: {str(e)}")
            raise