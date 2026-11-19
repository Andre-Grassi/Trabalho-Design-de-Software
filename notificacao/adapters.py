from datetime import datetime
from autenticacao.domain import Usuario
from .interfaces import INotificador

class EmailNotificador(INotificador):
    def enviar_notificacao(self, usuario: Usuario, mensagem: str) -> None:
        print(f"\n[E-MAIL SMTP -> {usuario.email}] {mensagem}\n")

    def notificar_disponibilidade_sala(self, usuario: Usuario, sala_codigo: str, inicio: datetime, fim: datetime) -> None:
        print(f"\n[E-MAIL SMTP -> {usuario.email}] Vaga liberada! A sala {sala_codigo} ficou disponível entre {inicio} e {fim}.\n")

class WhatsAppNotificador(INotificador):
    def enviar_notificacao(self, usuario: Usuario, mensagem: str) -> None:
        print(f"\n[WHATSAPP API -> {usuario.telefone}] {mensagem}\n")

    def notificar_disponibilidade_sala(self, usuario: Usuario, sala_codigo: str, inicio: datetime, fim: datetime) -> None:
        print(f"\n[WHATSAPP API -> {usuario.telefone}] Vaga liberada na sala {sala_codigo} ({inicio} - {fim})!\n")
