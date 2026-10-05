import io
import os
import shutil
import tempfile
import unittest
from unittest import mock

from tests.test_seguranca import SENHA, BaseTeste


class TestErrosEmJson(BaseTeste):

    def test_rota_inexistente_devolve_json(self):
        resposta = self.cli.get("/api/rota-que-nao-existe")
        self.assertEqual(resposta.status_code, 404)
        self.assertEqual(resposta.content_type, "application/json")
        self.assertIn("erro", resposta.get_json())

    def test_metodo_nao_permitido_devolve_json(self):
        resposta = self.cli.get("/api/usuarios")
        self.assertEqual(resposta.status_code, 405)
        self.assertIn("erro", resposta.get_json())

    def test_corpo_grande_demais_devolve_413_em_json(self):
        usuario, token = self.criar_usuario_logado("Ana Grande")
        conteudo = b"a" * (4 * 1024 * 1024)
        resposta = self.cli.post(
            f"/api/usuarios/{usuario['id']}/foto",
            data={"foto": (io.BytesIO(conteudo), "foto.png")},
            content_type="multipart/form-data",
            headers=self.auth(token),
        )
        self.assertEqual(resposta.status_code, 413)
        self.assertIn("erro", resposta.get_json())

    def test_erro_inesperado_nao_vaza_html(self):
        with mock.patch(
            "controllers.controller.UsuarioService.estatisticas",
            side_effect=RuntimeError("falha simulada"),
        ):
            resposta = self.cli.get("/api/estatisticas")
        self.assertEqual(resposta.status_code, 500)
        self.assertEqual(resposta.content_type, "application/json")
        self.assertIn("erro", resposta.get_json())


class TestLimitesDeCampos(BaseTeste):

    def setUp(self):
        super().setUp()
        self.usuario, self.token = self.criar_usuario_logado("Ana Limite")

    def registrar(self, **campos):
        corpo = {"tipo": "musculacao", "tempo_min": 30}
        corpo.update(campos)
        return self.cli.post(
            f"/api/usuarios/{self.usuario['id']}/atividades",
            json=corpo,
            headers=self.auth(self.token),
        )

    def test_tempo_acima_do_limite_e_recusado(self):
        self.assertEqual(self.registrar(tempo_min=10000).status_code, 400)

    def test_carga_acima_do_limite_e_recusada(self):
        self.assertEqual(self.registrar(carga_kg=10000, repeticoes=5).status_code, 400)

    def test_repeticoes_acima_do_limite_e_recusada(self):
        self.assertEqual(self.registrar(carga_kg=50, repeticoes=5000).status_code, 400)

    def test_distancia_acima_do_limite_e_recusada(self):
        resposta = self.registrar(tipo="cardio", tempo_min=None, distancia_km=1000)
        self.assertEqual(resposta.status_code, 400)

    def test_valores_dentro_do_limite_sao_aceitos(self):
        resposta = self.registrar(carga_kg=100, repeticoes=10)
        self.assertEqual(resposta.status_code, 201)


class TestCorridaCadastroEmail(BaseTeste):

    def test_cadastro_concorrente_do_mesmo_email_nao_gera_500(self):
        email = "corrida@teste.com"
        corpo = {
            "nome": "Primeiro", "email": email, "idade": 25, "senha": SENHA,
            "aceite_termos": True, "consentimentos": {},
        }
        with mock.patch("services.service.UsuarioRepository.buscar_por_email", return_value=None):
            primeira = self.cli.post("/api/usuarios", json=corpo)
            segunda = self.cli.post("/api/usuarios", json=dict(corpo, nome="Segundo"))

        self.assertEqual(primeira.status_code, 201)
        self.assertEqual(segunda.status_code, 409)
        self.assertIn("erro", segunda.get_json())


class TestCorridaCurtida(BaseTeste):

    def test_curtida_concorrente_nao_gera_500(self):
        usuario, token = self.criar_usuario_logado("Ana Corrida")
        postagem = self.cli.post(
            "/api/postagens", data={"texto": "Treino"}, headers=self.auth(token)
        )
        id_postagem = postagem.get_json()["postagem"]["id"]

        with mock.patch("services.service.CurtidaRepository.buscar", return_value=None):
            primeira = self.cli.post(
                f"/api/feed/postagem/{id_postagem}/curtir", headers=self.auth(token)
            )
            segunda = self.cli.post(
                f"/api/feed/postagem/{id_postagem}/curtir", headers=self.auth(token)
            )

        self.assertEqual(primeira.status_code, 200)
        self.assertEqual(segunda.status_code, 200)
        self.assertTrue(primeira.get_json()["curti"])
        self.assertTrue(segunda.get_json()["curti"])
        self.assertEqual(segunda.get_json()["curtidas"], 1)


class TestLimpezaDeImagens(BaseTeste):

    def setUp(self):
        super().setUp()
        self.pasta_uploads = tempfile.mkdtemp()
        self.app.config["UPLOAD_FOLDER"] = self.pasta_uploads

    def tearDown(self):
        shutil.rmtree(self.pasta_uploads, ignore_errors=True)

    def _enviar_foto_de_perfil(self, usuario, token):
        resposta = self.cli.post(
            f"/api/usuarios/{usuario['id']}/foto",
            data={"foto": (io.BytesIO(b"conteudo-fake-de-imagem"), "avatar.png")},
            content_type="multipart/form-data",
            headers=self.auth(token),
        )
        self.assertEqual(resposta.status_code, 200, resposta.get_data(as_text=True))
        return resposta.get_json()["usuario"]["foto"]

    def test_apaga_foto_de_perfil_ao_excluir_conta(self):
        usuario, token = self.criar_usuario_logado("Ana Foto")
        caminho = self._enviar_foto_de_perfil(usuario, token)
        nome_arquivo = os.path.basename(caminho)
        self.assertTrue(os.path.exists(os.path.join(self.pasta_uploads, nome_arquivo)))

        exclusao = self.cli.delete(f"/api/usuarios/{usuario['id']}", headers=self.auth(token))
        self.assertEqual(exclusao.status_code, 200)
        self.assertFalse(os.path.exists(os.path.join(self.pasta_uploads, nome_arquivo)))

    def test_apaga_fotos_das_postagens_ao_excluir_conta(self):
        usuario, token = self.criar_usuario_logado("Bia Foto")
        postagem = self.cli.post(
            "/api/postagens",
            data={"texto": "Treino com foto", "foto": (io.BytesIO(b"fake-png"), "post.png")},
            content_type="multipart/form-data",
            headers=self.auth(token),
        )
        self.assertEqual(postagem.status_code, 201, postagem.get_data(as_text=True))
        nome_arquivo = os.path.basename(postagem.get_json()["postagem"]["foto"])
        self.assertTrue(os.path.exists(os.path.join(self.pasta_uploads, nome_arquivo)))

        exclusao = self.cli.delete(f"/api/usuarios/{usuario['id']}", headers=self.auth(token))
        self.assertEqual(exclusao.status_code, 200)
        self.assertFalse(os.path.exists(os.path.join(self.pasta_uploads, nome_arquivo)))


class TestLimiteDeTentativasDeLogin(BaseTeste):

    def test_bloqueia_apos_tentativas_demais_e_devolve_429(self):
        usuario = self.cadastrar("Ana Login", email="ana.login@teste.com")

        for _ in range(5):
            resposta = self.cli.post(
                "/api/login", json={"email": usuario["email"], "senha": "errada"}
            )
            self.assertEqual(resposta.status_code, 401)

        bloqueado = self.cli.post(
            "/api/login", json={"email": usuario["email"], "senha": SENHA}
        )
        self.assertEqual(bloqueado.status_code, 429)
        self.assertIn("erro", bloqueado.get_json())

    def test_login_correto_reseta_o_contador_de_falhas(self):
        usuario = self.cadastrar("Bia Login", email="bia.login@teste.com")

        for _ in range(3):
            self.cli.post("/api/login", json={"email": usuario["email"], "senha": "errada"})

        correto = self.cli.post("/api/login", json={"email": usuario["email"], "senha": SENHA})
        self.assertEqual(correto.status_code, 200)

        for _ in range(3):
            resposta = self.cli.post(
                "/api/login", json={"email": usuario["email"], "senha": "errada"}
            )
            self.assertEqual(resposta.status_code, 401)

    def test_bloqueio_e_por_email_e_nao_afeta_outras_contas(self):
        self.cadastrar("Cris Login", email="cris.login@teste.com")
        outro = self.cadastrar("Davi Login", email="davi.login@teste.com")

        for _ in range(5):
            self.cli.post("/api/login", json={"email": "cris.login@teste.com", "senha": "errada"})

        resposta = self.cli.post("/api/login", json={"email": outro["email"], "senha": SENHA})
        self.assertEqual(resposta.status_code, 200)


if __name__ == "__main__":
    unittest.main()
