from datetime import datetime, timedelta
from typing import List, Tuple
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import src.database as db
from src.agendamento.controller import AgendamentoController
from src.agendamento.repositories import (
    PoliticaSQLRepository,
    ReservaSQLRepository,
    SalaSQLRepository,
)
from src.agendamento.service import AgendamentoService
from src.auditoria.repositories import AuditoriaSQLRepository
from src.auditoria.service import AuditoriaService
from src.autenticacao.service import AutenticacaoService, UsuarioSQLRepository
from src.integracao_academica.adapter import GradeAcademicaAdapter
from src.notificacao.interfaces import (
    DestinatarioNotificacao,
    INotificador,
    ReservaNotificavel,
)


class NotificadorFake(INotificador):
    """Implementação fake de INotificador para testes unitários e de integração (DIP)."""

    def __init__(self):
        self.enviadas: List[Tuple[str, str, str]] = []

    def enviar_notificacao(
        self, usuario: DestinatarioNotificacao, reserva: ReservaNotificavel
    ) -> None:
        status = (
            reserva.status.value
            if hasattr(reserva.status, "value")
            else str(reserva.status)
        )
        self.enviadas.append((usuario.email, reserva.id, status))


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    """Cria um banco SQLite isolado em diretório temporário para cada teste."""
    db_path = str(tmp_path / "test_reservas.db")
    monkeypatch.setattr(db, "DB_FILE", db_path)
    db.init_db(db_path)
    return db_path


@pytest.fixture
def notificador_fake():
    return NotificadorFake()


@pytest.fixture
def audit_service(isolated_db):
    return AuditoriaService(AuditoriaSQLRepository(), assincrono=True)


@pytest.fixture
def agendamento_service(isolated_db, audit_service, notificador_fake):
    service = AgendamentoService(
        reserva_repo=ReservaSQLRepository(),
        sala_repo=SalaSQLRepository(),
        politica_repo=PoliticaSQLRepository(),
        auth_service=AutenticacaoService(UsuarioSQLRepository()),
        audit_service=audit_service,
        grade_service=GradeAcademicaAdapter(),
        notificador=notificador_fake,
        notificacao_assincrona=True,
    )
    yield service
    service.aguardar_notificacoes()
    audit_service.aguardar_pendentes()


@pytest.fixture
def client(agendamento_service):
    app = FastAPI()
    controller = AgendamentoController(agendamento_service)
    app.include_router(controller.router)
    return TestClient(app)


@pytest.fixture
def dia_futuro() -> datetime:
    """Retorna meia-noite de uma data futura (3 dias à frente) para evitar falhas de antecedência."""
    return (datetime.now() + timedelta(days=3)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
