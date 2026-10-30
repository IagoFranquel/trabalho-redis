"""Camada de integração com o Redis.

O Redis é usado em três funcionalidades diferentes:

1. CACHE (cache-aside com TTL)
   Relatório de vendas, lista de estoque e cálculo de desconto são guardados
   no Redis. A primeira leitura vai ao Supabase (MISS); as seguintes saem do
   Redis (HIT) até o TTL expirar ou até uma venda/cancelamento invalidar a chave.

2. RANKING (Sorted Set)
   Produtos mais vendidos, atualizados com ZINCRBY a cada venda.

3. CONTADORES (INCR atômico)
   Acertos/erros de cache e quantidade de vendas registradas pela aplicação.

Se REDIS_URL não estiver definida, ou o Redis estiver fora do ar, a aplicação
continua funcionando normalmente, lendo direto do Supabase.
"""
import json
import os
import time
from datetime import date, datetime
from decimal import Decimal
from urllib.parse import urlparse

import redis

REDIS_URL = os.getenv("REDIS_URL")

# Prefixos das chaves (tudo que é cache começa com "cache:")
CHAVE_RELATORIO = "cache:vendas:relatorio"
CHAVE_ESTOQUE = "cache:estoque:lista"
TTL_RELATORIO = 60       # segundos
TTL_ESTOQUE = 60
TTL_DESCONTO = 300

RANKING = "ranking:produtos"
STATS_HITS = "stats:hits"
STATS_MISSES = "stats:misses"
STATS_VENDAS = "stats:vendas_registradas"
STATS_LATENCIA = "stats:latencia_ms"   # hash: "<chave>:redis" / "<chave>:supabase"

_client = None
_pausado_ate = 0.0   # "disjuntor": após uma falha, evita esperar timeouts repetidos


def _default(o):
    """Converte tipos do PostgreSQL que o JSON não conhece."""
    if isinstance(o, Decimal):
        return float(o)
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    raise TypeError(f"Tipo não serializável: {type(o)}")


def _ms(inicio):
    return round((time.perf_counter() - inicio) * 1000, 1)


def _marcar_falha():
    global _pausado_ate
    _pausado_ate = time.time() + 15


def get_client():
    """Devolve o cliente Redis, ou None se não configurado/indisponível."""
    global _client
    if not REDIS_URL or time.time() < _pausado_ate:
        return None
    if _client is None:
        _client = redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
        )
    return _client


def servidor_info():
    """Dados para o painel: conexão, host (sem senha) e versão do servidor."""
    info = {"configurado": bool(REDIS_URL), "conectado": False, "host": None, "versao": None}
    if REDIS_URL:
        p = urlparse(REDIS_URL)
        info["host"] = f"{p.hostname}:{p.port}" if p.port else p.hostname
    r = get_client()
    if r is None:
        return info
    try:
        r.ping()
        info["conectado"] = True
        try:
            info["versao"] = r.info("server").get("redis_version")
        except redis.RedisError:
            pass
    except redis.RedisError:
        _marcar_falha()
    return info


# --------------------------------------------------------------------- cache
def cached(chave, ttl, carregar):
    """Padrão cache-aside.

    Devolve (dados, meta). meta = {"origem": "redis"|"supabase"|"sem-redis", "ms": ..., "ttl": ...}
    `carregar` é a função que busca os dados no Supabase quando não há cache.
    """
    r = get_client()
    inicio = time.perf_counter()

    if r is not None:
        try:
            bruto = r.get(chave)
            if bruto is not None:
                dados = json.loads(bruto)
                tempo = _ms(inicio)
                r.incr(STATS_HITS)
                r.hset(STATS_LATENCIA, f"{chave}:redis", tempo)
                return dados, {"origem": "redis", "ms": tempo, "ttl": r.ttl(chave)}
        except redis.RedisError:
            _marcar_falha()
            r = None

    inicio = time.perf_counter()
    dados = carregar()
    tempo = _ms(inicio)

    if r is None:
        return dados, {"origem": "sem-redis", "ms": tempo, "ttl": None}

    try:
        r.set(chave, json.dumps(dados, default=_default), ex=ttl)
        r.incr(STATS_MISSES)
        r.hset(STATS_LATENCIA, f"{chave}:supabase", tempo)
        return dados, {"origem": "supabase", "ms": tempo, "ttl": ttl}
    except redis.RedisError:
        _marcar_falha()
        return dados, {"origem": "sem-redis", "ms": tempo, "ttl": None}


def invalidar(*chaves):
    """Apaga chaves de cache (chamado quando os dados mudam no banco)."""
    r = get_client()
    if r is None or not chaves:
        return
    try:
        r.delete(*chaves)
    except redis.RedisError:
        _marcar_falha()


def limpar_cache():
    """Apaga todas as chaves cache:* e devolve quantas foram removidas."""
    r = get_client()
    if r is None:
        return 0
    try:
        chaves = list(r.scan_iter("cache:*"))
        if chaves:
            r.delete(*chaves)
        return len(chaves)
    except redis.RedisError:
        _marcar_falha()
        return 0


def listar_cache():
    """Lista as chaves de cache com o TTL restante (para o painel)."""
    r = get_client()
    if r is None:
        return []
    try:
        return sorted(
            ({"chave": k, "ttl": r.ttl(k)} for k in r.scan_iter("cache:*")),
            key=lambda x: x["chave"],
        )
    except redis.RedisError:
        _marcar_falha()
        return []


# ------------------------------------------------------------------- ranking
def ranking_incrementar(itens):
    """itens = [(nome_produto, quantidade)]. Soma no Sorted Set (ZINCRBY)."""
    r = get_client()
    if r is None:
        return
    try:
        pipe = r.pipeline()
        for nome, qtd in itens:
            pipe.zincrby(RANKING, qtd, nome)
        pipe.incr(STATS_VENDAS)
        pipe.execute()
    except redis.RedisError:
        _marcar_falha()


def ranking_decrementar(itens):
    """Desfaz o efeito de uma venda cancelada no ranking."""
    r = get_client()
    if r is None:
        return
    try:
        pipe = r.pipeline()
        for nome, qtd in itens:
            pipe.zincrby(RANKING, -qtd, nome)
        pipe.zremrangebyscore(RANKING, "-inf", 0)
        pipe.execute()
    except redis.RedisError:
        _marcar_falha()


def ranking_existe():
    r = get_client()
    try:
        return bool(r and r.exists(RANKING))
    except redis.RedisError:
        _marcar_falha()
        return False


def ranking_reconstruir(linhas):
    """Recria o ranking a partir do Supabase. linhas = [(nome, quantidade)]."""
    r = get_client()
    if r is None:
        return
    try:
        pipe = r.pipeline()
        pipe.delete(RANKING)
        if linhas:
            pipe.zadd(RANKING, {nome: qtd for nome, qtd in linhas})
        pipe.execute()
    except redis.RedisError:
        _marcar_falha()


def ranking_top(n=5):
    r = get_client()
    if r is None:
        return []
    try:
        return [(nome, int(score)) for nome, score in r.zrevrange(RANKING, 0, n - 1, withscores=True)]
    except redis.RedisError:
        _marcar_falha()
        return []


# ------------------------------------------------------------------- estatísticas
def estatisticas():
    r = get_client()
    vazio = {"hits": 0, "misses": 0, "taxa": 0, "vendas": 0, "latencia": {}}
    if r is None:
        return vazio
    try:
        hits = int(r.get(STATS_HITS) or 0)
        misses = int(r.get(STATS_MISSES) or 0)
        total = hits + misses
        return {
            "hits": hits,
            "misses": misses,
            "taxa": round(100 * hits / total) if total else 0,
            "vendas": int(r.get(STATS_VENDAS) or 0),
            "latencia": r.hgetall(STATS_LATENCIA),
        }
    except redis.RedisError:
        _marcar_falha()
        return vazio


def zerar_estatisticas():
    r = get_client()
    if r is None:
        return
    try:
        r.delete(STATS_HITS, STATS_MISSES, STATS_LATENCIA)
    except redis.RedisError:
        _marcar_falha()
