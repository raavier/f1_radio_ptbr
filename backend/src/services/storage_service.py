import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import aiofiles
from ..models.radio import RadioMessage
from ..models.session import Session, Meeting
from ..utils.logger import get_logger

logger = get_logger(__name__)

class LocalStorageService:
    def __init__(self, base_path: str = "./data"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
        
        # Cria estrutura de pastas
        (self.base_path / "radios").mkdir(exist_ok=True)
        (self.base_path / "sessions").mkdir(exist_ok=True)
        (self.base_path / "meetings").mkdir(exist_ok=True)
        (self.base_path / "drivers").mkdir(exist_ok=True)
    
    def _serialize_datetime(self, obj):
        """Serializa objetos datetime para JSON"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    async def save_radios(self, radios: List[RadioMessage], session_key: int) -> bool:
        """Salva rádios de uma sessão localmente"""
        try:
            filename = self.base_path / "radios" / f"session_{session_key}.json"
            
            # Converte para dict e serializa
            radios_data = []
            for radio in radios:
                radio_dict = radio.model_dump()
                if radio_dict.get('date'):
                    radio_dict['date'] = radio_dict['date'].isoformat() if isinstance(radio_dict['date'], datetime) else radio_dict['date']
                radios_data.append(radio_dict)
            
            data = {
                "session_key": session_key,
                "saved_at": datetime.now().isoformat(),
                "count": len(radios),
                "radios": radios_data
            }
            
            async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, indent=2, ensure_ascii=False, default=self._serialize_datetime))
            
            logger.info(f"Salvos {len(radios)} rádios para sessão {session_key}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar rádios: {str(e)}")
            return False
    
    async def load_radios(self, session_key: int) -> Optional[List[RadioMessage]]:
        """Carrega rádios de uma sessão do armazenamento local"""
        try:
            filename = self.base_path / "radios" / f"session_{session_key}.json"
            
            if not filename.exists():
                return None
            
            async with aiofiles.open(filename, 'r', encoding='utf-8') as f:
                content = await f.read()
                data = json.loads(content)
            
            radios = []
            for radio_data in data.get("radios", []):
                # Converte string de data de volta para datetime
                if radio_data.get("date"):
                    radio_data["date"] = datetime.fromisoformat(radio_data["date"])
                radios.append(RadioMessage(**radio_data))
            
            logger.info(f"Carregados {len(radios)} rádios da sessão {session_key}")
            return radios
            
        except Exception as e:
            logger.error(f"Erro ao carregar rádios: {str(e)}")
            return None
    
    async def save_sessions(self, sessions: List[Session]) -> bool:
        """Salva informações de sessões"""
        try:
            filename = self.base_path / "sessions" / "sessions.json"
            
            sessions_data = []
            for session in sessions:
                session_dict = session.model_dump()
                # Serializa datas
                if session_dict.get('date_start'):
                    session_dict['date_start'] = session_dict['date_start'].isoformat() if isinstance(session_dict['date_start'], datetime) else session_dict['date_start']
                if session_dict.get('date_end'):
                    session_dict['date_end'] = session_dict['date_end'].isoformat() if isinstance(session_dict['date_end'], datetime) else session_dict['date_end']
                sessions_data.append(session_dict)
            
            data = {
                "saved_at": datetime.now().isoformat(),
                "count": len(sessions),
                "sessions": sessions_data
            }
            
            async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, indent=2, ensure_ascii=False, default=self._serialize_datetime))
            
            logger.info(f"Salvas {len(sessions)} sessões")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar sessões: {str(e)}")
            return False
    
    async def load_sessions(self) -> Optional[List[Session]]:
        """Carrega sessões do armazenamento local"""
        try:
            filename = self.base_path / "sessions" / "sessions.json"
            
            if not filename.exists():
                return None
            
            async with aiofiles.open(filename, 'r', encoding='utf-8') as f:
                content = await f.read()
                data = json.loads(content)
            
            sessions = []
            for session_data in data.get("sessions", []):
                # Converte strings de data de volta para datetime
                if session_data.get("date_start"):
                    session_data["date_start"] = datetime.fromisoformat(session_data["date_start"])
                if session_data.get("date_end"):
                    session_data["date_end"] = datetime.fromisoformat(session_data["date_end"])
                sessions.append(Session(**session_data))
            
            logger.info(f"Carregadas {len(sessions)} sessões")
            return sessions
            
        except Exception as e:
            logger.error(f"Erro ao carregar sessões: {str(e)}")
            return None
    
    async def get_available_sessions(self) -> List[Dict[str, Any]]:
        """Lista todas as sessões que têm dados de rádio salvos"""
        try:
            radios_dir = self.base_path / "radios"
            available_sessions = []
            
            for file_path in radios_dir.glob("session_*.json"):
                session_key = int(file_path.stem.split("_")[1])
                
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    data = json.loads(content)
                
                available_sessions.append({
                    "session_key": session_key,
                    "radio_count": data.get("count", 0),
                    "saved_at": data.get("saved_at"),
                    "file_size": file_path.stat().st_size
                })
            
            return sorted(available_sessions, key=lambda x: x["session_key"], reverse=True)
            
        except Exception as e:
            logger.error(f"Erro ao listar sessões disponíveis: {str(e)}")
            return []
    
    async def cleanup_old_data(self, days_to_keep: int = 30) -> bool:
        """Remove dados antigos para economizar espaço"""
        try:
            cutoff_date = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)
            removed_count = 0
            
            for directory in ["radios", "sessions", "meetings", "drivers"]:
                dir_path = self.base_path / directory
                for file_path in dir_path.glob("*.json"):
                    if file_path.stat().st_mtime < cutoff_date:
                        file_path.unlink()
                        removed_count += 1
            
            logger.info(f"Removidos {removed_count} arquivos antigos")
            return True
            
        except Exception as e:
            logger.error(f"Erro na limpeza de dados antigos: {str(e)}")
            return False

# TODO: Implementar S3StorageService para futuro uso
class S3StorageService:
    def __init__(self, bucket_name: str, region: str = "us-east-1"):
        self.bucket_name = bucket_name
        self.region = region
        # TODO: Implementar conexão com AWS S3
        pass
    
    async def save_radios(self, radios: List[RadioMessage], session_key: int) -> bool:
        # TODO: Implementar upload para S3
        pass
    
    async def load_radios(self, session_key: int) -> Optional[List[RadioMessage]]:
        # TODO: Implementar download do S3
        pass