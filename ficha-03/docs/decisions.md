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
