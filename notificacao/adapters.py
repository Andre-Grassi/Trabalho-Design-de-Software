from autenticacao.domain import Usuario
from .interfaces import INotificador

class EmailNotificador(INotificador):
    def enviar_notificacao(self, usuario: Usuario, mensagem: str) -> None:
        print(f"\n[E-MAIL SMTP -> {usuario.email}] {mensagem}\n")

class WhatsAppNotificador(INotificador):
    def enviar_notificacao(self, usuario: Usuario, mensagem: str) -> None:
        print(f"\n[WHATSAPP API -> {usuario.telefone}] {mensagem}\n")
