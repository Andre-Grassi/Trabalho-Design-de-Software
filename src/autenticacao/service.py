from typing import Optional
from src.database import get_connection
from .domain import PerfilUsuario, Usuario
from .interfaces import IAutenticacaoService, IUsuarioRepository


class UsuarioSQLRepository(IUsuarioRepository):
    def _row_to_entity(self, row) -> Usuario:
        return Usuario(
            id=row["id"],
            nome=row["nome"],
            email=row["email"],
            telefone=row["telefone"] or "",
            perfil=PerfilUsuario(row["perfil"]),
            vinculo_ativo=bool(row["vinculo_ativo"]),
        )

    def buscar_por_id(self, usuario_id: str) -> Optional[Usuario]:
        conn = get_connection()
        row = conn.execute(
            "SELECT * FROM autenticacao_usuarios WHERE id = ?", (usuario_id,)
        ).fetchone()
        conn.close()
        return self._row_to_entity(row) if row else None

    def buscar_por_email(self, email: str) -> Optional[Usuario]:
        conn = get_connection()
        row = conn.execute(
            "SELECT * FROM autenticacao_usuarios WHERE email = ?", (email,)
        ).fetchone()
        conn.close()
        return self._row_to_entity(row) if row else None


class AutenticacaoService(IAutenticacaoService):
    def __init__(self, usuario_repo: IUsuarioRepository):
        self.usuario_repo = usuario_repo

    def validar_vinculo(self, usuario_id: str) -> Usuario:
        usuario = self.usuario_repo.buscar_por_id(usuario_id)
        if not usuario or not usuario.is_vinculo_ativo():
            raise ValueError("Usuário inexistente ou sem vínculo institucional ativo.")
        return usuario

    def possui_permissao_gestor(self, usuario_id: str) -> bool:
        usuario = self.validar_vinculo(usuario_id)
        return usuario.pode_aprovar_laboratorio()
