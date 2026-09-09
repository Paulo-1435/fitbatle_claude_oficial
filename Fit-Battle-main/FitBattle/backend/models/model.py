"""Camada Model - mapeia a tabela `usuario` do banco FitBattle."""

from datetime import datetime, timezone

from database import db


def _agora():
    return datetime.now(timezone.utc)


class Usuario(db.Model):
    __tablename__ = "usuario"

    id_usuario = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    senha = db.Column(db.String(255), nullable=False)          # armazena o HASH
    idade = db.Column(db.SmallInteger)
    peso = db.Column(db.Numeric(5, 2))       # kg
    altura = db.Column(db.Numeric(3, 2))     # metros
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
        """Versão segura para enviar ao frontend (sem a senha)."""
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
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
            "responsavel": (
                {
                    "nome": self.responsavel_nome,
                    "email": self.responsavel_email,
                    "autorizado_em": (
                        self.responsavel_autorizado_em.isoformat()
                        if self.responsavel_autorizado_em else None
                    ),
                }
                if self.responsavel_nome else None
            ),
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
            "data_registro": self.data_registro.isoformat() if self.data_registro else None,
        }


class Consentimento(db.Model):
    """Registro granular de consentimento LGPD - uma linha por finalidade."""

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
            "data_registro": self.data_registro.isoformat() if self.data_registro else None,
            "data_atualizacao": (
                self.data_atualizacao.isoformat() if self.data_atualizacao else None
            ),
        }
