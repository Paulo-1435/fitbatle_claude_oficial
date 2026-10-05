import os
import secrets
from functools import wraps

from flask import current_app, g, jsonify, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

VALIDADE_TOKEN_SEGUNDOS = 7 * 24 * 60 * 60
SALT_TOKEN = "fitbattle-auth"
ARQUIVO_CHAVE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".secret_key")


def carregar_chave_secreta():
    chave = os.getenv("SECRET_KEY")
    if chave:
        return chave

    try:
        with open(ARQUIVO_CHAVE, "r", encoding="utf-8") as arquivo:
            chave = arquivo.read().strip()
            if chave:
                return chave
    except FileNotFoundError:
        pass

    chave = secrets.token_hex(32)
    try:
        descritor = os.open(ARQUIVO_CHAVE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        with open(ARQUIVO_CHAVE, "r", encoding="utf-8") as arquivo:
            return arquivo.read().strip()
    with os.fdopen(descritor, "w", encoding="utf-8") as arquivo:
        arquivo.write(chave)
    return chave


def _serializador():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=SALT_TOKEN)


def gerar_token(id_usuario):
    return _serializador().dumps({"id": id_usuario})


def ler_token(token):
    try:
        dados = _serializador().loads(token, max_age=VALIDADE_TOKEN_SEGUNDOS)
    except (BadSignature, SignatureExpired):
        return None
    if not isinstance(dados, dict) or not isinstance(dados.get("id"), int):
        return None
    return dados["id"]


def _token_do_cabecalho():
    cabecalho = request.headers.get("Authorization", "")
    partes = cabecalho.split(" ", 1)
    if len(partes) == 2 and partes[0].lower() == "bearer" and partes[1].strip():
        return partes[1].strip()
    return None


def _nao_autenticado():
    return jsonify({"erro": "Autenticação necessária."}), 401


def protegido(view, dono=False):
    @wraps(view)
    def envolvida(*args, **kwargs):
        from repositories.repository import UsuarioRepository

        token = _token_do_cabecalho()
        id_usuario = ler_token(token) if token else None
        usuario = UsuarioRepository.buscar_por_id(id_usuario) if id_usuario else None
        if usuario is None:
            return _nao_autenticado()

        g.usuario_atual = usuario

        if dono and kwargs.get("id_usuario") != usuario.id_usuario:
            return jsonify({"erro": "Você não tem permissão para acessar este recurso."}), 403

        return view(*args, **kwargs)

    return envolvida
