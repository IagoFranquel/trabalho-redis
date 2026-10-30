-- =====================================================================
-- FUNCTION: fn_calcular_desconto(cliente_id, subtotal)
-- Finalidade: centralizar a regra de desconto no banco.
--   * Cliente VIP ........... 10%
--   * Subtotal >= R$ 500 .... +5%
-- Retorna o VALOR do desconto (em reais).
-- Usada em: tela "Nova Venda" (prévia do desconto via /api/desconto)
--           e dentro da procedure sp_realizar_venda.
-- =====================================================================
CREATE OR REPLACE FUNCTION fn_calcular_desconto(p_cliente_id INT, p_subtotal NUMERIC)
RETURNS NUMERIC(12,2)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_categoria VARCHAR(10);
    v_perc      NUMERIC := 0;
BEGIN
    SELECT categoria INTO v_categoria FROM clientes WHERE id = p_cliente_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Cliente % não encontrado', p_cliente_id;
    END IF;

    IF v_categoria = 'VIP' THEN
        v_perc := v_perc + 0.10;
    END IF;

    IF p_subtotal >= 500 THEN
        v_perc := v_perc + 0.05;
    END IF;

    RETURN ROUND(p_subtotal * v_perc, 2);
END;
$$;
