from abc import ABC, abstractmethod
from autenticacao.domain import Usuario

class INotificador(ABC):
    @abstractmethod
    def enviar_notificacao(self, usuario: Usuario, mensagem: str) -> None:
        pass
