from fastapi import FastAPI
from database import init_db
from autenticacao.service import UsuarioSQLRepository, AutenticacaoService
from auditoria.repositories import AuditoriaSQLRepository
from auditoria.service import AuditoriaService
from integracao_academica.adapter import GradeAcademicaAdapter
from notificacao.adapters import EmailNotificador
from agendamento.repositories import (
    ReservaSQLRepository,
    SalaSQLRepository,
    PoliticaSQLRepository,
)
from agendamento.service import AgendamentoService
from agendamento.controller import criar_router

app = FastAPI(
    title="Sistema de Reserva de Salas e Laboratórios",
    description="Protótipo Funcional — Arquitetura Monólito Modular (DIP + Transações ACID)",
    version="1.0.0",
)

init_db()

audit_repo = AuditoriaSQLRepository()
service = AgendamentoService(
    reserva_repo=ReservaSQLRepository(),
    sala_repo=SalaSQLRepository(),
    politica_repo=PoliticaSQLRepository(),
    auth_service=AutenticacaoService(UsuarioSQLRepository()),
    audit_service=AuditoriaService(audit_repo),
    grade_service=GradeAcademicaAdapter(),
    notificador=EmailNotificador(),
)

app.include_router(criar_router(service, audit_repo))
