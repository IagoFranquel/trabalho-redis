-- =====================================================================
-- VIEW 1: vw_relatorio_vendas
-- Finalidade: consolidar vendas + cliente + quantidade de itens em uma
-- única consulta, usada pela tela "Relatório de Vendas".
-- Tabelas envolvidas: vendas, clientes, itens_venda
-- =====================================================================
CREATE OR REPLACE VIEW vw_relatorio_vendas AS
SELECT
    v.id                                AS venda_id,
    v.data_venda,
    c.id                                AS cliente_id,
    c.nome                              AS cliente,
    c.categoria,
    COALESCE(SUM(i.quantidade), 0)::INT AS qtd_itens,
    v.subtotal,
    v.desconto,
    v.total,
    v.status
FROM vendas v
JOIN clientes c         ON c.id = v.cliente_id
LEFT JOIN itens_venda i ON i.venda_id = v.id
GROUP BY v.id, c.id;
