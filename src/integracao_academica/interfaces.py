from abc import ABC, abstractmethod
from datetime import datetime

class IGradeAcademicaService(ABC):
    @abstractmethod
    def possui_aula_no_horario(self, sala_id: str, inicio: datetime, fim: datetime) -> bool:
        pass
