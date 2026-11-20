from datetime import datetime, time, timedelta
from typing import List
from pydantic import BaseModel


class IntervaloHorario(BaseModel):
    inicio: time
    fim: time


class GradeAcademica(BaseModel):
    sala_id: str
    semestre_letivo: str
    horarios_aulas: List[IntervaloHorario] = []

    def possui_aula_no_horario(self, inicio: datetime, fim: datetime) -> bool:
        if fim <= inicio:
            return False

        dia_atual = inicio.date()
        ultimo_dia = fim.date()
        tz = inicio.tzinfo

        while dia_atual <= ultimo_dia:
            for intervalo in self.horarios_aulas:
                aula_inicio = datetime.combine(dia_atual, intervalo.inicio, tzinfo=tz)
                aula_fim = datetime.combine(dia_atual, intervalo.fim, tzinfo=tz)
                if inicio < aula_fim and fim > aula_inicio:
                    return True
            dia_atual += timedelta(days=1)

        return False
