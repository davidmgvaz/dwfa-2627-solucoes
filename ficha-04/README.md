# Ficha 04 — SPA Vue autenticada · Authenticated Vue SPA (partes 1 e 2 · parts 1 and 2)

Aulas 05 + 06 (02/11 e 09/11/2026) · solução de referência · reference solution — construída sobre `ficha-03/` · built on top of `ficha-03/`. O backend é o da Ficha 03 com **uma** alteração: `COMPONENT_SPLIT_REQUEST: True` no drf-spectacular (e o `schema.yaml` regenerado), para que os tipos gerados do OpenAPI tenham `…Request` sem os campos `read_only` · the backend is Ficha 03's with **one** change: `COMPONENT_SPLIT_REQUEST` (and a regenerated `schema.yaml`), so the generated request types drop the `read_only` fields. O que é novo está em **[`frontend/`](frontend/)**: parte 1 (Aula 05) lista e detalhe do catálogo; parte 2 (Aula 06) tipos gerados + `openapi-fetch`, *store* Pinia `auth` com *refresh*, login + *guard*, «as minhas encomendas» e formulário com erros por campo, 10 testes · part 1: list and detail; part 2: generated types, auth store with refresh, login + guard, my orders and an order form with field errors, 10 tests.

```sh
cp .env.example .env && docker compose up -d && uv sync
uv run python manage.py migrate && uv run python manage.py seed
uv run python manage.py runserver                        # API em :8000 (CORS: http://localhost:5173)
cd frontend && cp .env.example .env && npm install && npm run dev   # SPA em :5173
```

---

## Backend (= Ficha 03) · backend (= Ficha 03)

Aula 04 (26/10/2026) · solução de referência · reference solution — construída sobre `ficha-02/` · built on top of `ficha-02/`

**PT** — Os alunos entregaram o mesmo *fork* da Ficha 02 com a tag `ficha-03`. Não é a única resposta certa: comparem com o vosso código. Login e *refresh* com JWT (`djangorestframework-simplejwt`, access 30 min, refresh 1 dia, rotação + blacklist), `IsAuthenticated` por omissão, `/api/v1/me/`; papel **`gestores`** (grupo criado por migração de dados) com `IsGestor`/`IsGestorOrReadOnly`; encomendas filtradas ao cliente (**alheia = 404**) e `IsOwnerOrGestor` em `pay`/`cancel`/`PATCH`; `customer`/`status`/`total` só de leitura; CORS com lista explícita, throttling `auth` 10/min no login, Argon2, `check --deploy` limpo em `prod.py`; e o teste de autorização parametrizado por papel. Opcional implementado: nenhum (CSP, allauth e audit log ficam como exercício — ver os slides da Aula 04).
**EN** — Students submitted the same Ficha 02 fork tagged `ficha-03`. Not the only correct answer: compare it with your own code. JWT login and refresh (simplejwt, 30-min access, 1-day refresh, rotation + blacklist), `IsAuthenticated` by default, `/api/v1/me/`; **`gestores`** role (group from a data migration) with `IsGestor`/`IsGestorOrReadOnly`; orders filtered to the caller (**someone else's = 404**) and `IsOwnerOrGestor` on `pay`/`cancel`/`PATCH`; `customer`/`status`/`total` read-only; explicit CORS allowlist, `auth` throttle 10/min on login, Argon2, clean `check --deploy` on `prod.py`; and the role-parametrised authorization test. Optional parts not implemented (CSP, allauth, audit log stay as exercises — see the Aula 04 slides).

```sh
cp .env.example .env && docker compose up -d && uv sync
uv run python manage.py migrate                     # + tabelas da blacklist, grupo "gestores" · blacklist tables, group
uv run python manage.py seed && uv run python manage.py createsuperuser
uv run python manage.py runserver
curl -s localhost:8000/api/v1/orders/                                   # 401 (Problem Details)
curl -s -X POST localhost:8000/api/v1/auth/token/ -H "Content-Type: application/json" \
  -d '{"username":"ana","password":"<a password do seed>"}'              # {"access":…,"refresh":…}
curl -s localhost:8000/api/v1/me/ -H "Authorization: Bearer <access>"   # {"id":…,"username":"ana","groups":[]}
uv run pytest                                       # 36 testes verdes · 36 green tests
DJANGO_SETTINGS_MODULE=config.settings.prod ALLOWED_HOSTS=shop.example \
  uv run python manage.py check --deploy            # System check identified no issues
```

> O `seed` cria `ana`, `bruno`, `carla` com a password `pass1234` da `UserFactory` (só para dev) · the seed users use the factory password `pass1234` (dev only). Para testar como gestor: admin → Users → Groups → `gestores` · to test as a manager, add a user to the `gestores` group in the admin.

## Como foi feito · How it was built

```sh
uv add djangorestframework-simplejwt django-cors-headers argon2-cffi
uv run python manage.py makemigrations shop --empty --name group_gestores   # RunPython → Group "gestores"
uv run python manage.py migrate
uv run python manage.py spectacular --file schema.yaml
```

`config/settings/base.py` (`REST_FRAMEWORK` auth/permissões/throttle, `SIMPLE_JWT`, `CORS_*`, `PASSWORD_HASHERS`, validador a 12, `SECRET_KEY_FALLBACKS`) · `config/settings/prod.py` (HSTS 1 ano + preload) · `accounts/views.py` (`ThrottledTokenView`, `MeView`) · `config/urls.py` · `shop/permissions.py` · `shop/migrations/0002_group_gestores.py` · `shop/views.py` (queryset filtrado, `perform_create`, `get_serializer_class`) · `shop/serializers.py` (`read_only_fields`, `GestorOrderSerializer`) · testes em `accounts/tests/test_jwt.py`, `accounts/tests/test_hardening.py`, `shop/tests/test_auth.py` (+ `conftest.py` com os três atores) · `docs/decisions.md` · `docs/ficha-03.md`.

## O que se verifica · What to check

1. `GET /api/v1/orders/` sem token → **401** com corpo Problem Details; com `Bearer` → 200 e **só as encomendas do cliente** · 401 without a token; only the caller's orders with one.
2. `POST /api/v1/auth/token/` → par `access`/`refresh`; o *refresh* repetido com o **mesmo** token → 401 «Token is blacklisted» · reusing the old refresh token fails.
3. `GET /api/v1/me/` → `{"id","username","groups"}` · the SPA's "who am I".
4. `/api/v1/categories/` e `/api/v1/products/` leem-se **sem** token (`AllowAny`/`IsGestorOrReadOnly`, com comentário); `POST /products/` → 401 anónimo, **403** cliente, 201 gestor · public catalogue, writes for managers.
5. `GET /api/v1/orders/<id de outro>/` e `POST …/pay/` como cliente → **404**, não 403 · a foreign order is a 404.
6. `PATCH /orders/<minha>/ {"status":"paid"}` → 200 e o `status` **não muda** (`read_only_fields`); `POST /orders/` com `customer` de outro → o dono é o `request.user` · server-owned fields.
7. `MIDDLEWARE[0]` é o `CorsMiddleware`; `OPTIONS` com `Origin: http://localhost:5173` → 200 com `Access-Control-Allow-Origin` · preflight works for the SPA origin.
8. 11 logins errados seguidos → `401 ×10` e depois **429** · throttled after ten attempts.
9. `check --deploy` com `config.settings.prod` → `System check identified no issues (0 silenced)` (inclui os avisos do drf-spectacular: `queryset = Model.objects.none()` nos viewsets com `get_queryset`, `@extend_schema` na `MeView`) · zero warnings, spectacular's included.
10. `uv run pytest` → 36 verdes: 12 da Ficha 02 (os de API agora autenticados) + 3 JWT + 4 hardening + 17 da matriz endpoint × papel · 36 green.
11. `docs/decisions.md` com os tempos de vida, onde a SPA guarda o token e porquê, e a matriz; `docs/ficha-03.md` com as duas respostas · decisions and answers.

## Erros comuns · Common mistakes

- `CorsMiddleware` depois do `CommonMiddleware` → o *preflight* leva 401 e a SPA nunca chega a fazer o pedido · CORS middleware must be first.
- `IsAuthenticated` por omissão sem reabrir o catálogo → `/api/v1/products/` dá 401 e a SPA da Aula 05 não lista produtos · reopen the catalogue on purpose.
- `SessionAuthentication` removida → a Browsable API passa a 403 em `POST` e a culpa cai no JWT · keep session auth for the admin and Browsable API.
- Grupo criado à mão no admin e não por migração → `Group.DoesNotExist` na CI · create the group in a data migration.
- `has_object_permission` sem filtro no queryset → a lista mostra tudo; filtro sem `has_object_permission` → `PATCH` num id conhecido passa; encomenda alheia a dar 403 em vez de 404 · both layers, 404 not 403.
- `is_gestor()` chamado duas vezes por pedido (queryset + serializer) sem cache → uma query a mais; o teste «≤ 4 queries» apanha-o · cache the group check on the user.
- `throttle_scope` sem `throttle_classes` na subclasse da vista de token → a *rate* `auth` nunca se aplica · both attributes on the subclass.
- `check --deploy` corrido com `dev.py`, ou contra `prod.py` com uma `SECRET_KEY` curta (W009) · run it against prod with a real-length key.
- Viewsets só com `get_queryset` sem `queryset = Model.objects.none()` → avisos do drf-spectacular no `check` e `id` sem tipo no Swagger · schema generation needs the model hint.
- `SECRET_KEY` com valor por omissão em `base.py` «para os testes passarem» → vai para o git · never a default secret in code.
