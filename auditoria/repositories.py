from datetime import datetime
from typing import List, Dict
from database import get_connection
from .interfaces import IAuditoriaRepository

class AuditoriaSQLRepository(IAuditoriaRepository):
    def salvar_log(self, usuario_id: str, acao: str, entidade_id: str, ip: str) -> None:
        conn = get_connection()
        conn.execute(
            "INSERT INTO auditoria_logs (timestamp, usuario_id, acao, entidade_id, ip) VALUES (?, ?, ?, ?, ?)",
            (datetime.now().isoformat(), usuario_id, acao, entidade_id, ip)
        )
        conn.commit()
        conn.close()

    def listar_todos(self) -> List[Dict]:
        conn = get_connection()
        rows = conn.execute("SELECT * FROM auditoria_logs ORDER BY id DESC").fetchall()
        conn.close()
        return [dict(r) for r in rows]
