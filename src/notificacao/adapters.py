from .interfaces import DestinatarioNotificacao, INotificador, ReservaNotificavel


def _formatar_status(status) -> str:
    return status.value if hasattr(status, "value") else str(status)


def _montar_mensagem(usuario: DestinatarioNotificacao, reserva: ReservaNotificavel) -> str:
    status = _formatar_status(reserva.status)
    return (
        f"Olá {usuario.nome}, sua reserva {reserva.id} "
        f"(sala {reserva.sala_id}, {reserva.inicio.isoformat()} - {reserva.fim.isoformat()}) "
        f"está com status: {status}."
    )


class EmailNotificador(INotificador):
    def __init__(self, servidor_smtp: str = "smtp.ufpr.br"):
        self.servidor_smtp = servidor_smtp

    def enviar_notificacao(
        self, usuario: DestinatarioNotificacao, reserva: ReservaNotificavel
    ) -> None:
        mensagem = _montar_mensagem(usuario, reserva)
        print(f"\n[E-MAIL SMTP ({self.servidor_smtp}) -> {usuario.email}] {mensagem}\n")


class WhatsAppNotificador(INotificador):
    def __init__(self, api_token: str = "demo-whatsapp-token"):
        self.api_token = api_token

    def enviar_notificacao(
        self, usuario: DestinatarioNotificacao, reserva: ReservaNotificavel
    ) -> None:
        mensagem = _montar_mensagem(usuario, reserva)
        print(f"\n[WHATSAPP API -> {usuario.telefone}] {mensagem}\n")
