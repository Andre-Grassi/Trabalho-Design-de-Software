from abc import ABC, abstractmethod
from typing import List, Dict

class IAuditoriaRepository(ABC):
    @abstractmethod
    def salvar_log(self, usuario_id: str, acao: str, entidade_id: str, ip: str) -> None:
        pass

    @abstractmethod
    def listar_todos(self) -> List[Dict]:
        pass

class IAuditoriaService(ABC):
    @abstractmethod
    def registrar(self, usuario_id: str, acao: str, entidade_id: str, ip: str) -> None:
        pass
