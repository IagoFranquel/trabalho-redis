# Roteiro do vídeo – Supabase + Redis

Duração sugerida: 6 a 8 minutos. O vídeo precisa mostrar o **sistema funcionando** (não slides).

## Antes de gravar
- Terminal com `py app.py` rodando (com `DATABASE_URL` e `REDIS_URL` definidas) e minimizado.
- Abas abertas no navegador: o sistema (http://127.0.0.1:5000), o painel do **Supabase** (Table Editor e SQL Editor) e o console do **Upstash** (Data Browser, se tiver).
- Abertos no Bloco de Notas ou VS Code: `src/cache.py` e `src/app.py`.
- No sistema, vá em **Painel Redis** e clique em **Limpar cache** e **Zerar contadores**, para começar do zero.
- Teste o microfone.

## 1. Proposta (≈ 40 s)
**Mostrar:** tela Relatório de Vendas.

> "Oi, eu sou [seu nome], disciplina [disciplina], professor [professor]. Este é um sistema de vendas com controle de estoque, que resolve o registro seguro de vendas e a consulta de relatórios. Neste trabalho eu evoluí o projeto anterior, que já tinha View, Function e Procedure, e integrei o Supabase como banco de dados e o Redis como cache, ranking e contadores."

## 2. Telas (≈ 1 min)
**Mostrar:** menu: Relatório de Vendas, Nova Venda, Estoque, Clientes, Produtos, Painel Redis.

> "O Relatório mostra as vendas; Nova Venda registra uma venda; Estoque mostra a situação dos produtos; Clientes e Produtos são os cadastros; e o Painel Redis mostra o que está guardado no Redis."

## 3. Supabase (≈ 1 min 30 s)
**Mostrar:** painel do Supabase → Table Editor (tabelas `clientes`, `produtos`, `vendas`). Depois SQL Editor com `SELECT * FROM vw_relatorio_vendas;`.

> "O Supabase é o banco de dados principal, um PostgreSQL na nuvem. Aqui estão as tabelas e a View do relatório. As regras de negócio ficam no banco: a Function de desconto e as Procedures de venda e cancelamento."

**Mostrar:** `src/app.py`, função `connect()`.

> "A aplicação conecta pela variável de ambiente `DATABASE_URL`, sem senha escrita no código."

**Demonstração rápida:** faça uma venda em **Nova Venda** (ex.: Ana Souza, 2 Teclados) e volte ao Supabase, tabela `vendas` (atualize): a venda aparece.

> "Fiz a venda na tela e ela foi gravada no Supabase pela Procedure."

## 4. Redis – explicação (≈ 1 min)
**Mostrar:** `src/cache.py`, topo do arquivo e a função `cached()`.

> "Usei o Redis em três funcionalidades. Primeira, cache com tempo de expiração do relatório, do estoque e do desconto. O problema é que o Supabase fica na internet e cada consulta abre uma conexão e executa uma View, o que é lento. Segunda, um ranking de produtos mais vendidos com Sorted Set. Terceira, contadores atômicos de acertos e erros do cache. O Redis guarda tudo em memória e apaga as chaves sozinho quando o tempo acaba."

## 5. Redis – demonstração (≈ 3 min)
**Mostrar, nesta ordem:**

1. **Painel Redis**: mostre que está **CONECTADO** e que o cache está vazio (limpe se precisar).
2. **Relatório de Vendas** → aparece **cache MISS** com o tempo do Supabase.
   > "Primeira leitura: veio do Supabase e foi guardada no Redis."
3. Aperte **F5** → aparece **cache HIT** com o tempo do Redis e o "expira em X s".
   > "Segunda leitura: veio do Redis, bem mais rápido. Ele expira em 60 segundos."
4. **Painel Redis**: mostre as chaves `cache:vendas:relatorio` etc. com o TTL e as latências "Último Supabase" e "Último Redis".
5. **Nova Venda**: escolha Ana Souza (VIP), 2 Teclados → o desconto aparece como MISS. Mude a quantidade e volte para a mesma → aparece HIT.
   > "O cálculo do desconto é a Function do banco, e o resultado também fica em cache."
6. Clique em **Confirmar venda** → o **Relatório** mostra **MISS** de novo, já com a venda nova.
   > "Quando há uma venda, o cache é invalidado, para o relatório nunca ficar desatualizado."
7. **Painel Redis**: mostre o **ranking** com o Teclado somado, a taxa de acerto e o contador de vendas.
   > "O ranking é atualizado com ZINCRBY a cada venda, sem consulta pesada no banco."
8. No Relatório, **cancele** essa venda e volte ao Painel Redis: o ranking diminuiu.
9. (Opcional) Console do Upstash → **Data Browser**: mostre as chaves e o `ranking:produtos`.

## 6. Benefícios e encerramento (≈ 40 s)

> "Com o Redis, as consultas repetidas ficam mais rápidas, o Supabase recebe menos carga, o ranking é imediato e os contadores são atômicos. Se o Redis cair, o sistema continua funcionando lendo direto do Supabase. Obrigado."

## Depois de gravar
Assista uns 20 segundos para conferir o áudio, suba no YouTube como **não listado** (ou no Drive com link liberado) e cole o link no `README.md`, na seção **Vídeos**.
