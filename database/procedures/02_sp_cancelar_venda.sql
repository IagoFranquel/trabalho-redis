-- =====================================================================
-- PROCEDURE: sp_cancelar_venda(venda_id)
-- Finalidade: cancelar uma venda e devolver os itens ao estoque,
-- registrando a movimentação de ENTRADA.
-- Usada em: tela "Relatório de Vendas" (botão Cancelar).
-- =====================================================================
CREATE OR REPLACE PROCEDURE sp_cancelar_venda(p_venda_id INT)
LANGUAGE plpgsql
AS $$
DECLARE
    v_status VARCHAR(12);
BEGIN
    SELECT status INTO v_status FROM vendas WHERE id = p_venda_id FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Venda % não encontrada', p_venda_id;
    END IF;

    IF v_status = 'CANCELADA' THEN
        RAISE EXCEPTION 'A venda % já está cancelada', p_venda_id;
    END IF;

    UPDATE produtos p
       SET estoque = p.estoque + t.qtd
      FROM (SELECT produto_id, SUM(quantidade) AS qtd
              FROM itens_venda
             WHERE venda_id = p_venda_id
             GROUP BY produto_id) t
     WHERE p.id = t.produto_id;

    INSERT INTO movimentacoes_estoque (produto_id, venda_id, tipo, quantidade)
    SELECT produto_id, p_venda_id, 'ENTRADA', SUM(quantidade)
      FROM itens_venda
     WHERE venda_id = p_venda_id
     GROUP BY produto_id;

    UPDATE vendas SET status = 'CANCELADA' WHERE id = p_venda_id;
END;
$$;
