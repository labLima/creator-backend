# Creator backend

Backend Python 3.12/FastAPI do Creator: multi-tenant, contract-first, com
autenticação própria, SQLite local e providers de IA atrás de interfaces.

## Quick start

```bash
cp .env.example .env
make dev/start
curl http://localhost:8000/health
```

`make dev/start` constrói a imagem, aplica as migrations e sobe API, worker e
Redis. O banco SQLite fica em um volume nomeado; o storage local também.

Se um `.env` antigo ainda definir `DATABASE_URL` para PostgreSQL, comente essa
linha para usar o SQLite padrão do Compose (`/data/creator.db`). Uma variável
`DATABASE_URL` definida no shell também prevalece sobre o `.env`. O SQLite é
um banco novo; dados antigos de PostgreSQL exigem backup e migração explícita.

```bash
make dev/stop          # para os serviços sem remover volumes
make dev/clean CONFIRM=yes  # remove containers, volumes e imagens do projeto
```

`make dev/clean` é destrutivo e exige `CONFIRM=yes`. Use `make dev/logs` para
acompanhar os containers.

## Execução local sem Docker

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e '.[dev]'
alembic upgrade head
uvicorn creator.main:app --host 0.0.0.0 --port 8000 --reload
```

Em outro processo:

```bash
creator-worker all
```

O banco padrão é `sqlite+pysqlite:///./.local/db/creator.db`. A conexão é
configurável por `DATABASE_URL`; o runtime é compatível com SQLite e libSQL
(servidor SQLite) sem alterar os casos de uso.

## Autenticação

A autenticação é própria do Creator:

- `POST /api/v1/auth/signup` cria User, Workspace e Membership `owner`.
- `POST /api/v1/auth/login` retorna access token JWT e refresh token rotativo.
- `POST /api/v1/auth/refresh` rotaciona o refresh token e detecta reuso.
- `POST /api/v1/auth/logout` revoga a sessão.

Configure `AUTH_JWT_SECRET` com um valor forte. Em produção, use
`AUTH_REQUIRED=true` e mantenha o secret em um gestor de secrets.

## IA e storage

O provider de IA inicial é Google Gemini, via `google-genai`:

- texto: `gemini-2.5-flash`;
- imagem: `gemini-2.5-flash-image`;
- reviewer multimodal: `gemini-2.5-flash`.

Configure `GEMINI_API_KEY` no `.env`. Sem a chave, as chamadas de geração
retornam erro estruturado de provider não configurado; a API continua
disponível. CrewAI e LangChain estão preparados atrás de interfaces, mas
desabilitados por padrão.

Storage local é o padrão de desenvolvimento; Supabase Storage permanece
opcional atrás de `STORAGE_PROVIDER=supabase`.

## Comandos

```bash
make install       # instala dependências de desenvolvimento
make check         # ruff lint, format check, mypy e pytest
make security      # pip-audit + gitleaks
make e2e           # fluxos E2E de auth, Workspace e geração
make test          # pytest sem os testes marcados como e2e
make run           # API local
make worker        # worker local (creator-worker all)
make dev/start     # Compose: API, worker, Redis, migrations
make dev/stop      # para sem remover volumes
make dev/clean     # remove containers/volumes/imagens do projeto (CONFIRM=yes)
```

O CI executa `make check`, `make dependency-audit`, Gitleaks, paridade do
OpenAPI, `make e2e` e um smoke test dos containers.

## Arquitetura

- `src/creator/api`: dependências, DTOs e contratos HTTP.
- `src/creator/domain`: vocabulário e modelos independentes de vendor.
- `src/creator/application`: casos de uso.
- `src/creator/infrastructure`: banco, auth, fila, storage e métricas.
- `src/creator/repositories`: protocolos e implementações de persistência.
- `src/creator/services`: providers de IA, storage, agentes e retrieval.
- `src/creator/integrations`: adapters concretos de vendors.
- `src/creator/workers`: workers RQ.
- `docs/adr`: decisões arquiteturais; `docs/issues`: issues rastreáveis.

O contrato HTTP é `docs/openapi.yaml`. O teste `tests/test_openapi_contract.py`
garante paridade entre o contrato estático e `app.openapi()`; qualquer drift
falha no CI.

### Migração do SPA para cookies

Use `credentials: "include"` em todas as chamadas à API. O access e o refresh
ficam em cookies `HttpOnly`; o SPA lê apenas `creator_csrf` e envia seu valor
no header `X-CSRF-Token` em mutações. Não armazene tokens em `localStorage`.

Coordene um único refresh por vez (single-flight). Em `401`, aguarde o refresh
compartilhado e repita a requisição uma vez. Em `409 REFRESH_IN_PROGRESS`,
aguarde o refresh em andamento; falhas posteriores devem limpar o estado local
e exigir novo login. Durante a janela de migração, o backend pode manter Bearer
e tokens no corpo; o cutover desliga essas flags.

## Banco e migrations

O baseline SQLite está em `migrations/versions/0001_sqlite_baseline.py`. As
migrations PostgreSQL antigas foram arquivadas em `migrations/legacy_postgres/`
e não são executadas. O cutover assume banco novo (decisão C1); se houver dados
a preservar, faça backup e um ETL explícito antes de aplicar o baseline.

## GitHub issues

O script `scripts/create_github_issues.sh` publica de forma idempotente os
arquivos de `docs/issues/` usando `gh`, adicionando labels e preservando os
links ADR. Ele exige `gh auth status` válido e nunca imprime tokens.
