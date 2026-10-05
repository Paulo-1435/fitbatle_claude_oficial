from flask import current_app, g, jsonify, request

from auth import gerar_token
from services.service import (
    AtividadeService,
    ComentarioService,
    ConsentimentoService,
    ConviteService,
    CurtidaService,
    ErroValidacao,
    FeedService,
    GrupoService,
    MetaService,
    PostagemService,
    RankingService,
    UsuarioService,
)


def _id_logado():
    return g.usuario_atual.id_usuario


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
            return jsonify({
                "mensagem": "Login efetuado!",
                "token": gerar_token(usuario.id_usuario),
                "usuario": usuario.to_dict(),
            })
        except ErroValidacao as erro:
            return jsonify({"erro": erro.mensagem}), erro.status

    @staticmethod
    def eu():
        return jsonify({"usuario": g.usuario_atual.to_dict()})

    @staticmethod
    def busca():
        try:
            usuarios = UsuarioService.buscar_por_termo(
                request.args.get("nome"), _id_logado()
            )
            return jsonify([u.to_publico() for u in usuarios])
        except ErroValidacao as erro:
            return jsonify({"erro": erro.mensagem}), erro.status

    @staticmethod
    def buscar(id_usuario):
        try:
            usuario = UsuarioService.buscar_visivel(id_usuario, _id_logado())
            if usuario.id_usuario == _id_logado():
                return jsonify(usuario.to_dict())
            return jsonify(usuario.to_publico())
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
            UsuarioService.excluir(id_usuario, current_app.config["UPLOAD_FOLDER"])
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
            return jsonify(AtividadeService.buscar_visivel(id_atividade, _id_logado()).to_dict())
        except ErroValidacao as erro:
            return jsonify({"erro": erro.mensagem}), erro.status

    @staticmethod
    def excluir(id_atividade):
        try:
            AtividadeService.excluir(_id_logado(), id_atividade)
            return jsonify({"mensagem": "Atividade excluída.", "id": id_atividade})
        except ErroValidacao as erro:
            return jsonify({"erro": erro.mensagem}), erro.status


class PostagemController:

    @staticmethod
    def criar():
        try:
            postagem = PostagemService.criar(
                _id_logado(),
                request.form.get("texto"),
                request.files.get("foto"),
                current_app.config["UPLOAD_FOLDER"],
            )
            return jsonify({
                "mensagem": "Postagem publicada!",
                "postagem": postagem.to_dict(),
            }), 201
        except ErroValidacao as erro:
            return jsonify({"erro": erro.mensagem}), erro.status

    @staticmethod
    def excluir(id_postagem):
        try:
            PostagemService.excluir(_id_logado(), id_postagem)
            return jsonify({"mensagem": "Postagem excluída.", "id": id_postagem})
        except ErroValidacao as erro:
            return jsonify({"erro": erro.mensagem}), erro.status


class FeedController:

    @staticmethod
    def listar():
        limite = request.args.get("limite", 30)
        return jsonify(FeedService.listar(_id_logado(), limite))


class CurtidaController:

    @staticmethod
    def alternar(tipo_alvo, id_alvo):
        try:
            resultado = CurtidaService.alternar(_id_logado(), tipo_alvo, id_alvo)
            return jsonify(resultado)
        except ErroValidacao as erro:
            return jsonify({"erro": erro.mensagem}), erro.status


class ComentarioController:

    @staticmethod
    def listar(tipo_alvo, id_alvo):
        try:
            comentarios = ComentarioService.listar(tipo_alvo, id_alvo)
            return jsonify(comentarios)
        except ErroValidacao as erro:
            return jsonify({"erro": erro.mensagem}), erro.status

    @staticmethod
    def criar(tipo_alvo, id_alvo):
        dados = request.get_json(silent=True) or {}
        try:
            comentario = ComentarioService.criar(
                _id_logado(), tipo_alvo, id_alvo, dados.get("texto")
            )
            resultado = comentario.to_dict()
            autor = UsuarioService.buscar(comentario.id_usuario)
            resultado["usuario"] = {
                "id": autor.id_usuario, "nome": autor.nome, "foto": autor.foto,
            }
            return jsonify({"mensagem": "Comentário publicado.", "comentario": resultado}), 201
        except ErroValidacao as erro:
            return jsonify({"erro": erro.mensagem}), erro.status

    @staticmethod
    def excluir(id_comentario):
        try:
            ComentarioService.excluir(_id_logado(), id_comentario)
            return jsonify({"mensagem": "Comentário excluído.", "id": id_comentario})
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
    def ranking_por_exercicio():
        try:
            dados = RankingService.por_exercicio(
                request.args.get("titulo"),
                request.args.get("cidade"),
                request.args.get("limite", 20),
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


class GrupoController:

    @staticmethod
    def criar():
        try:
            grupo = GrupoService.criar(_id_logado(), request.get_json(silent=True))
            return jsonify({"mensagem": "Grupo criado!", "grupo": grupo.to_dict()}), 201
        except ErroValidacao as erro:
            return jsonify({"erro": erro.mensagem}), erro.status

    @staticmethod
    def listar_meus():
        return jsonify(GrupoService.listar_meus(_id_logado()))

    @staticmethod
    def detalhe(id_grupo):
        try:
            return jsonify(GrupoService.detalhe(id_grupo, _id_logado()))
        except ErroValidacao as erro:
            return jsonify({"erro": erro.mensagem}), erro.status

    @staticmethod
    def membros(id_grupo):
        try:
            return jsonify(GrupoService.membros(id_grupo, _id_logado()))
        except ErroValidacao as erro:
            return jsonify({"erro": erro.mensagem}), erro.status

    @staticmethod
    def ranking(id_grupo):
        try:
            return jsonify(GrupoService.ranking(id_grupo, _id_logado(), request.args.get("limite", 20)))
        except ErroValidacao as erro:
            return jsonify({"erro": erro.mensagem}), erro.status

    @staticmethod
    def convite_info(id_grupo):
        try:
            return jsonify(GrupoService.convite_info(id_grupo, _id_logado()))
        except ErroValidacao as erro:
            return jsonify({"erro": erro.mensagem}), erro.status

    @staticmethod
    def regenerar_convite(id_grupo):
        try:
            return jsonify(GrupoService.regenerar_codigo(id_grupo, _id_logado()))
        except ErroValidacao as erro:
            return jsonify({"erro": erro.mensagem}), erro.status

    @staticmethod
    def entrar():
        dados = request.get_json(silent=True) or {}
        try:
            grupo = GrupoService.entrar_por_codigo(_id_logado(), dados.get("codigo"))
            return jsonify({"mensagem": "Você entrou no grupo!", "grupo": grupo.to_dict()})
        except ErroValidacao as erro:
            return jsonify({"erro": erro.mensagem}), erro.status

    @staticmethod
    def buscar_para_convidar(id_grupo):
        try:
            resultado = GrupoService.buscar_para_convidar(
                id_grupo, _id_logado(), request.args.get("nome")
            )
            return jsonify(resultado)
        except ErroValidacao as erro:
            return jsonify({"erro": erro.mensagem}), erro.status

    @staticmethod
    def convidar(id_grupo):
        dados = request.get_json(silent=True) or {}
        try:
            convite = GrupoService.convidar(id_grupo, _id_logado(), dados.get("id_usuario"))
            return jsonify({"mensagem": "Convite enviado!", "id": convite.id_convite}), 201
        except ErroValidacao as erro:
            return jsonify({"erro": erro.mensagem}), erro.status


class ConviteController:

    @staticmethod
    def meus_recebidos():
        return jsonify(ConviteService.meus_recebidos(_id_logado()))

    @staticmethod
    def responder(id_convite):
        dados = request.get_json(silent=True) or {}
        try:
            ConviteService.responder(id_convite, _id_logado(), dados.get("aceito"))
            return jsonify({"mensagem": "Convite respondido.", "id": id_convite})
        except ErroValidacao as erro:
            return jsonify({"erro": erro.mensagem}), erro.status


class MetaController:

    @staticmethod
    def criar():
        try:
            meta = MetaService.criar(_id_logado(), request.get_json(silent=True))
            return jsonify({"mensagem": "Meta criada!", "meta": meta}), 201
        except ErroValidacao as erro:
            return jsonify({"erro": erro.mensagem}), erro.status

    @staticmethod
    def listar():
        return jsonify(MetaService.listar_do_usuario(_id_logado()))

    @staticmethod
    def detalhe(id_meta):
        try:
            return jsonify(MetaService.detalhe(id_meta, _id_logado()))
        except ErroValidacao as erro:
            return jsonify({"erro": erro.mensagem}), erro.status

    @staticmethod
    def atualizar(id_meta):
        try:
            meta = MetaService.atualizar(id_meta, _id_logado(), request.get_json(silent=True))
            return jsonify({"mensagem": "Meta atualizada.", "meta": meta})
        except ErroValidacao as erro:
            return jsonify({"erro": erro.mensagem}), erro.status

    @staticmethod
    def excluir(id_meta):
        try:
            MetaService.excluir(id_meta, _id_logado())
            return jsonify({"mensagem": "Meta excluída.", "id": id_meta})
        except ErroValidacao as erro:
            return jsonify({"erro": erro.mensagem}), erro.status
