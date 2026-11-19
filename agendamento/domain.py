from datetime import datetime
from enum import Enum
from typing import List
from pydantic import BaseModel
from autenticacao.domain import Usuario, PerfilUsuario

class StatusReserva(str, Enum):
    PENDENTE = "PENDENTE"
    CONFIRMADA = "CONFIRMADA"
    REJEITADA = "REJEITADA"
    CANCELADA = "CANCELADA"

class TipoAmbiente(str, Enum):
    SALA_AULA = "SALA_AULA"
    LABORATORIO = "LABORATORIO"
    LABORATORIO_RESTRITO = "LABORATORIO_RESTRITO"

class Sala(BaseModel):
    id: str
    codigo: str
    tipo: TipoAmbiente
    lotacao: int
    nivel_permissao_minimo: int
    bloqueada_manutencao: bool

    def tem_capacidade_para(self, qtd_pessoas: int) -> bool:
        return qtd_pessoas <= self.lotacao

    def pode_ser_visualizada_por(self, nivel_usuario: int) -> bool:
        return nivel_usuario >= self.nivel_permissao_minimo

    def esta_bloqueada(self) -> bool:
        return self.bloqueada_manutencao

    def exige_aprovacao_tecnica(self) -> bool:
        return self.tipo == TipoAmbiente.LABORATORIO_RESTRITO

class Reserva(BaseModel):
    id: str
    usuario_id: str
    sala_id: str
    inicio: datetime
    fim: datetime
    qtd_pessoas: int
    status: StatusReserva

    def conflita_com(self, outro_inicio: datetime, outro_fim: datetime) -> bool:
        return self.inicio < outro_fim and self.fim > outro_inicio

    def esta_ativa(self) -> bool:
        return self.status in (StatusReserva.CONFIRMADA, StatusReserva.PENDENTE)

    def confirmar(self) -> None:
        self.status = StatusReserva.CONFIRMADA

    def rejeitar(self) -> None:
        self.status = StatusReserva.REJEITADA

    def cancelar(self) -> None:
        self.status = StatusReserva.CANCELADA

class PoliticaReserva(BaseModel):
    perfil: PerfilUsuario
    max_horas_reserva: int
    max_reservas_ativas: int
    nivel_permissao: int
    antecedencia_minima_minutos: int

    def validar_solicitacao(
        self,
        usuario: Usuario,
        sala: Sala,
        inicio: datetime,
        fim: datetime,
        qtd_pessoas: int,
        tem_aula_grade: bool,
        reservas_sala: List[Reserva],
    ) -> None:
        if fim <= inicio:
            raise ValueError("O horário final deve ser posterior ao inicial.")
        duracao_horas = (fim - inicio).total_seconds() / 3600
        if duracao_horas > self.max_horas_reserva:
            raise ValueError(f"Duração máxima permitida para {usuario.perfil.value} é de {self.max_horas_reserva}h.")
        if sala.esta_bloqueada():
            raise ValueError("Ambiente bloqueado para manutenção operacional.")
        if not sala.pode_ser_visualizada_por(self.nivel_permissao):
            raise PermissionError("Perfil sem permissão para reservar este espaço.")
        if not sala.tem_capacidade_para(qtd_pessoas):
            raise ValueError(f"Lotação máxima excedida (capacidade: {sala.lotacao}).")
        if tem_aula_grade:
            raise ValueError("Conflito com horário oficial da Grade Acadêmica.")
        for r in reservas_sala:
            if r.esta_ativa() and r.conflita_com(inicio, fim):
                raise FileExistsError("SALA_OCUPADA")

    def validar_cota_reservas_ativas(self, reservas_ativas_usuario: List[Reserva]) -> None:
        if len(reservas_ativas_usuario) >= self.max_reservas_ativas:
            raise ValueError(f"Limite máximo de {self.max_reservas_ativas} reservas ativas atingido.")

    def validar_conflito_agenda_usuario(
        self, inicio: datetime, fim: datetime, reservas_usuario: List[Reserva]
    ) -> str | None:
        for r in reservas_usuario:
            if r.esta_ativa() and r.conflita_com(inicio, fim):
                return r.id
        return None

    def definir_status_inicial(self, usuario: Usuario, sala: Sala) -> StatusReserva:
        if usuario.eh_aluno() or sala.exige_aprovacao_tecnica():
            return StatusReserva.PENDENTE
        return StatusReserva.CONFIRMADA
