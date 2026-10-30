# Roteiro do vídeo explicativo

Duração sugerida: 6 a 8 minutos. Tenha abertos: o navegador com a aplicação, o editor de código e o cliente do banco (pgAdmin, DBeaver ou psql).

## 1. Apresentação do sistema (≈ 40 s)
- Objetivo: sistema de vendas com controle de estoque.
- Problema: registrar vendas com segurança (estoque, desconto e histórico consistentes) e consultar relatórios.
- Funcionalidades: relatório de vendas, nova venda, cancelamento, estoque, cadastro de clientes e produtos.

## 2. Demonstração das telas (≈ 1 min)
Percorra o menu: Relatório de Vendas → Nova Venda → Estoque → Clientes → Produtos.

## 3. View (≈ 1 min 30 s)
- Abra `database/views/01_vw_relatorio_vendas.sql`.
- Motivo: evitar repetir JOIN e GROUP BY na aplicação; entrega o relatório pronto.
- Tabelas: `vendas`, `clientes`, `itens_venda`.
- Retorna: id, data, cliente, categoria, quantidade de itens, subtotal, desconto, total e status.
- Usada em: tela Relatório de Vendas (`app.py`, rota `/vendas`).
- Cite também `vw_estoque_situacao` (tela Estoque).
- No banco: rode `SELECT * FROM vw_relatorio_vendas;`.

## 4. Function (≈ 1 min 30 s)
- Abra `database/functions/01_fn_calcular_desconto.sql`.
- Faz: calcula o valor do desconto (VIP 10% + 5% se subtotal ≥ R$ 500).
- Parâmetros: `p_cliente_id`, `p_subtotal`. Retorna: valor do desconto (NUMERIC).
- Usada em: prévia na tela Nova Venda (`/api/desconto` em `app.py`) e dentro da procedure `sp_realizar_venda`.
- Motivo: regra de negócio num só lugar.
- No banco: `SELECT fn_calcular_desconto(1, 600);`

## 5. Procedure (≈ 2 min)
- Abra `database/procedures/01_sp_realizar_venda.sql`.
- Faz: registra a venda completa de forma atômica.
- Parâmetros: cliente, array de produtos, array de quantidades, e `INOUT p_venda_id`.
- Operações: valida cliente/itens → cria venda → trava o produto (`FOR UPDATE`) → valida estoque → insere item → baixa estoque → registra movimentação → calcula total com a function.
- Se algo falhar, nada é gravado (transação).
- Chamada por: botão "Confirmar venda" (`app.py`, rota `/vendas/nova`, `CALL sp_realizar_venda(...)`).
- Mencione `sp_cancelar_venda` (botão Cancelar).

## 6. Funcionamento integrado (≈ 2 min)
1. Em **Estoque**, anote o estoque de um produto.
2. Em **Nova Venda**, escolha cliente VIP, adicione itens e mostre o desconto mudando (Function).
3. Confirme a venda (Procedure).
4. Em **Relatório de Vendas**, mostre a venda nova (View).
5. Volte em **Estoque**: o estoque baixou.
6. Tente vender acima do estoque: mostre a mensagem de erro vinda do banco.
7. Cancele a venda e mostre o estoque devolvido.
8. Mostre a tabela `movimentacoes_estoque` no banco (SAIDA e ENTRADA).

Fluxo a reforçar: **tela → chamada ao banco → View/Function/Procedure → resultado na tela**.

## Dicas
- Mostre o código SQL na tela ao explicar cada recurso.
- Fale o nome do arquivo e da rota/tela onde cada recurso é usado.
- Poste o vídeo (YouTube não listado ou Drive) e coloque o link no README.
