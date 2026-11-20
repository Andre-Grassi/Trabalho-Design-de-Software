from datetime import time
from typing import Dict
from .domain import GradeAcademica, IntervaloHorario
from .interfaces import IGradeAcademicaService


class GradeAcademicaAdapter(IGradeAcademicaService):
    def __init__(self, api_endpoint: str = "https://siga.ufpr.br/api/v1/ensalamento"):
        self._api_endpoint = api_endpoint
        # Cache semestral simulando horários oficiais importados do sistema legado
        self._cache_semestre: Dict[str, GradeAcademica] = {
            "s1": GradeAcademica(
                sala_id="s1",
                semestre_letivo="2026/2",
                horarios_aulas=[IntervaloHorario(inicio=time(8, 0), fim=time(10, 0))],
            ),
            "s2": GradeAcademica(
                sala_id="s2",
                semestre_letivo="2026/2",
                horarios_aulas=[],
            ),
            "s3": GradeAcademica(
                sala_id="s3",
                semestre_letivo="2026/2",
                horarios_aulas=[IntervaloHorario(inicio=time(14, 0), fim=time(16, 0))],
            ),
        }

    def obter_grade_da_sala(self, sala_id: str) -> GradeAcademica:
        if sala_id not in self._cache_semestre:
            self._cache_semestre[sala_id] = self._buscar_na_api_externa(sala_id)
        return self._cache_semestre[sala_id]

    def _buscar_na_api_externa(self, sala_id: str) -> GradeAcademica:
        return GradeAcademica(sala_id=sala_id, semestre_letivo="2026/2", horarios_aulas=[])
