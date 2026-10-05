import os
import sys
import unittest
from unittest import mock

os.environ["DB_URI"] = "sqlite:///:memory:"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import criar_app
from auth import gerar_token
from database import db
from services.service import resetar_limitador_login
from tests.apoio import criar_views_de_ranking

SENHA = "senhaforte123"
CAMPOS_PRIVADOS = {"email", "idade", "peso", "altura", "responsavel"}
CAMPOS_PUBLICOS = {"id", "nome", "cidade", "estado", "foto", "descricao", "nivel", "xp", "criado_em"}


class BaseTeste(unittest.TestCase):

    def setUp(self):
        resetar_limitador_login()
        self.app = criar_app()
        with self.app.app_context():
            criar_views_de_ranking(db)
        self.cli = self.app.test_client()

    def cadastrar(self, nome, email=None, idade=25, consentimentos=None, responsavel=None):
        email = email or nome.lower().replace(" ", ".") + "@teste.com"
        corpo = {
            "nome": nome,
            "email": email,
            "idade": idade,
            "senha": SENHA,
            "aceite_termos": True,
            "consentimentos": consentimentos or {},
        }
        if responsavel:
            corpo["responsavel"] = responsavel
            corpo["autorizacao_responsavel"] = True
        resposta = self.cli.post("/api/usuarios", json=corpo)
        self.assertEqual(resposta.status_code, 201, resposta.get_data(as_text=True))
        return resposta.get_json()["usuario"]

    def entrar(self, email):
        resposta = self.cli.post("/api/login", json={"email": email, "senha": SENHA})
        self.assertEqual(resposta.status_code, 200)
        return resposta.get_json()["token"]

    def criar_usuario_logado(self, nome, **kwargs):
        usuario = self.cadastrar(nome, **kwargs)
        return usuario, self.entrar(usuario["email"])

    @staticmethod
    def auth(token):
        return {"Authorization": "Bearer " + token}

    def registrar_treino(self, usuario, token):
        resposta = self.cli.post(
            f"/api/usuarios/{usuario['id']}/atividades",
            json={"tipo": "musculacao", "titulo": "Peito", "tempo_min": 40},
            headers=self.auth(token),
        )
        self.assertEqual(resposta.status_code, 201)
        return resposta.get_json()["atividade"]


class TestAutenticacao(BaseTeste):

    def test_login_devolve_token_e_usuario(self):
        self.cadastrar("Ana Silva", email="ana@teste.com")
        resposta = self.cli.post("/api/login", json={"email": "ana@teste.com", "senha": SENHA})
        corpo = resposta.get_json()
        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(corpo["token"])
        self.assertEqual(corpo["usuario"]["email"], "ana@teste.com")

    def test_login_com_senha_errada_nao_devolve_token(self):
        self.cadastrar("Ana Silva", email="ana@teste.com")
        resposta = self.cli.post("/api/login", json={"email": "ana@teste.com", "senha": "errada123"})
        self.assertEqual(resposta.status_code, 401)
        self.assertNotIn("token", resposta.get_json())

    def test_rotas_protegidas_exigem_token(self):
        alvos = [
            ("get", "/api/eu"),
            ("get", "/api/feed"),
            ("get", "/api/ranking/global"),
            ("get", "/api/ranking/regional?cidade=x"),
            ("get", "/api/ranking/exercicio?titulo=Supino+Reto"),
            ("get", "/api/usuarios/busca?nome=ab"),
            ("get", "/api/usuarios/1"),
            ("put", "/api/usuarios/1"),
            ("delete", "/api/usuarios/1"),
            ("post", "/api/usuarios/1/foto"),
            ("get", "/api/usuarios/1/atividades"),
            ("post", "/api/usuarios/1/atividades"),
            ("get", "/api/atividades/1"),
            ("delete", "/api/atividades/1"),
            ("post", "/api/postagens"),
            ("delete", "/api/postagens/1"),
            ("post", "/api/feed/postagem/1/curtir"),
            ("get", "/api/feed/postagem/1/comentarios"),
            ("post", "/api/feed/postagem/1/comentarios"),
            ("delete", "/api/comentarios/1"),
            ("get", "/api/usuarios/1/ranking"),
            ("get", "/api/usuarios/1/consentimentos"),
            ("put", "/api/usuarios/1/consentimentos/ranking_publico"),
            ("post", "/api/grupos"),
            ("get", "/api/grupos"),
            ("get", "/api/grupos/1"),
            ("get", "/api/grupos/1/membros"),
            ("get", "/api/grupos/1/ranking"),
            ("get", "/api/grupos/1/convite"),
            ("post", "/api/grupos/1/convite/regenerar"),
            ("post", "/api/grupos/entrar"),
            ("get", "/api/grupos/1/busca-convidar?nome=ab"),
            ("post", "/api/grupos/1/convites"),
            ("get", "/api/convites"),
            ("put", "/api/convites/1"),
            ("post", "/api/metas"),
            ("get", "/api/metas"),
            ("get", "/api/metas/1"),
            ("put", "/api/metas/1"),
            ("delete", "/api/metas/1"),
        ]
        for metodo, caminho in alvos:
            with self.subTest(rota=f"{metodo.upper()} {caminho}"):
                resposta = getattr(self.cli, metodo)(caminho)
                self.assertEqual(resposta.status_code, 401)

    def test_rotas_publicas_continuam_abertas(self):
        self.assertEqual(self.cli.get("/api/estatisticas").status_code, 200)
        self.cadastrar("Ana Silva")

    def test_listagem_aberta_de_usuarios_foi_removida(self):
        self.cadastrar("Ana Silva")
        resposta = self.cli.get("/api/usuarios")
        self.assertEqual(resposta.status_code, 405)

    def test_token_adulterado_e_recusado(self):
        _, token = self.criar_usuario_logado("Ana Silva")
        adulterado = token[:-3] + ("aaa" if not token.endswith("aaa") else "bbb")
        resposta = self.cli.get("/api/eu", headers=self.auth(adulterado))
        self.assertEqual(resposta.status_code, 401)

    def test_cabecalhos_invalidos_sao_recusados(self):
        for cabecalho in ("Bearer", "Bearer ", "Basic abc", "abc", "Bearer nao.e.token"):
            with self.subTest(cabecalho=cabecalho):
                resposta = self.cli.get("/api/eu", headers={"Authorization": cabecalho})
                self.assertEqual(resposta.status_code, 401)

    def test_token_assinado_com_outra_chave_e_recusado(self):
        usuario, _ = self.criar_usuario_logado("Ana Silva")
        outro_app = criar_app()
        outro_app.config["SECRET_KEY"] = "outra-chave-qualquer"
        with outro_app.app_context():
            falso = gerar_token(usuario["id"])
        resposta = self.cli.get("/api/eu", headers=self.auth(falso))
        self.assertEqual(resposta.status_code, 401)

    def test_token_expirado_e_recusado(self):
        _, token = self.criar_usuario_logado("Ana Silva")
        with mock.patch("auth.VALIDADE_TOKEN_SEGUNDOS", -1):
            resposta = self.cli.get("/api/eu", headers=self.auth(token))
        self.assertEqual(resposta.status_code, 401)

    def test_token_de_usuario_excluido_e_recusado(self):
        usuario, token = self.criar_usuario_logado("Ana Silva")
        exclusao = self.cli.delete(f"/api/usuarios/{usuario['id']}", headers=self.auth(token))
        self.assertEqual(exclusao.status_code, 200)
        resposta = self.cli.get("/api/eu", headers=self.auth(token))
        self.assertEqual(resposta.status_code, 401)

    def test_eu_devolve_dados_atualizados_do_proprio_usuario(self):
        usuario, token = self.criar_usuario_logado("Ana Silva")
        self.registrar_treino(usuario, token)
        resposta = self.cli.get("/api/eu", headers=self.auth(token))
        corpo = resposta.get_json()["usuario"]
        self.assertEqual(corpo["id"], usuario["id"])
        self.assertGreater(corpo["xp"], 0)


class TestDonoDoRecurso(BaseTeste):

    def setUp(self):
        super().setUp()
        self.ana, self.token_ana = self.criar_usuario_logado("Ana Silva")
        self.bia, self.token_bia = self.criar_usuario_logado("Bia Costa")

    def test_outro_usuario_nao_edita_nem_exclui_conta(self):
        alvo = f"/api/usuarios/{self.ana['id']}"
        editar = self.cli.put(alvo, json={"nome": "Invasor"}, headers=self.auth(self.token_bia))
        excluir = self.cli.delete(alvo, headers=self.auth(self.token_bia))
        self.assertEqual(editar.status_code, 403)
        self.assertEqual(excluir.status_code, 403)
        atual = self.cli.get("/api/eu", headers=self.auth(self.token_ana)).get_json()["usuario"]
        self.assertEqual(atual["nome"], "Ana Silva")

    def test_outro_usuario_nao_troca_foto(self):
        resposta = self.cli.post(
            f"/api/usuarios/{self.ana['id']}/foto", headers=self.auth(self.token_bia)
        )
        self.assertEqual(resposta.status_code, 403)

    def test_outro_usuario_nao_registra_nem_le_treinos_alheios(self):
        base = f"/api/usuarios/{self.ana['id']}/atividades"
        registrar = self.cli.post(
            base, json={"tipo": "cardio", "tempo_min": 30}, headers=self.auth(self.token_bia)
        )
        historico = self.cli.get(base, headers=self.auth(self.token_bia))
        self.assertEqual(registrar.status_code, 403)
        self.assertEqual(historico.status_code, 403)

    def test_outro_usuario_nao_mexe_em_consentimentos(self):
        base = f"/api/usuarios/{self.ana['id']}/consentimentos"
        ler = self.cli.get(base, headers=self.auth(self.token_bia))
        alterar = self.cli.put(
            base + "/ranking_publico", json={"aceito": False}, headers=self.auth(self.token_bia)
        )
        self.assertEqual(ler.status_code, 403)
        self.assertEqual(alterar.status_code, 403)

    def test_outro_usuario_nao_ve_ranking_pessoal_alheio(self):
        resposta = self.cli.get(
            f"/api/usuarios/{self.ana['id']}/ranking", headers=self.auth(self.token_bia)
        )
        self.assertEqual(resposta.status_code, 403)

    def test_dono_edita_e_exclui_o_proprio_recurso(self):
        alvo = f"/api/usuarios/{self.ana['id']}"
        editar = self.cli.put(alvo, json={"nome": "Ana Souza"}, headers=self.auth(self.token_ana))
        self.assertEqual(editar.status_code, 200)
        self.assertEqual(editar.get_json()["usuario"]["nome"], "Ana Souza")
        treino = self.registrar_treino(self.ana, self.token_ana)
        excluir = self.cli.delete(f"/api/atividades/{treino['id']}", headers=self.auth(self.token_ana))
        self.assertEqual(excluir.status_code, 200)

    def test_exclusao_anonima_de_treino_e_recusada(self):
        treino = self.registrar_treino(self.ana, self.token_ana)
        resposta = self.cli.delete(f"/api/atividades/{treino['id']}")
        self.assertEqual(resposta.status_code, 401)
        existe = self.cli.get(f"/api/atividades/{treino['id']}", headers=self.auth(self.token_ana))
        self.assertEqual(existe.status_code, 200)

    def test_outro_usuario_nao_exclui_treino_alheio_mesmo_forjando_o_id(self):
        treino = self.registrar_treino(self.ana, self.token_ana)
        resposta = self.cli.delete(
            f"/api/atividades/{treino['id']}",
            json={"id_usuario": self.ana["id"]},
            headers=self.auth(self.token_bia),
        )
        self.assertEqual(resposta.status_code, 403)
        existe = self.cli.get(f"/api/atividades/{treino['id']}", headers=self.auth(self.token_ana))
        self.assertEqual(existe.status_code, 200)

    def test_outro_usuario_nao_exclui_postagem_nem_comentario_alheios(self):
        postagem = self.cli.post(
            "/api/postagens", data={"texto": "Treino de hoje"}, headers=self.auth(self.token_ana)
        )
        self.assertEqual(postagem.status_code, 201)
        id_postagem = postagem.get_json()["postagem"]["id"]

        comentario = self.cli.post(
            f"/api/feed/postagem/{id_postagem}/comentarios",
            json={"texto": "Boa!"},
            headers=self.auth(self.token_ana),
        )
        id_comentario = comentario.get_json()["comentario"]["id"]

        apagar_postagem = self.cli.delete(
            f"/api/postagens/{id_postagem}", headers=self.auth(self.token_bia)
        )
        apagar_comentario = self.cli.delete(
            f"/api/comentarios/{id_comentario}", headers=self.auth(self.token_bia)
        )
        self.assertEqual(apagar_postagem.status_code, 403)
        self.assertEqual(apagar_comentario.status_code, 403)

    def test_id_enviado_no_corpo_e_ignorado(self):
        postagem = self.cli.post(
            "/api/postagens",
            data={"texto": "Postagem da Ana", "id_usuario": str(self.bia["id"])},
            headers=self.auth(self.token_ana),
        )
        self.assertEqual(postagem.get_json()["postagem"]["id_usuario"], self.ana["id"])

        id_postagem = postagem.get_json()["postagem"]["id"]
        comentario = self.cli.post(
            f"/api/feed/postagem/{id_postagem}/comentarios",
            json={"texto": "Comentario da Bia", "id_usuario": self.ana["id"]},
            headers=self.auth(self.token_bia),
        )
        self.assertEqual(comentario.get_json()["comentario"]["id_usuario"], self.bia["id"])

        curtida = self.cli.post(
            f"/api/feed/postagem/{id_postagem}/curtir",
            json={"id_usuario": self.ana["id"]},
            headers=self.auth(self.token_bia),
        )
        self.assertTrue(curtida.get_json()["curti"])

        feed_da_bia = self.cli.get("/api/feed", headers=self.auth(self.token_bia)).get_json()
        self.assertTrue(next(i for i in feed_da_bia if i["tipo_conteudo"] == "postagem")["curti"])
        feed_da_ana = self.cli.get("/api/feed", headers=self.auth(self.token_ana)).get_json()
        self.assertFalse(next(i for i in feed_da_ana if i["tipo_conteudo"] == "postagem")["curti"])


class TestExposicaoDeDados(BaseTeste):

    def setUp(self):
        super().setUp()
        self.responsavel = {"nome": "Carlos Responsavel", "email": "carlos.resp@teste.com"}
        self.jovem, self.token_jovem = self.criar_usuario_logado(
            "Davi Menor", idade=15, responsavel=self.responsavel
        )
        self.ana, self.token_ana = self.criar_usuario_logado("Ana Silva")

    def assertSemDadosDoResponsavel(self, texto):
        self.assertNotIn("carlos.resp@teste.com", texto)
        self.assertNotIn("Carlos Responsavel", texto)
        self.assertNotIn("responsavel", texto)

    def test_dados_do_responsavel_nao_saem_em_nenhuma_resposta_do_proprio_menor(self):
        self.assertSemDadosDoResponsavel(str(self.jovem))
        respostas = [
            self.cli.post("/api/login", json={"email": self.jovem["email"], "senha": SENHA}),
            self.cli.get("/api/eu", headers=self.auth(self.token_jovem)),
            self.cli.get(f"/api/usuarios/{self.jovem['id']}", headers=self.auth(self.token_jovem)),
            self.cli.put(
                f"/api/usuarios/{self.jovem['id']}",
                json={"descricao": "oi"},
                headers=self.auth(self.token_jovem),
            ),
        ]
        for resposta in respostas:
            self.assertEqual(resposta.status_code, 200)
            self.assertSemDadosDoResponsavel(resposta.get_data(as_text=True))

    def test_perfil_alheio_devolve_so_campos_publicos(self):
        resposta = self.cli.get(f"/api/usuarios/{self.jovem['id']}", headers=self.auth(self.token_ana))
        corpo = resposta.get_json()
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(set(corpo), CAMPOS_PUBLICOS)
        self.assertEqual(corpo["nome"], "Davi Menor")
        self.assertSemDadosDoResponsavel(resposta.get_data(as_text=True))

    def test_perfil_proprio_devolve_campos_privados_do_usuario(self):
        resposta = self.cli.get(f"/api/usuarios/{self.ana['id']}", headers=self.auth(self.token_ana))
        self.assertEqual(resposta.get_json()["email"], "ana.silva@teste.com")

    def test_perfil_privado_fica_invisivel_para_terceiros(self):
        ocultar = self.cli.put(
            f"/api/usuarios/{self.ana['id']}/consentimentos/ranking_publico",
            json={"aceito": False},
            headers=self.auth(self.token_ana),
        )
        self.assertEqual(ocultar.status_code, 200)
        treino = self.registrar_treino(self.ana, self.token_ana)

        perfil = self.cli.get(f"/api/usuarios/{self.ana['id']}", headers=self.auth(self.token_jovem))
        atividade = self.cli.get(f"/api/atividades/{treino['id']}", headers=self.auth(self.token_jovem))
        propria = self.cli.get(f"/api/atividades/{treino['id']}", headers=self.auth(self.token_ana))
        self.assertEqual(perfil.status_code, 404)
        self.assertEqual(atividade.status_code, 404)
        self.assertEqual(propria.status_code, 200)

    def test_atividade_de_perfil_publico_e_visivel_para_logados(self):
        treino = self.registrar_treino(self.ana, self.token_ana)
        resposta = self.cli.get(f"/api/atividades/{treino['id']}", headers=self.auth(self.token_jovem))
        self.assertEqual(resposta.status_code, 200)


class TestBuscaRestrita(BaseTeste):

    def setUp(self):
        super().setUp()
        self.eu, self.token = self.criar_usuario_logado("Marcos Busca")
        self.cadastrar("Pedro Encontravel")
        self.cadastrar("Paula Sem Busca", consentimentos={"busca_perfil": False})
        self.cadastrar("Pablo Privado", consentimentos={"ranking_publico": False})

    def buscar(self, termo):
        return self.cli.get(
            "/api/usuarios/busca", query_string={"nome": termo}, headers=self.auth(self.token)
        )

    def test_exige_login(self):
        resposta = self.cli.get("/api/usuarios/busca", query_string={"nome": "pe"})
        self.assertEqual(resposta.status_code, 401)

    def test_exige_minimo_de_duas_letras(self):
        for termo in ("", " ", "p", " p "):
            with self.subTest(termo=termo):
                self.assertEqual(self.buscar(termo).status_code, 400)
        sem_parametro = self.cli.get("/api/usuarios/busca", headers=self.auth(self.token))
        self.assertEqual(sem_parametro.status_code, 400)
        self.assertEqual(self.buscar("pe").status_code, 200)

    def test_devolve_so_perfis_publicos_que_aceitaram_ser_encontrados(self):
        nomes = {u["nome"] for u in self.buscar("pe").get_json()}
        self.assertEqual(nomes, {"Pedro Encontravel"})
        self.assertEqual(self.buscar("Paula").get_json(), [])
        self.assertEqual(self.buscar("Pablo").get_json(), [])

    def test_devolve_so_campos_publicos(self):
        resultado = self.buscar("Pedro").get_json()[0]
        self.assertEqual(set(resultado), CAMPOS_PUBLICOS)

    def test_nao_devolve_o_proprio_usuario(self):
        self.assertEqual(self.buscar("Marcos").get_json(), [])

    def test_curingas_do_like_sao_tratados_como_texto(self):
        self.assertEqual(self.buscar("%%").get_json(), [])
        self.assertEqual(self.buscar("__").get_json(), [])

    def test_limita_a_20_resultados(self):
        for i in range(23):
            self.cadastrar(f"Zeca Numero {i:02d}")
        self.assertEqual(len(self.buscar("Zeca").get_json()), 20)


if __name__ == "__main__":
    unittest.main()
