from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum

class RadioCategory(str, Enum):
    TEAM_RADIO = "team_radio"
    DRIVER_RADIO = "driver_radio"
    RACE_CONTROL = "race_control"

class Driver(BaseModel):
    driver_number: int = Field(..., description="Número do piloto")
    broadcast_name: Optional[str] = Field(None, description="Nome para broadcast")
    country_code: Optional[str] = Field(None, description="Código do país")
    first_name: Optional[str] = Field(None, description="Primeiro nome")
    full_name: Optional[str] = Field(None, description="Nome completo")
    headshot_url: Optional[str] = Field(None, description="URL da foto")
    last_name: Optional[str] = Field(None, description="Sobrenome")
    team_colour: Optional[str] = Field(None, description="Cor da equipe")
    team_name: Optional[str] = Field(None, description="Nome da equipe")
    name_acronym: Optional[str] = Field(None, description="Acrônimo do nome")

class RadioMessage(BaseModel):
    date: datetime = Field(..., description="Data e hora da mensagem")
    driver_number: Optional[int] = Field(None, description="Número do piloto")
    meeting_key: int = Field(..., description="Chave da sessão")
    recording_url: str = Field(..., description="URL do áudio")
    session_key: int = Field(..., description="Chave da sessão específica")
    
    # Campos adicionais que podem ser úteis
    category: Optional[RadioCategory] = Field(None, description="Categoria do rádio")
    duration: Optional[float] = Field(None, description="Duração em segundos")
    transcription: Optional[str] = Field(None, description="Transcrição do áudio")
    driver_info: Optional[Driver] = Field(None, description="Informações do piloto")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class RadioResponse(BaseModel):
    radios: List[RadioMessage]
    total: int
    page: int
    per_page: int
    session_info: Optional[dict] = None