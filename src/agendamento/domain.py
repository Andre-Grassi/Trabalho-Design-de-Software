from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel
from src.autenticacao.domain import PerfilUsuario, Usuario
from src.integracao_academica.domain import GradeAcademica


def normalizar_datetime(dt: datetime) -> datetime:
    """Normaliza datetimes com timezone para horário local naive para comparação consistente."""
    if dt.tzinfo is not None:
        return dt.astimezone().replace(tzinfo=None)
    return dt


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
        return 0 < qtd_pessoas <= self.lotacao

    def pode_ser_visualizada_por(self, nivel_usuario: int) -> bool:
        return nivel_usuario >= self.nivel_permissao_minimo

    def esta_bloqueada(self) -> bool:
        return self.bloqueada_manutencao

    def exige_aprovacao_tecnica(self) -> bool:
        return self.tipo == TipoAmbiente.LABORATORIO_RESTRITO

    def alterar_bloqueio(self, status: bool) -> None:
        self.bloqueada_manutencao = status


class Reserva(BaseModel):
    id: str
    usuario_id: str
    sala_id: str
    inicio: datetime
    fim: datetime
    qtd_pessoas: int
    status: StatusReserva

    def conflita_com(self, outro_inicio: datetime, outro_fim: datetime) -> bool:
        ini_a = normalizar_datetime(self.inicio)
        fim_a = normalizar_datetime(self.fim)
        ini_b = normalizar_datetime(outro_inicio)
        fim_b = normalizar_datetime(outro_fim)
        return ini_a < fim_b and fim_a > ini_b

    def duracao_em_minutos(self) -> int:
        ini = normalizar_datetime(self.inicio)
        fim = normalizar_datetime(self.fim)
        return int((fim - ini).total_seconds() // 60)

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
    tolerancia_no_show_minutos: int = 15

    def validar_solicitacao(
        self,
        usuario: Usuario,
        sala: Sala,
        inicio: datetime,
        fim: datetime,
        qtd_pessoas: int,
        grade: GradeAcademica,
        reservas_sala: List[Reserva],
        agora: Optional[datetime] = None,
    ) -> None:
        ini = normalizar_datetime(inicio)
        termino = normalizar_datetime(fim)
        referencia = normalizar_datetime(agora or datetime.now())

        if qtd_pessoas <= 0:
            raise ValueError("A quantidade de pessoas deve ser maior que zero.")
        if termino <= ini:
            raise ValueError("O horário final deve ser posterior ao inicial.")
        limite_antecedencia = referencia + timedelta(
            minutes=self.antecedencia_minima_minutos
        )
        if ini < limite_antecedencia:
            raise ValueError(
                f"A reserva deve ser feita com pelo menos {self.antecedencia_minima_minutos} minutos de antecedência."
            )
        duracao_horas = (termino - ini).total_seconds() / 3600
        if duracao_horas > self.max_horas_reserva:
            raise ValueError(
                f"Duração máxima permitida para {usuario.perfil.value} é de {self.max_horas_reserva}h."
            )
        if sala.esta_bloqueada():
            raise ValueError("Ambiente bloqueado para manutenção operacional.")
        if not sala.pode_ser_visualizada_por(self.nivel_permissao):
            raise PermissionError("Perfil sem permissão para reservar este espaço.")
        if not sala.tem_capacidade_para(qtd_pessoas):
            raise ValueError(f"Lotação máxima excedida (capacidade: {sala.lotacao}).")
        if grade.possui_aula_no_horario(ini, termino):
            raise ValueError("Conflito com horário oficial da Grade Acadêmica.")
        for r in reservas_sala:
            if r.esta_ativa() and r.conflita_com(ini, termino):
                raise FileExistsError("SALA_OCUPADA")

    def validar_cota_reservas_ativas(self, reservas_ativas_usuario: List[Reserva]) -> None:
        if len(reservas_ativas_usuario) >= self.max_reservas_ativas:
            raise ValueError(
                f"Limite máximo de {self.max_reservas_ativas} reservas ativas atingido."
            )

    def validar_conflito_agenda_usuario(
        self, inicio: datetime, fim: datetime, reservas_usuario: List[Reserva]
    ) -> Optional[str]:
        ini = normalizar_datetime(inicio)
        termino = normalizar_datetime(fim)
        for r in reservas_usuario:
            if r.esta_ativa() and r.conflita_com(ini, termino):
                return r.id
        return None

    def definir_status_inicial(self, usuario: Usuario, sala: Sala) -> StatusReserva:
        if usuario.eh_aluno() or sala.exige_aprovacao_tecnica():
            return StatusReserva.PENDENTE
        return StatusReserva.CONFIRMADA

    def pode_cancelar(
        self,
        reserva: Reserva,
        solicitante: Usuario,
        instante_atual: Optional[datetime] = None,
    ) -> bool:
        if not reserva.esta_ativa():
            return False
        if reserva.usuario_id != solicitante.id and not solicitante.pode_aprovar_laboratorio():
            return False
        referencia = normalizar_datetime(instante_atual or datetime.now())
        return referencia < normalizar_datetime(reserva.inicio)
