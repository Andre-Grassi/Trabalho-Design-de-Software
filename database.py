import sqlite3

DB_FILE = "reservas_institucional.db"

def get_connection():
    conn = sqlite3.connect(DB_FILE, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS autenticacao_usuarios (
            id TEXT PRIMARY KEY,
            nome TEXT NOT NULL,
            email TEXT NOT NULL,
            telefone TEXT,
            perfil TEXT NOT NULL,
            vinculo_ativo INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS agendamento_salas (
            id TEXT PRIMARY KEY,
            codigo TEXT NOT NULL,
            tipo TEXT NOT NULL,
            lotacao INTEGER NOT NULL,
            nivel_permissao_minimo INTEGER NOT NULL,
            bloqueada_manutencao INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS agendamento_politicas (
            perfil TEXT PRIMARY KEY,
            max_horas_reserva INTEGER NOT NULL,
            max_reservas_ativas INTEGER NOT NULL,
            nivel_permissao INTEGER NOT NULL,
            antecedencia_minima_minutos INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS agendamento_reservas (
            id TEXT PRIMARY KEY,
            usuario_id TEXT NOT NULL,
            sala_id TEXT NOT NULL,
            inicio TEXT NOT NULL,
            fim TEXT NOT NULL,
            qtd_pessoas INTEGER NOT NULL,
            status TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS auditoria_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            usuario_id TEXT NOT NULL,
            acao TEXT NOT NULL,
            entidade_id TEXT NOT NULL,
            ip TEXT NOT NULL
        );
    """)

    cur.execute("INSERT OR IGNORE INTO autenticacao_usuarios VALUES ('u1', 'Prof. Carlos', 'carlos@ufpr.br', '41999990001', 'DOCENTE', 1)")
    cur.execute("INSERT OR IGNORE INTO autenticacao_usuarios VALUES ('u2', 'Ana (Aluna)', 'ana@ufpr.br', '41999990002', 'ALUNO', 1)")
    cur.execute("INSERT OR IGNORE INTO autenticacao_usuarios VALUES ('u3', 'Técnico Marcos', 'marcos@ufpr.br', '41999990003', 'GESTOR', 1)")

    cur.execute("INSERT OR IGNORE INTO agendamento_salas VALUES ('s1', 'PA-04', 'SALA_AULA', 40, 1, 0)")
    cur.execute("INSERT OR IGNORE INTO agendamento_salas VALUES ('s2', 'LAB-REDES', 'LABORATORIO', 25, 1, 0)")
    cur.execute("INSERT OR IGNORE INTO agendamento_salas VALUES ('s3', 'LAB-PESQUISA', 'LABORATORIO_RESTRITO', 15, 2, 0)")

    cur.execute("INSERT OR IGNORE INTO agendamento_politicas VALUES ('ALUNO', 2, 2, 1, 30)")
    cur.execute("INSERT OR IGNORE INTO agendamento_politicas VALUES ('DOCENTE', 4, 5, 2, 15)")
    cur.execute("INSERT OR IGNORE INTO agendamento_politicas VALUES ('GESTOR', 8, 10, 3, 0)")

    conn.commit()
    conn.close()
