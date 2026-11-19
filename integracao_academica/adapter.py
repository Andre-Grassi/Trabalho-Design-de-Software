from datetime import datetime
from typing import Dict, List, Tuple
from .interfaces import IGradeAcademicaService

class GradeAcademica:
    def __init__(self, sala_id: str, semestre_letivo: str, horarios_aulas: List[Tuple[int, int]]):
        self.sala_id = sala_id
        self.semestre_letivo = semestre_letivo
        self.horarios_aulas = horarios_aulas

    def possui_aula_no_horario(self, inicio: datetime, fim: datetime) -> bool:
        for hora_ini, hora_fim in self.horarios_aulas:
            if inicio.hour < hora_fim and fim.hour > hora_ini:
                return True
        return False

class GradeAcademicaAdapter(IGradeAcademicaService):
    def __init__(self):
        # Cache semestral simulando horários oficiais importados do sistema legado (ex: s1 tem aula das 08h às 10h)
        self._cache_semestre: Dict[str, GradeAcademica] = {
            "s1": GradeAcademica("s1", "2026/2", [(8, 10)]),
            "s2": GradeAcademica("s2", "2026/2", []),
            "s3": GradeAcademica("s3", "2026/2", [(14, 16)])
        }

    def possui_aula_no_horario(self, sala_id: str, inicio: datetime, fim: datetime) -> bool:
        grade = self._cache_semestre.get(sala_id)
        if not grade:
            return False
        return grade.possui_aula_no_horario(inicio, fim)
