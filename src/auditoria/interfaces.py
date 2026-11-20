from abc import ABC, abstractmethod
from typing import List
from .domain import EventoAuditoria


class IAuditoriaRepository(ABC):
    @abstractmethod
    def salvar_log(self, evento: EventoAuditoria) -> None:
        pass

    @abstractmethod
    def buscar_por_entidade(self, entidade_id: str) -> List[EventoAuditoria]:
        pass

    @abstractmethod
    def listar_todos(self) -> List[EventoAuditoria]:
        pass


class IAuditoriaService(ABC):
    @abstractmethod
    def registrar(self, evento: EventoAuditoria) -> None:
        pass

    @abstractmethod
    def buscar_por_entidade(self, entidade_id: str) -> List[EventoAuditoria]:
        pass

    @abstractmethod
    def listar_todos(self) -> List[EventoAuditoria]:
        pass
