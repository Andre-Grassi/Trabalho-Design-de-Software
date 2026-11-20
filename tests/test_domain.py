from datetime import datetime, time, timedelta, timezone
import pytest

from src.agendamento.domain import (
    PoliticaReserva,
    Reserva,
    Sala,
    StatusReserva,
    TipoAmbiente,
)
from src.autenticacao.domain import PerfilUsuario, Usuario
from src.integracao_academica.domain import GradeAcademica, IntervaloHorario


def _usuario(perfil: PerfilUsuario, uid: str = "u1", ativo: bool = True) -> Usuario:
    return Usuario(
        id=uid,
        nome="Teste",
        email="teste@ufpr.br",
        telefone="41999990000",
        perfil=perfil,
        vinculo_ativo=ativo,
    )


def _sala(
    tipo: TipoAmbiente = TipoAmbiente.SALA_AULA,
    lotacao: int = 30,
    nivel: int = 1,
    bloqueada: bool = False,
) -> Sala:
    return Sala(
        id="s1",
        codigo="PA-04",
        tipo=tipo,
        lotacao=lotacao,
        nivel_permissao_minimo=nivel,
        bloqueada_manutencao=bloqueada,
    )


def _politica(
    perfil: PerfilUsuario = PerfilUsuario.DOCENTE,
    max_horas: int = 4,
    max_ativas: int = 5,
    nivel: int = 2,
    antecedencia: int = 15,
) -> PoliticaReserva:
    return PoliticaReserva(
        perfil=perfil,
        max_horas_reserva=max_horas,
        max_reservas_ativas=max_ativas,
        nivel_permissao=nivel,
        antecedencia_minima_minutos=antecedencia,
    )


class TestSala:
    def test_capacidade(self):
        sala = _sala(lotacao=20)
        assert sala.tem_capacidade_para(1) is True
        assert sala.tem_capacidade_para(20) is True
        assert sala.tem_capacidade_para(0) is False
        assert sala.tem_capacidade_para(-5) is False
        assert sala.tem_capacidade_para(21) is False

    def test_visibilidade_e_bloqueio(self):
        sala = _sala(tipo=TipoAmbiente.LABORATORIO_RESTRITO, nivel=2)
        assert sala.pode_ser_visualizada_por(1) is False
        assert sala.pode_ser_visualizada_por(2) is True
        assert sala.exige_aprovacao_tecnica() is True
        assert sala.esta_bloqueada() is False

        sala.alterar_bloqueio(True)
        assert sala.esta_bloqueada() is True


class TestReserva:
    def test_conflito_e_duracao(self):
        base = datetime(2026, 12, 1, 10, 0)
        reserva = Reserva(
            id="r1",
            usuario_id="u1",
            sala_id="s1",
            inicio=base,
            fim=base + timedelta(hours=2),
            qtd_pessoas=10,
            status=StatusReserva.CONFIRMADA,
        )
        assert reserva.duracao_em_minutos() == 120
        assert reserva.conflita_com(datetime(2026, 12, 1, 11, 0), datetime(2026, 12, 1, 13, 0)) is True
        assert reserva.conflita_com(datetime(2026, 12, 1, 12, 0), datetime(2026, 12, 1, 14, 0)) is False
        assert reserva.conflita_com(datetime(2026, 12, 1, 8, 0), datetime(2026, 12, 1, 10, 0)) is False

    def test_transicoes_de_status(self):
        base = datetime(2026, 12, 1, 10, 0)
        reserva = Reserva(
            id="r1",
            usuario_id="u2",
            sala_id="s2",
            inicio=base,
            fim=base + timedelta(hours=1),
            qtd_pessoas=5,
            status=StatusReserva.PENDENTE,
        )
        assert reserva.esta_ativa() is True
        reserva.confirmar()
        assert reserva.status == StatusReserva.CONFIRMADA
        assert reserva.esta_ativa() is True
        reserva.cancelar()
        assert reserva.status == StatusReserva.CANCELADA
        assert reserva.esta_ativa() is False
        reserva.rejeitar()
        assert reserva.status == StatusReserva.REJEITADA
        assert reserva.esta_ativa() is False


class TestGradeAcademica:
    def test_sobreposicao_com_precisao_de_minutos(self):
        grade = GradeAcademica(
            sala_id="s1",
            semestre_letivo="2026/2",
            horarios_aulas=[IntervaloHorario(inicio=time(8, 0), fim=time(10, 0))],
        )
        # Sobreposição parcial no início da aula (07:30-08:30 cruza 08:00-10:00)
        assert grade.possui_aula_no_horario(
            datetime(2026, 12, 1, 7, 30), datetime(2026, 12, 1, 8, 30)
        ) is True
        # Sobreposição parcial no final da aula (09:30-10:30)
        assert grade.possui_aula_no_horario(
            datetime(2026, 12, 1, 9, 30), datetime(2026, 12, 1, 10, 30)
        ) is True
        # Adjacentes sem sobreposição
        assert grade.possui_aula_no_horario(
            datetime(2026, 12, 1, 7, 0), datetime(2026, 12, 1, 8, 0)
        ) is False
        assert grade.possui_aula_no_horario(
            datetime(2026, 12, 1, 10, 0), datetime(2026, 12, 1, 12, 0)
        ) is False

    def test_intervalo_multidia(self):
        grade = GradeAcademica(
            sala_id="s1",
            semestre_letivo="2026/2",
            horarios_aulas=[IntervaloHorario(inicio=time(8, 0), fim=time(10, 0))],
        )
        assert grade.possui_aula_no_horario(
            datetime(2026, 12, 1, 22, 0), datetime(2026, 12, 2, 9, 0)
        ) is True


class TestPoliticaReserva:
    def test_regras_de_validacao(self):
        agora = datetime(2026, 12, 1, 10, 0)
        usuario = _usuario(PerfilUsuario.ALUNO)
        sala = _sala(lotacao=20, nivel=1)
        grade_vazia = GradeAcademica(sala_id="s1", semestre_letivo="2026/2")
        politica = _politica(
            perfil=PerfilUsuario.ALUNO, max_horas=2, max_ativas=2, nivel=1, antecedencia=30
        )

        # Quantidade inválida
        with pytest.raises(ValueError, match="maior que zero"):
            politica.validar_solicitacao(
                usuario, sala, agora + timedelta(hours=1), agora + timedelta(hours=2), 0, grade_vazia, [], agora
            )

        # Horário final <= inicial
        with pytest.raises(ValueError, match="posterior"):
            politica.validar_solicitacao(
                usuario, sala, agora + timedelta(hours=2), agora + timedelta(hours=1), 5, grade_vazia, [], agora
            )

        # Antecedência mínima não respeitada
        with pytest.raises(ValueError, match="antecedência"):
            politica.validar_solicitacao(
                usuario, sala, agora + timedelta(minutes=10), agora + timedelta(hours=1), 5, grade_vazia, [], agora
            )

        # Duração máxima excedida
        with pytest.raises(ValueError, match="Duração máxima"):
            politica.validar_solicitacao(
                usuario, sala, agora + timedelta(hours=1), agora + timedelta(hours=4), 5, grade_vazia, [], agora
            )

        # Sala bloqueada
        with pytest.raises(ValueError, match="bloqueado"):
            politica.validar_solicitacao(
                usuario, _sala(bloqueada=True), agora + timedelta(hours=1), agora + timedelta(hours=2), 5, grade_vazia, [], agora
            )

        # Permissão insuficiente
        with pytest.raises(PermissionError, match="permissão"):
            politica.validar_solicitacao(
                usuario, _sala(nivel=2), agora + timedelta(hours=1), agora + timedelta(hours=2), 5, grade_vazia, [], agora
            )

        # Lotação excedida
        with pytest.raises(ValueError, match="Lotação máxima"):
            politica.validar_solicitacao(
                usuario, sala, agora + timedelta(hours=1), agora + timedelta(hours=2), 25, grade_vazia, [], agora
            )

        # Conflito com grade acadêmica
        grade_com_aula = GradeAcademica(
            sala_id="s1",
            semestre_letivo="2026/2",
            horarios_aulas=[IntervaloHorario(inicio=time(11, 0), fim=time(12, 0))],
        )
        with pytest.raises(ValueError, match="Grade Acadêmica"):
            politica.validar_solicitacao(
                usuario, sala, agora + timedelta(hours=1), agora + timedelta(hours=2), 5, grade_com_aula, [], agora
            )

        # Sala já ocupada
        existente = Reserva(
            id="r-ex",
            usuario_id="u9",
            sala_id="s1",
            inicio=agora + timedelta(hours=1),
            fim=agora + timedelta(hours=2),
            qtd_pessoas=5,
            status=StatusReserva.CONFIRMADA,
        )
        with pytest.raises(FileExistsError, match="SALA_OCUPADA"):
            politica.validar_solicitacao(
                usuario, sala, agora + timedelta(hours=1), agora + timedelta(hours=2), 5, grade_vazia, [existente], agora
            )

    def test_definir_status_inicial_rf9(self):
        politica = _politica()
        sala_comum = _sala(tipo=TipoAmbiente.SALA_AULA)
        lab_restrito = _sala(tipo=TipoAmbiente.LABORATORIO_RESTRITO)

        assert politica.definir_status_inicial(_usuario(PerfilUsuario.DOCENTE), sala_comum) == StatusReserva.CONFIRMADA
        assert politica.definir_status_inicial(_usuario(PerfilUsuario.ALUNO), sala_comum) == StatusReserva.PENDENTE
        assert politica.definir_status_inicial(_usuario(PerfilUsuario.DOCENTE), lab_restrito) == StatusReserva.PENDENTE

    def test_pode_cancelar_rf6(self):
        politica = _politica()
        dono = _usuario(PerfilUsuario.DOCENTE, uid="u1")
        outro = _usuario(PerfilUsuario.ALUNO, uid="u2")
        gestor = _usuario(PerfilUsuario.GESTOR, uid="u3")
        inicio = datetime(2026, 12, 1, 14, 0)

        reserva = Reserva(
            id="r1",
            usuario_id="u1",
            sala_id="s1",
            inicio=inicio,
            fim=inicio + timedelta(hours=1),
            qtd_pessoas=5,
            status=StatusReserva.CONFIRMADA,
        )

        # Antes do horário: dono e gestor podem cancelar; outro usuário não
        assert politica.pode_cancelar(reserva, dono, inicio - timedelta(minutes=1)) is True
        assert politica.pode_cancelar(reserva, gestor, inicio - timedelta(minutes=1)) is True
        assert politica.pode_cancelar(reserva, outro, inicio - timedelta(minutes=1)) is False

        # No horário ou após o início: ninguém pode cancelar
        assert politica.pode_cancelar(reserva, dono, inicio) is False
        assert politica.pode_cancelar(reserva, gestor, inicio + timedelta(minutes=5)) is False

        # Reserva já cancelada não pode ser cancelada novamente
        reserva.cancelar()
        assert politica.pode_cancelar(reserva, dono, inicio - timedelta(hours=1)) is False

    def test_aceita_datetime_com_timezone(self):
        tz_br = timezone(timedelta(hours=-3))
        agora = datetime(2026, 12, 1, 10, 0, tzinfo=tz_br)
        politica = _politica(antecedencia=15)
        grade_vazia = GradeAcademica(sala_id="s1", semestre_letivo="2026/2")
        politica.validar_solicitacao(
            _usuario(PerfilUsuario.DOCENTE),
            _sala(),
            agora + timedelta(hours=1),
            agora + timedelta(hours=2),
            10,
            grade_vazia,
            [],
            agora,
        )
