from fastapi import FastAPI
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
from src.database import init_db
from src.integracao_academica.adapter import GradeAcademicaAdapter
from src.notificacao.adapters import EmailNotificador

app = FastAPI(
    title="Sistema de Reserva de Salas e Laboratórios",
    description=(
        "Protótipo Funcional — Arquitetura Monólito Modular "
        "(DIP + Transações ACID + Auditoria/Notificação Assíncronas)"
    ),
    version="1.0.0",
)

init_db()

auth_service = AutenticacaoService(UsuarioSQLRepository())
audit_service = AuditoriaService(AuditoriaSQLRepository())
agendamento_service = AgendamentoService(
    reserva_repo=ReservaSQLRepository(),
    sala_repo=SalaSQLRepository(),
    politica_repo=PoliticaSQLRepository(),
    auth_service=auth_service,
    audit_service=audit_service,
    grade_service=GradeAcademicaAdapter(),
    notificador=EmailNotificador(),
)

controller = AgendamentoController(agendamento_service)
app.include_router(controller.router)
