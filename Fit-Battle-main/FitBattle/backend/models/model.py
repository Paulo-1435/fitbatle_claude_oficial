from datetime import datetime, timezone

from database import db


def _agora():
    return datetime.now(timezone.utc)


def _iso_utc(valor):
    if valor is None:
        return None
    if valor.tzinfo is None:
        valor = valor.replace(tzinfo=timezone.utc)
    return valor.isoformat()


class Usuario(db.Model):
    __tablename__ = "usuario"

    id_usuario = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    senha = db.Column(db.String(255), nullable=False)
    idade = db.Column(db.SmallInteger)
    peso = db.Column(db.Numeric(5, 2))
    altura = db.Column(db.Numeric(3, 2))
    cidade = db.Column(db.String(100))
    estado = db.Column(db.String(2))
    foto = db.Column(db.String(255))
    descricao = db.Column(db.String(300))
    responsavel_nome = db.Column(db.String(120))
    responsavel_email = db.Column(db.String(150))
    responsavel_autorizado_em = db.Column(db.DateTime)
    nivel = db.Column(db.String(20), nullable=False, default="iniciante")
    xp = db.Column(db.Integer, nullable=False, default=0)
    perfil_publico = db.Column(db.Boolean, nullable=False, default=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=_agora)

    atividades = db.relationship(
        "Atividade",
        backref="usuario",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    consentimentos = db.relationship(
        "Consentimento",
        backref="usuario",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def to_dict(self):
        return {
            "id": self.id_usuario,
            "nome": self.nome,
            "email": self.email,
            "idade": self.idade,
            "peso": float(self.peso) if self.peso is not None else None,
            "altura": float(self.altura) if self.altura is not None else None,
            "cidade": self.cidade,
            "estado": self.estado,
            "foto": self.foto,
            "descricao": self.descricao,
            "nivel": self.nivel,
            "xp": self.xp,
            "perfil_publico": self.perfil_publico,
            "criado_em": _iso_utc(self.criado_em),
        }

    def to_publico(self):
        return {
            "id": self.id_usuario,
            "nome": self.nome,
            "cidade": self.cidade,
            "estado": self.estado,
            "foto": self.foto,
            "descricao": self.descricao,
            "nivel": self.nivel,
            "xp": self.xp,
            "criado_em": _iso_utc(self.criado_em),
        }


class Atividade(db.Model):
    __tablename__ = "atividade"

    id_atividade = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_usuario = db.Column(
        db.Integer,
        db.ForeignKey("usuario.id_usuario", ondelete="CASCADE"),
        nullable=False,
    )
    tipo = db.Column(db.String(60), nullable=False)
    titulo = db.Column(db.String(120))
    descricao = db.Column(db.String(500))
    tempo_min = db.Column(db.Integer)
    distancia_km = db.Column(db.Numeric(6, 2))
    carga_kg = db.Column(db.Numeric(6, 2))
    repeticoes = db.Column(db.Integer)
    pontuacao = db.Column(db.Integer, nullable=False, default=0)
    data_registro = db.Column(db.DateTime, nullable=False, default=_agora)

    def to_dict(self):
        return {
            "id": self.id_atividade,
            "id_usuario": self.id_usuario,
            "tipo": self.tipo,
            "titulo": self.titulo,
            "descricao": self.descricao,
            "tempo_min": self.tempo_min,
            "distancia_km": float(self.distancia_km) if self.distancia_km is not None else None,
            "carga_kg": float(self.carga_kg) if self.carga_kg is not None else None,
            "repeticoes": self.repeticoes,
            "pontuacao": self.pontuacao,
            "data_registro": _iso_utc(self.data_registro),
        }


class Postagem(db.Model):
    __tablename__ = "postagem"

    id_postagem = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_usuario = db.Column(
        db.Integer,
        db.ForeignKey("usuario.id_usuario", ondelete="CASCADE"),
        nullable=False,
    )
    texto = db.Column(db.String(1000), nullable=False)
    foto = db.Column(db.String(255))
    data_registro = db.Column(db.DateTime, nullable=False, default=_agora)

    def to_dict(self):
        return {
            "id": self.id_postagem,
            "id_usuario": self.id_usuario,
            "texto": self.texto,
            "foto": self.foto,
            "data_registro": _iso_utc(self.data_registro),
        }


class Curtida(db.Model):
    __tablename__ = "curtida"
    __table_args__ = (
        db.UniqueConstraint("id_usuario", "tipo_alvo", "id_alvo", name="uq_curtida_usuario_alvo"),
    )

    id_curtida = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_usuario = db.Column(
        db.Integer,
        db.ForeignKey("usuario.id_usuario", ondelete="CASCADE"),
        nullable=False,
    )
    tipo_alvo = db.Column(db.String(20), nullable=False)
    id_alvo = db.Column(db.Integer, nullable=False)
    data_registro = db.Column(db.DateTime, nullable=False, default=_agora)


class Comentario(db.Model):
    __tablename__ = "comentario"

    id_comentario = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_usuario = db.Column(
        db.Integer,
        db.ForeignKey("usuario.id_usuario", ondelete="CASCADE"),
        nullable=False,
    )
    tipo_alvo = db.Column(db.String(20), nullable=False)
    id_alvo = db.Column(db.Integer, nullable=False)
    texto = db.Column(db.String(500), nullable=False)
    data_registro = db.Column(db.DateTime, nullable=False, default=_agora)

    def to_dict(self):
        return {
            "id": self.id_comentario,
            "id_usuario": self.id_usuario,
            "texto": self.texto,
            "data_registro": _iso_utc(self.data_registro),
        }


class Grupo(db.Model):
    __tablename__ = "grupo"

    id_grupo = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome = db.Column(db.String(120), nullable=False)
    descricao = db.Column(db.String(300))
    privacidade = db.Column(db.String(10), nullable=False, default="privado")
    codigo_convite = db.Column(db.String(10), unique=True)
    id_criador = db.Column(
        db.Integer,
        db.ForeignKey("usuario.id_usuario", ondelete="CASCADE"),
        nullable=False,
    )
    data_criacao = db.Column(db.DateTime, nullable=False, default=_agora)

    def to_dict(self):
        return {
            "id": self.id_grupo,
            "nome": self.nome,
            "descricao": self.descricao,
            "id_criador": self.id_criador,
            "data_criacao": _iso_utc(self.data_criacao),
        }


class GrupoMembro(db.Model):
    __tablename__ = "grupo_membro"

    id_grupo = db.Column(
        db.Integer,
        db.ForeignKey("grupo.id_grupo", ondelete="CASCADE"),
        primary_key=True,
    )
    id_usuario = db.Column(
        db.Integer,
        db.ForeignKey("usuario.id_usuario", ondelete="CASCADE"),
        primary_key=True,
    )
    papel = db.Column(db.String(10), nullable=False, default="membro")
    entrou_em = db.Column(db.DateTime, nullable=False, default=_agora)


class Convite(db.Model):
    __tablename__ = "convite"
    __table_args__ = (
        db.UniqueConstraint("id_grupo", "id_destinatario", "status", name="uq_convite"),
    )

    id_convite = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_grupo = db.Column(
        db.Integer,
        db.ForeignKey("grupo.id_grupo", ondelete="CASCADE"),
        nullable=False,
    )
    id_remetente = db.Column(
        db.Integer,
        db.ForeignKey("usuario.id_usuario", ondelete="CASCADE"),
        nullable=False,
    )
    id_destinatario = db.Column(
        db.Integer,
        db.ForeignKey("usuario.id_usuario", ondelete="CASCADE"),
        nullable=False,
    )
    status = db.Column(db.String(10), nullable=False, default="pendente")
    data_envio = db.Column(db.DateTime, nullable=False, default=_agora)
    data_resposta = db.Column(db.DateTime)


class Meta(db.Model):
    __tablename__ = "meta"

    id_meta = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_usuario = db.Column(
        db.Integer,
        db.ForeignKey("usuario.id_usuario", ondelete="CASCADE"),
        nullable=False,
    )
    descricao = db.Column(db.String(300), nullable=False)
    tipo = db.Column(db.String(12), nullable=False, default="curto_prazo")
    tipo_metrica = db.Column(db.String(12), nullable=False)
    exercicio = db.Column(db.String(120))
    valor_objetivo = db.Column(db.Numeric(8, 2), nullable=False)
    valor_partida = db.Column(db.Numeric(8, 2))
    data_inicio = db.Column(db.Date, nullable=False)
    data_final = db.Column(db.Date)
    status = db.Column(db.String(12), nullable=False, default="em_andamento")
    concluida_em = db.Column(db.DateTime)


class Consentimento(db.Model):
    __tablename__ = "consentimento"
    __table_args__ = (
        db.UniqueConstraint("id_usuario", "chave", name="uq_consent_usuario_chave"),
    )

    id_consentimento = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_usuario = db.Column(
        db.Integer,
        db.ForeignKey("usuario.id_usuario", ondelete="CASCADE"),
        nullable=False,
    )
    chave = db.Column(db.String(40), nullable=False)
    descricao = db.Column(db.String(200), nullable=False)
    obrigatorio = db.Column(db.Boolean, nullable=False, default=False)
    aceito = db.Column(db.Boolean, nullable=False, default=True)
    data_registro = db.Column(db.DateTime, nullable=False, default=_agora)
    data_atualizacao = db.Column(db.DateTime)

    def to_dict(self):
        return {
            "chave": self.chave,
            "descricao": self.descricao,
            "obrigatorio": self.obrigatorio,
            "aceito": self.aceito,
            "data_registro": _iso_utc(self.data_registro),
            "data_atualizacao": _iso_utc(self.data_atualizacao),
        }
