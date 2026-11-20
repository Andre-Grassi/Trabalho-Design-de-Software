from datetime import timedelta


class TestSalasAPI:
    def test_listar_salas_respeita_perfil_rf4(self, client):
        r_aluno = client.get("/salas", params={"usuario_id": "u2"})
        assert r_aluno.status_code == 200
        assert {s["id"] for s in r_aluno.json()} == {"s1", "s2"}

        r_docente = client.get("/salas", params={"usuario_id": "u1"})
        assert r_docente.status_code == 200
        assert {s["id"] for s in r_docente.json()} == {"s1", "s2", "s3"}

    def test_listar_salas_usuario_inexistente_retorna_403(self, client):
        resp = client.get("/salas", params={"usuario_id": "inexistente"})
        assert resp.status_code == 403

    def test_listar_salas_filtra_disponibilidade_por_horario(self, client, dia_futuro):
        # Em 08h-10h, s1 possui aula oficial na Grade Acadêmica
        resp = client.get(
            "/salas",
            params={
                "usuario_id": "u1",
                "inicio": dia_futuro.replace(hour=8, minute=30).isoformat(),
                "fim": dia_futuro.replace(hour=9, minute=30).isoformat(),
            },
        )
        assert resp.status_code == 200
        assert {s["id"] for s in resp.json()} == {"s2", "s3"}

    def test_gestor_bloqueia_sala_para_manutencao(self, client, dia_futuro):
        # Aluno não pode bloquear
        r_forb = client.patch(
            "/salas/s2/bloqueio", params={"gestor_id": "u2", "bloqueada": "true"}
        )
        assert r_forb.status_code == 403

        # Gestor bloqueia s2
        r_ok = client.patch(
            "/salas/s2/bloqueio", params={"gestor_id": "u3", "bloqueada": "true"}
        )
        assert r_ok.status_code == 200
        assert r_ok.json()["bloqueada_manutencao"] is True

        # Tentativa de reservar sala bloqueada retorna 400
        r_res = client.post(
            "/reservas",
            json={
                "usuario_id": "u1",
                "sala_id": "s2",
                "inicio": dia_futuro.replace(hour=10).isoformat(),
                "fim": dia_futuro.replace(hour=12).isoformat(),
                "qtd_pessoas": 10,
            },
        )
        assert r_res.status_code == 400
        assert "bloqueado" in r_res.json()["detail"].lower()


class TestReservasAPI:
    def test_fluxo_completo_docente_conflito_troca_e_cancelamento(self, client, dia_futuro):
        # 1. Docente reserva s1 (10h-12h) -> 201 Created, CONFIRMADA
        r1 = client.post(
            "/reservas",
            json={
                "usuario_id": "u1",
                "sala_id": "s1",
                "inicio": dia_futuro.replace(hour=10).isoformat(),
                "fim": dia_futuro.replace(hour=12).isoformat(),
                "qtd_pessoas": 20,
            },
        )
        assert r1.status_code == 201
        res_id = r1.json()["id"]
        assert r1.json()["status"] == "CONFIRMADA"

        # 2. Outro usuário tenta mesma sala e horário -> 409 Conflict
        r_ocup = client.post(
            "/reservas",
            json={
                "usuario_id": "u3",
                "sala_id": "s1",
                "inicio": dia_futuro.replace(hour=11).isoformat(),
                "fim": dia_futuro.replace(hour=13).isoformat(),
                "qtd_pessoas": 10,
            },
        )
        assert r_ocup.status_code == 409

        # 3. Mesmo docente tenta outra sala no horário sobreposto -> 409 com ação sugerida (RF 5)
        r_conf = client.post(
            "/reservas",
            json={
                "usuario_id": "u1",
                "sala_id": "s2",
                "inicio": dia_futuro.replace(hour=11).isoformat(),
                "fim": dia_futuro.replace(hour=13).isoformat(),
                "qtd_pessoas": 10,
            },
        )
        assert r_conf.status_code == 409
        assert r_conf.json()["detail"]["codigo"] == "CONFLITO_AGENDA_USUARIO"
        assert r_conf.json()["detail"]["reserva_atual_id"] == res_id

        # 4. Troca atômica -> 200 OK
        r_troca = client.post(
            f"/reservas/{res_id}/troca",
            json={
                "usuario_id": "u1",
                "sala_id": "s2",
                "inicio": dia_futuro.replace(hour=11).isoformat(),
                "fim": dia_futuro.replace(hour=13).isoformat(),
                "qtd_pessoas": 10,
            },
        )
        assert r_troca.status_code == 200
        nova_id = r_troca.json()["id"]
        assert r_troca.json()["status"] == "CONFIRMADA"

        # 5. Outro usuário não pode cancelar reserva alheia -> 403
        r_canc_forb = client.post(
            f"/reservas/{nova_id}/cancelar", params={"usuario_id": "u2"}
        )
        assert r_canc_forb.status_code == 403

        # 6. Dono cancela -> 200 OK; cancelar de novo -> 400
        r_canc = client.post(
            f"/reservas/{nova_id}/cancelar", params={"usuario_id": "u1"}
        )
        assert r_canc.status_code == 200
        assert r_canc.json()["status"] == "CANCELADA"

        r_canc2 = client.post(
            f"/reservas/{nova_id}/cancelar", params={"usuario_id": "u1"}
        )
        assert r_canc2.status_code == 400

    def test_fluxo_aprovacao_e_rejeicao_estudante_rf9(self, client, dia_futuro):
        # Aluno reserva s2 -> PENDENTE
        r1 = client.post(
            "/reservas",
            json={
                "usuario_id": "u2",
                "sala_id": "s2",
                "inicio": dia_futuro.replace(hour=10).isoformat(),
                "fim": dia_futuro.replace(hour=12).isoformat(),
                "qtd_pessoas": 10,
            },
        )
        assert r1.status_code == 201
        res_id = r1.json()["id"]
        assert r1.json()["status"] == "PENDENTE"

        # Docente não tem perfil GESTOR para aprovar -> 403
        r_forb = client.post(
            f"/reservas/{res_id}/avaliar",
            params={"aprovador_id": "u1", "aprovada": "true"},
        )
        assert r_forb.status_code == 403

        # Gestor aprova -> CONFIRMADA
        r_ok = client.post(
            f"/reservas/{res_id}/avaliar",
            params={"aprovador_id": "u3", "aprovada": "true"},
        )
        assert r_ok.status_code == 200
        assert r_ok.json()["status"] == "CONFIRMADA"

        # Reavaliar reserva já confirmada -> 400
        r_dup = client.post(
            f"/reservas/{res_id}/avaliar",
            params={"aprovador_id": "u3", "aprovada": "false"},
        )
        assert r_dup.status_code == 400

        # Aluno faz segunda reserva e gestor rejeita -> REJEITADA
        r2 = client.post(
            "/reservas",
            json={
                "usuario_id": "u2",
                "sala_id": "s2",
                "inicio": dia_futuro.replace(hour=14).isoformat(),
                "fim": dia_futuro.replace(hour=16).isoformat(),
                "qtd_pessoas": 10,
            },
        )
        res2_id = r2.json()["id"]
        r_rej = client.post(
            f"/reservas/{res2_id}/avaliar",
            params={"aprovador_id": "u3", "aprovada": "false"},
        )
        assert r_rej.status_code == 200
        assert r_rej.json()["status"] == "REJEITADA"

    def test_validacoes_de_erro_http(self, client, dia_futuro):
        # Sala inexistente -> 404
        r_404 = client.post(
            "/reservas",
            json={
                "usuario_id": "u1",
                "sala_id": "s999",
                "inicio": dia_futuro.replace(hour=10).isoformat(),
                "fim": dia_futuro.replace(hour=12).isoformat(),
                "qtd_pessoas": 5,
            },
        )
        assert r_404.status_code == 404

        # Aluno tentando laboratório restrito s3 -> 403
        r_403 = client.post(
            "/reservas",
            json={
                "usuario_id": "u2",
                "sala_id": "s3",
                "inicio": dia_futuro.replace(hour=10).isoformat(),
                "fim": dia_futuro.replace(hour=12).isoformat(),
                "qtd_pessoas": 5,
            },
        )
        assert r_403.status_code == 403

        # Conflito com Grade Acadêmica (s1 08h-10h) -> 400
        r_grade = client.post(
            "/reservas",
            json={
                "usuario_id": "u1",
                "sala_id": "s1",
                "inicio": dia_futuro.replace(hour=7, minute=30).isoformat(),
                "fim": dia_futuro.replace(hour=8, minute=30).isoformat(),
                "qtd_pessoas": 10,
            },
        )
        assert r_grade.status_code == 400
        assert "Grade Acadêmica" in r_grade.json()["detail"]

        # Cota máxima de reservas ativas para aluno (máximo 2) -> 3ª retorna 400
        for hora in (10, 13):
            ok = client.post(
                "/reservas",
                json={
                    "usuario_id": "u2",
                    "sala_id": "s2",
                    "inicio": dia_futuro.replace(hour=hora).isoformat(),
                    "fim": (dia_futuro.replace(hour=hora) + timedelta(hours=2)).isoformat(),
                    "qtd_pessoas": 5,
                },
            )
            assert ok.status_code == 201

        r_cota = client.post(
            "/reservas",
            json={
                "usuario_id": "u2",
                "sala_id": "s2",
                "inicio": dia_futuro.replace(hour=16).isoformat(),
                "fim": dia_futuro.replace(hour=18).isoformat(),
                "qtd_pessoas": 5,
            },
        )
        assert r_cota.status_code == 400
        assert "Limite máximo" in r_cota.json()["detail"]


class TestAuditoriaAPI:
    def test_acesso_restrito_a_gestor_e_filtro_por_entidade_asr2(self, client, dia_futuro):
        r_res = client.post(
            "/reservas",
            json={
                "usuario_id": "u2",
                "sala_id": "s2",
                "inicio": dia_futuro.replace(hour=10).isoformat(),
                "fim": dia_futuro.replace(hour=12).isoformat(),
                "qtd_pessoas": 8,
            },
        )
        res_id = r_res.json()["id"]
        client.post(
            f"/reservas/{res_id}/avaliar",
            params={"aprovador_id": "u3", "aprovada": "true"},
        )

        # Aluno e docente não podem ler auditoria
        assert client.get("/auditoria", params={"gestor_id": "u2"}).status_code == 403
        assert client.get("/auditoria", params={"gestor_id": "u1"}).status_code == 403

        # Gestor visualiza todos os logs e filtra por entidade
        r_todos = client.get("/auditoria", params={"gestor_id": "u3"})
        assert r_todos.status_code == 200
        assert len(r_todos.json()) >= 2

        r_ent = client.get(
            "/auditoria", params={"gestor_id": "u3", "entidade_id": res_id}
        )
        assert r_ent.status_code == 200
        acoes = [log["acao"] for log in r_ent.json()]
        assert "RESERVA_PENDENTE" in acoes
        assert "APROVACAO_RESERVA" in acoes
