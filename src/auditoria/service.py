import logging
from concurrent.futures import Future, ThreadPoolExecutor
from typing import List
from .domain import EventoAuditoria
from .interfaces import IAuditoriaRepository, IAuditoriaService

logger = logging.getLogger(__name__)


class AuditoriaService(IAuditoriaService):
    """Serviço de auditoria com persistência assíncrona (não bloqueante)."""

    def __init__(self, repo: IAuditoriaRepository, assincrono: bool = True):
        self.repo = repo
        self.assincrono = assincrono
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="auditoria")
        self._pendentes: List[Future] = []

    def _salvar_seguro(self, evento: EventoAuditoria) -> None:
        try:
            self.repo.salvar_log(evento)
        except Exception:
            logger.exception("Falha ao persistir evento de auditoria: %s", evento)

    def registrar(self, evento: EventoAuditoria) -> None:
        if self.assincrono:
            self._pendentes = [f for f in self._pendentes if not f.done()]
            future = self._executor.submit(self._salvar_seguro, evento)
            self._pendentes.append(future)
        else:
            self.repo.salvar_log(evento)

    def aguardar_pendentes(self) -> None:
        for future in list(self._pendentes):
            future.result()
        self._pendentes.clear()

    def buscar_por_entidade(self, entidade_id: str) -> List[EventoAuditoria]:
        self.aguardar_pendentes()
        return self.repo.buscar_por_entidade(entidade_id)

    def listar_todos(self) -> List[EventoAuditoria]:
        self.aguardar_pendentes()
        return self.repo.listar_todos()
