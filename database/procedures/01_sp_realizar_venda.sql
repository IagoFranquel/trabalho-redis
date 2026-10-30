-- =====================================================================
-- PROCEDURE: sp_realizar_venda(cliente_id, produto_ids[], quantidades[])
-- Finalidade: executar a venda inteira de forma atômica:
--   1. valida o cliente e os itens
--   2. cria a venda
--   3. para cada item: trava o produto, valida o estoque, insere o item,
--      baixa o estoque e registra a movimentação
--   4. calcula subtotal, desconto (fn_calcular_desconto) e total
-- Em caso de erro (ex.: estoque insuficiente) tudo é desfeito.
-- Retorna o id da venda no parâmetro INOUT p_venda_id.
-- Usada em: tela "Nova Venda" (botão Confirmar venda).
-- =====================================================================
CREATE OR REPLACE PROCEDURE sp_realizar_venda(
    p_cliente_id   INT,
    p_produto_ids  INT[],
    p_quantidades  INT[],
    INOUT p_venda_id INT DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    i          INT;
    v_nome     VARCHAR(100);
    v_preco    NUMERIC(10,2);
    v_estoque  INT;
    v_subtotal NUMERIC(12,2) := 0;
    v_desconto NUMERIC(12,2);
BEGIN
    IF NOT EXISTS (SELECT 1 FROM clientes WHERE id = p_cliente_id) THEN
        RAISE EXCEPTION 'Cliente % não encontrado', p_cliente_id;
    END IF;

    IF p_produto_ids IS NULL
       OR array_length(p_produto_ids, 1) IS NULL
       OR array_length(p_produto_ids, 1) <> COALESCE(array_length(p_quantidades, 1), 0) THEN
        RAISE EXCEPTION 'Informe ao menos um item válido para a venda';
    END IF;

    INSERT INTO vendas (cliente_id) VALUES (p_cliente_id)
    RETURNING id INTO p_venda_id;

    FOR i IN 1..array_length(p_produto_ids, 1) LOOP
        IF p_quantidades[i] <= 0 THEN
            RAISE EXCEPTION 'Quantidade inválida para o produto %', p_produto_ids[i];
        END IF;

        SELECT nome, preco, estoque
          INTO v_nome, v_preco, v_estoque
          FROM produtos
         WHERE id = p_produto_ids[i]
           FOR UPDATE;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'Produto % não encontrado', p_produto_ids[i];
        END IF;

        IF v_estoque < p_quantidades[i] THEN
            RAISE EXCEPTION 'Estoque insuficiente para "%": disponível %, solicitado %',
                v_nome, v_estoque, p_quantidades[i];
        END IF;

        INSERT INTO itens_venda (venda_id, produto_id, quantidade, preco_unitario)
        VALUES (p_venda_id, p_produto_ids[i], p_quantidades[i], v_preco);

        UPDATE produtos
           SET estoque = estoque - p_quantidades[i]
         WHERE id = p_produto_ids[i];

        INSERT INTO movimentacoes_estoque (produto_id, venda_id, tipo, quantidade)
        VALUES (p_produto_ids[i], p_venda_id, 'SAIDA', p_quantidades[i]);

        v_subtotal := v_subtotal + (v_preco * p_quantidades[i]);
    END LOOP;

    v_desconto := fn_calcular_desconto(p_cliente_id, v_subtotal);

    UPDATE vendas
       SET subtotal = v_subtotal,
           desconto = v_desconto,
           total    = v_subtotal - v_desconto
     WHERE id = p_venda_id;
END;
$$;
