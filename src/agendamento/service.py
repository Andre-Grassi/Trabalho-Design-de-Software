import logging
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime
from typing import List, Optional
from src.auditoria.domain import EventoAuditoria
from src.auditoria.interfaces import IAuditoriaService
from src.autenticacao.domain import Usuario
from src.autenticacao.interfaces import IAutenticacaoService
from src.integracao_academica.interfaces import IGradeAcademicaService
from src.notificacao.interfaces import INotificador
from .domain import Reserva, Sala, StatusReserva, normalizar_datetime
from .interfaces import IPoliticaRepository, IReservaRepository, ISalaRepository

logger = logging.getLogger(__name__)


class ConflitoAgendaUsuarioError(Exception):
    def __init__(self, reserva_atual_id: str):
        self.reserva_atual_id = reserva_atual_id
        super().__init__(
            f"Usuário já possui a reserva ativa {reserva_atual_id} neste horário."
        )


class AgendamentoService:
    def __init__(
        self,
        reserva_repo: IReservaRepository,
        sala_repo: ISalaRepository,
        politica_repo: IPoliticaRepository,
        auth_service: IAutenticacaoService,
        audit_service: IAuditoriaService,
        grade_service: IGradeAcademicaService,
        notificador: INotificador,
        notificacao_assincrona: bool = True,
    ):
        self.reserva_repo = reserva_repo
        self.sala_repo = sala_repo
        self.politica_repo = politica_repo
        self.auth_service = auth_service
        self.audit_service = audit_service
        self.grade_service = grade_service
        self.notificador = notificador
        self.notificacao_assincrona = notificacao_assincrona
        self._notif_executor = ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="notificacao"
        )
        self._notif_pendentes: List[Future] = []

    def _enviar_notificacao_segura(self, usuario: Usuario, reserva: Reserva) -> None:
        try:
            self.notificador.enviar_notificacao(usuario, reserva)
        except Exception:
            logger.exception("Falha ao enviar notificação da reserva %s", reserva.id)

    def _notificar(self, usuario: Usuario, reserva: Reserva) -> None:
        if self.notificacao_assincrona:
            self._notif_pendentes = [f for f in self._notif_pendentes if not f.done()]
            future = self._notif_executor.submit(
                self._enviar_notificacao_segura, usuario, reserva
            )
            self._notif_pendentes.append(future)
        else:
            self.notificador.enviar_notificacao(usuario, reserva)

    def aguardar_notificacoes(self) -> None:
        for future in list(self._notif_pendentes):
            future.result()
        self._notif_pendentes.clear()

    def listar_salas_disponiveis(
        self,
        usuario_id: str,
        inicio: Optional[datetime] = None,
        fim: Optional[datetime] = None,
    ) -> List[Sala]:
        usuario = self.auth_service.validar_vinculo(usuario_id)
        politica = self.politica_repo.obter_politica_por_perfil(usuario.perfil)
        salas = self.sala_repo.listar_por_nivel_maximo(politica.nivel_permissao)

        if inicio is None or fim is None:
            return salas

        ini = normalizar_datetime(inicio)
        termino = normalizar_datetime(fim)
        if termino <= ini:
            raise ValueError("O horário final deve ser posterior ao inicial.")

        disponiveis: List[Sala] = []
        for sala in salas:
            if sala.esta_bloqueada():
                continue
            grade = self.grade_service.obter_grade_da_sala(sala.id)
            if grade.possui_aula_no_horario(ini, termino):
                continue
            conflitos = self.reserva_repo.buscar_por_sala_e_periodo(sala.id, ini, termino)
            if not conflitos:
                disponiveis.append(sala)
        return disponiveis

    def alterar_bloqueio_sala(
        self, gestor_id: str, sala_id: str, bloqueada: bool, ip: str
    ) -> Sala:
        if not self.auth_service.possui_permissao_gestor(gestor_id):
            raise PermissionError(
                "Apenas gestores podem alterar o bloqueio operacional da sala."
            )
        sala = self.sala_repo.buscar_por_id(sala_id)
        if not sala:
            raise LookupError("Sala não encontrada.")

        sala.alterar_bloqueio(bloqueada)
        self.sala_repo.atualizar(sala)
        acao = "BLOQUEIO_SALA" if bloqueada else "DESBLOQUEIO_SALA"
        self.audit_service.registrar(
            EventoAuditoria(acao=acao, usuario_id=gestor_id, entidade_id=sala.id, ip=ip)
        )
        return sala

    def solicitar_reserva(
        self,
        usuario_id: str,
        sala_id: str,
        inicio: datetime,
        fim: datetime,
        qtd_pessoas: int,
        ip: str,
    ) -> Reserva:
        usuario = self.auth_service.validar_vinculo(usuario_id)
        sala = self.sala_repo.buscar_por_id(sala_id)
        if not sala:
            raise LookupError("Sala não encontrada.")
        politica = self.politica_repo.obter_politica_por_perfil(usuario.perfil)
        grade = self.grade_service.obter_grade_da_sala(sala_id)

        ini = normalizar_datetime(inicio)
        termino = normalizar_datetime(fim)

        with self.reserva_repo.transacao_exclusiva():
            reservas_sala = self.reserva_repo.buscar_por_sala_e_periodo(
                sala_id, ini, termino
            )
            reservas_usuario = self.reserva_repo.buscar_ativas_por_usuario(usuario_id)

            politica.validar_solicitacao(
                usuario, sala, ini, termino, qtd_pessoas, grade, reservas_sala
            )
            politica.validar_cota_reservas_ativas(reservas_usuario)

            conflito_id = politica.validar_conflito_agenda_usuario(
                ini, termino, reservas_usuario
            )
            if conflito_id:
                raise ConflitoAgendaUsuarioError(conflito_id)

            status_inicial = politica.definir_status_inicial(usuario, sala)
            nova = Reserva(
                id=f"res-{uuid.uuid4().hex[:8]}",
                usuario_id=usuario.id,
                sala_id=sala.id,
                inicio=ini,
                fim=termino,
                qtd_pessoas=qtd_pessoas,
                status=status_inicial,
            )
            self.reserva_repo.salvar(nova)

        self.audit_service.registrar(
            EventoAuditoria(
                acao=f"RESERVA_{nova.status.value}",
                usuario_id=usuario.id,
                entidade_id=nova.id,
                ip=ip,
            )
        )
        self._notificar(usuario, nova)
        return nova

    def trocar_reserva(
        self,
        reserva_antiga_id: str,
        usuario_id: str,
        nova_sala_id: str,
        inicio: datetime,
        fim: datetime,
        qtd_pessoas: int,
        ip: str,
    ) -> Reserva:
        usuario = self.auth_service.validar_vinculo(usuario_id)
        nova_sala = self.sala_repo.buscar_por_id(nova_sala_id)
        if not nova_sala:
            raise LookupError("Nova sala não encontrada.")

        politica = self.politica_repo.obter_politica_por_perfil(usuario.perfil)
        grade = self.grade_service.obter_grade_da_sala(nova_sala_id)

        ini = normalizar_datetime(inicio)
        termino = normalizar_datetime(fim)

        with self.reserva_repo.transacao_exclusiva():
            antiga = self.reserva_repo.buscar_por_id(reserva_antiga_id)
            if not antiga or antiga.usuario_id != usuario.id:
                raise LookupError("Reserva anterior não encontrada para este usuário.")
            if not antiga.esta_ativa():
                raise ValueError(
                    "A reserva anterior não está ativa e não pode ser substituída."
                )

            reservas_sala = [
                r
                for r in self.reserva_repo.buscar_por_sala_e_periodo(
                    nova_sala_id, ini, termino
                )
                if r.id != antiga.id
            ]
            politica.validar_solicitacao(
                usuario, nova_sala, ini, termino, qtd_pessoas, grade, reservas_sala
            )

            outras_reservas_usuario = [
                r
                for r in self.reserva_repo.buscar_ativas_por_usuario(usuario_id)
                if r.id != antiga.id
            ]
            conflito_id = politica.validar_conflito_agenda_usuario(
                ini, termino, outras_reservas_usuario
            )
            if conflito_id:
                raise ConflitoAgendaUsuarioError(conflito_id)

            status_inicial = politica.definir_status_inicial(usuario, nova_sala)
            antiga.cancelar()
            nova = Reserva(
                id=f"res-{uuid.uuid4().hex[:8]}",
                usuario_id=usuario.id,
                sala_id=nova_sala.id,
                inicio=ini,
                fim=termino,
                qtd_pessoas=qtd_pessoas,
                status=status_inicial,
            )
            self.reserva_repo.substituir_atomicamente(antiga, nova)

        self.audit_service.registrar(
            EventoAuditoria(
                acao="TROCA_ATOMICA",
                usuario_id=usuario.id,
                entidade_id=f"{antiga.id}->{nova.id}",
                ip=ip,
            )
        )
        self._notificar(usuario, nova)
        return nova

    def cancelar_reserva(self, reserva_id: str, usuario_id: str, ip: str) -> Reserva:
        usuario = self.auth_service.validar_vinculo(usuario_id)
        politica = self.politica_repo.obter_politica_por_perfil(usuario.perfil)

        with self.reserva_repo.transacao_exclusiva():
            reserva = self.reserva_repo.buscar_por_id(reserva_id)
            if not reserva:
                raise LookupError("Reserva não encontrada.")
            if reserva.usuario_id != usuario.id and not usuario.pode_aprovar_laboratorio():
                raise PermissionError("Sem permissão para cancelar esta reserva.")
            if not reserva.esta_ativa():
                raise ValueError("A reserva já está cancelada ou rejeitada.")
            if not politica.pode_cancelar(reserva, usuario):
                raise ValueError(
                    "Não é possível cancelar uma reserva após o horário de início."
                )

            reserva.cancelar()
            self.reserva_repo.salvar(reserva)

        self.audit_service.registrar(
            EventoAuditoria(
                acao="CANCELAMENTO_RESERVA",
                usuario_id=usuario.id,
                entidade_id=reserva.id,
                ip=ip,
            )
        )
        destinatario = (
            usuario
            if reserva.usuario_id == usuario.id
            else self.auth_service.validar_vinculo(reserva.usuario_id)
        )
        self._notificar(destinatario, reserva)
        return reserva

    def avaliar_reserva_pendente(
        self, reserva_id: str, aprovador_id: str, aprovada: bool, ip: str
    ) -> Reserva:
        if not self.auth_service.possui_permissao_gestor(aprovador_id):
            raise PermissionError(
                "Apenas gestores/técnicos podem aprovar ou rejeitar reservas."
            )

        with self.reserva_repo.transacao_exclusiva():
            reserva = self.reserva_repo.buscar_por_id(reserva_id)
            if not reserva or reserva.status != StatusReserva.PENDENTE:
                raise ValueError("Reserva inexistente ou não está pendente.")

            if aprovada:
                reserva.confirmar()
                acao = "APROVACAO_RESERVA"
            else:
                reserva.rejeitar()
                acao = "REJEICAO_RESERVA"

            self.reserva_repo.salvar(reserva)

        self.audit_service.registrar(
            EventoAuditoria(
                acao=acao,
                usuario_id=aprovador_id,
                entidade_id=reserva.id,
                ip=ip,
            )
        )
        solicitante = self.auth_service.validar_vinculo(reserva.usuario_id)
        self._notificar(solicitante, reserva)
        return reserva

    def listar_logs_auditoria(
        self, gestor_id: str, entidade_id: Optional[str] = None
    ) -> List[EventoAuditoria]:
        if not self.auth_service.possui_permissao_gestor(gestor_id):
            raise PermissionError(
                "Apenas gestores podem consultar a trilha de auditoria."
            )
        if entidade_id:
            return self.audit_service.buscar_por_entidade(entidade_id)
        return self.audit_service.listar_todos()
