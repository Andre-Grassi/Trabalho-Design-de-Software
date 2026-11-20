import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import pytest

import src.database as db
from src.agendamento.domain import StatusReserva
from src.agendamento.repositories import (
    PoliticaSQLRepository,
    ReservaSQLRepository,
    SalaSQLRepository,
)
from src.agendamento.service import AgendamentoService, ConflitoAgendaUsuarioError
from src.auditoria.repositories import AuditoriaSQLRepository
from src.auditoria.service import AuditoriaService
from src.autenticacao.service import AutenticacaoService, UsuarioSQLRepository
from src.integracao_academica.adapter import GradeAcademicaAdapter
from src.notificacao.adapters import WhatsAppNotificador


class TestConcorrenciaEIntegridadeBD:
    def test_reservas_simultaneas_apenas_uma_vence_asr1(self, agendamento_service, dia_futuro):
        """Simula disputa concorrente pela mesma sala e horário (ASR 1 / ADR-002)."""
        inicio = dia_futuro.replace(hour=10)
        fim = dia_futuro.replace(hour=12)

        def tentar_reservar(uid: str):
            return agendamento_service.solicitar_reserva(uid, "s2", inicio, fim, 10, "127.0.0.1")

        # 3 usuários diferentes tentando reservar a mesma sala s2 no mesmo instante
        usuarios = ["u1", "u2", "u3"]
        sucessos = []
        erros_ocupada = []

        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = [pool.submit(tentar_reservar, u) for u in usuarios]
            for fut in futures:
                try:
                    sucessos.append(fut.result())
                except FileExistsError:
                    erros_ocupada.append(True)

        assert len(sucessos) == 1
        assert len(erros_ocupada) == 2

    def test_trigger_bd_impede_insercao_sobreposta_adr002(self, agendamento_service, dia_futuro):
        """Mesmo fora da camada de serviço, o banco SQL bloqueia conflito de sala (ADR-002)."""
        inicio = dia_futuro.replace(hour=10)
        fim = dia_futuro.replace(hour=12)
        agendamento_service.solicitar_reserva("u1", "s1", inicio, fim, 10, "127.0.0.1")

        conn = db.get_connection()
        try:
            with pytest.raises(sqlite3.IntegrityError, match="CONFLITO_INTEGRIDADE_SALA"):
                conn.execute(
                    "INSERT INTO agendamento_reservas VALUES ('res-dup', 'u3', 's1', ?, ?, 5, 'CONFIRMADA')",
                    ((inicio + timedelta(minutes=30)).isoformat(), (fim + timedelta(minutes=30)).isoformat()),
                )
        finally:
            conn.close()

    def test_auditoria_imutavel_no_banco_asr2(self, agendamento_service, audit_service, dia_futuro):
        """Logs de auditoria são append-only: UPDATE e DELETE são bloqueados no BD (ASR 2)."""
        agendamento_service.solicitar_reserva(
            "u1", "s1", dia_futuro.replace(hour=10), dia_futuro.replace(hour=12), 10, "127.0.0.1"
        )
        audit_service.aguardar_pendentes()

        conn = db.get_connection()
        try:
            with pytest.raises(sqlite3.IntegrityError, match="AUDITORIA_IMUTAVEL"):
                conn.execute("UPDATE auditoria_logs SET acao = 'FRAUDE'")
            with pytest.raises(sqlite3.IntegrityError, match="AUDITORIA_IMUTAVEL"):
                conn.execute("DELETE FROM auditoria_logs")
        finally:
            conn.close()


class TestTrocaAtomicaECancelamento:
    def test_troca_atomica_mesma_sala_e_rollback_em_erro(self, agendamento_service, dia_futuro):
        r1 = agendamento_service.solicitar_reserva(
            "u1", "s1", dia_futuro.replace(hour=10), dia_futuro.replace(hour=12), 15, "127.0.0.1"
        )

        # Se a nova reserva violar alguma regra (ex: conflito com aula 08h-10h), a antiga permanece ativa
        with pytest.raises(ValueError, match="Grade Acadêmica"):
            agendamento_service.trocar_reserva(
                r1.id, "u1", "s1", dia_futuro.replace(hour=9), dia_futuro.replace(hour=11), 15, "127.0.0.1"
            )
        assert agendamento_service.reserva_repo.buscar_por_id(r1.id).status == StatusReserva.CONFIRMADA

        # Troca válida deslocando horário na mesma sala (10h-12h -> 11h-13h)
        r2 = agendamento_service.trocar_reserva(
            r1.id, "u1", "s1", dia_futuro.replace(hour=11), dia_futuro.replace(hour=13), 15, "127.0.0.1"
        )
        assert r2.status == StatusReserva.CONFIRMADA
        assert agendamento_service.reserva_repo.buscar_por_id(r1.id).status == StatusReserva.CANCELADA

    def test_troca_detecta_conflito_com_segunda_reserva_ativa(self, agendamento_service, dia_futuro):
        r1 = agendamento_service.solicitar_reserva(
            "u1", "s1", dia_futuro.replace(hour=10), dia_futuro.replace(hour=12), 10, "127.0.0.1"
        )
        r2 = agendamento_service.solicitar_reserva(
            "u1", "s1", dia_futuro.replace(hour=15), dia_futuro.replace(hour=17), 10, "127.0.0.1"
        )

        with pytest.raises(ConflitoAgendaUsuarioError) as exc_info:
            agendamento_service.trocar_reserva(
                r1.id, "u1", "s2", dia_futuro.replace(hour=16), dia_futuro.replace(hour=18), 10, "127.0.0.1"
            )
        assert exc_info.value.reserva_atual_id == r2.id
        # Ambas permanecem ativas
        assert agendamento_service.reserva_repo.buscar_por_id(r1.id).status == StatusReserva.CONFIRMADA
        assert agendamento_service.reserva_repo.buscar_por_id(r2.id).status == StatusReserva.CONFIRMADA

    def test_cancelamento_apos_inicio_bloqueado_rf6(self, agendamento_service):
        conn = db.get_connection()
        passado_ini = (datetime.now() - timedelta(hours=2)).isoformat()
        passado_fim = (datetime.now() - timedelta(hours=1)).isoformat()
        conn.execute(
            "INSERT INTO agendamento_reservas VALUES ('res-passada', 'u1', 's1', ?, ?, 5, 'CONFIRMADA')",
            (passado_ini, passado_fim),
        )
        conn.commit()
        conn.close()

        with pytest.raises(ValueError, match="início"):
            agendamento_service.cancelar_reserva("res-passada", "u1", "127.0.0.1")


class TestSubstituibilidadeDependenciaExterna:
    def test_notificador_substituivel_dip(self, isolated_db, dia_futuro, capsys):
        """Comprova que trocar EmailNotificador por WhatsAppNotificador não exige alterar o serviço."""
        audit = AuditoriaService(AuditoriaSQLRepository(), assincrono=False)
        service = AgendamentoService(
            reserva_repo=ReservaSQLRepository(),
            sala_repo=SalaSQLRepository(),
            politica_repo=PoliticaSQLRepository(),
            auth_service=AutenticacaoService(UsuarioSQLRepository()),
            audit_service=audit,
            grade_service=GradeAcademicaAdapter(),
            notificador=WhatsAppNotificador(),
            notificacao_assincrona=False,
        )

        reserva = service.solicitar_reserva(
            "u1", "s1", dia_futuro.replace(hour=10), dia_futuro.replace(hour=12), 10, "127.0.0.1"
        )
        captured = capsys.readouterr()
        assert "[WHATSAPP API -> 41999990001]" in captured.out
        assert reserva.id in captured.out

    def test_notificacoes_assincronas_entregues_no_fake(
        self, agendamento_service, notificador_fake, dia_futuro
    ):
        reserva = agendamento_service.solicitar_reserva(
            "u2", "s2", dia_futuro.replace(hour=14), dia_futuro.replace(hour=16), 8, "127.0.0.1"
        )
        agendamento_service.avaliar_reserva_pendente(reserva.id, "u3", True, "127.0.0.1")
        agendamento_service.aguardar_notificacoes()

        assert ("ana@ufpr.br", reserva.id, "PENDENTE") in notificador_fake.enviadas
        assert ("ana@ufpr.br", reserva.id, "CONFIRMADA") in notificador_fake.enviadas
