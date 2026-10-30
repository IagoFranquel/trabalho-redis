-- =====================================================================
-- Criação das tabelas - Sistema de Vendas
-- SGBD: PostgreSQL 12+
-- Pode ser executado várias vezes (recria o esquema do zero).
-- =====================================================================

DROP TABLE IF EXISTS movimentacoes_estoque CASCADE;
DROP TABLE IF EXISTS itens_venda CASCADE;
DROP TABLE IF EXISTS vendas CASCADE;
DROP TABLE IF EXISTS produtos CASCADE;
DROP TABLE IF EXISTS clientes CASCADE;

CREATE TABLE clientes (
    id          SERIAL PRIMARY KEY,
    nome        VARCHAR(100) NOT NULL,
    email       VARCHAR(120) UNIQUE,
    categoria   VARCHAR(10)  NOT NULL DEFAULT 'REGULAR'
                CHECK (categoria IN ('REGULAR', 'VIP')),
    criado_em   TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE TABLE produtos (
    id              SERIAL PRIMARY KEY,
    nome            VARCHAR(100)  NOT NULL,
    preco           NUMERIC(10,2) NOT NULL CHECK (preco > 0),
    estoque         INT           NOT NULL DEFAULT 0 CHECK (estoque >= 0),
    estoque_minimo  INT           NOT NULL DEFAULT 5 CHECK (estoque_minimo >= 0)
);

CREATE TABLE vendas (
    id          SERIAL PRIMARY KEY,
    cliente_id  INT           NOT NULL REFERENCES clientes(id),
    data_venda  TIMESTAMP     NOT NULL DEFAULT NOW(),
    subtotal    NUMERIC(12,2) NOT NULL DEFAULT 0,
    desconto    NUMERIC(12,2) NOT NULL DEFAULT 0,
    total       NUMERIC(12,2) NOT NULL DEFAULT 0,
    status      VARCHAR(12)   NOT NULL DEFAULT 'CONCLUIDA'
                CHECK (status IN ('CONCLUIDA', 'CANCELADA'))
);

CREATE TABLE itens_venda (
    id              SERIAL PRIMARY KEY,
    venda_id        INT           NOT NULL REFERENCES vendas(id) ON DELETE CASCADE,
    produto_id      INT           NOT NULL REFERENCES produtos(id),
    quantidade      INT           NOT NULL CHECK (quantidade > 0),
    preco_unitario  NUMERIC(10,2) NOT NULL
);

CREATE TABLE movimentacoes_estoque (
    id          SERIAL PRIMARY KEY,
    produto_id  INT         NOT NULL REFERENCES produtos(id),
    venda_id    INT         REFERENCES vendas(id) ON DELETE SET NULL,
    tipo        VARCHAR(7)  NOT NULL CHECK (tipo IN ('ENTRADA', 'SAIDA')),
    quantidade  INT         NOT NULL CHECK (quantidade > 0),
    data_mov    TIMESTAMP   NOT NULL DEFAULT NOW()
);
