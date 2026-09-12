from sqlalchemy import func, text

from database import db
from models.model import Atividade, Comentario, Consentimento, Curtida, Postagem, Usuario

_COLUNAS_RANKING = "id_usuario, nome, cidade, estado, pontuacao_total, posicao"

_CAMPOS_EDITAVEIS = (
    "nome", "email", "idade", "peso", "altura",
    "cidade", "estado", "foto", "descricao",
)


class UsuarioRepository:

    @staticmethod
    def listar(filtro_nome=None):
        query = Usuario.query
        if filtro_nome:
            query = query.filter(Usuario.nome.like(f"%{filtro_nome}%"))
        return query.order_by(Usuario.nome).all()

    @staticmethod
    def buscar_por_id(id_usuario):
        return db.session.get(Usuario, id_usuario)

    @staticmethod
    def buscar_por_email(email):
        return Usuario.query.filter_by(email=email).first()

    @staticmethod
    def criar(dados):
        usuario = Usuario(
            nome=dados["nome"],
            email=dados["email"],
            senha=dados["senha"],
            idade=dados.get("idade"),
            cidade=dados.get("cidade"),
            estado=dados.get("estado"),
            descricao=dados.get("descricao"),
            perfil_publico=dados.get("perfil_publico", True),
            responsavel_nome=dados.get("responsavel_nome"),
            responsavel_email=dados.get("responsavel_email"),
            responsavel_autorizado_em=dados.get("responsavel_autorizado_em"),
        )
        db.session.add(usuario)
        db.session.commit()
        return usuario

    @staticmethod
    def atualizar(usuario, dados):
        for campo in _CAMPOS_EDITAVEIS:
            if dados.get(campo) is not None:
                setattr(usuario, campo, dados[campo])
        if dados.get("senha"):
            usuario.senha = dados["senha"]
        db.session.commit()
        return usuario

    @staticmethod
    def excluir(usuario):
        db.session.delete(usuario)
        db.session.commit()

    @staticmethod
    def salvar(usuario):
        db.session.add(usuario)
        db.session.commit()
        return usuario


class AtividadeRepository:

    @staticmethod
    def listar_do_usuario(id_usuario):
        return (
            Atividade.query.filter_by(id_usuario=id_usuario)
            .order_by(Atividade.data_registro.desc())
            .all()
        )

    @staticmethod
    def buscar_por_id(id_atividade):
        return db.session.get(Atividade, id_atividade)

    @staticmethod
    def criar(id_usuario, dados):
        atividade = Atividade(
            id_usuario=id_usuario,
            tipo=dados["tipo"],
            titulo=dados.get("titulo"),
            descricao=dados.get("descricao"),
            tempo_min=dados.get("tempo_min"),
            distancia_km=dados.get("distancia_km"),
            carga_kg=dados.get("carga_kg"),
            repeticoes=dados.get("repeticoes"),
            pontuacao=dados["pontuacao"],
        )
        db.session.add(atividade)
        db.session.commit()
        return atividade

    @staticmethod
    def excluir(atividade):
        db.session.delete(atividade)
        db.session.commit()

    @staticmethod
    def listar_publicas(limite):
        return (
            Atividade.query.join(Usuario, Atividade.id_usuario == Usuario.id_usuario)
            .filter(Usuario.perfil_publico.is_(True))
            .order_by(Atividade.data_registro.desc())
            .limit(limite)
            .all()
        )


class PostagemRepository:

    @staticmethod
    def buscar_por_id(id_postagem):
        return db.session.get(Postagem, id_postagem)

    @staticmethod
    def criar(id_usuario, texto, foto):
        postagem = Postagem(id_usuario=id_usuario, texto=texto, foto=foto)
        db.session.add(postagem)
        db.session.commit()
        return postagem

    @staticmethod
    def excluir(postagem):
        db.session.delete(postagem)
        db.session.commit()

    @staticmethod
    def listar_publicas(limite):
        return (
            Postagem.query.join(Usuario, Postagem.id_usuario == Usuario.id_usuario)
            .filter(Usuario.perfil_publico.is_(True))
            .order_by(Postagem.data_registro.desc())
            .limit(limite)
            .all()
        )


class CurtidaRepository:

    @staticmethod
    def buscar(id_usuario, tipo_alvo, id_alvo):
        return Curtida.query.filter_by(
            id_usuario=id_usuario, tipo_alvo=tipo_alvo, id_alvo=id_alvo
        ).first()

    @staticmethod
    def curtir(id_usuario, tipo_alvo, id_alvo):
        curtida = Curtida(id_usuario=id_usuario, tipo_alvo=tipo_alvo, id_alvo=id_alvo)
        db.session.add(curtida)
        db.session.commit()
        return curtida

    @staticmethod
    def descurtir(curtida):
        db.session.delete(curtida)
        db.session.commit()

    @staticmethod
    def contar(tipo_alvo, id_alvo):
        return Curtida.query.filter_by(tipo_alvo=tipo_alvo, id_alvo=id_alvo).count()

    @staticmethod
    def contar_em_lote(tipo_alvo, ids_alvo):
        if not ids_alvo:
            return {}
        linhas = (
            db.session.query(Curtida.id_alvo, func.count(Curtida.id_curtida))
            .filter(Curtida.tipo_alvo == tipo_alvo, Curtida.id_alvo.in_(ids_alvo))
            .group_by(Curtida.id_alvo)
            .all()
        )
        return {id_alvo: total for id_alvo, total in linhas}

    @staticmethod
    def curtidos_pelo_usuario(id_usuario, tipo_alvo, ids_alvo):
        if not ids_alvo:
            return set()
        linhas = (
            db.session.query(Curtida.id_alvo)
            .filter(
                Curtida.id_usuario == id_usuario,
                Curtida.tipo_alvo == tipo_alvo,
                Curtida.id_alvo.in_(ids_alvo),
            )
            .all()
        )
        return {id_alvo for (id_alvo,) in linhas}

    @staticmethod
    def excluir_do_alvo(tipo_alvo, id_alvo):
        Curtida.query.filter_by(tipo_alvo=tipo_alvo, id_alvo=id_alvo).delete()
        db.session.commit()


class ComentarioRepository:

    @staticmethod
    def buscar_por_id(id_comentario):
        return db.session.get(Comentario, id_comentario)

    @staticmethod
    def criar(id_usuario, tipo_alvo, id_alvo, texto):
        comentario = Comentario(
            id_usuario=id_usuario, tipo_alvo=tipo_alvo, id_alvo=id_alvo, texto=texto
        )
        db.session.add(comentario)
        db.session.commit()
        return comentario

    @staticmethod
    def excluir(comentario):
        db.session.delete(comentario)
        db.session.commit()

    @staticmethod
    def listar(tipo_alvo, id_alvo):
        return (
            Comentario.query.filter_by(tipo_alvo=tipo_alvo, id_alvo=id_alvo)
            .order_by(Comentario.data_registro.asc())
            .all()
        )

    @staticmethod
    def contar_em_lote(tipo_alvo, ids_alvo):
        if not ids_alvo:
            return {}
        linhas = (
            db.session.query(Comentario.id_alvo, func.count(Comentario.id_comentario))
            .filter(Comentario.tipo_alvo == tipo_alvo, Comentario.id_alvo.in_(ids_alvo))
            .group_by(Comentario.id_alvo)
            .all()
        )
        return {id_alvo: total for id_alvo, total in linhas}

    @staticmethod
    def excluir_do_alvo(tipo_alvo, id_alvo):
        Comentario.query.filter_by(tipo_alvo=tipo_alvo, id_alvo=id_alvo).delete()
        db.session.commit()


class ConsentimentoRepository:

    @staticmethod
    def listar_do_usuario(id_usuario):
        return (
            Consentimento.query.filter_by(id_usuario=id_usuario)
            .order_by(Consentimento.obrigatorio.desc(), Consentimento.id_consentimento)
            .all()
        )

    @staticmethod
    def buscar(id_usuario, chave):
        return Consentimento.query.filter_by(id_usuario=id_usuario, chave=chave).first()

    @staticmethod
    def criar_varios(id_usuario, registros):
        objetos = [Consentimento(id_usuario=id_usuario, **r) for r in registros]
        db.session.add_all(objetos)
        db.session.commit()
        return objetos

    @staticmethod
    def salvar(consentimento):
        db.session.add(consentimento)
        db.session.commit()
        return consentimento


def _linha_ranking(linha):
    if linha is None:
        return None
    d = dict(linha)
    if "pontuacao_total" in d:
        d["pontuacao_total"] = int(d["pontuacao_total"] or 0)
    if "posicao" in d and d["posicao"] is not None:
        d["posicao"] = int(d["posicao"])
    return d


class RankingRepository:

    @staticmethod
    def global_(limite):
        sql = text(
            f"SELECT {_COLUNAS_RANKING} FROM vw_ranking_global "
            "ORDER BY posicao LIMIT :lim"
        )
        linhas = db.session.execute(sql, {"lim": limite}).mappings()
        return [_linha_ranking(linha) for linha in linhas]

    @staticmethod
    def regional(cidade, limite):
        sql = text(
            f"SELECT {_COLUNAS_RANKING} FROM vw_ranking_regional "
            "WHERE cidade = :cidade ORDER BY posicao LIMIT :lim"
        )
        linhas = db.session.execute(sql, {"cidade": cidade, "lim": limite}).mappings()
        return [_linha_ranking(linha) for linha in linhas]

    @staticmethod
    def minha_posicao_global(id_usuario):
        sql = text(
            "SELECT posicao, pontuacao_total FROM vw_ranking_global "
            "WHERE id_usuario = :id"
        )
        return _linha_ranking(db.session.execute(sql, {"id": id_usuario}).mappings().first())

    @staticmethod
    def minha_posicao_regional(id_usuario):
        sql = text(
            "SELECT posicao, pontuacao_total, cidade FROM vw_ranking_regional "
            "WHERE id_usuario = :id"
        )
        return _linha_ranking(db.session.execute(sql, {"id": id_usuario}).mappings().first())
