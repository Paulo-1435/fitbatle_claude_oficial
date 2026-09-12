from flask import current_app, jsonify, request

from services.service import (
    AtividadeService,
    ConsentimentoService,
    ErroValidacao,
    RankingService,
    UsuarioService,
)


class UsuarioController:

    @staticmethod
    def cadastrar():
        try:
            usuario = UsuarioService.cadastrar(request.get_json(silent=True))
            return jsonify({
                "mensagem": "Cadastro concluído!",
                "usuario": usuario.to_dict(),
            }), 201
        except ErroValidacao as erro:
            return jsonify({"erro": erro.mensagem}), erro.status

    @staticmethod
    def login():
        dados = request.get_json(silent=True) or {}
        try:
            usuario = UsuarioService.autenticar(dados.get("email"), dados.get("senha"))
            return jsonify({"mensagem": "Login efetuado!", "usuario": usuario.to_dict()})
        except ErroValidacao as erro:
            return jsonify({"erro": erro.mensagem}), erro.status

    @staticmethod
    def listar():
        usuarios = UsuarioService.listar(request.args.get("nome"))
        return jsonify([u.to_dict() for u in usuarios])

    @staticmethod
    def buscar(id_usuario):
        try:
            return jsonify(UsuarioService.buscar(id_usuario).to_dict())
        except ErroValidacao as erro:
            return jsonify({"erro": erro.mensagem}), erro.status

    @staticmethod
    def atualizar(id_usuario):
        try:
            usuario = UsuarioService.atualizar(id_usuario, request.get_json(silent=True))
            return jsonify({
                "mensagem": "Usuário atualizado.",
                "usuario": usuario.to_dict(),
            })
        except ErroValidacao as erro:
            return jsonify({"erro": erro.mensagem}), erro.status

    @staticmethod
    def excluir(id_usuario):
        try:
            UsuarioService.excluir(id_usuario)
            return jsonify({"mensagem": "Usuário excluído.", "id": id_usuario})
        except ErroValidacao as erro:
            return jsonify({"erro": erro.mensagem}), erro.status

    @staticmethod
    def upload_foto(id_usuario):
        try:
            usuario = UsuarioService.salvar_foto(
                id_usuario,
                request.files.get("foto"),
                current_app.config["UPLOAD_FOLDER"],
            )
            return jsonify({"mensagem": "Foto atualizada.", "usuario": usuario.to_dict()})
        except ErroValidacao as erro:
            return jsonify({"erro": erro.mensagem}), erro.status

    @staticmethod
    def estatisticas():
        return jsonify(UsuarioService.estatisticas())


class AtividadeController:

    @staticmethod
    def registrar(id_usuario):
        try:
            atividade, usuario = AtividadeService.registrar(
                id_usuario, request.get_json(silent=True)
            )
            return jsonify({
                "mensagem": "Treino registrado!",
                "pontuacao_ganha": atividade.pontuacao,
                "atividade": atividade.to_dict(),
                "usuario": usuario.to_dict(),
            }), 201
        except ErroValidacao as erro:
            return jsonify({"erro": erro.mensagem}), erro.status

    @staticmethod
    def historico(id_usuario):
        try:
            atividades = AtividadeService.historico(id_usuario)
            return jsonify([a.to_dict() for a in atividades])
        except ErroValidacao as erro:
            return jsonify({"erro": erro.mensagem}), erro.status

    @staticmethod
    def buscar(id_atividade):
        try:
            return jsonify(AtividadeService.buscar(id_atividade).to_dict())
        except ErroValidacao as erro:
            return jsonify({"erro": erro.mensagem}), erro.status

    @staticmethod
    def excluir(id_atividade):
        try:
            AtividadeService.excluir(id_atividade)
            return jsonify({"mensagem": "Atividade excluída.", "id": id_atividade})
        except ErroValidacao as erro:
            return jsonify({"erro": erro.mensagem}), erro.status


class RankingController:

    @staticmethod
    def ranking_global():
        return jsonify(RankingService.global_(request.args.get("limite", 20)))

    @staticmethod
    def ranking_regional():
        try:
            dados = RankingService.regional(
                request.args.get("cidade"), request.args.get("limite", 20)
            )
            return jsonify(dados)
        except ErroValidacao as erro:
            return jsonify({"erro": erro.mensagem}), erro.status

    @staticmethod
    def resumo_usuario(id_usuario):
        try:
            return jsonify(RankingService.resumo_usuario(id_usuario))
        except ErroValidacao as erro:
            return jsonify({"erro": erro.mensagem}), erro.status


class ConsentimentoController:

    @staticmethod
    def listar(id_usuario):
        try:
            registros = ConsentimentoService.listar(id_usuario)
            return jsonify([c.to_dict() for c in registros])
        except ErroValidacao as erro:
            return jsonify({"erro": erro.mensagem}), erro.status

    @staticmethod
    def atualizar(id_usuario, chave):
        dados = request.get_json(silent=True) or {}
        try:
            registro = ConsentimentoService.atualizar(id_usuario, chave, dados.get("aceito"))
            return jsonify({
                "mensagem": "Consentimento atualizado.",
                "consentimento": registro.to_dict(),
            })
        except ErroValidacao as erro:
            return jsonify({"erro": erro.mensagem}), erro.status
