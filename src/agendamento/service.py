import uuid
from datetime import datetime
from typing import List
from database import get_connection
from autenticacao.interfaces import IAutenticacaoService
from auditoria.interfaces import IAuditoriaService
from integracao_academica.interfaces import IGradeAcademicaService
from notificacao.interfaces import INotificador
from .domain import Reserva, Sala, StatusReserva
from .interfaces import IReservaRepository, ISalaRepository, IPoliticaRepository

class ConflitoAgendaUsuarioError(Exception):
    def __init__(self, reserva_atual_id: str):
        self.reserva_atual_id = reserva_atual_id
        super().__init__(f"Usuário já possui a reserva ativa {reserva_atual_id} neste horário.")

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
    ):
        self.reserva_repo = reserva_repo
        self.sala_repo = sala_repo
        self.politica_repo = politica_repo
        self.auth_service = auth_service
        self.audit_service = audit_service
        self.grade_service = grade_service
        self.notificador = notificador

    def listar_salas_disponiveis(self, usuario_id: str) -> List[Sala]:
        usuario = self.auth_service.validar_vinculo(usuario_id)
        politica = self.politica_repo.obter_politica_por_perfil(usuario.perfil)
        return self.sala_repo.listar_por_nivel_maximo(politica.nivel_permissao)

    def solicitar_reserva(
        self, usuario_id: str, sala_id: str, inicio: datetime, fim: datetime, qtd_pessoas: int, ip: str
    ) -> Reserva:
        usuario = self.auth_service.validar_vinculo(usuario_id)
        sala = self.sala_repo.buscar_por_id(sala_id)
        if not sala:
            raise LookupError("Sala não encontrada.")
        politica = self.politica_repo.obter_politica_por_perfil(usuario.perfil)
        tem_aula = self.grade_service.possui_aula_no_horario(sala_id, inicio, fim)

        conn = get_connection()
        try:
            conn.execute("BEGIN EXCLUSIVE")  # Lock pessimista ACID (ASR 1)
            reservas_sala = self.reserva_repo.buscar_por_sala_e_periodo(sala_id, inicio, fim, conn=conn)
            reservas_usuario = self.reserva_repo.buscar_ativas_por_usuario(usuario_id, conn=conn)

            politica.validar_solicitacao(usuario, sala, inicio, fim, qtd_pessoas, tem_aula, reservas_sala)
            politica.validar_cota_reservas_ativas(reservas_usuario)

            conflito_id = politica.validar_conflito_agenda_usuario(inicio, fim, reservas_usuario)
            if conflito_id:
                raise ConflitoAgendaUsuarioError(conflito_id)

            status_inicial = politica.definir_status_inicial(usuario, sala)
            nova = Reserva(
                id=f"res-{uuid.uuid4().hex[:8]}",
                usuario_id=usuario.id,
                sala_id=sala.id,
                inicio=inicio,
                fim=fim,
                qtd_pessoas=qtd_pessoas,
                status=status_inicial,
            )
            self.reserva_repo.salvar(nova, conn=conn)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

        self.audit_service.registrar(usuario.id, f"RESERVA_{nova.status.value}", nova.id, ip)
        self.notificador.enviar_notificacao(usuario, f"Reserva {nova.id} ({sala.codigo}) registrada com status {nova.status.value}.")
        return nova

    def trocar_reserva(
        self, reserva_antiga_id: str, usuario_id: str, nova_sala_id: str, inicio: datetime, fim: datetime, qtd_pessoas: int, ip: str
    ) -> Reserva:
        usuario = self.auth_service.validar_vinculo(usuario_id)
        antiga = self.reserva_repo.buscar_por_id(reserva_antiga_id)
        if not antiga or antiga.usuario_id != usuario.id:
            raise LookupError("Reserva anterior não encontrada para este usuário.")

        nova_sala = self.sala_repo.buscar_por_id(nova_sala_id)
        if not nova_sala:
            raise LookupError("Nova sala não encontrada.")

        politica = self.politica_repo.obter_politica_por_perfil(usuario.perfil)
        tem_aula = self.grade_service.possui_aula_no_horario(nova_sala_id, inicio, fim)

        conn = get_connection()
        try:
            conn.execute("BEGIN EXCLUSIVE")
            reservas_sala = self.reserva_repo.buscar_por_sala_e_periodo(nova_sala_id, inicio, fim, conn=conn)
            politica.validar_solicitacao(usuario, nova_sala, inicio, fim, qtd_pessoas, tem_aula, reservas_sala)

            status_inicial = politica.definir_status_inicial(usuario, nova_sala)
            nova = Reserva(
                id=f"res-{uuid.uuid4().hex[:8]}",
                usuario_id=usuario.id,
                sala_id=nova_sala.id,
                inicio=inicio,
                fim=fim,
                qtd_pessoas=qtd_pessoas,
                status=status_inicial,
            )
            self.reserva_repo.substituir_atomicamente(antiga, nova, conn=conn)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

        self.audit_service.registrar(usuario.id, "TROCA_ATOMICA", f"{antiga.id}->{nova.id}", ip)
        self.notificador.enviar_notificacao(usuario, f"Troca atômica concluída: {antiga.id} cancelada e {nova.id} ({nova.status.value}) criada.")
        return nova

    def cancelar_reserva(self, reserva_id: str, usuario_id: str, ip: str) -> Reserva:
        usuario = self.auth_service.validar_vinculo(usuario_id)
        reserva = self.reserva_repo.buscar_por_id(reserva_id)
        if not reserva:
            raise LookupError("Reserva não encontrada.")
        if reserva.usuario_id != usuario.id and not usuario.pode_aprovar_laboratorio():
            raise PermissionError("Sem permissão para cancelar esta reserva.")

        reserva.cancelar()
        self.reserva_repo.salvar(reserva)
        self.audit_service.registrar(usuario.id, "CANCELAMENTO_RESERVA", reserva.id, ip)
        self.notificador.enviar_notificacao(usuario, f"Reserva {reserva.id} foi CANCELADA.")
        return reserva

    def avaliar_reserva_pendente(self, reserva_id: str, aprovador_id: str, aprovada: bool, ip: str) -> Reserva:
        if not self.auth_service.possui_permissao_gestor(aprovador_id):
            raise PermissionError("Apenas gestores/técnicos podem aprovar ou rejeitar reservas.")
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
        self.audit_service.registrar(aprovador_id, acao, reserva.id, ip)
        solicitante = self.auth_service.validar_vinculo(reserva.usuario_id)
        self.notificador.enviar_notificacao(solicitante, f"Sua reserva {reserva.id} foi {reserva.status.value}.")
        return reserva
