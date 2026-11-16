# Decisões · Decisions

PT: uma linha por decisão — o quê, porquê, alternativa rejeitada. Cresce ficha a ficha; o M1/M2/M3 avaliam este ficheiro.
EN: one line per decision — what, why, rejected alternative. Grows ficha by ficha; M1/M2/M3 grade this file.

## Esqueleto · Skeleton

- **`AUTH_USER_MODEL = "accounts.User"` desde o dia zero** — trocar depois da primeira migração obriga a reescrever o histórico; um `AbstractUser` vazio não custa nada. · Declared on day zero; swapping later means rewriting migration history; an empty `AbstractUser` is free.
- **Settings por ambiente (`base/dev/test/prod`) com `django-environ`** — o mesmo código em todos os ambientes, só as variáveis mudam (12-factor); segredos fora do git. · Same code everywhere, only env vars change; secrets stay out of git.
- **`/api/health/` devolve 503, não 500, com a base de dados em baixo** — é o código que um load balancer lê como "tira esta instância de rotação". · 503 is what a load balancer reads as "take this instance out of rotation".

## Ficha 02 — modelos · models

- **`Order.customer` com `on_delete=PROTECT`** (e `Product.category`, `OrderItem.product`) — uma encomenda é um registo contabilístico e não desaparece com o cliente; só `OrderItem.order` e `Payment.order` são CASCADE porque não existem sem a encomenda. Rejeitado: CASCADE em tudo, que apagaria histórico de vendas. · An order is an accounting record; only lines and payments cascade. Rejected: CASCADE everywhere, which would delete sales history.
- **`UniqueConstraint(order, product)` em `OrderItem`** — o mesmo produto duas vezes na mesma encomenda é um erro de cliente; a constraint apanha-o em todos os caminhos de escrita (admin, shell, serializer). Mais `CheckConstraint` em `quantity > 0`, `price >= 0`, `amount > 0`. · Same product twice in an order is a client error; the DB catches it on every write path.
- **JSONB sim, em `Product.attributes`** — atributos variam por categoria (cor, tamanho, voltagem) e não são filtrados nesta fase; uma tabela EAV ou colunas por categoria seriam mais caras para nenhum ganho. Sem `GinIndex` até haver uma query que o justifique (Aula 09). · Per-category attributes with no fixed schema; EAV or per-category columns rejected; no GIN index until a query needs it.
- **Índice composto `(customer, created_at)` em `Order`** — a listagem "as minhas encomendas, mais recentes primeiro" é a query mais frequente da loja. · The most frequent shop query is "my orders, newest first".

## Ficha 02 — API

- **`unit_price`, `total`, `status`, `created_at` só de leitura** — o preço é copiado do produto no servidor (`OrderItemSerializer.create`), o total vem de `annotate`, o estado só muda por `pay`/`cancel`; nada disto vem do cliente. · Price copied on the server, total annotated, status only via actions; none of it comes from the client.
- **`PageNumberPagination`, `PAGE_SIZE = 20`** — simples e suficiente para catálogos pequenos; `CursorPagination` quando a tabela de encomendas crescer e `?page=500` começar a custar (candidato a tema do trabalho de investigação). · Simple and enough for a small catalogue; cursor pagination when offset pages get expensive.
- **Versionamento por URL (`/api/v1/`)** — visível, cacheável, fácil de rotear no Nginx; rejeitado o versionamento por cabeçalho `Accept`, mais "correto" mas invisível no browser e no Swagger. · URL versioning is visible and routable; header versioning rejected as invisible in the browser and Swagger.
- **Queries na lista de encomendas: 82 sem `prefetch_related`, 3 com** (25 encomendas × 3 linhas: `COUNT` + encomendas com JOIN de cliente/utilizador + linhas com JOIN de produto). O teste `test_order_list_is_paginated_without_n_plus_one` falha no dia em que alguém remover o prefetch. · 82 queries without the prefetch, 3 with it; the test fails the day someone removes it.
- **Erros no formato Problem Details (RFC 9457)** via `EXCEPTION_HANDLER` — um só envelope (`type`, `title`, `status`, `errors`) para 400/404/409/429; o que não é exceção DRF continua a ser 500, um bug a registar. · One error envelope for every DRF error; non-DRF exceptions stay 500.
- **`pay` e `cancel` em `services.py` com `select_for_update`** — a transição de estado corre numa transação com bloqueio de linha; dois `POST /pay/` concorrentes não pagam duas vezes. A vista só traduz a exceção `Conflict` em 409. · State transitions lock the row; the view only maps `Conflict` to 409.

## Ficha 03 — autenticação, autorização e segurança · authentication, authorization and security

- **JWT (simplejwt) para `/api/v1/`, sessão mantida para o admin e a Browsable API** — a SPA da Aula 05 corre noutra origem (`localhost:5173`) e um cliente mobile reutilizaria o mesmo login; rejeitada a sessão-só, que obrigaria a CSRF e ao mesmo site. · JWT for the API because the SPA lives on another origin; session kept for admin/Browsable API.
- **Access 30 min · refresh 1 dia · rotação + blacklist** — janela curta para um token roubado e logout real; rejeitado refresh de 7 dias sem blacklist. · Short window for a stolen token and a real logout.
- **Token no corpo da resposta; access em memória, refresh em `localStorage`** — sem CSRF; o XSS mitiga-se com os tempos curtos e CSP (opcional); rejeitada a cookie `HttpOnly`, que traria o CSRF de volta e exigiria o mesmo site. · Tokens in the body; HttpOnly cookie rejected (brings CSRF back, needs same-site).
- **`IsAuthenticated` por omissão; `AllowAny` só em `categories`, `IsAuthenticatedOrReadOnly` em `products`** — fechado por omissão, aberto de propósito e com comentário. · Closed by default, opened on purpose.
- **Papel = grupo `gestores` criado por migração de dados** — o `User` fica vazio, atribuível no admin sem deploy, existe na CI; rejeitado um campo `role` no `User`. · Role as a Django group from a data migration; `role` field rejected.
- **Encomenda alheia → `404` (filtro no `get_queryset`), não `403`** — não confirmar que existe; `IsOwnerOrGestor` fica como segunda camada para `pay`/`cancel`/`PATCH`. · Foreign order is a 404 via the queryset filter; object permission is the second layer.
- **`customer`, `status`, `total`, `unit_price` só de leitura; `GestorOrderSerializer` com `status` escrevível** — o cliente não paga com um `PATCH`; o gestor pode corrigir. · Server-owned fields read-only; managers get a second serializer.
- **CORS: lista explícita do `.env`, middleware em primeiro, só `/api/`** — `*` rejeitado (e proibido pelo browser com credenciais). · Explicit allowlist, middleware first, API paths only.
- **Throttle `auth` 10/min no endpoint de token** — trava a adivinhação sem bloquear contas (lockout = DoS contra os próprios utilizadores). · Login throttling instead of account lockout.
- **Argon2 primeiro, PBKDF2 segundo; `min_length` 12** — hashes antigos continuam válidos e migram no próximo login. · Argon2 first; PBKDF2 keeps old hashes valid.
- **`check --deploy` limpo com `prod.py`: HSTS 1 ano + preload** — o esqueleto já tinha o resto; o `dev.py` avisa sempre, por desenho. · HSTS one year + preload; `dev.py` always warns, by design.
- **Matriz endpoint × papel** (anónimo · cliente · gestor): `categories`/`products` GET ✓ ✓ ✓ · `products` escrita 401 403 ✓ · `orders` GET 401 só as suas todas · `orders/{id}` alheia 401 **404** ✓ · `orders` POST 401 ✓ (dono = eu) ✓ · `orders/{id}/pay` 401 só a sua ✓ · `customers` 401 403 ✓ · `me` 401 ✓ ✓. É o `shop/tests/test_auth.py`.

## Ficha 04 — frontend (parte 1 · part 1)

- **`frontend/` dentro do mesmo repositório** — o M2 entrega SPA + CI + Docker num só repositório; o CI corre `pytest` e `vue-tsc`/`vitest` no mesmo *workflow*. Rejeitado: um repositório separado por frontend. · One repository: M2, CI and Docker build live together; a separate frontend repo rejected.
- **`npm create vue@latest` com TypeScript, Router, Pinia, Vitest, ESLint** — o *scaffold* oficial; `strict` ligado; a Pinia fica instalada para a parte 2. · Official scaffold, strict TS; Pinia waits for part 2.
- **CORS (Ficha 03) em vez de `server.proxy` do Vite** — é o que o M2 vai precisar com o frontend servido pelo Nginx noutra origem; o *proxy* só esconderia o problema em dev. · CORS is what production needs; the dev proxy only hides it.
- **Tipos escritos à mão em `src/types.ts`** — para sentir o contrato; na Aula 06 passam a ser gerados do `schema.yaml` (`openapi-typescript`). `price` é `string` porque o DRF serializa `DecimalField` assim. · Hand-written now, generated from OpenAPI in Aula 06; decimals are strings.
- **Pesquisa e página no `route.query`, não só em `ref`s** — recarregar e partilhar o *link* mantêm o estado; `v-model.lazy` para não fazer um pedido por tecla. · The URL is the source of truth for list state.
- **`useFetch<T>` com `watchEffect`** — os três estados escritos uma vez; re-executa quando `search`/`page` mudam. Rejeitado: `onMounted` + `watch` à mão em cada vista. · One composable for the three states, re-run on dependency change.
- **Rota de detalhe *lazy*** — `() => import(...)` cria um *chunk* próprio; o catálogo carrega sem o código do detalhe. · Lazy detail route, separate chunk.

## Ficha 04 — frontend (parte 2 · part 2)

- **Tipos gerados do `schema.yaml` com `openapi-typescript`, cliente `openapi-fetch`** — o contrato é o OpenAPI da API, não um ficheiro à mão; um caminho ou um parâmetro de *query* errados não compilam. `types.ts` fica como *aliases* curtos. Rejeitado: manter o `fetch` à mão (funcionava, mas o tipo era uma promessa sem verificação). · Generated types and a typed client; hand-written types kept only as short aliases.
- **`COMPONENT_SPLIT_REQUEST: True` no drf-spectacular** — sem isto o componente `TokenObtainPair` exigia `access`/`refresh` no corpo do pedido (são `read_only`). Os campos com `default` continuam opcionais na resposta (`stock`, `attributes`, `is_active`) — estreitados uma vez em `types.ts`. · Split request/response components; defaulted fields narrowed once.
- **`access` em memória, `refresh` em `localStorage`** (a decisão da Aula 04): um XSS lê o `localStorage`, mas o `access` de 30 min não está lá e o `refresh` roda a cada uso (blacklist). Rejeitado: cookie `HttpOnly` — a API teria de emitir cookies e voltar a precisar de CSRF; é uma alternativa válida, não a nossa. · Access in memory, refresh in storage; the HttpOnly-cookie path rejected for this API.
- **Renovar uma vez e repetir, no *middleware*** — um `401` em qualquer pedido dispara `refreshAccess()` e o pedido clonado repete-se com o token novo; um segundo `401` (ou um `401` na renovação) termina em `logout()`. Nunca em *loop*. · Refresh once and retry; a second 401 ends the session.
- **`bootstrap()` antes de montar a app** — com `refresh` guardado, renova e carrega `/me/` antes do primeiro ecrã: o *guard* decide com informação certa e ninguém faz login a cada F5. · Bootstrap before mount so the guard knows.
- **O *guard* protege o ecrã; a API protege os dados** — `meta.requiresAuth` + `beforeEach` evitam ecrãs vazios com `401`; remover o *guard* nas DevTools não dá acesso a nada (Ficha 03). · The guard is UX; authorization lives in the API.
- **Encomenda em sequência: `POST /orders/` + um `POST /order-items/` por linha** — o backend não tem escrita aninhada (opcional da Ficha 02). Custo assumido: uma linha inválida deixa uma encomenda incompleta (a vista avisa). É exatamente o que o ponto 4 do M1 exige que o grupo resolva com uma transação e `items` no mesmo pedido. · Sequential creation accepted for the ficha; M1 fixes it with a nested, transactional write.
- **Erros do serializer ao lado do campo** — `problem.errors.quantity` ≈ `form.errors["quantity"]`: a validação é do servidor, o cliente só mostra, e mostra onde o utilizador olha. O total em `computed` é cosmético: o que conta é o `total` da API. · Field errors next to the field; the API's total is the real one.
- **`switch` exaustivo em `OrderStatusBadge`** (`satisfies never`) — um estado novo no `TextChoices` + schema faz o `vue-tsc` acusar onde falta tratar. · Exhaustive switch over the literal union.

