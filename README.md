# Sistema de Vendas – Integração com Supabase e Redis

## Identificação

- **Aluno:** _(coloque seu nome completo)_
- **Disciplina:** _(nome da disciplina)_
- **Professor:** _(nome do professor)_

## Vídeos

- **Trabalho atual (Supabase + Redis):** _(cole aqui o link do novo vídeo)_
- **Trabalho anterior (View, Function e Procedure):** https://youtu.be/DC_rN21dBm0

## Sobre o projeto

Aplicação web de vendas com controle de estoque. Ela resolve o problema de registrar uma venda com segurança (validação de estoque, desconto, baixa de estoque e histórico) e de consultar relatórios de forma rápida.

Este trabalho **evolui o projeto anterior** (CRUD + View, Function e Procedure no PostgreSQL) com duas integrações:

- **Supabase**: banco de dados PostgreSQL na nuvem, onde ficam os dados e as regras de negócio (View, Function e Procedures).
- **Redis**: cache das consultas ao Supabase, ranking de produtos mais vendidos e contadores.

### Funcionalidades

- Relatório de vendas (lê a View `vw_relatorio_vendas`).
- Nova venda com cálculo de desconto (Function) e registro atômico (Procedure).
- Cancelamento de venda, devolvendo o estoque (Procedure).
- Estoque com situação OK / BAIXO / ESGOTADO (View `vw_estoque_situacao`).
- Cadastro de clientes e produtos.
- **Painel Redis**: chaves em cache com tempo de expiração, taxa de acerto, ranking e latências.

## Tecnologias utilizadas

- Python 3 + Flask
- PostgreSQL hospedado no **Supabase**
- **Redis** (Upstash ou Redis local) com a biblioteca `redis-py`
- psycopg2
- HTML/CSS/JavaScript

## Capturas de tela

| Relatório de Vendas (cache HIT no Redis) | Estoque |
|---|---|
| ![Relatório](docs/img/01-relatorio-vendas.png) | ![Estoque](docs/img/02-estoque.png) |

| Nova Venda (desconto vindo da Function / Redis) | Painel Redis |
|---|---|
| ![Nova venda](docs/img/03-nova-venda.png) | ![Painel Redis](docs/img/04-painel-redis.png) |

## Integração com o Supabase

O Supabase é o banco de dados principal. A aplicação se conecta a ele pela variável de ambiente `DATABASE_URL` (string de conexão do **Session pooler**), usando `psycopg2` (`src/app.py`, função `connect()`).

O que fica no Supabase:

| Recurso | Nome | Finalidade | Onde é usado |
|---|---|---|---|
| Tabelas | `clientes`, `produtos`, `vendas`, `itens_venda`, `movimentacoes_estoque` | Armazenam os dados | Todas as telas |
| View | `vw_relatorio_vendas` | Junta vendas, clientes e itens em um relatório | Tela Relatório de Vendas |
| View | `vw_estoque_situacao` | Classifica o estoque e soma o total vendido | Tela Estoque e lista da Nova Venda |
| Function | `fn_calcular_desconto(cliente_id, subtotal)` | VIP 10% + 5% se subtotal ≥ R$ 500 | Prévia de desconto da Nova Venda |
| Procedure | `sp_realizar_venda(...)` | Registra a venda inteira de forma atômica | Botão "Confirmar venda" |
| Procedure | `sp_cancelar_venda(venda_id)` | Cancela a venda e devolve o estoque | Botão "Cancelar" |

Os scripts SQL estão em `database/` (`tables`, `views`, `functions`, `procedures`, `inserts`) e são executados por `src/init_db.py`. Todas as telas leem e gravam dados reais no Supabase.

## Integração com o Redis

O Redis é usado em **três funcionalidades**, todas no arquivo `src/cache.py` e chamadas por `src/app.py`.

### 1. Cache com TTL (cache-aside)

- **Onde:** Relatório de Vendas (`/vendas`), Estoque (`/estoque`) e cálculo de desconto (`/api/desconto`).
- **Problema:** esses dados são lidos o tempo todo e o Supabase fica na internet. Cada leitura abre uma conexão com o banco remoto e executa uma View ou Function, o que é lento e sobrecarrega o banco.
- **Como funciona:** na primeira leitura os dados vêm do Supabase (**MISS**) e são guardados no Redis com um tempo de expiração (TTL: 60 s para relatório e estoque, 300 s para o desconto). Nas leituras seguintes vêm direto do Redis (**HIT**). As telas mostram a origem dos dados e o tempo da consulta.
- **Invalidação:** uma venda, um cancelamento ou o cadastro de um produto apagam as chaves afetadas (`cache:vendas:relatorio`, `cache:estoque:lista`), para que os números nunca fiquem desatualizados.
- **Exceção proposital:** a lista de produtos da tela Nova Venda **não** usa cache, porque a venda precisa sempre do estoque real.

### 2. Ranking de produtos mais vendidos (Sorted Set)

- **Onde:** Painel Redis (`/redis`).
- **Problema:** calcular "os mais vendidos" exigiria um `GROUP BY` no Supabase a cada consulta.
- **Como funciona:** cada venda soma as quantidades com `ZINCRBY` na chave `ranking:produtos`, e cada cancelamento subtrai. O top 5 é lido com `ZREVRANGE`, que já vem ordenado. Se o ranking for perdido, o botão "Recalcular ranking pelo Supabase" o reconstrói a partir das vendas.

### 3. Contadores atômicos

- **Onde:** Painel Redis.
- **Como funciona:** `INCR` conta os acertos (HIT), os erros (MISS) e as vendas registradas. É atômico, então funciona corretamente mesmo com vários acessos simultâneos.

### Por que o Redis?

Ele guarda dados em memória, tem expiração automática de chaves (TTL) e estruturas prontas como o Sorted Set. Isso reduz a latência e a carga no Supabase sem alterar as regras de negócio, que continuam no banco.

### Se o Redis estiver fora do ar

A aplicação continua funcionando: se `REDIS_URL` não estiver definida ou o Redis não responder, os dados são lidos direto do Supabase e as telas mostram o aviso "Redis indisponível".

## Como executar

### Pré-requisitos

- Python 3.10 ou superior
- Uma conta gratuita no [Supabase](https://supabase.com) e outra no [Upstash](https://upstash.com) (Redis na nuvem). Dá para usar um Redis local no lugar do Upstash.

### 1. Supabase

1. Crie um projeto no Supabase e guarde a senha do banco (use só letras e números).
2. Clique em **Connect** e copie a string do **Session pooler**:
   `postgresql://postgres.SEU_PROJETO:SENHA@aws-0-REGIAO.pooler.supabase.com:5432/postgres`

### 2. Redis (Upstash)

1. No Upstash, crie um banco **Redis** (plano Free, TLS ligado).
2. Na página do banco, pegue **Endpoint**, **Port** e **Token** (aba **Connect → TCP**).
3. Monte a URL: `rediss://default:TOKEN@ENDPOINT:PORT`

Alternativa com Redis local (Linux/Mac/Docker): `docker run -p 6379:6379 redis` e use `REDIS_URL=redis://localhost:6379/0`.

### 3. Instalar e configurar

```bash
cd src
pip install -r requirements.txt
```

As configurações sensíveis ficam em **variáveis de ambiente**, nunca nos arquivos:

| Variável | O que é |
|---|---|
| `DATABASE_URL` | String de conexão do Supabase |
| `REDIS_URL` | URL do Redis (`rediss://default:TOKEN@HOST:PORT`) |

Windows (PowerShell):
```powershell
$env:DATABASE_URL="postgresql://postgres.SEU_PROJETO:SENHA@aws-0-REGIAO.pooler.supabase.com:5432/postgres"
$env:REDIS_URL="rediss://default:TOKEN@ENDPOINT:6379"
```

Linux/Mac:
```bash
export DATABASE_URL="postgresql://postgres.SEU_PROJETO:SENHA@aws-0-REGIAO.pooler.supabase.com:5432/postgres"
export REDIS_URL="rediss://default:TOKEN@ENDPOINT:6379"
```

### 4. Criar o banco e executar

```bash
py init_db.py     # Windows (no Linux/Mac: python3). Cria tabelas, view, function, procedures e dados de teste
py app.py         # inicia a aplicação
```

Acesse http://127.0.0.1:5000. O `init_db.py` só precisa rodar uma vez; ele recria o banco do zero.

### 5. Como testar o Redis

1. Abra **Painel Redis** e clique em **Limpar cache** e **Zerar contadores**.
2. Abra **Relatório de Vendas**: aparece **cache MISS** (dados do Supabase). Atualize a página: aparece **cache HIT** (dados do Redis), com o tempo de expiração.
3. Em **Nova Venda**, escolha um cliente e produtos: o desconto (Function) aparece como MISS e, ao repetir o mesmo carrinho, como HIT.
4. Confirme uma venda (Procedure): o relatório volta a mostrar MISS (cache invalidado) já com a venda nova.
5. No **Painel Redis**, veja as chaves com TTL, a taxa de acerto e o ranking de produtos. Cancele uma venda e veja o ranking diminuir.

## Estrutura do repositório

```
/
├── src/                  aplicação Flask (app.py, cache.py, init_db.py, templates/)
├── database/
│   ├── tables/           criação das tabelas
│   ├── views/            views
│   ├── functions/        functions
│   ├── procedures/       procedures
│   └── inserts/          dados de teste
├── docs/                 roteiros dos vídeos e capturas de tela
└── README.md
```
