# Ficha 01 — Ambiente e primeiro endpoint · Environment and first endpoint

Aula 01 (12/10/2026) · solução de referência · reference solution

**PT** — Os alunos entregaram um repositório `dwfa-<nome>` com este conteúdo. Não é a única resposta certa: comparem com o vosso código. Projeto Django 5.2 criado com `uv`, PostgreSQL 16 em Docker, ligação configurada por `DATABASE_URL` (django-environ) e um endpoint `GET /api/health/` que devolve `200 {"status":"ok","db":"ok"}` quando a base de dados responde e **503** quando não responde. É a semente do projeto: o M1 constrói-se sobre este repositório.
**EN** — Students submitted a `dwfa-<yourname>` repository with this content. Not the only correct answer: compare it with your own code. Django 5.2 project created with `uv`, PostgreSQL 16 in Docker, connection configured through `DATABASE_URL` (django-environ) and a `GET /api/health/` endpoint returning `200 {"status":"ok","db":"ok"}` when the database answers and **503** when it does not. It is the seed of the project: M1 is built on this repository.

```sh
docker compose up -d db && docker compose ps        # db "healthy"
uv sync                                             # cria .venv com as dependências · creates .venv with the deps
uv run python manage.py migrate                     # 18 tabelas · 18 tables
docker compose exec db psql -U dwfa -c '\dt'        # confirmar · check
uv run python manage.py runserver                   # http://localhost:8000/api/health/
curl -i http://localhost:8000/api/health/           # HTTP/1.1 200 · Content-Type: application/json
docker compose stop db && curl -i http://localhost:8000/api/health/   # HTTP/1.1 503
uv run python manage.py test                        # 2 testes · 2 tests
```

Python 3.13 · uv · Docker Compose v2 · Node 22 só a partir da Aula 05 · Node 22 only from Aula 05 on.

## Como foi feito · How it was built

```sh
uv init dwfa && cd dwfa
uv add "django>=5.2,<5.3" "psycopg[binary]" django-environ
uv run django-admin startproject config .
uv run python manage.py startapp core
```

Depois · then: `compose.yaml`, `DATABASES` em `config/settings.py`, `core/views.py` + `config/urls.py`, `core/tests.py`, `.gitignore`, `.env.example`, `docs/ficha-01.md`.

## O que se verifica · What to check

1. `docker compose ps` mostra `db` `healthy`; `psql -c '\dt'` lista as tabelas do `migrate` · shows `db` healthy; `\dt` lists the migrated tables.
2. `curl -i /api/health/` → `200`, `Content-Type: application/json`, corpo `{"status": "ok", "db": "ok"}`.
3. Com a base de dados parada → **`503`** com corpo JSON, não um *traceback* 500 · with the DB stopped → **503** with a JSON body, not a 500 traceback.
4. `config/settings.py` lê `DATABASE_URL` do ambiente, com *default* para o Docker local; não há palavras-passe de produção no código · reads `DATABASE_URL` from the environment, default for local Docker; no production passwords in code.
5. `.gitignore` exclui `.venv/`, `.env`, `__pycache__/`, `pgdata/`; o repositório tem `uv.lock` · excludes those; the repo includes `uv.lock`.
6. `docs/ficha-01.md` responde às perguntas de reflexão · answers the reflection questions.

## Erros comuns · Common mistakes

- `docker compose up` sem `-d` e sem `db` — o terminal fica preso ao log · without `-d` the terminal is stuck on the log.
- Porta 5432 ocupada por um PostgreSQL local (`lsof -i :5432`) → `"5433:5432"` no compose **e** `DATABASE_URL` com `:5433` · port 5432 taken by a local PostgreSQL → change both.
- `uv run django-admin startproject config` **sem o ponto** cria `config/config/` · without the trailing dot creates a nested folder.
- Esquecer `"core"` em `INSTALLED_APPS` — não falha hoje, falha nas migrações da Ficha 02 · forgetting it does not fail today, fails at Ficha 02's migrations.
- Fazer *commit* da `.venv/` ou do `.env` · committing `.venv/` or `.env`.
- Health check que devolve 200 com `"db": "error"` — o código de estado é a parte que as máquinas leem · a 200 with `"db": "error"` in the body — the status code is the part machines read.
