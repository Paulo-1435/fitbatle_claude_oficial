import unittest

from tests.test_seguranca import BaseTeste


class BaseMeta(BaseTeste):

    def setUp(self):
        super().setUp()
        self.ana, self.token_ana = self.criar_usuario_logado("Ana Silva")
        self.bia, self.token_bia = self.criar_usuario_logado("Bia Costa")

    def levantar(self, usuario, token, titulo, carga, reps=5):
        resposta = self.cli.post(
            f"/api/usuarios/{usuario['id']}/atividades",
            json={"tipo": "musculacao", "titulo": titulo, "tempo_min": 40, "carga_kg": carga, "repeticoes": reps},
            headers=self.auth(token),
        )
        self.assertEqual(resposta.status_code, 201, resposta.get_data(as_text=True))

    def criar_meta(self, token, **extra):
        corpo = {"titulo": "Atingir 150 kg no Supino Reto", "tipo": "curto_prazo",
                 "tipo_metrica": "carga_maxima", "exercicio": "Supino Reto", "valor_objetivo": 150}
        corpo.update(extra)
        resposta = self.cli.post("/api/metas", json=corpo, headers=self.auth(token))
        self.assertEqual(resposta.status_code, 201, resposta.get_data(as_text=True))
        return resposta.get_json()["meta"]


class TestCriarMeta(BaseMeta):

    def test_exige_titulo(self):
        resposta = self.cli.post(
            "/api/metas",
            json={"tipo": "curto_prazo", "tipo_metrica": "carga_maxima", "exercicio": "Supino Reto", "valor_objetivo": 150},
            headers=self.auth(self.token_ana),
        )
        self.assertEqual(resposta.status_code, 400)

    def test_tipo_metrica_invalido_e_recusado(self):
        resposta = self.cli.post(
            "/api/metas",
            json={"titulo": "x", "tipo": "curto_prazo", "tipo_metrica": "velocidade", "valor_objetivo": 10},
            headers=self.auth(self.token_ana),
        )
        self.assertEqual(resposta.status_code, 400)

    def test_carga_maxima_exige_exercicio(self):
        resposta = self.cli.post(
            "/api/metas",
            json={"titulo": "x", "tipo": "curto_prazo", "tipo_metrica": "carga_maxima", "valor_objetivo": 150},
            headers=self.auth(self.token_ana),
        )
        self.assertEqual(resposta.status_code, 400)

    def test_valor_partida_automatico_a_partir_do_historico_real(self):
        self.levantar(self.ana, self.token_ana, "Supino Reto", 100)
        self.levantar(self.ana, self.token_ana, "Supino Reto", 120)
        meta = self.criar_meta(self.token_ana)
        self.assertEqual(meta["valor_partida"], 120.0)
        self.assertEqual(meta["valor_atual"], 120.0)

    def test_valor_partida_zero_quando_nunca_treinou_o_exercicio(self):
        meta = self.criar_meta(self.token_ana)
        self.assertEqual(meta["valor_partida"], 0)
        self.assertEqual(meta["valor_atual"], 0)

    def test_meta_de_frequencia_nao_exige_exercicio(self):
        resposta = self.cli.post(
            "/api/metas",
            json={"titulo": "Treinar 20 vezes no mês", "tipo": "curto_prazo",
                  "tipo_metrica": "frequencia", "valor_objetivo": 20},
            headers=self.auth(self.token_ana),
        )
        self.assertEqual(resposta.status_code, 201)
        self.assertIsNone(resposta.get_json()["meta"]["exercicio"])


class TestProgressoDaMeta(BaseMeta):

    def test_carga_maxima_usa_a_maior_carga_registrada(self):
        meta = self.criar_meta(self.token_ana, valor_objetivo=150)
        self.levantar(self.ana, self.token_ana, "Supino Reto", 130)
        self.levantar(self.ana, self.token_ana, "Supino Reto", 125)

        atualizada = self.cli.get(f"/api/metas/{meta['id']}", headers=self.auth(self.token_ana)).get_json()
        self.assertEqual(atualizada["valor_atual"], 130.0)
        self.assertEqual(atualizada["faltam"], 20.0)
        self.assertEqual(atualizada["percentual"], 87)

    def test_atingir_o_objetivo_marca_como_concluida(self):
        meta = self.criar_meta(self.token_ana, valor_objetivo=120)
        self.levantar(self.ana, self.token_ana, "Supino Reto", 120)

        atualizada = self.cli.get(f"/api/metas/{meta['id']}", headers=self.auth(self.token_ana)).get_json()
        self.assertEqual(atualizada["status"], "concluida")
        self.assertIsNotNone(atualizada["concluida_em"])
        self.assertEqual(atualizada["percentual"], 100)

    def test_frequencia_conta_treinos_registrados_desde_a_criacao_da_meta(self):
        resposta = self.cli.post(
            "/api/metas",
            json={"titulo": "Treinar 3 vezes", "tipo": "curto_prazo", "tipo_metrica": "frequencia", "valor_objetivo": 3},
            headers=self.auth(self.token_ana),
        )
        meta = resposta.get_json()["meta"]
        self.levantar(self.ana, self.token_ana, "Supino Reto", 50)
        self.levantar(self.ana, self.token_ana, "Agachamento Livre", 60)

        atualizada = self.cli.get(f"/api/metas/{meta['id']}", headers=self.auth(self.token_ana)).get_json()
        self.assertEqual(atualizada["valor_atual"], 2)
        self.assertEqual(atualizada["status"], "em_andamento")


class TestHistoricoVinculado(BaseMeta):

    def test_historico_mostra_delta_entre_sessoes(self):
        meta = self.criar_meta(self.token_ana, valor_objetivo=200)
        self.levantar(self.ana, self.token_ana, "Supino Reto", 100)
        self.levantar(self.ana, self.token_ana, "Supino Reto", 100)
        self.levantar(self.ana, self.token_ana, "Supino Reto", 110)
        self.levantar(self.ana, self.token_ana, "Supino Reto", 95)

        detalhe = self.cli.get(f"/api/metas/{meta['id']}", headers=self.auth(self.token_ana)).get_json()
        rotulos = [item["rotulo"] for item in detalhe["historico"]]
        self.assertEqual(rotulos, [
            "Registro inicial da meta", "Carga mantida",
            "+10 kg em relação ao anterior", "-15 kg em relação ao anterior",
        ])

    def test_frequencia_nao_tem_historico_de_delta(self):
        resposta = self.cli.post(
            "/api/metas",
            json={"titulo": "Treinar 3 vezes", "tipo": "curto_prazo", "tipo_metrica": "frequencia", "valor_objetivo": 3},
            headers=self.auth(self.token_ana),
        )
        meta = resposta.get_json()["meta"]
        detalhe = self.cli.get(f"/api/metas/{meta['id']}", headers=self.auth(self.token_ana)).get_json()
        self.assertEqual(detalhe["historico"], [])


class TestAcessoAMeta(BaseMeta):

    def test_so_o_dono_ve_a_meta(self):
        meta = self.criar_meta(self.token_ana)
        resposta = self.cli.get(f"/api/metas/{meta['id']}", headers=self.auth(self.token_bia))
        self.assertEqual(resposta.status_code, 403)

    def test_so_o_dono_edita_e_exclui(self):
        meta = self.criar_meta(self.token_ana)
        editar = self.cli.put(
            f"/api/metas/{meta['id']}", json={"titulo": "Hackeado"}, headers=self.auth(self.token_bia)
        )
        excluir = self.cli.delete(f"/api/metas/{meta['id']}", headers=self.auth(self.token_bia))
        self.assertEqual(editar.status_code, 403)
        self.assertEqual(excluir.status_code, 403)

    def test_dono_edita_e_exclui_normalmente(self):
        meta = self.criar_meta(self.token_ana)
        editar = self.cli.put(
            f"/api/metas/{meta['id']}", json={"titulo": "Novo título"}, headers=self.auth(self.token_ana)
        )
        self.assertEqual(editar.status_code, 200)
        self.assertEqual(editar.get_json()["meta"]["titulo"], "Novo título")

        excluir = self.cli.delete(f"/api/metas/{meta['id']}", headers=self.auth(self.token_ana))
        self.assertEqual(excluir.status_code, 200)
        sumiu = self.cli.get(f"/api/metas/{meta['id']}", headers=self.auth(self.token_ana))
        self.assertEqual(sumiu.status_code, 404)

    def test_listar_so_traz_metas_do_proprio_usuario(self):
        self.criar_meta(self.token_ana)
        self.criar_meta(self.token_bia, titulo="Meta da Bia")
        minhas = self.cli.get("/api/metas", headers=self.auth(self.token_ana)).get_json()
        self.assertEqual(len(minhas), 1)
        self.assertEqual(minhas[0]["titulo"], "Atingir 150 kg no Supino Reto")


if __name__ == "__main__":
    unittest.main()
