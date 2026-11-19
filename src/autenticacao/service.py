from typing import Optional
from database import get_connection
from .domain import Usuario, PerfilUsuario
from .interfaces import IUsuarioRepository, IAutenticacaoService

class UsuarioSQLRepository(IUsuarioRepository):
    def buscar_por_id(self, usuario_id: str) -> Optional[Usuario]:
        conn = get_connection()
        row = conn.execute("SELECT * FROM autenticacao_usuarios WHERE id = ?", (usuario_id,)).fetchone()
        conn.close()
        if not row:
            return None
        return Usuario(
            id=row["id"],
            nome=row["nome"],
            email=row["email"],
            telefone=row["telefone"] or "",
            perfil=PerfilUsuario(row["perfil"]),
            vinculo_ativo=bool(row["vinculo_ativo"])
        )

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
