from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class EventoAuditoria(BaseModel):
    id: Optional[int] = None
    acao: str
    usuario_id: str
    entidade_id: str
    ip: str
    timestamp: datetime = Field(default_factory=datetime.now)
