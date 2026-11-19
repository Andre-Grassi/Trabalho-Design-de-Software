from abc import ABC, abstractmethod
from datetime import datetime
from autenticacao.domain import Usuario

class INotificador(ABC):
    @abstractmethod
    def enviar_notificacao(self, usuario: Usuario, mensagem: str) -> None:
        pass

    @abstractmethod
    def notificar_disponibilidade_sala(self, usuario: Usuario, sala_codigo: str, inicio: datetime, fim: datetime) -> None:
        pass
