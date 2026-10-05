import unittest

from tests.test_seguranca import BaseTeste


class BaseGrupo(BaseTeste):

    def setUp(self):
        super().setUp()
        self.ana, self.token_ana = self.criar_usuario_logado("Ana Silva")
        self.bia, self.token_bia = self.criar_usuario_logado("Bia Costa")
        self.cris, self.token_cris = self.criar_usuario_logado("Cris Lima")

    def criar_grupo(self, token, nome="Grupo Teste", descricao="Descrição do grupo"):
        resposta = self.cli.post(
            "/api/grupos", json={"nome": nome, "descricao": descricao}, headers=self.auth(token)
        )
        self.assertEqual(resposta.status_code, 201, resposta.get_data(as_text=True))
        return resposta.get_json()["grupo"]

    def convite_recebido(self, token):
        return self.cli.get("/api/convites", headers=self.auth(token)).get_json()["pendentes"][0]


class TestCriarGrupo(BaseGrupo):

    def test_cria_grupo_e_criador_vira_admin(self):
        grupo = self.criar_grupo(self.token_ana)
        meus = self.cli.get("/api/grupos", headers=self.auth(self.token_ana)).get_json()
        self.assertEqual(len(meus), 1)
        self.assertEqual(meus[0]["meu_papel"], "admin")
        self.assertEqual(meus[0]["membros"], 1)
        self.assertEqual(meus[0]["nome"], grupo["nome"])

    def test_exige_nome(self):
        resposta = self.cli.post(
            "/api/grupos", json={"nome": "  ", "descricao": "x"}, headers=self.auth(self.token_ana)
        )
        self.assertEqual(resposta.status_code, 400)

    def test_nome_acima_do_limite_e_recusado(self):
        resposta = self.cli.post(
            "/api/grupos", json={"nome": "x" * 51}, headers=self.auth(self.token_ana)
        )
        self.assertEqual(resposta.status_code, 400)

    def test_descricao_acima_do_limite_e_recusada(self):
        resposta = self.cli.post(
            "/api/grupos", json={"nome": "Grupo", "descricao": "x" * 301}, headers=self.auth(self.token_ana)
        )
        self.assertEqual(resposta.status_code, 400)

    def test_cada_grupo_recebe_um_codigo_de_convite_diferente(self):
        self.criar_grupo(self.token_ana, nome="Grupo 1")
        self.criar_grupo(self.token_ana, nome="Grupo 2")
        meus = self.cli.get("/api/grupos", headers=self.auth(self.token_ana)).get_json()
        codigos = [
            self.cli.get(f"/api/grupos/{g['id']}/convite", headers=self.auth(self.token_ana)).get_json()["codigo"]
            for g in meus
        ]
        self.assertEqual(len(set(codigos)), 2)


class TestAcessoAoGrupo(BaseGrupo):

    def setUp(self):
        super().setUp()
        self.grupo = self.criar_grupo(self.token_ana)

    def test_nao_membro_nao_ve_detalhe_membros_ranking(self):
        alvos = [
            ("get", f"/api/grupos/{self.grupo['id']}"),
            ("get", f"/api/grupos/{self.grupo['id']}/membros"),
            ("get", f"/api/grupos/{self.grupo['id']}/ranking"),
        ]
        for metodo, caminho in alvos:
            with self.subTest(rota=caminho):
                resposta = getattr(self.cli, metodo)(caminho, headers=self.auth(self.token_bia))
                self.assertEqual(resposta.status_code, 403)

    def test_membro_comum_nao_ve_nem_gera_link_de_convite(self):
        self.cli.post(
            f"/api/grupos/{self.grupo['id']}/convites", json={"id_usuario": self.bia["id"]},
            headers=self.auth(self.token_ana),
        )
        id_convite = self.convite_recebido(self.token_bia)["id"]
        self.cli.put(f"/api/convites/{id_convite}", json={"aceito": True}, headers=self.auth(self.token_bia))

        info = self.cli.get(f"/api/grupos/{self.grupo['id']}/convite", headers=self.auth(self.token_bia))
        regenerar = self.cli.post(
            f"/api/grupos/{self.grupo['id']}/convite/regenerar", headers=self.auth(self.token_bia)
        )
        self.assertEqual(info.status_code, 403)
        self.assertEqual(regenerar.status_code, 403)

    def test_admin_ve_e_regenera_o_link(self):
        info = self.cli.get(f"/api/grupos/{self.grupo['id']}/convite", headers=self.auth(self.token_ana))
        self.assertEqual(info.status_code, 200)
        codigo_antigo = info.get_json()["codigo"]

        regenerado = self.cli.post(
            f"/api/grupos/{self.grupo['id']}/convite/regenerar", headers=self.auth(self.token_ana)
        )
        self.assertEqual(regenerado.status_code, 200)
        self.assertNotEqual(regenerado.get_json()["codigo"], codigo_antigo)

    def test_grupo_inexistente_devolve_404(self):
        resposta = self.cli.get("/api/grupos/9999", headers=self.auth(self.token_ana))
        self.assertEqual(resposta.status_code, 404)


class TestConvidarPorBusca(BaseGrupo):

    def setUp(self):
        super().setUp()
        self.grupo = self.criar_grupo(self.token_ana)

    def test_membro_comum_consegue_convidar(self):
        self.cli.post(
            f"/api/grupos/{self.grupo['id']}/convites", json={"id_usuario": self.bia["id"]},
            headers=self.auth(self.token_ana),
        )
        id_convite = self.convite_recebido(self.token_bia)["id"]
        self.cli.put(f"/api/convites/{id_convite}", json={"aceito": True}, headers=self.auth(self.token_bia))

        resposta = self.cli.post(
            f"/api/grupos/{self.grupo['id']}/convites", json={"id_usuario": self.cris["id"]},
            headers=self.auth(self.token_bia),
        )
        self.assertEqual(resposta.status_code, 201)

    def test_busca_para_convidar_exclui_membros_e_marca_convite_pendente(self):
        self.cli.post(
            f"/api/grupos/{self.grupo['id']}/convites", json={"id_usuario": self.bia["id"]},
            headers=self.auth(self.token_ana),
        )
        resultado = self.cli.get(
            f"/api/grupos/{self.grupo['id']}/busca-convidar", query_string={"nome": "Cris Lima"},
            headers=self.auth(self.token_ana),
        ).get_json()
        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]["nome"], "Cris Lima")
        self.assertFalse(resultado[0]["convite_pendente"])

        pendente = self.cli.get(
            f"/api/grupos/{self.grupo['id']}/busca-convidar", query_string={"nome": "Bia Costa"},
            headers=self.auth(self.token_ana),
        ).get_json()
        self.assertEqual(len(pendente), 1)
        self.assertTrue(pendente[0]["convite_pendente"])

    def test_convidar_quem_ja_e_membro_devolve_409(self):
        resposta = self.cli.post(
            f"/api/grupos/{self.grupo['id']}/convites", json={"id_usuario": self.ana["id"]},
            headers=self.auth(self.token_ana),
        )
        self.assertEqual(resposta.status_code, 409)

    def test_convidar_duas_vezes_a_mesma_pessoa_devolve_409(self):
        self.cli.post(
            f"/api/grupos/{self.grupo['id']}/convites", json={"id_usuario": self.bia["id"]},
            headers=self.auth(self.token_ana),
        )
        resposta = self.cli.post(
            f"/api/grupos/{self.grupo['id']}/convites", json={"id_usuario": self.bia["id"]},
            headers=self.auth(self.token_ana),
        )
        self.assertEqual(resposta.status_code, 409)

    def test_convidar_usuario_inexistente_devolve_404(self):
        resposta = self.cli.post(
            f"/api/grupos/{self.grupo['id']}/convites", json={"id_usuario": 9999},
            headers=self.auth(self.token_ana),
        )
        self.assertEqual(resposta.status_code, 404)


class TestConvitesRecebidos(BaseGrupo):

    def setUp(self):
        super().setUp()
        self.grupo = self.criar_grupo(self.token_ana)
        self.cli.post(
            f"/api/grupos/{self.grupo['id']}/convites", json={"id_usuario": self.bia["id"]},
            headers=self.auth(self.token_ana),
        )

    def test_lista_convite_pendente_com_contadores(self):
        resposta = self.cli.get("/api/convites", headers=self.auth(self.token_bia)).get_json()
        self.assertEqual(len(resposta["pendentes"]), 1)
        self.assertEqual(resposta["pendentes"][0]["grupo"]["nome"], self.grupo["nome"])
        self.assertEqual(resposta["pendentes"][0]["remetente"]["nome"], "Ana Silva")
        self.assertEqual(resposta["meus_grupos"], 0)

        enviados = self.cli.get("/api/convites", headers=self.auth(self.token_ana)).get_json()
        self.assertEqual(enviados["convites_enviados_pendentes"], 1)

    def test_aceitar_adiciona_como_membro(self):
        id_convite = self.convite_recebido(self.token_bia)["id"]
        resposta = self.cli.put(
            f"/api/convites/{id_convite}", json={"aceito": True}, headers=self.auth(self.token_bia)
        )
        self.assertEqual(resposta.status_code, 200)
        membros = self.cli.get(
            f"/api/grupos/{self.grupo['id']}/membros", headers=self.auth(self.token_bia)
        ).get_json()
        self.assertIn("Bia Costa", [m["nome"] for m in membros])

    def test_recusar_nao_adiciona_como_membro(self):
        id_convite = self.convite_recebido(self.token_bia)["id"]
        self.cli.put(f"/api/convites/{id_convite}", json={"aceito": False}, headers=self.auth(self.token_bia))
        detalhe = self.cli.get(f"/api/grupos/{self.grupo['id']}", headers=self.auth(self.token_bia))
        self.assertEqual(detalhe.status_code, 403)

    def test_outro_usuario_nao_responde_convite_alheio(self):
        id_convite = self.convite_recebido(self.token_bia)["id"]
        resposta = self.cli.put(
            f"/api/convites/{id_convite}", json={"aceito": True}, headers=self.auth(self.token_cris)
        )
        self.assertEqual(resposta.status_code, 403)

    def test_responder_convite_ja_respondido_devolve_409(self):
        id_convite = self.convite_recebido(self.token_bia)["id"]
        self.cli.put(f"/api/convites/{id_convite}", json={"aceito": True}, headers=self.auth(self.token_bia))
        resposta = self.cli.put(
            f"/api/convites/{id_convite}", json={"aceito": True}, headers=self.auth(self.token_bia)
        )
        self.assertEqual(resposta.status_code, 409)


class TestEntrarPorCodigo(BaseGrupo):

    def setUp(self):
        super().setUp()
        self.grupo = self.criar_grupo(self.token_ana)
        self.codigo = self.cli.get(
            f"/api/grupos/{self.grupo['id']}/convite", headers=self.auth(self.token_ana)
        ).get_json()["codigo"]

    def test_entra_no_grupo_com_codigo_valido(self):
        resposta = self.cli.post(
            "/api/grupos/entrar", json={"codigo": self.codigo}, headers=self.auth(self.token_bia)
        )
        self.assertEqual(resposta.status_code, 200)
        membros = self.cli.get(
            f"/api/grupos/{self.grupo['id']}/membros", headers=self.auth(self.token_bia)
        ).get_json()
        self.assertIn("Bia Costa", [m["nome"] for m in membros])

    def test_codigo_invalido_devolve_404(self):
        resposta = self.cli.post(
            "/api/grupos/entrar", json={"codigo": "NAOEXISTE1"}, headers=self.auth(self.token_bia)
        )
        self.assertEqual(resposta.status_code, 404)

    def test_entrar_de_novo_no_mesmo_grupo_devolve_409(self):
        resposta = self.cli.post(
            "/api/grupos/entrar", json={"codigo": self.codigo}, headers=self.auth(self.token_ana)
        )
        self.assertEqual(resposta.status_code, 409)

    def test_codigo_e_insensivel_a_caixa(self):
        resposta = self.cli.post(
            "/api/grupos/entrar", json={"codigo": self.codigo.lower()}, headers=self.auth(self.token_bia)
        )
        self.assertEqual(resposta.status_code, 200)


class TestRankingInternoDoGrupo(BaseGrupo):

    def setUp(self):
        super().setUp()
        self.grupo = self.criar_grupo(self.token_ana)
        codigo = self.cli.get(
            f"/api/grupos/{self.grupo['id']}/convite", headers=self.auth(self.token_ana)
        ).get_json()["codigo"]
        self.cli.post("/api/grupos/entrar", json={"codigo": codigo}, headers=self.auth(self.token_bia))
        self.cli.post("/api/grupos/entrar", json={"codigo": codigo}, headers=self.auth(self.token_cris))

    def treinar(self, usuario, token, minutos):
        resposta = self.cli.post(
            f"/api/usuarios/{usuario['id']}/atividades",
            json={"tipo": "cardio", "titulo": "Corrida", "tempo_min": minutos},
            headers=self.auth(token),
        )
        self.assertEqual(resposta.status_code, 201)

    def test_ranking_ordena_por_xp_e_considera_quem_desativou_o_ranking_publico(self):
        self.treinar(self.ana, self.token_ana, 30)
        self.treinar(self.bia, self.token_bia, 90)
        self.treinar(self.cris, self.token_cris, 60)
        self.cli.put(
            f"/api/usuarios/{self.bia['id']}/consentimentos/ranking_publico",
            json={"aceito": False}, headers=self.auth(self.token_bia),
        )

        ranking = self.cli.get(
            f"/api/grupos/{self.grupo['id']}/ranking", headers=self.auth(self.token_ana)
        ).get_json()
        nomes = [linha["nome"] for linha in ranking]
        self.assertEqual(nomes, ["Bia Costa", "Cris Lima", "Ana Silva"])

        publico = self.cli.get("/api/ranking/global", headers=self.auth(self.token_ana)).get_json()
        self.assertNotIn("Bia Costa", [l["nome"] for l in publico])


if __name__ == "__main__":
    unittest.main()
