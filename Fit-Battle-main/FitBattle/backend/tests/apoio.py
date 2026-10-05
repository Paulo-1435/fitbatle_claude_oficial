import os
import re

from sqlalchemy import text

CAMINHO_SQL = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "database",
    "create_database.sql",
)

VIEWS_DE_RANKING = (
    "vw_ranking_global", "vw_ranking_regional", "vw_ranking_exercicio", "vw_ranking_grupo",
)


def criar_views_de_ranking(db):
    with open(CAMINHO_SQL, encoding="utf-8") as arquivo:
        conteudo = arquivo.read()

    for nome, consulta in re.findall(r"CREATE OR REPLACE VIEW (\w+) AS\s*(.*?);", conteudo, re.S):
        if nome not in VIEWS_DE_RANKING:
            continue
        db.session.execute(text(f"DROP VIEW IF EXISTS {nome}"))
        db.session.execute(text(f"CREATE VIEW {nome} AS {consulta}"))
    db.session.commit()
