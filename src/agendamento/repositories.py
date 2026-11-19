from datetime import datetime
from typing import List, Optional
from database import get_connection
from autenticacao.domain import PerfilUsuario
from .domain import Reserva, Sala, PoliticaReserva, StatusReserva, TipoAmbiente
from .interfaces import IReservaRepository, ISalaRepository, IPoliticaRepository

class ReservaSQLRepository(IReservaRepository):
    def _row_to_entity(self, row) -> Reserva:
        return Reserva(
            id=row["id"],
            usuario_id=row["usuario_id"],
            sala_id=row["sala_id"],
            inicio=datetime.fromisoformat(row["inicio"]),
            fim=datetime.fromisoformat(row["fim"]),
            qtd_pessoas=row["qtd_pessoas"],
            status=StatusReserva(row["status"]),
        )

    def salvar(self, reserva: Reserva, conn=None) -> Reserva:
        own_conn = conn is None
        conn = conn or get_connection()
        conn.execute(
            """
            INSERT INTO agendamento_reservas (id, usuario_id, sala_id, inicio, fim, qtd_pessoas, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET status=excluded.status
            """,
            (reserva.id, reserva.usuario_id, reserva.sala_id, reserva.inicio.isoformat(), reserva.fim.isoformat(), reserva.qtd_pessoas, reserva.status.value),
        )
        if own_conn:
            conn.commit()
            conn.close()
        return reserva

    def substituir_atomicamente(self, antiga: Reserva, nova: Reserva, conn=None) -> Reserva:
        own_conn = conn is None
        conn = conn or get_connection()
        if own_conn:
            conn.execute("BEGIN EXCLUSIVE")
        conn.execute("UPDATE agendamento_reservas SET status = ? WHERE id = ?", (StatusReserva.CANCELADA.value, antiga.id))
        self.salvar(nova, conn=conn)
        if own_conn:
            conn.commit()
            conn.close()
        return nova

    def buscar_por_id(self, reserva_id: str) -> Optional[Reserva]:
        conn = get_connection()
        row = conn.execute("SELECT * FROM agendamento_reservas WHERE id = ?", (reserva_id,)).fetchone()
        conn.close()
        return self._row_to_entity(row) if row else None

    def buscar_por_sala_e_periodo(self, sala_id: str, inicio: datetime, fim: datetime, conn=None) -> List[Reserva]:
        own_conn = conn is None
        conn = conn or get_connection()
        rows = conn.execute(
            """
            SELECT * FROM agendamento_reservas
            WHERE sala_id = ? AND status IN ('CONFIRMADA', 'PENDENTE')
            AND inicio < ? AND fim > ?
            """,
            (sala_id, fim.isoformat(), inicio.isoformat()),
        ).fetchall()
        if own_conn:
            conn.close()
        return [self._row_to_entity(r) for r in rows]

    def buscar_ativas_por_usuario(self, usuario_id: str, conn=None) -> List[Reserva]:
        own_conn = conn is None
        conn = conn or get_connection()
        rows = conn.execute(
            "SELECT * FROM agendamento_reservas WHERE usuario_id = ? AND status IN ('CONFIRMADA', 'PENDENTE')",
            (usuario_id,),
        ).fetchall()
        if own_conn:
            conn.close()
        return [self._row_to_entity(r) for r in rows]

class SalaSQLRepository(ISalaRepository):
    def _row_to_entity(self, row) -> Sala:
        return Sala(
            id=row["id"],
            codigo=row["codigo"],
            tipo=TipoAmbiente(row["tipo"]),
            lotacao=row["lotacao"],
            nivel_permissao_minimo=row["nivel_permissao_minimo"],
            bloqueada_manutencao=bool(row["bloqueada_manutencao"]),
        )

    def buscar_por_id(self, sala_id: str) -> Optional[Sala]:
        conn = get_connection()
        row = conn.execute("SELECT * FROM agendamento_salas WHERE id = ?", (sala_id,)).fetchone()
        conn.close()
        return self._row_to_entity(row) if row else None

    def listar_por_nivel_maximo(self, nivel_permissao: int) -> List[Sala]:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM agendamento_salas WHERE nivel_permissao_minimo <= ?",
            (nivel_permissao,),
        ).fetchall()
        conn.close()
        return [self._row_to_entity(r) for r in rows]

class PoliticaSQLRepository(IPoliticaRepository):
    def obter_politica_por_perfil(self, perfil: PerfilUsuario) -> PoliticaReserva:
        conn = get_connection()
        row = conn.execute("SELECT * FROM agendamento_politicas WHERE perfil = ?", (perfil.value,)).fetchone()
        conn.close()
        return PoliticaReserva(
            perfil=PerfilUsuario(row["perfil"]),
            max_horas_reserva=row["max_horas_reserva"],
            max_reservas_ativas=row["max_reservas_ativas"],
            nivel_permissao=row["nivel_permissao"],
            antecedencia_minima_minutos=row["antecedencia_minima_minutos"],
        )
