import os
import re
from urllib.parse import quote_plus

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from auth import carregar_chave_secreta
from database import db
from routers.routers import Fitbattle_bp

PASTA_UPLOAD = os.path.join(os.path.dirname(__file__), "uploads")
PASTA_FRONTEND = os.path.join(os.path.dirname(__file__), "..", "frontend")

ORIGENS_PERMITIDAS = [
    re.compile(r"^https?://localhost(:\d+)?$"),
    re.compile(r"^https?://127\.0\.0\.1(:\d+)?$"),
    re.compile(r"^https?://192\.168\.\d{1,3}\.\d{1,3}(:\d+)?$"),
    re.compile(r"^https?://10\.\d{1,3}\.\d{1,3}\.\d{1,3}(:\d+)?$"),
    re.compile(r"^https?://172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}(:\d+)?$"),
]


def _origens_cors():
    origens = list(ORIGENS_PERMITIDAS)
    extras = os.getenv("CORS_EXTRA_ORIGENS", "")
    origens.extend(origem.strip() for origem in extras.split(",") if origem.strip())
    return origens


def criar_app():
    app = Flask(__name__)

    usuario = os.getenv("DB_USER", "fitbattle")
    senha = os.getenv("DB_PASSWORD", "Fitbattle@123")
    host = os.getenv("DB_HOST", "localhost")
    porta = os.getenv("DB_PORT", "3306")
    banco = os.getenv("DB_NAME", "fitbattle")

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DB_URI") or (
        f"mysql+pymysql://{quote_plus(usuario)}:{quote_plus(senha)}"
        f"@{host}:{porta}/{banco}"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = carregar_chave_secreta()
    app.config["UPLOAD_FOLDER"] = PASTA_UPLOAD
    app.config["MAX_CONTENT_LENGTH"] = 3 * 1024 * 1024

    os.makedirs(PASTA_UPLOAD, exist_ok=True)

    db.init_app(app)
    CORS(app, origins=_origens_cors())

    app.register_blueprint(Fitbattle_bp)

    import models.model

    with app.app_context():
        db.create_all()

    @app.get("/healthz")
    def health():
        return jsonify({"status": "ok", "servico": "FitBattle API"})

    @app.get("/uploads/<path:nome>")
    def servir_upload(nome):
        return send_from_directory(app.config["UPLOAD_FOLDER"], nome)

    servir_frontend = os.path.isdir(PASTA_FRONTEND)

    if servir_frontend:
        @app.get("/")
        def servir_raiz():
            return send_from_directory(PASTA_FRONTEND, "login.html")
    else:
        @app.get("/")
        def servir_raiz():
            return jsonify({"status": "ok", "servico": "FitBattle API"})

    @app.errorhandler(HTTPException)
    def erro_http(erro):
        if (
            servir_frontend
            and erro.code == 404
            and not request.path.startswith(("/api/", "/uploads/"))
        ):
            arquivo = request.path.lstrip("/")
            if os.path.isfile(os.path.join(PASTA_FRONTEND, arquivo)):
                return send_from_directory(PASTA_FRONTEND, arquivo)
        return jsonify({"erro": erro.description}), erro.code

    @app.errorhandler(Exception)
    def erro_inesperado(erro):
        app.logger.exception(erro)
        return jsonify({"erro": "Erro interno do servidor."}), 500

    return app


app = criar_app()

if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG") == "1", port=5000)
