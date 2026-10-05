import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

CAMINHO_BANCO = os.path.join(RAIZ, "dev.db").replace("\\", "/")
os.environ.setdefault("DB_URI", "sqlite:///" + CAMINHO_BANCO)

from app import criar_app
from database import db
from models.model import Usuario
from services.service import AtividadeService, ComentarioService, CurtidaService, UsuarioService
from tests.apoio import criar_views_de_ranking

SENHA = "senhaforte123"

USUARIOS = [
    ("Paulo Susu", "paulo@fitbattle.dev", 28, "Belo Horizonte", "MG"),
    ("Lu Quimica", "lu@fitbattle.dev", 26, "Belo Horizonte", "MG"),
    ("Clebim", "clebim@fitbattle.dev", 31, "Belo Horizonte", "MG"),
    ("Camila Martins", "camila@fitbattle.dev", 24, "Belo Horizonte", "MG"),
    ("Pedro Surfistao", "pedro@fitbattle.dev", 29, "Belo Horizonte", "MG"),
    ("Mari", "mari@fitbattle.dev", 27, "Belo Horizonte", "MG"),
    ("Marcelo", "marcelo@fitbattle.dev", 35, "Belo Horizonte", "MG"),
    ("Breno Iron", "breno@fitbattle.dev", 30, "Contagem", "MG"),
    ("Rafael Souza", "rafael@fitbattle.dev", 33, "Belo Horizonte", "MG"),
    ("Thiago Rocha", "thiago@fitbattle.dev", 28, "Belo Horizonte", "MG"),
    ("Beatriz Sales", "beatriz@fitbattle.dev", 25, "Belo Horizonte", "MG"),
    ("Gabriel B", "gabriel@fitbattle.dev", 27, "Belo Horizonte", "MG"),
]

TREINOS = {
    "paulo@fitbattle.dev": [
        ("musculacao", "Supino Reto", 60, 140, 6),
        ("cardio", "Corrida leve", 40, None, None),
        ("musculacao", "Agachamento Livre", 55, 120, 8),
    ],
    "lu@fitbattle.dev": [("musculacao", "Levantamento Terra", 70, 250, 3), ("cardio", "Esteira", 30, None, None)],
    "clebim@fitbattle.dev": [("musculacao", "Leg Press", 50, 267, 8)],
    "camila@fitbattle.dev": [("musculacao", "Supino Reto", 60, 155, 2), ("yoga", "Yoga", 45, None, None)],
    "pedro@fitbattle.dev": [("musculacao", "Supino Reto", 60, 145, 5)],
    "marcelo@fitbattle.dev": [("musculacao", "Agachamento Livre", 65, 200, 5)],
    "breno@fitbattle.dev": [("musculacao", "Agachamento Livre", 65, 220, 4)],
    "rafael@fitbattle.dev": [("musculacao", "Supino Reto", 60, 160, 3)],
    "thiago@fitbattle.dev": [("musculacao", "Supino Reto", 60, 150, 1)],
    "beatriz@fitbattle.dev": [("musculacao", "Supino Reto", 60, 145, 4)],
    "gabriel@fitbattle.dev": [("musculacao", "Supino Reto", 75, 210, 1)],
}


def popular():
    if Usuario.query.count() > 0:
        return
    ids = {}
    for nome, email, idade, cidade, estado in USUARIOS:
        usuario = UsuarioService.cadastrar({
            "nome": nome, "email": email, "idade": idade, "senha": SENHA,
            "aceite_termos": True, "consentimentos": {},
        })
        usuario.cidade = cidade
        usuario.estado = estado
        db.session.commit()
        ids[email] = usuario.id_usuario

    for email, treinos in TREINOS.items():
        for tipo, titulo, minutos, carga, reps in treinos:
            AtividadeService.registrar(ids[email], {
                "tipo": tipo, "titulo": titulo, "tempo_min": minutos,
                "carga_kg": carga, "repeticoes": reps,
                "descricao": "Treino de exemplo do ambiente de desenvolvimento.",
            })

    ComentarioService.criar(ids["camila@fitbattle.dev"], "atividade", 1, "Mandou bem demais!")
    ComentarioService.criar(ids["lu@fitbattle.dev"], "atividade", 1, "Bora pra cima.")
    CurtidaService.alternar(ids["lu@fitbattle.dev"], "atividade", 1)
    CurtidaService.alternar(ids["clebim@fitbattle.dev"], "atividade", 1)


def preparar():
    app = criar_app()
    with app.app_context():
        criar_views_de_ranking(db)
        popular()
    return app


if __name__ == "__main__":
    preparar().run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
        debug=False,
    )
