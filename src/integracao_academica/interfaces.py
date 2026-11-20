from abc import ABC, abstractmethod
from .domain import GradeAcademica


class IGradeAcademicaService(ABC):
    @abstractmethod
    def obter_grade_da_sala(self, sala_id: str) -> GradeAcademica:
        pass
