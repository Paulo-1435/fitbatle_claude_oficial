"""Instância única do SQLAlchemy compartilhada por toda a aplicação."""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
