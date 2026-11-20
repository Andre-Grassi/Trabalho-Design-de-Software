import sqlite3
from pathlib import Path

DB_FILE = str(Path(__file__).resolve().parent.parent / "reservas_institucional.db")


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path or DB_FILE, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str | None = None) -> None:
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.executescript(
        """
        -- Schema lógico: Módulo Autenticação
        CREATE TABLE IF NOT EXISTS autenticacao_usuarios (
            id TEXT PRIMARY KEY,
            nome TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            telefone TEXT,
            perfil TEXT NOT NULL CHECK (perfil IN ('ALUNO', 'DOCENTE', 'GESTOR')),
            vinculo_ativo INTEGER NOT NULL CHECK (vinculo_ativo IN (0, 1))
        );

        -- Schema lógico: Módulo Agendamento
        CREATE TABLE IF NOT EXISTS agendamento_salas (
            id TEXT PRIMARY KEY,
            codigo TEXT NOT NULL UNIQUE,
            tipo TEXT NOT NULL CHECK (tipo IN ('SALA_AULA', 'LABORATORIO', 'LABORATORIO_RESTRITO')),
            lotacao INTEGER NOT NULL CHECK (lotacao > 0),
            nivel_permissao_minimo INTEGER NOT NULL CHECK (nivel_permissao_minimo >= 1),
            bloqueada_manutencao INTEGER NOT NULL CHECK (bloqueada_manutencao IN (0, 1))
        );

        CREATE TABLE IF NOT EXISTS agendamento_politicas (
            perfil TEXT PRIMARY KEY CHECK (perfil IN ('ALUNO', 'DOCENTE', 'GESTOR')),
            max_horas_reserva INTEGER NOT NULL CHECK (max_horas_reserva > 0),
            max_reservas_ativas INTEGER NOT NULL CHECK (max_reservas_ativas > 0),
            nivel_permissao INTEGER NOT NULL CHECK (nivel_permissao >= 1),
            antecedencia_minima_minutos INTEGER NOT NULL CHECK (antecedencia_minima_minutos >= 0),
            tolerancia_no_show_minutos INTEGER NOT NULL DEFAULT 15 CHECK (tolerancia_no_show_minutos >= 0)
        );

        CREATE TABLE IF NOT EXISTS agendamento_reservas (
            id TEXT PRIMARY KEY,
            usuario_id TEXT NOT NULL,
            sala_id TEXT NOT NULL,
            inicio TEXT NOT NULL,
            fim TEXT NOT NULL,
            qtd_pessoas INTEGER NOT NULL CHECK (qtd_pessoas > 0),
            status TEXT NOT NULL CHECK (status IN ('PENDENTE', 'CONFIRMADA', 'REJEITADA', 'CANCELADA')),
            CHECK (fim > inicio),
            FOREIGN KEY (sala_id) REFERENCES agendamento_salas(id)
        );

        -- Restrições de integridade no banco de dados (ADR-002)
        CREATE TRIGGER IF NOT EXISTS trg_impedir_conflito_sala_insert
        BEFORE INSERT ON agendamento_reservas
        WHEN NEW.status IN ('CONFIRMADA', 'PENDENTE')
        BEGIN
            SELECT RAISE(ABORT, 'CONFLITO_INTEGRIDADE_SALA')
            WHERE EXISTS (
                SELECT 1
                FROM agendamento_reservas
                WHERE sala_id = NEW.sala_id
                  AND status IN ('CONFIRMADA', 'PENDENTE')
                  AND id != NEW.id
                  AND inicio < NEW.fim
                  AND fim > NEW.inicio
            );
        END;

        CREATE TRIGGER IF NOT EXISTS trg_impedir_conflito_sala_update
        BEFORE UPDATE ON agendamento_reservas
        WHEN NEW.status IN ('CONFIRMADA', 'PENDENTE')
        BEGIN
            SELECT RAISE(ABORT, 'CONFLITO_INTEGRIDADE_SALA')
            WHERE EXISTS (
                SELECT 1
                FROM agendamento_reservas
                WHERE sala_id = NEW.sala_id
                  AND status IN ('CONFIRMADA', 'PENDENTE')
                  AND id != NEW.id
                  AND inicio < NEW.fim
                  AND fim > NEW.inicio
            );
        END;

        -- Schema lógico: Módulo Auditoria (Append-Only / Imutável - ASR 2)
        CREATE TABLE IF NOT EXISTS auditoria_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            usuario_id TEXT NOT NULL,
            acao TEXT NOT NULL,
            entidade_id TEXT NOT NULL,
            ip TEXT NOT NULL
        );

        CREATE TRIGGER IF NOT EXISTS trg_auditoria_imutavel_update
        BEFORE UPDATE ON auditoria_logs
        BEGIN
            SELECT RAISE(ABORT, 'AUDITORIA_IMUTAVEL');
        END;

        CREATE TRIGGER IF NOT EXISTS trg_auditoria_imutavel_delete
        BEFORE DELETE ON auditoria_logs
        BEGIN
            SELECT RAISE(ABORT, 'AUDITORIA_IMUTAVEL');
        END;
        """
    )

    cur.execute(
        "INSERT OR IGNORE INTO autenticacao_usuarios VALUES ('u1', 'Prof. Carlos', 'carlos@ufpr.br', '41999990001', 'DOCENTE', 1)"
    )
    cur.execute(
        "INSERT OR IGNORE INTO autenticacao_usuarios VALUES ('u2', 'Ana (Aluna)', 'ana@ufpr.br', '41999990002', 'ALUNO', 1)"
    )
    cur.execute(
        "INSERT OR IGNORE INTO autenticacao_usuarios VALUES ('u3', 'Técnico Marcos', 'marcos@ufpr.br', '41999990003', 'GESTOR', 1)"
    )

    cur.execute(
        "INSERT OR IGNORE INTO agendamento_salas VALUES ('s1', 'PA-04', 'SALA_AULA', 40, 1, 0)"
    )
    cur.execute(
        "INSERT OR IGNORE INTO agendamento_salas VALUES ('s2', 'LAB-REDES', 'LABORATORIO', 25, 1, 0)"
    )
    cur.execute(
        "INSERT OR IGNORE INTO agendamento_salas VALUES ('s3', 'LAB-PESQUISA', 'LABORATORIO_RESTRITO', 15, 2, 0)"
    )

    cur.execute(
        "INSERT OR IGNORE INTO agendamento_politicas VALUES ('ALUNO', 2, 2, 1, 30, 15)"
    )
    cur.execute(
        "INSERT OR IGNORE INTO agendamento_politicas VALUES ('DOCENTE', 4, 5, 2, 15, 15)"
    )
    cur.execute(
        "INSERT OR IGNORE INTO agendamento_politicas VALUES ('GESTOR', 8, 10, 3, 0, 15)"
    )

    conn.commit()
    conn.close()
