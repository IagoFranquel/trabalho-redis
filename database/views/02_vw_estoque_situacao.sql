-- =====================================================================
-- VIEW 2: vw_estoque_situacao
-- Finalidade: listar produtos com a situação do estoque (OK / BAIXO /
-- ESGOTADO) e o total vendido, usada pela tela "Estoque".
-- Tabelas envolvidas: produtos, itens_venda, vendas
-- =====================================================================
CREATE OR REPLACE VIEW vw_estoque_situacao AS
SELECT
    p.id AS produto_id,
    p.nome,
    p.preco,
    p.estoque,
    p.estoque_minimo,
    CASE
        WHEN p.estoque = 0                  THEN 'ESGOTADO'
        WHEN p.estoque <= p.estoque_minimo  THEN 'BAIXO'
        ELSE 'OK'
    END AS situacao,
    COALESCE(SUM(i.quantidade) FILTER (WHERE v.status = 'CONCLUIDA'), 0)::INT AS total_vendido
FROM produtos p
LEFT JOIN itens_venda i ON i.produto_id = p.id
LEFT JOIN vendas v      ON v.id = i.venda_id
GROUP BY p.id;
