import os
import re
import secrets
import string
import time
from datetime import date, datetime, timezone

from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from database import db
from models.model import _iso_utc
from repositories.repository import (
    AtividadeRepository,
    ComentarioRepository,
    ConsentimentoRepository,
    ConviteRepository,
    CurtidaRepository,
    GrupoRepository,
    MetaRepository,
    PostagemRepository,
    RankingRepository,
    UsuarioRepository,
)

EMAIL_REGEX = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"

IDADE_MINIMA_CADASTRO = 13
IDADE_MAIORIDADE = 18

EXTENSOES_FOTO = {"png", "jpg", "jpeg", "webp"}

TIPOS_ALVO_FEED = {"atividade", "postagem"}

FAIXAS_NIVEL = [
    (0, "iniciante"),
    (1000, "intermediario"),
    (3000, "avancado"),
    (7000, "profissional"),
    (15000, "elite"),
]

CONSENTIMENTOS_OBRIGATORIOS = {
    "conta_autenticacao": "Criar, autenticar e manter a minha conta",
    "registro_atividades": "Registrar e armazenar meus treinos",
    "historico_estatisticas": "Manter meu histórico e minhas estatísticas individuais",
    "dados_saude": "Tratar dados de treino que possam revelar condição de saúde (art. 11 da LGPD)",
    "seguranca_auditoria": "Guardar registros técnicos de segurança e auditoria",
}
CONSENTIMENTOS_OPCIONAIS = {
    "ranking_publico": "Exibir meu perfil e desempenho nos rankings regional e global",
    "localizacao": "Usar minha cidade/região para o ranking regional",
    "chat_publico": "Participar dos chats públicos da plataforma",
    "chat_privado_externo": "Receber mensagens privadas de usuários fora dos meus grupos",
    "busca_perfil": "Permitir que outros usuários me encontrem pela busca",
    "notificacoes": "Receber notificações por push ou e-mail",
    "compartilhamento": "Compartilhar conquistas e recordes em redes sociais externas",
}


def _agora():
    return datetime.now(timezone.utc)


def nivel_por_xp(xp):
    nivel = FAIXAS_NIVEL[0][1]
    for xp_minimo, nome in FAIXAS_NIVEL:
        if xp >= xp_minimo:
            nivel = nome
    return nivel


class ErroValidacao(Exception):

    def __init__(self, mensagem, status=400):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status = status


class _LimitadorLogin:

    MAX_TENTATIVAS = 5
    JANELA_SEGUNDOS = 15 * 60
    BLOQUEIO_SEGUNDOS = 15 * 60

    _tentativas = {}

    @classmethod
    def verificar(cls, chave):
        registro = cls._tentativas.get(chave)
        if not registro:
            return
        bloqueado_ate = registro.get("bloqueado_ate")
        if bloqueado_ate and bloqueado_ate > time.time():
            restante = int(bloqueado_ate - time.time())
            raise ErroValidacao(
                f"Muitas tentativas de login. Tente novamente em {restante} segundos.",
                status=429,
            )

    @classmethod
    def registrar_falha(cls, chave):
        agora = time.time()
        registro = cls._tentativas.setdefault(chave, {"falhas": [], "bloqueado_ate": None})
        registro["falhas"] = [t for t in registro["falhas"] if agora - t < cls.JANELA_SEGUNDOS]
        registro["falhas"].append(agora)
        if len(registro["falhas"]) >= cls.MAX_TENTATIVAS:
            registro["bloqueado_ate"] = agora + cls.BLOQUEIO_SEGUNDOS
            registro["falhas"] = []

    @classmethod
    def registrar_sucesso(cls, chave):
        cls._tentativas.pop(chave, None)

    @classmethod
    def resetar(cls):
        cls._tentativas.clear()


def resetar_limitador_login():
    _LimitadorLogin.resetar()


class UsuarioService:

    BUSCA_MINIMO_CARACTERES = 2
    BUSCA_LIMITE = 20

    @staticmethod
    def cadastrar(dados):
        dados = dados or {}
        limpos = UsuarioService._validar(dados, senha_obrigatoria=True)

        if not dados.get("aceite_termos"):
            raise ErroValidacao(
                "É necessário ler e aceitar o Termo de Uso e o Termo de Consentimento."
            )

        limpos.update(UsuarioService._validar_faixa_etaria(limpos["idade"], dados))

        if UsuarioRepository.buscar_por_email(limpos["email"]):
            raise ErroValidacao("E-mail já cadastrado.", status=409)

        consentimentos = dados.get("consentimentos") or {}
        limpos["perfil_publico"] = bool(consentimentos.get("ranking_publico", True))

        limpos["senha"] = generate_password_hash(limpos["senha"])
        try:
            usuario = UsuarioRepository.criar(limpos)
        except IntegrityError:
            db.session.rollback()
            raise ErroValidacao("E-mail já cadastrado.", status=409)
        ConsentimentoService.registrar_iniciais(usuario.id_usuario, consentimentos)
        return usuario

    @staticmethod
    def autenticar(email, senha):
        email = (email or "").strip()
        chave = email.lower()
        _LimitadorLogin.verificar(chave)

        usuario = UsuarioRepository.buscar_por_email(email)
        if not usuario or not check_password_hash(usuario.senha, senha or ""):
            _LimitadorLogin.registrar_falha(chave)
            raise ErroValidacao("E-mail ou senha incorretos.", status=401)

        _LimitadorLogin.registrar_sucesso(chave)
        return usuario

    @staticmethod
    def buscar_por_termo(termo, id_solicitante):
        termo = (termo or "").strip()
        if len(termo) < UsuarioService.BUSCA_MINIMO_CARACTERES:
            raise ErroValidacao(
                f"Digite ao menos {UsuarioService.BUSCA_MINIMO_CARACTERES} letras para buscar."
            )
        return UsuarioRepository.buscar_publicos(
            termo, id_solicitante, UsuarioService.BUSCA_LIMITE
        )

    @staticmethod
    def buscar(id_usuario):
        usuario = UsuarioRepository.buscar_por_id(id_usuario)
        if not usuario:
            raise ErroValidacao("Usuário não encontrado.", status=404)
        return usuario

    @staticmethod
    def buscar_visivel(id_usuario, id_solicitante):
        usuario = UsuarioService.buscar(id_usuario)
        if usuario.id_usuario != id_solicitante and not usuario.perfil_publico:
            raise ErroValidacao("Usuário não encontrado.", status=404)
        return usuario

    @staticmethod
    def atualizar(id_usuario, dados):
        usuario = UsuarioService.buscar(id_usuario)
        dados = dict(dados or {})

        if dados.get("nome") is not None and len(dados["nome"].strip()) < 3:
            raise ErroValidacao("O nome deve ter no mínimo 3 caracteres.")

        if dados.get("email"):
            email = dados["email"].strip()
            if not re.match(EMAIL_REGEX, email):
                raise ErroValidacao("Informe um e-mail válido.")
            existente = UsuarioRepository.buscar_por_email(email)
            if existente and existente.id_usuario != usuario.id_usuario:
                raise ErroValidacao("E-mail já cadastrado.", status=409)
            dados["email"] = email

        if dados.get("senha"):
            if len(dados["senha"]) < 8:
                raise ErroValidacao("A senha deve ter no mínimo 8 caracteres.")
            dados["senha"] = generate_password_hash(dados["senha"])

        if dados.get("idade") is not None:
            dados["idade"] = UsuarioService._validar_idade(dados["idade"])

        if dados.get("peso") not in (None, ""):
            dados["peso"] = UsuarioService._validar_numero(dados["peso"], "peso", 20, 400)
        if dados.get("altura") not in (None, ""):
            dados["altura"] = UsuarioService._validar_numero(dados["altura"], "altura", 0.5, 2.7)

        return UsuarioRepository.atualizar(usuario, dados)

    @staticmethod
    def salvar_foto(id_usuario, arquivo, pasta_destino):
        usuario = UsuarioService.buscar(id_usuario)

        if arquivo is None or not arquivo.filename:
            raise ErroValidacao("Nenhuma imagem enviada.")

        ext = arquivo.filename.rsplit(".", 1)[-1].lower() if "." in arquivo.filename else ""
        if ext not in EXTENSOES_FOTO:
            raise ErroValidacao("Formato inválido. Envie uma imagem PNG, JPG ou WEBP.")
        if ext == "jpeg":
            ext = "jpg"

        os.makedirs(pasta_destino, exist_ok=True)

        prefixo = f"usuario_{id_usuario}"
        for nome_arquivo in os.listdir(pasta_destino):
            if nome_arquivo.startswith(prefixo + "_") or nome_arquivo.startswith(prefixo + "."):
                try:
                    os.remove(os.path.join(pasta_destino, nome_arquivo))
                except OSError:
                    pass

        nome = f"{prefixo}_{int(time.time())}.{ext}"
        arquivo.save(os.path.join(pasta_destino, nome))

        usuario.foto = "/uploads/" + nome
        return UsuarioRepository.salvar(usuario)

    @staticmethod
    def excluir(id_usuario, pasta_uploads=None):
        usuario = UsuarioService.buscar(id_usuario)

        caminhos_foto = []
        if usuario.foto:
            caminhos_foto.append(usuario.foto)
        for postagem in PostagemRepository.listar_do_usuario(id_usuario):
            if postagem.foto:
                caminhos_foto.append(postagem.foto)

        UsuarioRepository.excluir(usuario)

        if pasta_uploads:
            for caminho in caminhos_foto:
                try:
                    os.remove(os.path.join(pasta_uploads, os.path.basename(caminho)))
                except OSError:
                    pass

    @staticmethod
    def estatisticas():
        usuarios = UsuarioRepository.listar()
        total = len(usuarios)
        media_xp = round(sum(u.xp for u in usuarios) / total, 2) if total else 0
        return {"total_usuarios": total, "media_xp": media_xp}

    @staticmethod
    def _validar(dados, senha_obrigatoria):
        if not dados:
            raise ErroValidacao("Corpo da requisição vazio ou JSON inválido.")

        nome = (dados.get("nome") or "").strip()
        email = (dados.get("email") or "").strip()
        senha = dados.get("senha") or ""

        if len(nome) < 3:
            raise ErroValidacao("O nome deve ter no mínimo 3 caracteres.")
        if not re.match(EMAIL_REGEX, email):
            raise ErroValidacao("Informe um e-mail válido.")
        if senha_obrigatoria and len(senha) < 8:
            raise ErroValidacao("A senha deve ter no mínimo 8 caracteres.")

        idade = dados.get("idade")
        if idade is not None and idade != "":
            idade = UsuarioService._validar_idade(idade)
        else:
            idade = None

        return {
            "nome": nome,
            "email": email,
            "senha": senha,
            "idade": idade,
            "cidade": (dados.get("cidade") or None),
            "estado": (dados.get("estado") or None),
            "descricao": (dados.get("descricao") or None),
        }

    @staticmethod
    def _validar_idade(valor):
        try:
            idade = int(valor)
        except (TypeError, ValueError):
            raise ErroValidacao("Idade inválida.")
        if idade < 1 or idade > 120:
            raise ErroValidacao("Idade inválida.")
        return idade

    @staticmethod
    def _validar_numero(valor, nome, minimo, maximo):
        try:
            numero = float(str(valor).replace(",", "."))
        except (TypeError, ValueError):
            raise ErroValidacao(f"Valor de {nome} inválido.")
        if numero < minimo or numero > maximo:
            raise ErroValidacao(f"Valor de {nome} fora do intervalo permitido.")
        return round(numero, 2)

    @staticmethod
    def _validar_faixa_etaria(idade, dados):
        if idade is None:
            raise ErroValidacao("Informe a idade.")

        if idade < IDADE_MINIMA_CADASTRO:
            raise ErroValidacao(
                "O cadastro não é permitido para menores de 13 anos (art. 14 da LGPD)."
            )

        if idade >= IDADE_MAIORIDADE:
            return {}

        responsavel = dados.get("responsavel") or {}
        nome = (responsavel.get("nome") or "").strip()
        email = (responsavel.get("email") or "").strip()

        if not dados.get("autorizacao_responsavel"):
            raise ErroValidacao(
                "Para menores de 18 anos é necessária a autorização do responsável legal."
            )
        if len(nome) < 3:
            raise ErroValidacao("Informe o nome completo do responsável legal.")
        if not re.match(EMAIL_REGEX, email):
            raise ErroValidacao("Informe um e-mail válido do responsável legal.")

        return {
            "responsavel_nome": nome,
            "responsavel_email": email,
            "responsavel_autorizado_em": _agora(),
        }


class AtividadeService:

    TIPOS_VALIDOS = {"musculacao", "cardio", "yoga", "outro"}

    LIMITES_CAMPOS = {
        "tempo_min": 600,
        "distancia_km": 500,
        "carga_kg": 500,
        "repeticoes": 1000,
    }

    @staticmethod
    def registrar(id_usuario, dados):
        usuario = UsuarioService.buscar(id_usuario)
        limpos = AtividadeService._validar(dados)

        limpos["pontuacao"] = AtividadeService.calcular_pontuacao(limpos)
        atividade = AtividadeRepository.criar(id_usuario, limpos)

        usuario.xp += atividade.pontuacao
        usuario.nivel = nivel_por_xp(usuario.xp)
        UsuarioRepository.salvar(usuario)

        return atividade, usuario

    @staticmethod
    def historico(id_usuario):
        UsuarioService.buscar(id_usuario)
        return AtividadeRepository.listar_do_usuario(id_usuario)

    @staticmethod
    def buscar(id_atividade):
        atividade = AtividadeRepository.buscar_por_id(id_atividade)
        if not atividade:
            raise ErroValidacao("Atividade não encontrada.", status=404)
        return atividade

    @staticmethod
    def buscar_visivel(id_atividade, id_solicitante):
        atividade = AtividadeService.buscar(id_atividade)
        if atividade.id_usuario != id_solicitante:
            dono = UsuarioRepository.buscar_por_id(atividade.id_usuario)
            if dono is None or not dono.perfil_publico:
                raise ErroValidacao("Atividade não encontrada.", status=404)
        return atividade

    @staticmethod
    def excluir(id_usuario, id_atividade):
        atividade = AtividadeService.buscar(id_atividade)
        if atividade.id_usuario != id_usuario:
            raise ErroValidacao("Você só pode excluir seus próprios treinos.", status=403)
        usuario = UsuarioRepository.buscar_por_id(atividade.id_usuario)
        if usuario:
            usuario.xp = max(0, usuario.xp - atividade.pontuacao)
            usuario.nivel = nivel_por_xp(usuario.xp)
            UsuarioRepository.salvar(usuario)
        CurtidaRepository.excluir_do_alvo("atividade", id_atividade)
        ComentarioRepository.excluir_do_alvo("atividade", id_atividade)
        AtividadeRepository.excluir(atividade)

    @staticmethod
    def calcular_pontuacao(dados):
        tempo = dados.get("tempo_min") or 0
        distancia = dados.get("distancia_km") or 0
        carga = dados.get("carga_kg") or 0
        reps = dados.get("repeticoes") or 0

        pontos = tempo * 1 + distancia * 10 + (carga * reps) / 100

        bonus_tipo = {"musculacao": 20, "cardio": 15, "yoga": 10, "outro": 5}
        pontos += bonus_tipo.get(dados["tipo"], 5)

        return max(10, round(pontos))

    @staticmethod
    def _validar(dados):
        if not dados:
            raise ErroValidacao("Corpo da requisição vazio ou JSON inválido.")

        tipo = (dados.get("tipo") or "").strip().lower()
        if tipo not in AtividadeService.TIPOS_VALIDOS:
            raise ErroValidacao(
                "Tipo inválido. Use: " + ", ".join(sorted(AtividadeService.TIPOS_VALIDOS))
            )

        numericos = {}
        for campo in ("tempo_min", "distancia_km", "carga_kg", "repeticoes"):
            valor = dados.get(campo)
            if valor in (None, ""):
                numericos[campo] = None
                continue
            try:
                valor = float(str(valor).replace(",", "."))
            except (TypeError, ValueError):
                raise ErroValidacao(f"O campo '{campo}' deve ser numérico.")
            if valor < 0:
                raise ErroValidacao(f"O campo '{campo}' não pode ser negativo.")
            limite = AtividadeService.LIMITES_CAMPOS[campo]
            if valor > limite:
                raise ErroValidacao(f"O campo '{campo}' não pode passar de {limite}.")
            numericos[campo] = valor

        if not numericos["tempo_min"] and not numericos["distancia_km"]:
            raise ErroValidacao("Informe ao menos a duração ou a distância do treino.")

        return {
            "tipo": tipo,
            "titulo": (dados.get("titulo") or None),
            "descricao": (dados.get("descricao") or None),
            **numericos,
        }


class PostagemService:

    TEXTO_MAX = 1000

    @staticmethod
    def criar(id_usuario, texto, arquivo, pasta_destino):
        if id_usuario is None:
            raise ErroValidacao("Informe o usuário.", status=401)
        UsuarioService.buscar(id_usuario)
        texto = (texto or "").strip()

        if not texto and not (arquivo and arquivo.filename):
            raise ErroValidacao("Escreva algo ou envie uma foto para publicar.")
        if len(texto) > PostagemService.TEXTO_MAX:
            raise ErroValidacao(
                f"O texto pode ter no máximo {PostagemService.TEXTO_MAX} caracteres."
            )

        foto = None
        if arquivo and arquivo.filename:
            ext = arquivo.filename.rsplit(".", 1)[-1].lower() if "." in arquivo.filename else ""
            if ext not in EXTENSOES_FOTO:
                raise ErroValidacao("Formato inválido. Envie uma imagem PNG, JPG ou WEBP.")
            if ext == "jpeg":
                ext = "jpg"
            os.makedirs(pasta_destino, exist_ok=True)
            nome = f"postagem_{id_usuario}_{int(time.time())}.{ext}"
            arquivo.save(os.path.join(pasta_destino, nome))
            foto = "/uploads/" + nome

        return PostagemRepository.criar(id_usuario, texto, foto)

    @staticmethod
    def excluir(id_usuario, id_postagem):
        if id_usuario is None:
            raise ErroValidacao("Informe o usuário.", status=401)
        postagem = PostagemRepository.buscar_por_id(id_postagem)
        if not postagem:
            raise ErroValidacao("Postagem não encontrada.", status=404)
        if postagem.id_usuario != id_usuario:
            raise ErroValidacao("Você só pode excluir suas próprias postagens.", status=403)
        CurtidaRepository.excluir_do_alvo("postagem", id_postagem)
        ComentarioRepository.excluir_do_alvo("postagem", id_postagem)
        PostagemRepository.excluir(postagem)


class FeedService:

    LIMITE_PADRAO = 30
    LIMITE_MAXIMO = 100

    @staticmethod
    def listar(id_usuario_atual, limite=LIMITE_PADRAO):
        limite = FeedService._limite(limite)

        atividades = AtividadeRepository.listar_publicas(limite)
        postagens = PostagemRepository.listar_publicas(limite)

        itens = []
        for a in atividades:
            itens.append({
                "tipo": "atividade", "id": a.id_atividade, "id_usuario": a.id_usuario,
                "data_registro": a.data_registro, "objeto": a,
            })
        for p in postagens:
            itens.append({
                "tipo": "postagem", "id": p.id_postagem, "id_usuario": p.id_usuario,
                "data_registro": p.data_registro, "objeto": p,
            })

        itens.sort(key=lambda i: i["data_registro"], reverse=True)
        itens = itens[:limite]

        ids_atividade = [i["id"] for i in itens if i["tipo"] == "atividade"]
        ids_postagem = [i["id"] for i in itens if i["tipo"] == "postagem"]

        curtidas_atividade = CurtidaRepository.contar_em_lote("atividade", ids_atividade)
        curtidas_postagem = CurtidaRepository.contar_em_lote("postagem", ids_postagem)
        comentarios_atividade = ComentarioRepository.contar_em_lote("atividade", ids_atividade)
        comentarios_postagem = ComentarioRepository.contar_em_lote("postagem", ids_postagem)

        curti_atividade = set()
        curti_postagem = set()
        if id_usuario_atual:
            curti_atividade = CurtidaRepository.curtidos_pelo_usuario(
                id_usuario_atual, "atividade", ids_atividade
            )
            curti_postagem = CurtidaRepository.curtidos_pelo_usuario(
                id_usuario_atual, "postagem", ids_postagem
            )

        ids_donos = {i["id_usuario"] for i in itens}
        donos = {
            uid: UsuarioRepository.buscar_por_id(uid)
            for uid in ids_donos
        }

        resultado = []
        for i in itens:
            dono = donos.get(i["id_usuario"])
            base = i["objeto"].to_dict()
            base["tipo_conteudo"] = i["tipo"]
            base["usuario"] = {
                "id": dono.id_usuario if dono else None,
                "nome": dono.nome if dono else "Usuário removido",
                "foto": dono.foto if dono else None,
            }
            if i["tipo"] == "atividade":
                base["curtidas"] = curtidas_atividade.get(i["id"], 0)
                base["comentarios"] = comentarios_atividade.get(i["id"], 0)
                base["curti"] = i["id"] in curti_atividade
            else:
                base["curtidas"] = curtidas_postagem.get(i["id"], 0)
                base["comentarios"] = comentarios_postagem.get(i["id"], 0)
                base["curti"] = i["id"] in curti_postagem
            resultado.append(base)

        return resultado

    @staticmethod
    def _limite(valor):
        try:
            numero = int(valor)
        except (TypeError, ValueError):
            return FeedService.LIMITE_PADRAO
        return max(1, min(numero, FeedService.LIMITE_MAXIMO))

    @staticmethod
    def buscar_alvo(tipo_alvo, id_alvo):
        if tipo_alvo not in TIPOS_ALVO_FEED:
            raise ErroValidacao("Tipo de conteúdo inválido.")
        if tipo_alvo == "atividade":
            alvo = AtividadeRepository.buscar_por_id(id_alvo)
        else:
            alvo = PostagemRepository.buscar_por_id(id_alvo)
        if not alvo:
            raise ErroValidacao("Conteúdo não encontrado.", status=404)
        return alvo


class CurtidaService:

    @staticmethod
    def alternar(id_usuario, tipo_alvo, id_alvo):
        if id_usuario is None:
            raise ErroValidacao("Informe o usuário.", status=401)
        UsuarioService.buscar(id_usuario)
        FeedService.buscar_alvo(tipo_alvo, id_alvo)

        existente = CurtidaRepository.buscar(id_usuario, tipo_alvo, id_alvo)
        if existente:
            CurtidaRepository.descurtir(existente)
            curti = False
        else:
            try:
                CurtidaRepository.curtir(id_usuario, tipo_alvo, id_alvo)
            except IntegrityError:
                db.session.rollback()
            curti = True

        return {"curti": curti, "curtidas": CurtidaRepository.contar(tipo_alvo, id_alvo)}


class ComentarioService:

    TEXTO_MAX = 500

    @staticmethod
    def listar(tipo_alvo, id_alvo):
        FeedService.buscar_alvo(tipo_alvo, id_alvo)
        comentarios = ComentarioRepository.listar(tipo_alvo, id_alvo)

        resultado = []
        for c in comentarios:
            dado = c.to_dict()
            autor = UsuarioRepository.buscar_por_id(c.id_usuario)
            dado["usuario"] = {
                "id": autor.id_usuario if autor else None,
                "nome": autor.nome if autor else "Usuário removido",
                "foto": autor.foto if autor else None,
            }
            resultado.append(dado)
        return resultado

    @staticmethod
    def criar(id_usuario, tipo_alvo, id_alvo, texto):
        if id_usuario is None:
            raise ErroValidacao("Informe o usuário.", status=401)
        UsuarioService.buscar(id_usuario)
        FeedService.buscar_alvo(tipo_alvo, id_alvo)

        texto = (texto or "").strip()
        if not texto:
            raise ErroValidacao("Escreva um comentário.")
        if len(texto) > ComentarioService.TEXTO_MAX:
            raise ErroValidacao(
                f"O comentário pode ter no máximo {ComentarioService.TEXTO_MAX} caracteres."
            )

        return ComentarioRepository.criar(id_usuario, tipo_alvo, id_alvo, texto)

    @staticmethod
    def excluir(id_usuario, id_comentario):
        if id_usuario is None:
            raise ErroValidacao("Informe o usuário.", status=401)
        comentario = ComentarioRepository.buscar_por_id(id_comentario)
        if not comentario:
            raise ErroValidacao("Comentário não encontrado.", status=404)
        if comentario.id_usuario != id_usuario:
            raise ErroValidacao("Você só pode excluir seus próprios comentários.", status=403)
        ComentarioRepository.excluir(comentario)


class ConsentimentoService:

    @staticmethod
    def registrar_iniciais(id_usuario, escolhas):
        escolhas = escolhas or {}
        registros = []

        for chave, descricao in CONSENTIMENTOS_OBRIGATORIOS.items():
            registros.append({
                "chave": chave, "descricao": descricao,
                "obrigatorio": True, "aceito": True,
            })

        for chave, descricao in CONSENTIMENTOS_OPCIONAIS.items():
            registros.append({
                "chave": chave, "descricao": descricao,
                "obrigatorio": False,
                "aceito": bool(escolhas.get(chave, True)),
            })

        return ConsentimentoRepository.criar_varios(id_usuario, registros)

    @staticmethod
    def listar(id_usuario):
        UsuarioService.buscar(id_usuario)
        return ConsentimentoRepository.listar_do_usuario(id_usuario)

    @staticmethod
    def atualizar(id_usuario, chave, aceito):
        UsuarioService.buscar(id_usuario)

        if chave in CONSENTIMENTOS_OBRIGATORIOS:
            raise ErroValidacao(
                "Este consentimento é obrigatório para manter a conta e não pode ser alterado.",
                status=409,
            )
        if chave not in CONSENTIMENTOS_OPCIONAIS:
            raise ErroValidacao("Consentimento não encontrado.", status=404)
        if aceito is None:
            raise ErroValidacao("Informe o campo 'aceito' (true ou false).")

        registro = ConsentimentoRepository.buscar(id_usuario, chave)
        if not registro:
            raise ErroValidacao("Consentimento não encontrado.", status=404)

        registro.aceito = bool(aceito)
        registro.data_atualizacao = _agora()
        ConsentimentoRepository.salvar(registro)

        if chave == "ranking_publico":
            usuario = UsuarioRepository.buscar_por_id(id_usuario)
            usuario.perfil_publico = registro.aceito
            UsuarioRepository.salvar(usuario)

        return registro


class RankingService:

    LIMITE_PADRAO = 20
    LIMITE_MAXIMO = 100

    @staticmethod
    def global_(limite=LIMITE_PADRAO):
        return RankingRepository.global_(RankingService._limite(limite))

    @staticmethod
    def regional(cidade, limite=LIMITE_PADRAO):
        cidade = (cidade or "").strip()
        if not cidade:
            raise ErroValidacao(
                "Informe a cidade para ver o ranking regional."
            )
        return RankingRepository.regional(cidade, RankingService._limite(limite))

    @staticmethod
    def por_exercicio(titulo, cidade=None, limite=LIMITE_PADRAO):
        titulo = (titulo or "").strip()
        if not titulo:
            raise ErroValidacao("Informe o exercício para ver o ranking.")
        cidade = (cidade or "").strip() or None
        return RankingRepository.por_exercicio(titulo, cidade, RankingService._limite(limite))

    @staticmethod
    def resumo_usuario(id_usuario):
        UsuarioService.buscar(id_usuario)
        return {
            "global": RankingRepository.minha_posicao_global(id_usuario),
            "regional": RankingRepository.minha_posicao_regional(id_usuario),
        }

    @staticmethod
    def _limite(valor):
        try:
            numero = int(valor)
        except (TypeError, ValueError):
            return RankingService.LIMITE_PADRAO
        return max(1, min(numero, RankingService.LIMITE_MAXIMO))


CODIGO_CONVITE_ALFABETO = string.ascii_uppercase + string.digits


def _gerar_codigo_convite():
    for _ in range(10):
        codigo = "".join(secrets.choice(CODIGO_CONVITE_ALFABETO) for _ in range(10))
        if not GrupoRepository.buscar_por_codigo(codigo):
            return codigo
    raise ErroValidacao("Não foi possível gerar um código de convite. Tente novamente.", status=500)


def _handles(usuarios):
    raizes = {}
    contagem = {}
    for usuario in usuarios:
        raiz = (usuario.email.split("@")[0] or "atleta").lower()
        raizes[usuario.id_usuario] = raiz
        contagem[raiz] = contagem.get(raiz, 0) + 1

    handles = {}
    for usuario in usuarios:
        raiz = raizes[usuario.id_usuario]
        if contagem[raiz] > 1:
            handles[usuario.id_usuario] = f"{raiz}{usuario.id_usuario % 100:02d}"
        else:
            handles[usuario.id_usuario] = raiz
    return handles


class GrupoService:

    NOME_MAX = 50
    DESCRICAO_MAX = 300

    @staticmethod
    def criar(id_usuario, dados):
        dados = dados or {}
        nome = (dados.get("nome") or "").strip()
        descricao = (dados.get("descricao") or "").strip() or None

        if not nome:
            raise ErroValidacao("Informe o nome do grupo.")
        if len(nome) > GrupoService.NOME_MAX:
            raise ErroValidacao(f"O nome do grupo pode ter no máximo {GrupoService.NOME_MAX} caracteres.")
        if descricao and len(descricao) > GrupoService.DESCRICAO_MAX:
            raise ErroValidacao(f"A descrição pode ter no máximo {GrupoService.DESCRICAO_MAX} caracteres.")

        codigo = _gerar_codigo_convite()
        grupo = GrupoRepository.criar(nome, descricao, id_usuario, codigo)
        GrupoRepository.adicionar_membro(grupo.id_grupo, id_usuario, "admin")
        return grupo

    @staticmethod
    def buscar(id_grupo):
        grupo = GrupoRepository.buscar_por_id(id_grupo)
        if not grupo:
            raise ErroValidacao("Grupo não encontrado.", status=404)
        return grupo

    @staticmethod
    def _exigir_membro(id_grupo, id_usuario):
        grupo = GrupoService.buscar(id_grupo)
        papel = GrupoRepository.papel_do_membro(id_grupo, id_usuario)
        if papel is None:
            raise ErroValidacao("Você não participa deste grupo.", status=403)
        return grupo, papel

    @staticmethod
    def _exigir_admin(id_grupo, id_usuario):
        grupo, papel = GrupoService._exigir_membro(id_grupo, id_usuario)
        if papel != "admin":
            raise ErroValidacao("Apenas administradores do grupo podem fazer isso.", status=403)
        return grupo

    @staticmethod
    def listar_meus(id_usuario):
        resultado = []
        for grupo, papel in GrupoRepository.listar_do_usuario(id_usuario):
            dado = grupo.to_dict()
            dado["meu_papel"] = papel
            dado["membros"] = GrupoRepository.contar_membros(grupo.id_grupo)
            resultado.append(dado)
        return resultado

    @staticmethod
    def detalhe(id_grupo, id_usuario):
        grupo, papel = GrupoService._exigir_membro(id_grupo, id_usuario)
        dado = grupo.to_dict()
        dado["meu_papel"] = papel
        dado["membros"] = GrupoRepository.contar_membros(id_grupo)
        return dado

    @staticmethod
    def membros(id_grupo, id_usuario):
        GrupoService._exigir_membro(id_grupo, id_usuario)
        pares = GrupoRepository.listar_membros(id_grupo)
        handles = _handles([usuario for usuario, _ in pares])
        return [
            {
                "id": usuario.id_usuario,
                "nome": usuario.nome,
                "handle": handles[usuario.id_usuario],
                "cidade": usuario.cidade,
                "estado": usuario.estado,
                "foto": usuario.foto,
                "papel": papel,
            }
            for usuario, papel in pares
        ]

    @staticmethod
    def ranking(id_grupo, id_usuario, limite=20):
        GrupoService._exigir_membro(id_grupo, id_usuario)
        return RankingRepository.grupo(id_grupo, limite)

    @staticmethod
    def convite_info(id_grupo, id_usuario):
        grupo = GrupoService._exigir_admin(id_grupo, id_usuario)
        return {"codigo": grupo.codigo_convite}

    @staticmethod
    def regenerar_codigo(id_grupo, id_usuario):
        grupo = GrupoService._exigir_admin(id_grupo, id_usuario)
        grupo.codigo_convite = _gerar_codigo_convite()
        GrupoRepository.salvar(grupo)
        return {"codigo": grupo.codigo_convite}

    @staticmethod
    def entrar_por_codigo(id_usuario, codigo):
        codigo = (codigo or "").strip().upper()
        if not codigo:
            raise ErroValidacao("Informe o código de convite.")
        grupo = GrupoRepository.buscar_por_codigo(codigo)
        if not grupo:
            raise ErroValidacao("Código de convite inválido.", status=404)
        if GrupoRepository.papel_do_membro(grupo.id_grupo, id_usuario) is not None:
            raise ErroValidacao("Você já participa deste grupo.", status=409)
        GrupoRepository.adicionar_membro(grupo.id_grupo, id_usuario, "membro")
        return grupo

    @staticmethod
    def buscar_para_convidar(id_grupo, id_usuario, termo):
        GrupoService._exigir_membro(id_grupo, id_usuario)
        encontrados = UsuarioService.buscar_por_termo(termo, id_usuario)
        ids_membros = GrupoRepository.ids_membros(id_grupo)
        candidatos = [u for u in encontrados if u.id_usuario not in ids_membros]
        handles = _handles(candidatos)

        resultado = []
        for usuario in candidatos:
            resultado.append({
                "id": usuario.id_usuario,
                "nome": usuario.nome,
                "handle": handles[usuario.id_usuario],
                "cidade": usuario.cidade,
                "estado": usuario.estado,
                "foto": usuario.foto,
                "convite_pendente": ConviteRepository.buscar_pendente(id_grupo, usuario.id_usuario) is not None,
            })
        return resultado

    @staticmethod
    def convidar(id_grupo, id_remetente, id_destinatario):
        GrupoService._exigir_membro(id_grupo, id_remetente)
        destinatario = UsuarioService.buscar(id_destinatario)
        if GrupoRepository.papel_do_membro(id_grupo, destinatario.id_usuario) is not None:
            raise ErroValidacao("Esse usuário já é membro do grupo.", status=409)
        try:
            return ConviteRepository.criar(id_grupo, id_remetente, destinatario.id_usuario)
        except IntegrityError:
            db.session.rollback()
            raise ErroValidacao("Já existe um convite pendente para esse usuário.", status=409)


class ConviteService:

    @staticmethod
    def meus_recebidos(id_usuario):
        pendentes = []
        for convite, grupo, remetente in ConviteRepository.listar_pendentes_recebidos(id_usuario):
            pendentes.append({
                "id": convite.id_convite,
                "grupo": {
                    "id": grupo.id_grupo,
                    "nome": grupo.nome,
                    "descricao": grupo.descricao,
                    "membros": GrupoRepository.contar_membros(grupo.id_grupo),
                },
                "remetente": {"id": remetente.id_usuario, "nome": remetente.nome},
                "data_envio": _iso_utc(convite.data_envio),
            })
        return {
            "pendentes": pendentes,
            "meus_grupos": len(GrupoRepository.listar_do_usuario(id_usuario)),
            "convites_enviados_pendentes": ConviteRepository.contar_enviados_pendentes(id_usuario),
        }

    @staticmethod
    def responder(id_convite, id_usuario, aceito):
        convite = ConviteRepository.buscar_por_id(id_convite)
        if not convite:
            raise ErroValidacao("Convite não encontrado.", status=404)
        if convite.id_destinatario != id_usuario:
            raise ErroValidacao("Você não tem permissão para responder este convite.", status=403)
        if convite.status != "pendente":
            raise ErroValidacao("Este convite já foi respondido.", status=409)
        if aceito is None:
            raise ErroValidacao("Informe o campo 'aceito' (true ou false).")

        convite.status = "aceito" if aceito else "recusado"
        convite.data_resposta = _agora()
        ConviteRepository.salvar(convite)

        if aceito and GrupoRepository.papel_do_membro(convite.id_grupo, id_usuario) is None:
            GrupoRepository.adicionar_membro(convite.id_grupo, id_usuario, "membro")

        return convite


class MetaService:

    TIPOS_PRAZO = {"curto_prazo", "longo_prazo"}
    TIPOS_METRICA = {"carga_maxima", "frequencia"}
    TITULO_MAX = 300

    @staticmethod
    def criar(id_usuario, dados):
        dados = dados or {}
        titulo = (dados.get("titulo") or "").strip()
        tipo = dados.get("tipo")
        tipo_metrica = dados.get("tipo_metrica")
        exercicio = (dados.get("exercicio") or "").strip() or None
        data_final = dados.get("data_final")

        if not titulo:
            raise ErroValidacao("Informe o título da meta.")
        if len(titulo) > MetaService.TITULO_MAX:
            raise ErroValidacao(f"O título pode ter no máximo {MetaService.TITULO_MAX} caracteres.")
        if tipo not in MetaService.TIPOS_PRAZO:
            raise ErroValidacao("Tipo de prazo inválido. Use: curto_prazo ou longo_prazo.")
        if tipo_metrica not in MetaService.TIPOS_METRICA:
            raise ErroValidacao("Tipo de métrica inválido. Use: carga_maxima ou frequencia.")
        if tipo_metrica == "carga_maxima" and not exercicio:
            raise ErroValidacao("Informe o exercício vinculado a esta meta.")
        if tipo_metrica == "frequencia":
            exercicio = None

        valor_objetivo = MetaService._validar_numero(dados.get("valor_objetivo"), "valor objetivo")

        valor_partida = dados.get("valor_partida")
        if valor_partida not in (None, ""):
            valor_partida = MetaService._validar_numero(valor_partida, "valor de partida")
        elif tipo_metrica == "carga_maxima":
            valor_partida = AtividadeRepository.maior_carga(id_usuario, exercicio.lower()) or 0
        else:
            valor_partida = 0

        data_final_convertida = None
        if data_final:
            data_final_convertida = MetaService._validar_data(data_final)
            if data_final_convertida < date.today():
                raise ErroValidacao("O prazo da meta não pode ser uma data no passado.")

        meta = MetaRepository.criar({
            "id_usuario": id_usuario,
            "descricao": titulo,
            "tipo": tipo,
            "tipo_metrica": tipo_metrica,
            "exercicio": exercicio,
            "valor_objetivo": valor_objetivo,
            "valor_partida": valor_partida,
            "data_inicio": date.today(),
            "data_final": data_final_convertida,
            "status": "em_andamento",
        })
        return MetaService._com_progresso(meta)

    @staticmethod
    def buscar(id_meta):
        meta = MetaRepository.buscar_por_id(id_meta)
        if not meta:
            raise ErroValidacao("Meta não encontrada.", status=404)
        return meta

    @staticmethod
    def _exigir_dono(id_meta, id_usuario):
        meta = MetaService.buscar(id_meta)
        if meta.id_usuario != id_usuario:
            raise ErroValidacao("Você não tem permissão para acessar esta meta.", status=403)
        return meta

    @staticmethod
    def listar_do_usuario(id_usuario):
        metas = MetaRepository.listar_do_usuario(id_usuario)
        return [MetaService._com_progresso(m) for m in metas]

    @staticmethod
    def detalhe(id_meta, id_usuario):
        meta = MetaService._exigir_dono(id_meta, id_usuario)
        dado = MetaService._com_progresso(meta)
        dado["historico"] = MetaService._historico(meta)
        return dado

    @staticmethod
    def atualizar(id_meta, id_usuario, dados):
        meta = MetaService._exigir_dono(id_meta, id_usuario)
        dados = dados or {}

        if dados.get("titulo") is not None:
            titulo = dados["titulo"].strip()
            if not titulo:
                raise ErroValidacao("Informe o título da meta.")
            meta.descricao = titulo
        if dados.get("valor_objetivo") is not None:
            meta.valor_objetivo = MetaService._validar_numero(dados["valor_objetivo"], "valor objetivo")
        if "data_final" in dados:
            meta.data_final = MetaService._validar_data(dados["data_final"]) if dados["data_final"] else None

        MetaRepository.salvar(meta)
        return MetaService._com_progresso(meta)

    @staticmethod
    def excluir(id_meta, id_usuario):
        meta = MetaService._exigir_dono(id_meta, id_usuario)
        MetaRepository.excluir(meta)

    @staticmethod
    def _valor_atual(meta):
        if meta.tipo_metrica == "carga_maxima":
            maior = AtividadeRepository.maior_carga(meta.id_usuario, (meta.exercicio or "").strip().lower())
            if maior is None:
                return float(meta.valor_partida) if meta.valor_partida is not None else 0.0
            return maior
        inicio = datetime.combine(meta.data_inicio, datetime.min.time())
        return float(AtividadeRepository.contar_desde(meta.id_usuario, inicio))

    @staticmethod
    def _com_progresso(meta):
        atual = MetaService._valor_atual(meta)
        objetivo = float(meta.valor_objetivo)
        partida = float(meta.valor_partida) if meta.valor_partida is not None else 0.0

        if meta.status == "em_andamento" and objetivo > 0 and atual >= objetivo:
            meta.status = "concluida"
            meta.concluida_em = _agora()
            MetaRepository.salvar(meta)

        percentual = 0
        if objetivo > 0:
            percentual = max(0, min(100, round((atual / objetivo) * 100)))

        dias_restantes = None
        if meta.data_final:
            dias_restantes = (meta.data_final - date.today()).days

        return {
            "id": meta.id_meta,
            "titulo": meta.descricao,
            "tipo": meta.tipo,
            "tipo_metrica": meta.tipo_metrica,
            "exercicio": meta.exercicio,
            "valor_objetivo": objetivo,
            "valor_partida": partida,
            "valor_atual": atual,
            "faltam": max(0, round(objetivo - atual, 2)),
            "percentual": percentual,
            "status": meta.status,
            "data_inicio": meta.data_inicio.isoformat(),
            "data_final": meta.data_final.isoformat() if meta.data_final else None,
            "dias_restantes": dias_restantes,
            "concluida_em": meta.concluida_em.isoformat() if meta.concluida_em else None,
        }

    @staticmethod
    def _historico(meta):
        if meta.tipo_metrica != "carga_maxima" or not meta.exercicio:
            return []

        atividades = AtividadeRepository.listar_do_usuario_por_titulo(
            meta.id_usuario, meta.exercicio.strip().lower()
        )
        historico = []
        anterior = None
        for indice, atividade in enumerate(atividades, start=1):
            carga = float(atividade.carga_kg) if atividade.carga_kg is not None else None
            if anterior is None:
                rotulo = "Registro inicial da meta"
            elif carga == anterior:
                rotulo = "Carga mantida"
            elif carga is not None and anterior is not None and carga > anterior:
                rotulo = f"+{carga - anterior:g} kg em relação ao anterior"
            else:
                rotulo = f"{(carga - anterior):g} kg em relação ao anterior" if carga is not None and anterior is not None else "—"

            historico.append({
                "sessao": indice,
                "carga_kg": carga,
                "repeticoes": atividade.repeticoes,
                "data_registro": _iso_utc(atividade.data_registro),
                "rotulo": rotulo,
            })
            anterior = carga
        return historico

    @staticmethod
    def _validar_numero(valor, nome):
        try:
            numero = float(str(valor).replace(",", "."))
        except (TypeError, ValueError):
            raise ErroValidacao(f"Informe um {nome} válido.")
        if numero <= 0:
            raise ErroValidacao(f"O {nome} deve ser maior que zero.")
        return round(numero, 2)

    @staticmethod
    def _validar_data(valor):
        try:
            return datetime.strptime(valor, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            raise ErroValidacao("Data inválida. Use o formato AAAA-MM-DD.")
