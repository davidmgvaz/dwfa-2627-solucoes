# Ficha 01 — decisões e reflexão · decisions and reflection

## 1. Que código deve `/api/health/` devolver quando a base de dados está em baixo? · Which status code when the DB is down?

**PT** — `503 Service Unavailable`, com corpo JSON (`{"status": "degraded", "db": "unavailable"}`). Não é um erro do cliente (4xx) nem um *bug* da aplicação (500): é uma dependência indisponível, e 503 é o código que um *load balancer* ou o Kubernetes interpretam como "tira esta instância de rotação por agora". Com `DEBUG=True` o Django devolvia uma página de *traceback* com 500 — a vista tem de apanhar `OperationalError` e decidir o código ela própria.

**EN** — `503 Service Unavailable` with a JSON body. It is neither a client error (4xx) nor an application bug (500): a dependency is unavailable, and 503 is what a load balancer or Kubernetes reads as "take this instance out of rotation for now". With `DEBUG=True` Django would return a 500 traceback page — the view must catch `OperationalError` and choose the status code itself.

## 2. Porquê PostgreSQL em Docker em vez de instalado na máquina? · Why PostgreSQL in Docker rather than installed locally?

**PT** — A mesma versão (16) para toda a turma e para a produção; arranca e apaga-se com um comando (`docker compose up -d db` / `down -v`); não deixa serviços a correr no portátil; e é o primeiro passo para o `compose.yaml` que no M2 vai ter também a aplicação, o Redis e o Nginx. O custo é o Docker Desktop/WSL2 e a porta 5432 partilhada com um PostgreSQL local, se existir.

**EN** — Same version (16) for the whole class and for production; starts and disappears with one command; leaves no services running on the laptop; and it is the first step towards the `compose.yaml` that in M2 will also hold the app, Redis and Nginx. The cost is Docker Desktop/WSL2 and sharing port 5432 with a local PostgreSQL, if there is one.

## 3. Onde vive a lógica? · Where does the logic live?

**PT** — A vista de *health* fala diretamente com a ligação à base de dados. Para um *health check* é aceitável (é infraestrutura, não domínio). A partir da Ficha 02 a regra muda: as vistas chamam o ORM/serviços, nunca SQL à mão.
**EN** — The health view talks to the DB connection directly. For a health check that is fine (infrastructure, not domain). From Ficha 02 on the rule changes: views call the ORM/services, never hand-written SQL.
