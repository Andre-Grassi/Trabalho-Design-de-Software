from abc import ABC, abstractmethod
from contextlib import AbstractContextManager
from datetime import datetime
from typing import List, Optional
from src.autenticacao.domain import PerfilUsuario
from .domain import PoliticaReserva, Reserva, Sala


class IReservaRepository(ABC):
    @abstractmethod
    def transacao_exclusiva(self) -> AbstractContextManager[None]:
        pass

    @abstractmethod
    def salvar(self, reserva: Reserva) -> Reserva:
        pass

    @abstractmethod
    def substituir_atomicamente(self, antiga: Reserva, nova: Reserva) -> Reserva:
        pass

    @abstractmethod
    def buscar_por_id(self, reserva_id: str) -> Optional[Reserva]:
        pass

    @abstractmethod
    def buscar_por_sala_e_periodo(
        self, sala_id: str, inicio: datetime, fim: datetime
    ) -> List[Reserva]:
        pass

    @abstractmethod
    def buscar_ativas_por_usuario(self, usuario_id: str) -> List[Reserva]:
        pass


class ISalaRepository(ABC):
    @abstractmethod
    def buscar_por_id(self, sala_id: str) -> Optional[Sala]:
        pass

    @abstractmethod
    def listar_por_nivel_maximo(self, nivel_permissao: int) -> List[Sala]:
        pass

    @abstractmethod
    def atualizar(self, sala: Sala) -> None:
        pass


class IPoliticaRepository(ABC):
    @abstractmethod
    def obter_politica_por_perfil(self, perfil: PerfilUsuario) -> PoliticaReserva:
        pass
