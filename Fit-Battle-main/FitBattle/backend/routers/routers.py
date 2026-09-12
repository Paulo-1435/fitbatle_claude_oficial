from flask import Blueprint

from controllers.controller import (
    AtividadeController,
    ConsentimentoController,
    RankingController,
    UsuarioController,
)

Fitbattle_bp = Blueprint("fitbattle", __name__, url_prefix="/api")


def rota(regra, endpoint, view, metodos):
    Fitbattle_bp.add_url_rule(regra, endpoint=endpoint, view_func=view, methods=metodos)


rota("/usuarios", "usuario_cadastrar", UsuarioController.cadastrar, ["POST"])
rota("/usuarios", "usuario_listar", UsuarioController.listar, ["GET"])
rota("/usuarios/<int:id_usuario>", "usuario_buscar", UsuarioController.buscar, ["GET"])
rota("/usuarios/<int:id_usuario>", "usuario_atualizar", UsuarioController.atualizar, ["PUT"])
rota("/usuarios/<int:id_usuario>", "usuario_excluir", UsuarioController.excluir, ["DELETE"])
rota("/usuarios/<int:id_usuario>/foto", "usuario_foto", UsuarioController.upload_foto, ["POST"])
rota("/login", "usuario_login", UsuarioController.login, ["POST"])

rota("/usuarios/<int:id_usuario>/atividades", "atividade_registrar", AtividadeController.registrar, ["POST"])
rota("/usuarios/<int:id_usuario>/atividades", "atividade_historico", AtividadeController.historico, ["GET"])
rota("/atividades/<int:id_atividade>", "atividade_buscar", AtividadeController.buscar, ["GET"])
rota("/atividades/<int:id_atividade>", "atividade_excluir", AtividadeController.excluir, ["DELETE"])

rota("/ranking/global", "ranking_global", RankingController.ranking_global, ["GET"])
rota("/ranking/regional", "ranking_regional", RankingController.ranking_regional, ["GET"])
rota("/usuarios/<int:id_usuario>/ranking", "usuario_ranking",
     RankingController.resumo_usuario, ["GET"])

rota("/usuarios/<int:id_usuario>/consentimentos", "consentimento_listar",
     ConsentimentoController.listar, ["GET"])
rota("/usuarios/<int:id_usuario>/consentimentos/<chave>", "consentimento_atualizar",
     ConsentimentoController.atualizar, ["PUT"])

rota("/estatisticas", "estatisticas", UsuarioController.estatisticas, ["GET"])
