from flask import Blueprint

from auth import protegido
from controllers.controller import (
    AtividadeController,
    ComentarioController,
    ConsentimentoController,
    ConviteController,
    CurtidaController,
    FeedController,
    GrupoController,
    MetaController,
    PostagemController,
    RankingController,
    UsuarioController,
)

Fitbattle_bp = Blueprint("fitbattle", __name__, url_prefix="/api")

PUBLICO = "publico"
LOGADO = "logado"
DONO = "dono"


def rota(regra, endpoint, view, metodos, acesso=LOGADO):
    if acesso == LOGADO:
        view = protegido(view)
    elif acesso == DONO:
        view = protegido(view, dono=True)
    Fitbattle_bp.add_url_rule(regra, endpoint=endpoint, view_func=view, methods=metodos)


rota("/usuarios", "usuario_cadastrar", UsuarioController.cadastrar, ["POST"], PUBLICO)
rota("/login", "usuario_login", UsuarioController.login, ["POST"], PUBLICO)
rota("/estatisticas", "estatisticas", UsuarioController.estatisticas, ["GET"], PUBLICO)

rota("/eu", "usuario_eu", UsuarioController.eu, ["GET"], LOGADO)
rota("/usuarios/busca", "usuario_busca", UsuarioController.busca, ["GET"], LOGADO)
rota("/usuarios/<int:id_usuario>", "usuario_buscar", UsuarioController.buscar, ["GET"], LOGADO)
rota("/usuarios/<int:id_usuario>", "usuario_atualizar", UsuarioController.atualizar, ["PUT"], DONO)
rota("/usuarios/<int:id_usuario>", "usuario_excluir", UsuarioController.excluir, ["DELETE"], DONO)
rota("/usuarios/<int:id_usuario>/foto", "usuario_foto", UsuarioController.upload_foto, ["POST"], DONO)

rota("/usuarios/<int:id_usuario>/atividades", "atividade_registrar",
     AtividadeController.registrar, ["POST"], DONO)
rota("/usuarios/<int:id_usuario>/atividades", "atividade_historico",
     AtividadeController.historico, ["GET"], DONO)
rota("/atividades/<int:id_atividade>", "atividade_buscar", AtividadeController.buscar, ["GET"], LOGADO)
rota("/atividades/<int:id_atividade>", "atividade_excluir", AtividadeController.excluir, ["DELETE"], LOGADO)

rota("/postagens", "postagem_criar", PostagemController.criar, ["POST"], LOGADO)
rota("/postagens/<int:id_postagem>", "postagem_excluir", PostagemController.excluir, ["DELETE"], LOGADO)

rota("/feed", "feed_listar", FeedController.listar, ["GET"], LOGADO)
rota("/feed/<tipo_alvo>/<int:id_alvo>/curtir", "curtida_alternar",
     CurtidaController.alternar, ["POST"], LOGADO)
rota("/feed/<tipo_alvo>/<int:id_alvo>/comentarios", "comentario_listar",
     ComentarioController.listar, ["GET"], LOGADO)
rota("/feed/<tipo_alvo>/<int:id_alvo>/comentarios", "comentario_criar",
     ComentarioController.criar, ["POST"], LOGADO)
rota("/comentarios/<int:id_comentario>", "comentario_excluir",
     ComentarioController.excluir, ["DELETE"], LOGADO)

rota("/ranking/global", "ranking_global", RankingController.ranking_global, ["GET"], LOGADO)
rota("/ranking/regional", "ranking_regional", RankingController.ranking_regional, ["GET"], LOGADO)
rota("/ranking/exercicio", "ranking_por_exercicio", RankingController.ranking_por_exercicio, ["GET"], LOGADO)
rota("/usuarios/<int:id_usuario>/ranking", "usuario_ranking",
     RankingController.resumo_usuario, ["GET"], DONO)

rota("/usuarios/<int:id_usuario>/consentimentos", "consentimento_listar",
     ConsentimentoController.listar, ["GET"], DONO)
rota("/usuarios/<int:id_usuario>/consentimentos/<chave>", "consentimento_atualizar",
     ConsentimentoController.atualizar, ["PUT"], DONO)

rota("/grupos", "grupo_criar", GrupoController.criar, ["POST"], LOGADO)
rota("/grupos", "grupo_listar_meus", GrupoController.listar_meus, ["GET"], LOGADO)
rota("/grupos/entrar", "grupo_entrar", GrupoController.entrar, ["POST"], LOGADO)
rota("/grupos/<int:id_grupo>", "grupo_detalhe", GrupoController.detalhe, ["GET"], LOGADO)
rota("/grupos/<int:id_grupo>/membros", "grupo_membros", GrupoController.membros, ["GET"], LOGADO)
rota("/grupos/<int:id_grupo>/ranking", "grupo_ranking", GrupoController.ranking, ["GET"], LOGADO)
rota("/grupos/<int:id_grupo>/convite", "grupo_convite_info", GrupoController.convite_info, ["GET"], LOGADO)
rota("/grupos/<int:id_grupo>/convite/regenerar", "grupo_convite_regenerar",
     GrupoController.regenerar_convite, ["POST"], LOGADO)
rota("/grupos/<int:id_grupo>/busca-convidar", "grupo_busca_convidar",
     GrupoController.buscar_para_convidar, ["GET"], LOGADO)
rota("/grupos/<int:id_grupo>/convites", "grupo_convidar", GrupoController.convidar, ["POST"], LOGADO)

rota("/convites", "convite_listar_recebidos", ConviteController.meus_recebidos, ["GET"], LOGADO)
rota("/convites/<int:id_convite>", "convite_responder", ConviteController.responder, ["PUT"], LOGADO)

rota("/metas", "meta_criar", MetaController.criar, ["POST"], LOGADO)
rota("/metas", "meta_listar", MetaController.listar, ["GET"], LOGADO)
rota("/metas/<int:id_meta>", "meta_detalhe", MetaController.detalhe, ["GET"], LOGADO)
rota("/metas/<int:id_meta>", "meta_atualizar", MetaController.atualizar, ["PUT"], LOGADO)
rota("/metas/<int:id_meta>", "meta_excluir", MetaController.excluir, ["DELETE"], LOGADO)
