import os

import psycopg2
import psycopg2.extras
from flask import (Flask, flash, jsonify, redirect, render_template, request,
                   url_for)

import cache  # integração com o Redis (cache, ranking e contadores)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

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


# ---------------------------------------------------------------- helpers
def connect():
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL, client_encoding="UTF8")
    return psycopg2.connect(**DB)


def run(sql, params=(), fetch="all"):
    """Executa uma instrução; faz commit e devolve linhas como dicionários."""
    conn = connect()
    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params)
                if fetch == "all":
                    return cur.fetchall()
                if fetch == "one":
                    return cur.fetchone()
                return None
    finally:
        conn.close()


def erro_banco(e):
    """Mensagem amigável vinda do RAISE EXCEPTION do PostgreSQL."""
    diag = getattr(e, "diag", None)
    return (diag.message_primary if diag and diag.message_primary else str(e))


@app.template_filter("brl")
def brl(valor):
    valor = float(valor or 0)
    return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ------------------------------------------- consultas ao Supabase (com cache)
def carregar_relatorio():
    """Lê a VIEW vw_relatorio_vendas no Supabase (só roda quando não há cache)."""
    vendas = [dict(v) for v in run(
        "SELECT * FROM vw_relatorio_vendas ORDER BY data_venda DESC, venda_id DESC"
    )]
    for v in vendas:
        v["data_fmt"] = v.pop("data_venda").strftime("%d/%m/%Y %H:%M")
    ativas = [v for v in vendas if v["status"] == "CONCLUIDA"]
    resumo = {
        "qtd": len(ativas),
        "faturamento": float(sum(v["total"] for v in ativas)),
        "descontos": float(sum(v["desconto"] for v in ativas)),
    }
    return {"vendas": vendas, "resumo": resumo}


def carregar_estoque():
    """Lê a VIEW vw_estoque_situacao no Supabase (só roda quando não há cache)."""
    return [dict(i) for i in run("SELECT * FROM vw_estoque_situacao ORDER BY situacao DESC, nome")]


def reconstruir_ranking():
    """Recalcula o ranking do Redis a partir das vendas concluídas no Supabase."""
    linhas = run(
        """SELECT p.nome, SUM(i.quantidade)::int AS qtd
             FROM itens_venda i
             JOIN vendas v   ON v.id = i.venda_id AND v.status = 'CONCLUIDA'
             JOIN produtos p ON p.id = i.produto_id
            GROUP BY p.nome"""
    )
    cache.ranking_reconstruir([(l["nome"], l["qtd"]) for l in linhas])


def atualizar_redis_apos_venda(ids, qtds):
    """Venda nova: soma no ranking e invalida o cache (os dados mudaram)."""
    if cache.get_client() is not None:
        nomes = {r["id"]: r["nome"] for r in run(
            "SELECT id, nome FROM produtos WHERE id = ANY(%s)", (ids,))}
        cache.ranking_incrementar([(nomes[i], q) for i, q in zip(ids, qtds) if i in nomes])
    cache.invalidar(cache.CHAVE_RELATORIO, cache.CHAVE_ESTOQUE)


def atualizar_redis_apos_cancelamento(venda_id):
    """Venda cancelada: tira do ranking e invalida o cache."""
    if cache.get_client() is not None:
        itens = run(
            """SELECT p.nome, SUM(i.quantidade)::int AS qtd
                 FROM itens_venda i JOIN produtos p ON p.id = i.produto_id
                WHERE i.venda_id = %s GROUP BY p.nome""",
            (venda_id,),
        )
        cache.ranking_decrementar([(i["nome"], i["qtd"]) for i in itens])
    cache.invalidar(cache.CHAVE_RELATORIO, cache.CHAVE_ESTOQUE)


# ------------------------------------------------------------------ rotas
@app.route("/")
def index():
    return redirect(url_for("relatorio_vendas"))


# TELA 1 - Relatório de Vendas  -> VIEW vw_relatorio_vendas (+ cache no Redis)
@app.route("/vendas")
def relatorio_vendas():
    dados, origem = cache.cached(cache.CHAVE_RELATORIO, cache.TTL_RELATORIO, carregar_relatorio)
    return render_template("relatorio_vendas.html", vendas=dados["vendas"],
                           resumo=dados["resumo"], origem=origem)


# TELA 2 - Nova Venda -> PROCEDURE sp_realizar_venda
# (o estoque desta tela é sempre lido ao vivo, sem cache, para nunca vender
#  com um estoque desatualizado)
@app.route("/vendas/nova", methods=["GET", "POST"])
def nova_venda():
    if request.method == "POST":
        try:
            cliente_id = int(request.form["cliente_id"])
        except (KeyError, ValueError):
            flash("Selecione um cliente.", "erro")
            return redirect(url_for("nova_venda"))

        ids, qtds = [], []
        for chave, valor in request.form.items():
            if chave.startswith("produto_") and valor.strip().isdigit() and int(valor) > 0:
                ids.append(int(chave.split("_", 1)[1]))
                qtds.append(int(valor))

        if not ids:
            flash("Informe a quantidade de pelo menos um produto.", "erro")
            return redirect(url_for("nova_venda"))

        try:
            row = run(
                "CALL sp_realizar_venda(%s, %s::int[], %s::int[], NULL::int)",
                (cliente_id, ids, qtds),
                fetch="one",
            )
        except psycopg2.Error as e:
            flash(erro_banco(e), "erro")
            return redirect(url_for("nova_venda"))

        atualizar_redis_apos_venda(ids, qtds)
        flash(f"Venda #{row['p_venda_id']} registrada com sucesso!", "ok")
        return redirect(url_for("relatorio_vendas"))

    clientes = run("SELECT id, nome, categoria FROM clientes ORDER BY nome")
    produtos = run("SELECT produto_id AS id, nome, preco, estoque FROM vw_estoque_situacao ORDER BY nome")
    return render_template("nova_venda.html", clientes=clientes, produtos=produtos)


# API da tela Nova Venda -> FUNCTION fn_calcular_desconto (+ cache no Redis)
@app.route("/api/desconto")
def api_desconto():
    try:
        cliente_id = int(request.args["cliente_id"])
        subtotal = round(float(request.args["subtotal"]), 2)
        if subtotal < 0:
            raise ValueError
    except (KeyError, ValueError):
        return jsonify(erro="parâmetros inválidos"), 400

    def carregar():
        row = run("SELECT fn_calcular_desconto(%s, %s) AS desconto", (cliente_id, subtotal), fetch="one")
        return {"desconto": float(row["desconto"])}

    try:
        dados, meta = cache.cached(
            f"cache:desconto:{cliente_id}:{subtotal:.2f}", cache.TTL_DESCONTO, carregar)
    except psycopg2.Error as e:
        return jsonify(erro=erro_banco(e)), 400

    desconto = dados["desconto"]
    return jsonify(desconto=desconto, total=round(subtotal - desconto, 2),
                   origem=meta["origem"], ms=meta["ms"])


# Cancelamento -> PROCEDURE sp_cancelar_venda
@app.route("/vendas/<int:venda_id>/cancelar", methods=["POST"])
def cancelar_venda(venda_id):
    try:
        run("CALL sp_cancelar_venda(%s)", (venda_id,), fetch=None)
    except psycopg2.Error as e:
        flash(erro_banco(e), "erro")
        return redirect(url_for("relatorio_vendas"))
    atualizar_redis_apos_cancelamento(venda_id)
    flash(f"Venda #{venda_id} cancelada e estoque devolvido.", "ok")
    return redirect(url_for("relatorio_vendas"))


# TELA 3 - Estoque -> VIEW vw_estoque_situacao (+ cache no Redis)
@app.route("/estoque")
def estoque():
    itens, origem = cache.cached(cache.CHAVE_ESTOQUE, cache.TTL_ESTOQUE, carregar_estoque)
    return render_template("estoque.html", itens=itens, origem=origem)


# TELA 4 - Painel Redis: mostra o que está guardado no Redis
@app.route("/redis")
def painel_redis():
    info = cache.servidor_info()
    ranking, chaves = [], []
    if info["conectado"]:
        if not cache.ranking_existe():
            reconstruir_ranking()
        ranking = cache.ranking_top(5)
        chaves = cache.listar_cache()
    stats = cache.estatisticas()
    latencia = {}
    for chave, valor in stats["latencia"].items():
        base, _, tipo = chave.rpartition(":")
        latencia.setdefault(base, {})[tipo] = valor
    return render_template("redis.html", info=info, ranking=ranking, chaves=chaves,
                           stats=stats, latencia=latencia)


@app.route("/redis/limpar-cache", methods=["POST"])
def redis_limpar_cache():
    n = cache.limpar_cache()
    flash(f"{n} chave(s) de cache apagada(s). A próxima consulta vai ao Supabase.", "ok")
    return redirect(url_for("painel_redis"))


@app.route("/redis/reconstruir-ranking", methods=["POST"])
def redis_reconstruir_ranking():
    reconstruir_ranking()
    flash("Ranking recalculado a partir das vendas no Supabase.", "ok")
    return redirect(url_for("painel_redis"))


@app.route("/redis/zerar-estatisticas", methods=["POST"])
def redis_zerar_estatisticas():
    cache.zerar_estatisticas()
    flash("Contadores de cache zerados.", "ok")
    return redirect(url_for("painel_redis"))


# CRUD básico (evolução do trabalho anterior)
@app.route("/clientes", methods=["GET", "POST"])
def clientes():
    if request.method == "POST":
        try:
            run(
                "INSERT INTO clientes (nome, email, categoria) VALUES (%s, %s, %s)",
                (request.form["nome"].strip(), request.form["email"].strip() or None, request.form["categoria"]),
                fetch=None,
            )
            flash("Cliente cadastrado.", "ok")
        except psycopg2.Error as e:
            flash(erro_banco(e), "erro")
        return redirect(url_for("clientes"))
    lista = run("SELECT * FROM clientes ORDER BY nome")
    return render_template("clientes.html", clientes=lista)


@app.route("/produtos", methods=["GET", "POST"])
def produtos():
    if request.method == "POST":
        try:
            run(
                "INSERT INTO produtos (nome, preco, estoque, estoque_minimo) VALUES (%s, %s, %s, %s)",
                (
                    request.form["nome"].strip(),
                    request.form["preco"],
                    request.form["estoque"],
                    request.form["estoque_minimo"],
                ),
                fetch=None,
            )
            cache.invalidar(cache.CHAVE_ESTOQUE)  # novo produto aparece no estoque
            flash("Produto cadastrado.", "ok")
        except psycopg2.Error as e:
            flash(erro_banco(e), "erro")
        return redirect(url_for("produtos"))
    lista = run("SELECT * FROM produtos ORDER BY nome")
    return render_template("produtos.html", produtos=lista)


if __name__ == "__main__":
    app.run(debug=True)
