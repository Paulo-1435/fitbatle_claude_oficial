import os
from urllib.parse import quote_plus

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

from database import db
from routers.routers import Fitbattle_bp

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
    app.config["MAX_CONTENT_LENGTH"] = 3 * 1024 * 1024

    os.makedirs(PASTA_UPLOAD, exist_ok=True)

    db.init_app(app)
    CORS(app)

    app.register_blueprint(Fitbattle_bp)

    from models.model import Usuario

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
