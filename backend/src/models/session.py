from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum

class SessionType(str, Enum):
    PRACTICE_1 = "Practice 1"
    PRACTICE_2 = "Practice 2" 
    PRACTICE_3 = "Practice 3"
    QUALIFYING = "Qualifying"
    SPRINT = "Sprint"
    SPRINT_QUALIFYING = "Sprint Qualifying"
    RACE = "Race"

class Meeting(BaseModel):
    circuit_key: int = Field(..., description="Chave do circuito")
    circuit_short_name: str = Field(..., description="Nome curto do circuito")
    country_code: str = Field(..., description="Código do país")
    country_key: int = Field(..., description="Chave do país")
    country_name: str = Field(..., description="Nome do país")
    date_start: datetime = Field(..., description="Data de início")
    gmt_offset: str = Field(..., description="Offset GMT")
    location: str = Field(..., description="Localização")
    meeting_key: int = Field(..., description="Chave única da reunião")
    meeting_name: str = Field(..., description="Nome da reunião")
    meeting_official_name: str = Field(..., description="Nome oficial")
    year: int = Field(..., description="Ano da temporada")

class Session(BaseModel):
    circuit_key: int = Field(..., description="Chave do circuito")
    circuit_short_name: str = Field(..., description="Nome curto do circuito")
    country_code: str = Field(..., description="Código do país")
    country_key: int = Field(..., description="Chave do país")
    country_name: str = Field(..., description="Nome do país")
    date_end: datetime = Field(..., description="Data de fim")
    date_start: datetime = Field(..., description="Data de início")
    gmt_offset: str = Field(..., description="Offset GMT")
    location: str = Field(..., description="Localização")
    meeting_key: int = Field(..., description="Chave da reunião")
    session_key: int = Field(..., description="Chave única da sessão")
    session_name: str = Field(..., description="Nome da sessão")
    session_type: str = Field(..., description="Tipo da sessão")
    year: int = Field(..., description="Ano da temporada")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }