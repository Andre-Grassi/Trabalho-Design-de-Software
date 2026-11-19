from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
from autenticacao.domain import PerfilUsuario
from .domain import Reserva, Sala, PoliticaReserva

class IReservaRepository(ABC):
    @abstractmethod
    def salvar(self, reserva: Reserva, conn=None) -> Reserva: pass

    @abstractmethod
    def substituir_atomicamente(self, antiga: Reserva, nova: Reserva, conn=None) -> Reserva: pass

    @abstractmethod
    def buscar_por_id(self, reserva_id: str) -> Optional[Reserva]: pass

    @abstractmethod
    def buscar_por_sala_e_periodo(self, sala_id: str, inicio: datetime, fim: datetime, conn=None) -> List[Reserva]: pass

    @abstractmethod
    def buscar_ativas_por_usuario(self, usuario_id: str, conn=None) -> List[Reserva]: pass

class ISalaRepository(ABC):
    @abstractmethod
    def buscar_por_id(self, sala_id: str) -> Optional[Sala]: pass

    @abstractmethod
    def listar_por_nivel_maximo(self, nivel_permissao: int) -> List[Sala]: pass

class IPoliticaRepository(ABC):
    @abstractmethod
    def obter_politica_por_perfil(self, perfil: PerfilUsuario) -> PoliticaReserva: pass
