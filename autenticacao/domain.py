from enum import Enum
from pydantic import BaseModel

class PerfilUsuario(str, Enum):
    ALUNO = "ALUNO"
    DOCENTE = "DOCENTE"
    GESTOR = "GESTOR"

class Usuario(BaseModel):
    id: str
    nome: str
    email: str
    telefone: str
    perfil: PerfilUsuario
    vinculo_ativo: bool

    def is_vinculo_ativo(self) -> bool:
        return self.vinculo_ativo

    def eh_docente(self) -> bool:
        return self.perfil == PerfilUsuario.DOCENTE

    def eh_aluno(self) -> bool:
        return self.perfil == PerfilUsuario.ALUNO

    def pode_aprovar_laboratorio(self) -> bool:
        return self.perfil == PerfilUsuario.GESTOR
