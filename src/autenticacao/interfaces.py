from abc import ABC, abstractmethod
from typing import Optional
from .domain import Usuario

class IUsuarioRepository(ABC):
    @abstractmethod
    def buscar_por_id(self, usuario_id: str) -> Optional[Usuario]:
        pass

class IAutenticacaoService(ABC):
    @abstractmethod
    def validar_vinculo(self, usuario_id: str) -> Usuario:
        pass

    @abstractmethod
    def possui_permissao_gestor(self, usuario_id: str) -> bool:
        pass
