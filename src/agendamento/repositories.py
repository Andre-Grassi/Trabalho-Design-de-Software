import sqlite3
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime
from typing import Iterator, List, Optional
from src.autenticacao.domain import PerfilUsuario
from src.database import get_connection
from .domain import (
    PoliticaReserva,
    Reserva,
    Sala,
    StatusReserva,
    TipoAmbiente,
    normalizar_datetime,
)
from .interfaces import IPoliticaRepository, IReservaRepository, ISalaRepository

_conexao_transacao: ContextVar[Optional[sqlite3.Connection]] = ContextVar(
    "_conexao_transacao", default=None
)


def _obter_conn() -> tuple[sqlite3.Connection, bool]:
    conn_tx = _conexao_transacao.get()
    if conn_tx is not None:
        return conn_tx, False
    return get_connection(), True


class ReservaSQLRepository(IReservaRepository):
    @contextmanager
    def transacao_exclusiva(self) -> Iterator[None]:
        conn_existente = _conexao_transacao.get()
        if conn_existente is not None:
            yield
            return

        conn = get_connection()
        token = _conexao_transacao.set(conn)
        try:
            conn.execute("BEGIN EXCLUSIVE")  # Lock pessimista ACID (ASR 1 / ADR-002)
            yield
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            _conexao_transacao.reset(token)
            conn.close()

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

    def salvar(self, reserva: Reserva) -> Reserva:
        conn, own_conn = _obter_conn()
        ini = normalizar_datetime(reserva.inicio)
        fim = normalizar_datetime(reserva.fim)
        try:
            conn.execute(
                """
                INSERT INTO agendamento_reservas (id, usuario_id, sala_id, inicio, fim, qtd_pessoas, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET status=excluded.status
                """,
                (
                    reserva.id,
                    reserva.usuario_id,
                    reserva.sala_id,
                    ini.isoformat(),
                    fim.isoformat(),
                    reserva.qtd_pessoas,
                    reserva.status.value,
                ),
            )
            if own_conn:
                conn.commit()
        except sqlite3.IntegrityError as exc:
            if own_conn:
                conn.rollback()
            if "CONFLITO_INTEGRIDADE_SALA" in str(exc):
                raise FileExistsError("SALA_OCUPADA") from exc
            raise ValueError(f"Violação de integridade ao salvar reserva: {exc}") from exc
        finally:
            if own_conn:
                conn.close()
        return reserva

    def substituir_atomicamente(self, antiga: Reserva, nova: Reserva) -> Reserva:
        with self.transacao_exclusiva():
            conn, _ = _obter_conn()
            conn.execute(
                "UPDATE agendamento_reservas SET status = ? WHERE id = ?",
                (StatusReserva.CANCELADA.value, antiga.id),
            )
            self.salvar(nova)
        return nova

    def buscar_por_id(self, reserva_id: str) -> Optional[Reserva]:
        conn, own_conn = _obter_conn()
        try:
            row = conn.execute(
                "SELECT * FROM agendamento_reservas WHERE id = ?", (reserva_id,)
            ).fetchone()
            return self._row_to_entity(row) if row else None
        finally:
            if own_conn:
                conn.close()

    def buscar_por_sala_e_periodo(
        self, sala_id: str, inicio: datetime, fim: datetime
    ) -> List[Reserva]:
        conn, own_conn = _obter_conn()
        ini = normalizar_datetime(inicio)
        termino = normalizar_datetime(fim)
        try:
            rows = conn.execute(
                """
                SELECT * FROM agendamento_reservas
                WHERE sala_id = ? AND status IN ('CONFIRMADA', 'PENDENTE')
                AND inicio < ? AND fim > ?
                """,
                (sala_id, termino.isoformat(), ini.isoformat()),
            ).fetchall()
            return [self._row_to_entity(r) for r in rows]
        finally:
            if own_conn:
                conn.close()

    def buscar_ativas_por_usuario(self, usuario_id: str) -> List[Reserva]:
        conn, own_conn = _obter_conn()
        try:
            rows = conn.execute(
                """
                SELECT * FROM agendamento_reservas
                WHERE usuario_id = ? AND status IN ('CONFIRMADA', 'PENDENTE')
                """,
                (usuario_id,),
            ).fetchall()
            return [self._row_to_entity(r) for r in rows]
        finally:
            if own_conn:
                conn.close()


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
        conn, own_conn = _obter_conn()
        try:
            row = conn.execute(
                "SELECT * FROM agendamento_salas WHERE id = ?", (sala_id,)
            ).fetchone()
            return self._row_to_entity(row) if row else None
        finally:
            if own_conn:
                conn.close()

    def listar_por_nivel_maximo(self, nivel_permissao: int) -> List[Sala]:
        conn, own_conn = _obter_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM agendamento_salas WHERE nivel_permissao_minimo <= ?",
                (nivel_permissao,),
            ).fetchall()
            return [self._row_to_entity(r) for r in rows]
        finally:
            if own_conn:
                conn.close()

    def atualizar(self, sala: Sala) -> None:
        conn, own_conn = _obter_conn()
        try:
            conn.execute(
                """
                UPDATE agendamento_salas
                SET codigo = ?, tipo = ?, lotacao = ?, nivel_permissao_minimo = ?,
                    bloqueada_manutencao = ?
                WHERE id = ?
                """,
                (
                    sala.codigo,
                    sala.tipo.value,
                    sala.lotacao,
                    sala.nivel_permissao_minimo,
                    1 if sala.bloqueada_manutencao else 0,
                    sala.id,
                ),
            )
            if own_conn:
                conn.commit()
        finally:
            if own_conn:
                conn.close()


class PoliticaSQLRepository(IPoliticaRepository):
    def obter_politica_por_perfil(self, perfil: PerfilUsuario) -> PoliticaReserva:
        conn, own_conn = _obter_conn()
        try:
            row = conn.execute(
                "SELECT * FROM agendamento_politicas WHERE perfil = ?", (perfil.value,)
            ).fetchone()
            if not row:
                raise LookupError(
                    f"Política de reserva não encontrada para o perfil {perfil.value}."
                )
            return PoliticaReserva(
                perfil=PerfilUsuario(row["perfil"]),
                max_horas_reserva=row["max_horas_reserva"],
                max_reservas_ativas=row["max_reservas_ativas"],
                nivel_permissao=row["nivel_permissao"],
                antecedencia_minima_minutos=row["antecedencia_minima_minutos"],
                tolerancia_no_show_minutos=row["tolerancia_no_show_minutos"],
            )
        finally:
            if own_conn:
                conn.close()
