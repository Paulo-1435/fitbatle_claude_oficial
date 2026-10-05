import unittest

from tests.test_seguranca import BaseTeste


class TestRanking(BaseTeste):

    def setUp(self):
        super().setUp()
        self.ana, self.token_ana = self.criar_usuario_logado("Ana Silva")
        self.bia, self.token_bia = self.criar_usuario_logado("Bia Costa")
        self.cris, self.token_cris = self.criar_usuario_logado("Cris Lima")
        for usuario, cidade in ((self.ana, "Belo Horizonte"), (self.bia, "Belo Horizonte"), (self.cris, "Contagem")):
            self.cli.put(
                f"/api/usuarios/{usuario['id']}",
                json={"cidade": cidade},
                headers=self.auth(self.token_por_id(usuario["id"])),
            )
        self.treinar(self.ana, self.token_ana, 30)
        self.treinar(self.bia, self.token_bia, 90)
        self.treinar(self.cris, self.token_cris, 60)

    def token_por_id(self, id_usuario):
        return {self.ana["id"]: self.token_ana, self.bia["id"]: self.token_bia, self.cris["id"]: self.token_cris}[id_usuario]

    def treinar(self, usuario, token, minutos):
        resposta = self.cli.post(
            f"/api/usuarios/{usuario['id']}/atividades",
            json={"tipo": "cardio", "titulo": "Corrida", "tempo_min": minutos},
            headers=self.auth(token),
        )
        self.assertEqual(resposta.status_code, 201)

    def test_ranking_global_ordena_por_pontuacao(self):
        resposta = self.cli.get("/api/ranking/global", headers=self.auth(self.token_ana))
        self.assertEqual(resposta.status_code, 200)
        nomes = [linha["nome"] for linha in resposta.get_json()]
        self.assertEqual(nomes, ["Bia Costa", "Cris Lima", "Ana Silva"])
        posicoes = [linha["posicao"] for linha in resposta.get_json()]
        self.assertEqual(posicoes, [1, 2, 3])

    def test_ranking_regional_filtra_por_cidade(self):
        resposta = self.cli.get(
            "/api/ranking/regional", query_string={"cidade": "Belo Horizonte"},
            headers=self.auth(self.token_ana),
        )
        nomes = [linha["nome"] for linha in resposta.get_json()]
        self.assertEqual(nomes, ["Bia Costa", "Ana Silva"])

    def test_ranking_regional_exige_cidade(self):
        resposta = self.cli.get("/api/ranking/regional", headers=self.auth(self.token_ana))
        self.assertEqual(resposta.status_code, 400)

    def test_resumo_do_usuario_traz_posicao_global_e_regional(self):
        resposta = self.cli.get(
            f"/api/usuarios/{self.ana['id']}/ranking", headers=self.auth(self.token_ana)
        )
        corpo = resposta.get_json()
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(corpo["global"]["posicao"], 3)
        self.assertEqual(corpo["regional"]["posicao"], 2)

    def test_perfil_fora_do_ranking_publico_nao_aparece(self):
        self.cli.put(
            f"/api/usuarios/{self.bia['id']}/consentimentos/ranking_publico",
            json={"aceito": False},
            headers=self.auth(self.token_bia),
        )
        resposta = self.cli.get("/api/ranking/global", headers=self.auth(self.token_ana))
        nomes = [linha["nome"] for linha in resposta.get_json()]
        self.assertNotIn("Bia Costa", nomes)


class TestRankingPorExercicio(BaseTeste):

    def setUp(self):
        super().setUp()
        self.ana, self.token_ana = self.criar_usuario_logado("Ana Silva")
        self.bia, self.token_bia = self.criar_usuario_logado("Bia Costa")
        self.cris, self.token_cris = self.criar_usuario_logado("Cris Lima")
        for usuario, cidade, token in (
            (self.ana, "Belo Horizonte", self.token_ana),
            (self.bia, "Belo Horizonte", self.token_bia),
            (self.cris, "Contagem", self.token_cris),
        ):
            self.cli.put(
                f"/api/usuarios/{usuario['id']}",
                json={"cidade": cidade},
                headers=self.auth(token),
            )

    def levantar(self, usuario, token, titulo, carga, tipo="musculacao", reps=5):
        resposta = self.cli.post(
            f"/api/usuarios/{usuario['id']}/atividades",
            json={"tipo": tipo, "titulo": titulo, "tempo_min": 40, "carga_kg": carga, "repeticoes": reps},
            headers=self.auth(token),
        )
        self.assertEqual(resposta.status_code, 201, resposta.get_data(as_text=True))

    def buscar(self, titulo, token=None, cidade=None):
        parametros = {"titulo": titulo}
        if cidade:
            parametros["cidade"] = cidade
        return self.cli.get(
            "/api/ranking/exercicio", query_string=parametros, headers=self.auth(token or self.token_ana)
        )

    def test_ordena_pela_maior_carga_levantada(self):
        self.levantar(self.ana, self.token_ana, "Supino Reto", 100)
        self.levantar(self.bia, self.token_bia, "Supino Reto", 120)
        self.levantar(self.cris, self.token_cris, "Supino Reto", 90)

        resposta = self.buscar("Supino Reto")
        dados = resposta.get_json()
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual([l["nome"] for l in dados], ["Bia Costa", "Ana Silva", "Cris Lima"])
        self.assertEqual([l["carga_maxima"] for l in dados], [120.0, 100.0, 90.0])
        self.assertEqual([l["posicao"] for l in dados], [1, 2, 3])

    def test_usa_a_maior_carga_entre_varios_registros_do_mesmo_exercicio(self):
        self.levantar(self.ana, self.token_ana, "Supino Reto", 80)
        self.levantar(self.ana, self.token_ana, "Supino Reto", 100)
        self.levantar(self.ana, self.token_ana, "Supino Reto", 95)

        dados = self.buscar("Supino Reto").get_json()
        self.assertEqual(len(dados), 1)
        self.assertEqual(dados[0]["carga_maxima"], 100.0)

    def test_nao_ajusta_por_repeticoes_e_carga_bruta(self):
        self.levantar(self.ana, self.token_ana, "Supino Reto", 100, reps=1)
        self.levantar(self.bia, self.token_bia, "Supino Reto", 90, reps=20)

        dados = self.buscar("Supino Reto").get_json()
        self.assertEqual(dados[0]["nome"], "Ana Silva")
        self.assertEqual(dados[0]["carga_maxima"], 100.0)

    def test_titulo_e_case_insensitive_e_mescla_variacoes(self):
        self.levantar(self.ana, self.token_ana, "supino reto", 60)
        self.levantar(self.ana, self.token_ana, "SUPINO RETO", 130)

        dados = self.buscar("Supino Reto").get_json()
        self.assertEqual(len(dados), 1)
        self.assertEqual(dados[0]["carga_maxima"], 130.0)
        self.assertEqual(dados[0]["titulo"], "SUPINO RETO")

    def test_so_conta_atividades_de_musculacao(self):
        self.levantar(self.ana, self.token_ana, "Corrida", 400, tipo="cardio")
        dados = self.buscar("Corrida").get_json()
        self.assertEqual(dados, [])

    def test_exercicio_sem_ninguem_devolve_lista_vazia(self):
        resposta = self.buscar("Levantamento Terra")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.get_json(), [])

    def test_exige_o_titulo_do_exercicio(self):
        resposta = self.cli.get("/api/ranking/exercicio", headers=self.auth(self.token_ana))
        self.assertEqual(resposta.status_code, 400)

        resposta_vazio = self.cli.get(
            "/api/ranking/exercicio", query_string={"titulo": "   "}, headers=self.auth(self.token_ana)
        )
        self.assertEqual(resposta_vazio.status_code, 400)

    def test_filtra_por_cidade_quando_informada(self):
        self.levantar(self.ana, self.token_ana, "Agachamento Livre", 100)
        self.levantar(self.bia, self.token_bia, "Agachamento Livre", 150)
        self.levantar(self.cris, self.token_cris, "Agachamento Livre", 200)

        dados = self.buscar("Agachamento Livre", cidade="Belo Horizonte").get_json()
        nomes = [l["nome"] for l in dados]
        self.assertEqual(nomes, ["Bia Costa", "Ana Silva"])
        self.assertNotIn("Cris Lima", nomes)

    def test_empate_gera_a_mesma_posicao(self):
        self.levantar(self.ana, self.token_ana, "Leg Press", 200)
        self.levantar(self.bia, self.token_bia, "Leg Press", 200)
        self.levantar(self.cris, self.token_cris, "Leg Press", 150)

        dados = self.buscar("Leg Press").get_json()
        posicoes = {l["nome"]: l["posicao"] for l in dados}
        self.assertEqual(posicoes["Ana Silva"], 1)
        self.assertEqual(posicoes["Bia Costa"], 1)
        self.assertEqual(posicoes["Cris Lima"], 3)

    def test_perfil_privado_nao_aparece_no_ranking_por_exercicio(self):
        self.levantar(self.ana, self.token_ana, "Barra Fixa", 100)
        self.levantar(self.bia, self.token_bia, "Barra Fixa", 80)
        self.cli.put(
            f"/api/usuarios/{self.bia['id']}/consentimentos/ranking_publico",
            json={"aceito": False},
            headers=self.auth(self.token_bia),
        )

        dados = self.buscar("Barra Fixa").get_json()
        self.assertNotIn("Bia Costa", [l["nome"] for l in dados])
        self.assertIn("Ana Silva", [l["nome"] for l in dados])


if __name__ == "__main__":
    unittest.main()
