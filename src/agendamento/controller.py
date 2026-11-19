from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from auditoria.interfaces import IAuditoriaRepository
from .service import AgendamentoService, ConflitoAgendaUsuarioError

class SolicitarReservaDTO(BaseModel):
    usuario_id: str
    sala_id: str
    inicio: datetime
    fim: datetime
    qtd_pessoas: int

def criar_router(service: AgendamentoService, audit_repo: IAuditoriaRepository) -> APIRouter:
    router = APIRouter()

    @router.get("/salas", tags=["Salas"])
    def listar_salas(usuario_id: str):
        try:
            return service.listar_salas_disponiveis(usuario_id)
        except ValueError as e:
            raise HTTPException(status_code=403, detail=str(e))

    @router.post("/reservas", tags=["Reservas"])
    def solicitar_reserva(dados: SolicitarReservaDTO, request: Request):
        try:
            return service.solicitar_reserva(
                dados.usuario_id, dados.sala_id, dados.inicio, dados.fim, dados.qtd_pessoas, request.client.host
            )
        except ConflitoAgendaUsuarioError as e:
            raise HTTPException(
                status_code=409,
                detail={
                    "codigo": "CONFLITO_AGENDA_USUARIO",
                    "mensagem": str(e),
                    "reserva_atual_id": e.reserva_atual_id,
                    "acao_sugerida": f"Use POST /reservas/{e.reserva_atual_id}/troca para substituir atomicamente.",
                },
            )
        except FileExistsError:
            raise HTTPException(status_code=409, detail="Sala já reservada neste horário.")
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except LookupError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/reservas/{reserva_antiga_id}/troca", tags=["Reservas"])
    def trocar_reserva(reserva_antiga_id: str, novos_dados: SolicitarReservaDTO, request: Request):
        try:
            return service.trocar_reserva(
                reserva_antiga_id,
                novos_dados.usuario_id,
                novos_dados.sala_id,
                novos_dados.inicio,
                novos_dados.fim,
                novos_dados.qtd_pessoas,
                request.client.host,
            )
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except LookupError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except (ValueError, FileExistsError) as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/reservas/{reserva_id}/cancelar", tags=["Reservas"])
    def cancelar_reserva(reserva_id: str, usuario_id: str, request: Request):
        try:
            return service.cancelar_reserva(reserva_id, usuario_id, request.client.host)
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except LookupError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @router.post("/reservas/{reserva_id}/avaliar", tags=["Gestor / Aprovação"])
    def avaliar_reserva(reserva_id: str, aprovador_id: str, aprovada: bool, request: Request):
        try:
            return service.avaliar_reserva_pendente(reserva_id, aprovador_id, aprovada, request.client.host)
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.get("/auditoria", tags=["Auditoria (ASR 2)"])
    def listar_logs():
        return audit_repo.listar_todos()

    return router
