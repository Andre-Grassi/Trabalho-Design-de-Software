from .interfaces import IAuditoriaService, IAuditoriaRepository

class AuditoriaService(IAuditoriaService):
    def __init__(self, repo: IAuditoriaRepository):
        self.repo = repo

    def registrar(self, usuario_id: str, acao: str, entidade_id: str, ip: str) -> None:
        self.repo.salvar_log(usuario_id, acao, entidade_id, ip)
