"""
Ponto de entrada da API do FitBattle.

Antes de rodar:
  1. Crie o banco no MySQL:  mysql -u root -p < database/create_database.sql
  2. Instale as dependências: pip install -r requirements.txt
  3. (Opcional) configure as variáveis de ambiente do banco:
        DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME
  4. python app.py   ->   http://localhost:5000
"""

import os
from urllib.parse import quote_plus

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

from database import db
from routers.routers import Fitbattle_bp

# Pasta onde ficam as fotos de perfil enviadas pelos usuários
PASTA_UPLOAD = os.path.join(os.path.dirname(__file__), "uploads")


def criar_app():
    app = Flask(__name__)

    usuario = os.getenv("DB_USER", "fitbattle")
    senha = os.getenv("DB_PASSWORD", "Fitbattle@123")
    host = os.getenv("DB_HOST", "localhost")
    porta = os.getenv("DB_PORT", "3306")
    banco = os.getenv("DB_NAME", "fitbattle")

    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"mysql+pymysql://{quote_plus(usuario)}:{quote_plus(senha)}"
        f"@{host}:{porta}/{banco}"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-fitbattle-trocar-em-producao")
    app.config["UPLOAD_FOLDER"] = PASTA_UPLOAD
    app.config["MAX_CONTENT_LENGTH"] = 3 * 1024 * 1024  # limite de 3 MB por upload

    os.makedirs(PASTA_UPLOAD, exist_ok=True)

    db.init_app(app)
    CORS(app)

    app.register_blueprint(Fitbattle_bp)

    # Importa os models para que o SQLAlchemy os conheça
    from models.model import Usuario  # noqa: F401

    with app.app_context():
        db.create_all()

    @app.get("/")
    def health():
        return jsonify({"status": "ok", "servico": "FitBattle API"})

    @app.get("/uploads/<path:nome>")
    def servir_upload(nome):
        return send_from_directory(app.config["UPLOAD_FOLDER"], nome)

    return app


app = criar_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
