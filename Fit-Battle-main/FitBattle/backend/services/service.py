"""Camada Service - regras de negócio e validação do FitBattle."""

import os
import re
import time
from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from repositories.repository import (
    AtividadeRepository,
    ConsentimentoRepository,
    RankingRepository,
    UsuarioRepository,
)

EMAIL_REGEX = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"

# Faixa etária (Termo de Uso, Cláusula 13 / art. 14 da LGPD)
IDADE_MINIMA_CADASTRO = 13
IDADE_MAIORIDADE = 18

# Formatos de imagem aceitos para a foto de perfil
EXTENSOES_FOTO = {"png", "jpg", "jpeg", "webp"}

# Faixas de XP acumulado -> nível (RF13). (xp_mínimo, nome)
FAIXAS_NIVEL = [
    (0, "iniciante"),
    (1000, "intermediario"),
    (3000, "avancado"),
    (7000, "profissional"),
    (15000, "elite"),
]

# Consentimentos LGPD (Termo de Uso, Cláusula Sexta / Termo de Consentimento,
# Cláusula Segunda). Os obrigatórios são gravados sempre como aceitos; os
# opcionais vêm marcados por padrão e o usuário pode desmarcar.
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
    """Erro de regra de negócio. `status` vira o código HTTP na resposta."""

    def __init__(self, mensagem, status=400):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status = status


class UsuarioService:

    # ---------- cadastro (RF01) ----------
    @staticmethod
    def cadastrar(dados):
        dados = dados or {}
        limpos = UsuarioService._validar(dados, senha_obrigatoria=True)

        if not dados.get("aceite_termos"):
            raise ErroValidacao(
                "É necessário ler e aceitar o Termo de Uso e o Termo de Consentimento."
            )

        # faixa etária e autorização do responsável legal (art. 14 da LGPD)
        limpos.update(UsuarioService._validar_faixa_etaria(limpos["idade"], dados))

        if UsuarioRepository.buscar_por_email(limpos["email"]):
            raise ErroValidacao("E-mail já cadastrado.", status=409)

        consentimentos = dados.get("consentimentos") or {}
        # sem consentimento de ranking público, o perfil não entra nos rankings
        limpos["perfil_publico"] = bool(consentimentos.get("ranking_publico", True))

        limpos["senha"] = generate_password_hash(limpos["senha"])
        usuario = UsuarioRepository.criar(limpos)
        ConsentimentoService.registrar_iniciais(usuario.id_usuario, consentimentos)
        return usuario

    # ---------- login (RF02) ----------
    @staticmethod
    def autenticar(email, senha):
        usuario = UsuarioRepository.buscar_por_email((email or "").strip())
        if not usuario or not check_password_hash(usuario.senha, senha or ""):
            raise ErroValidacao("E-mail ou senha incorretos.", status=401)
        return usuario

    # ---------- consulta ----------
    @staticmethod
    def listar(filtro_nome=None):
        return UsuarioRepository.listar(filtro_nome)

    @staticmethod
    def buscar(id_usuario):
        usuario = UsuarioRepository.buscar_por_id(id_usuario)
        if not usuario:
            raise ErroValidacao("Usuário não encontrado.", status=404)
        return usuario

    # ---------- atualização (RF03) ----------
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

    # ---------- foto de perfil (RF03) ----------
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

        # apaga qualquer foto anterior deste usuário
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

    # ---------- exclusão ----------
    @staticmethod
    def excluir(id_usuario):
        usuario = UsuarioService.buscar(id_usuario)
        UsuarioRepository.excluir(usuario)

    # ---------- estatísticas ----------
    @staticmethod
    def estatisticas():
        usuarios = UsuarioRepository.listar()
        total = len(usuarios)
        media_xp = round(sum(u.xp for u in usuarios) / total, 2) if total else 0
        return {"total_usuarios": total, "media_xp": media_xp}

    # ---------- helpers ----------
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
        """Regras de idade do art. 14 da LGPD. Devolve os campos do responsável."""
        if idade is None:
            raise ErroValidacao("Informe a idade.")

        if idade < IDADE_MINIMA_CADASTRO:
            raise ErroValidacao(
                "O cadastro não é permitido para menores de 13 anos (art. 14 da LGPD)."
            )

        if idade >= IDADE_MAIORIDADE:
            return {}

        # adolescente de 13 a 17 anos: exige autorização do responsável legal
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
    """Registro de treinos (RF04), histórico (RF05), pontuação (RF12)."""

    TIPOS_VALIDOS = {"musculacao", "cardio", "yoga", "outro"}

    # ---------- registrar treino (RF04 + RF12 + RF13) ----------
    @staticmethod
    def registrar(id_usuario, dados):
        usuario = UsuarioService.buscar(id_usuario)
        limpos = AtividadeService._validar(dados)

        limpos["pontuacao"] = AtividadeService.calcular_pontuacao(limpos)
        atividade = AtividadeRepository.criar(id_usuario, limpos)

        # atualiza XP acumulado e recalcula o nível automaticamente
        usuario.xp += atividade.pontuacao
        usuario.nivel = nivel_por_xp(usuario.xp)
        UsuarioRepository.salvar(usuario)

        return atividade, usuario

    # ---------- histórico (RF05) ----------
    @staticmethod
    def historico(id_usuario):
        UsuarioService.buscar(id_usuario)  # garante que o usuário existe
        return AtividadeRepository.listar_do_usuario(id_usuario)

    @staticmethod
    def buscar(id_atividade):
        atividade = AtividadeRepository.buscar_por_id(id_atividade)
        if not atividade:
            raise ErroValidacao("Atividade não encontrada.", status=404)
        return atividade

    # ---------- excluir treino (desconta a pontuação) ----------
    @staticmethod
    def excluir(id_atividade):
        atividade = AtividadeService.buscar(id_atividade)
        usuario = UsuarioRepository.buscar_por_id(atividade.id_usuario)
        if usuario:
            usuario.xp = max(0, usuario.xp - atividade.pontuacao)
            usuario.nivel = nivel_por_xp(usuario.xp)
            UsuarioRepository.salvar(usuario)
        AtividadeRepository.excluir(atividade)

    # ---------- RF12: cálculo automático da pontuação ----------
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

    # ---------- validação ----------
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
            numericos[campo] = valor

        if not numericos["tempo_min"] and not numericos["distancia_km"]:
            raise ErroValidacao("Informe ao menos a duração ou a distância do treino.")

        return {
            "tipo": tipo,
            "titulo": (dados.get("titulo") or None),
            "descricao": (dados.get("descricao") or None),
            **numericos,
        }


class ConsentimentoService:
    """Consentimento LGPD granular (Termo de Uso/Consentimento)."""

    # ---------- gravado no cadastro ----------
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
                "aceito": bool(escolhas.get(chave, True)),  # marcado por padrão
            })

        return ConsentimentoRepository.criar_varios(id_usuario, registros)

    # ---------- consulta ----------
    @staticmethod
    def listar(id_usuario):
        UsuarioService.buscar(id_usuario)
        return ConsentimentoRepository.listar_do_usuario(id_usuario)

    # ---------- revogar / reativar um consentimento opcional ----------
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

        # a visibilidade pública do perfil acompanha o consentimento de ranking
        if chave == "ranking_publico":
            usuario = UsuarioRepository.buscar_por_id(id_usuario)
            usuario.perfil_publico = registro.aceito
            UsuarioRepository.salvar(usuario)

        return registro


class RankingService:
    """Rankings global e regional (RF10, RF11) a partir das views SQL."""

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
    def resumo_usuario(id_usuario):
        """Posição do usuário nos rankings - usado no card 'Ranking Local'."""
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
