from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from .service import AgendamentoService, ConflitoAgendaUsuarioError


class SolicitarReservaDTO(BaseModel):
    usuario_id: str
    sala_id: str
    inicio: datetime
    fim: datetime
    qtd_pessoas: int


class AgendamentoController:
    def __init__(self, agendamento_service: AgendamentoService):
        self.agendamento_service = agendamento_service
        self.router = self._criar_router()

    def _criar_router(self) -> APIRouter:
        router = APIRouter()
        service = self.agendamento_service

        @router.get("/salas", tags=["Salas"])
        def listar_salas(
            usuario_id: str,
            inicio: Optional[datetime] = None,
            fim: Optional[datetime] = None,
        ):
            try:
                return service.listar_salas_disponiveis(usuario_id, inicio, fim)
            except ValueError as e:
                status = 403 if "vínculo" in str(e).lower() else 400
                raise HTTPException(status_code=status, detail=str(e))

        @router.patch("/salas/{sala_id}/bloqueio", tags=["Gestor / Salas"])
        def alterar_bloqueio_sala(
            sala_id: str,
            gestor_id: str,
            bloqueada: bool,
            request: Request,
        ):
            try:
                ip = request.client.host if request.client else "unknown"
                return service.alterar_bloqueio_sala(gestor_id, sala_id, bloqueada, ip)
            except PermissionError as e:
                raise HTTPException(status_code=403, detail=str(e))
            except LookupError as e:
                raise HTTPException(status_code=404, detail=str(e))
            except ValueError as e:
                raise HTTPException(status_code=403, detail=str(e))

        @router.post("/reservas", status_code=201, tags=["Reservas"])
        def solicitar_reserva(dados: SolicitarReservaDTO, request: Request):
            try:
                ip = request.client.host if request.client else "unknown"
                return service.solicitar_reserva(
                    dados.usuario_id,
                    dados.sala_id,
                    dados.inicio,
                    dados.fim,
                    dados.qtd_pessoas,
                    ip,
                )
            except ConflitoAgendaUsuarioError as e:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "codigo": "CONFLITO_AGENDA_USUARIO",
                        "mensagem": str(e),
                        "reserva_atual_id": e.reserva_atual_id,
                        "acao_sugerida": (
                            f"Use POST /reservas/{e.reserva_atual_id}/troca "
                            "para substituir atomicamente."
                        ),
                    },
                )
            except FileExistsError:
                raise HTTPException(
                    status_code=409, detail="Sala já reservada neste horário."
                )
            except PermissionError as e:
                raise HTTPException(status_code=403, detail=str(e))
            except LookupError as e:
                raise HTTPException(status_code=404, detail=str(e))
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))

        @router.post("/reservas/{reserva_antiga_id}/troca", tags=["Reservas"])
        def trocar_reserva(
            reserva_antiga_id: str,
            novos_dados: SolicitarReservaDTO,
            request: Request,
        ):
            try:
                ip = request.client.host if request.client else "unknown"
                return service.trocar_reserva(
                    reserva_antiga_id,
                    novos_dados.usuario_id,
                    novos_dados.sala_id,
                    novos_dados.inicio,
                    novos_dados.fim,
                    novos_dados.qtd_pessoas,
                    ip,
                )
            except ConflitoAgendaUsuarioError as e:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "codigo": "CONFLITO_AGENDA_USUARIO",
                        "mensagem": str(e),
                        "reserva_atual_id": e.reserva_atual_id,
                    },
                )
            except FileExistsError:
                raise HTTPException(
                    status_code=409, detail="Sala já reservada neste horário."
                )
            except PermissionError as e:
                raise HTTPException(status_code=403, detail=str(e))
            except LookupError as e:
                raise HTTPException(status_code=404, detail=str(e))
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))

        @router.post("/reservas/{reserva_id}/cancelar", tags=["Reservas"])
        def cancelar_reserva(reserva_id: str, usuario_id: str, request: Request):
            try:
                ip = request.client.host if request.client else "unknown"
                return service.cancelar_reserva(reserva_id, usuario_id, ip)
            except PermissionError as e:
                raise HTTPException(status_code=403, detail=str(e))
            except LookupError as e:
                raise HTTPException(status_code=404, detail=str(e))
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))

        @router.post("/reservas/{reserva_id}/avaliar", tags=["Gestor / Aprovação"])
        def avaliar_reserva(
            reserva_id: str,
            aprovador_id: str,
            aprovada: bool,
            request: Request,
        ):
            try:
                ip = request.client.host if request.client else "unknown"
                return service.avaliar_reserva_pendente(
                    reserva_id, aprovador_id, aprovada, ip
                )
            except PermissionError as e:
                raise HTTPException(status_code=403, detail=str(e))
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))

        @router.get("/auditoria", tags=["Auditoria (ASR 2)"])
        def listar_logs(gestor_id: str, entidade_id: Optional[str] = None):
            try:
                return service.listar_logs_auditoria(gestor_id, entidade_id)
            except PermissionError as e:
                raise HTTPException(status_code=403, detail=str(e))
            except ValueError as e:
                raise HTTPException(status_code=403, detail=str(e))

        return router
