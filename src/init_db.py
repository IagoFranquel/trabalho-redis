"""Cria o banco a partir dos scripts da pasta /database.

Uso:  python init_db.py
Variáveis de ambiente (opcionais): DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
O banco (DB_NAME) precisa existir:  CREATE DATABASE loja_db;

Para usar um banco na nuvem (ex.: Supabase), defina apenas DATABASE_URL:
  postgresql://usuario:senha@host:5432/postgres
"""
import os
from pathlib import Path

import psycopg2

DB = dict(
    host=os.getenv("DB_HOST", "localhost"),
    port=os.getenv("DB_PORT", "5432"),
    dbname=os.getenv("DB_NAME", "loja_db"),
    user=os.getenv("DB_USER", "postgres"),
    password=os.getenv("DB_PASSWORD", "postgres"),
    client_encoding="UTF8",
)
# Se DATABASE_URL estiver definida (ex.: Supabase), ela tem prioridade.
DATABASE_URL = os.getenv("DATABASE_URL")

BASE = Path(__file__).resolve().parent.parent / "database"
ORDEM = ["tables", "views", "functions", "procedures", "inserts"]


def main():
    if DATABASE_URL:
        conn = psycopg2.connect(DATABASE_URL, client_encoding="UTF8")
    else:
        conn = psycopg2.connect(**DB)
    try:
        with conn, conn.cursor() as cur:
            for pasta in ORDEM:
                for arq in sorted((BASE / pasta).glob("*.sql")):
                    print(f"Executando {pasta}/{arq.name}")
                    cur.execute(arq.read_text(encoding="utf-8"))
        print("Banco criado com sucesso.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
