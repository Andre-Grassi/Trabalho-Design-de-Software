from datetime import datetime
from typing import List
from src.database import get_connection
from .domain import EventoAuditoria
from .interfaces import IAuditoriaRepository


class AuditoriaSQLRepository(IAuditoriaRepository):
    def _row_to_entity(self, row) -> EventoAuditoria:
        return EventoAuditoria(
            id=row["id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            usuario_id=row["usuario_id"],
            acao=row["acao"],
            entidade_id=row["entidade_id"],
            ip=row["ip"],
        )

    def salvar_log(self, evento: EventoAuditoria) -> None:
        conn = get_connection()
        conn.execute(
            """
            INSERT INTO auditoria_logs (timestamp, usuario_id, acao, entidade_id, ip)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                evento.timestamp.isoformat(),
                evento.usuario_id,
                evento.acao,
                evento.entidade_id,
                evento.ip,
            ),
        )
        conn.commit()
        conn.close()

    def buscar_por_entidade(self, entidade_id: str) -> List[EventoAuditoria]:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM auditoria_logs WHERE entidade_id = ? ORDER BY id DESC",
            (entidade_id,),
        ).fetchall()
        conn.close()
        return [self._row_to_entity(r) for r in rows]

    def listar_todos(self) -> List[EventoAuditoria]:
        conn = get_connection()
        rows = conn.execute("SELECT * FROM auditoria_logs ORDER BY id DESC").fetchall()
        conn.close()
        return [self._row_to_entity(r) for r in rows]
