from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Protocol


class DestinatarioNotificacao(Protocol):
    nome: str
    email: str
    telefone: str


class ReservaNotificavel(Protocol):
    id: str
    sala_id: str
    inicio: datetime
    fim: datetime
    status: Any


class INotificador(ABC):
    @abstractmethod
    def enviar_notificacao(
        self, usuario: DestinatarioNotificacao, reserva: ReservaNotificavel
    ) -> None:
        pass
