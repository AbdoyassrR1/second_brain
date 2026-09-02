# Second Brain — Personal Productivity REST API

A **security-first, production-oriented Flask backend** for managing tasks, projects, labels, reminders, and time tracking. Built as a feature-based **modular monolith** with a strict layered architecture, full observability, and a 423-test suite at **91% line coverage**.

Not a demo scaffold — this is a working API with JWT authentication (dual token revocation), email-based 2FA, Redis-backed rate limiting and caching, Celery background jobs, structured audit logging, and Prometheus metrics.

## Highlights

- **8 self-contained feature modules** (`auth`, `tasks`, `projects`, `labels`, `reminders`, `time_tracking`, `health`, `mail`) each following `routes → service → repository → model` layering.
- **60+ REST endpoints** under `/api/v1` with paginated list responses, bulk operations, and cross-feature guards.
- **Authentication & security**: bcrypt hashing, JWT with **dual revocation** (jti blocklist + token-version bump), email-OTP 2FA with constant-time comparison, account lockout, log redaction, ownership guards on every resource.
- **Async processing**: Celery over Redis — reminder dispatch, daily summaries, cleanup, and an auto-stop sweep for running timers.
- **Observability**: structured JSON logs with W3C Trace Context correlation, Prometheus `RED` metrics, health/liveness/readiness probes, and 40+ audit events.
- **Time tracking** with a concurrency-safe "one running timer per user" invariant and even-split allocation where `Σ allocated == wall-clock` exactly.
- **423 tests** (unit + integration) on in-memory SQLite with Celery eager mode — no external services needed to run the suite.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12 |
| Web Framework | Flask 3.1 (Gunicorn via `wsgi.py`) |
| Database | MySQL (dev/prod), SQLite in-memory (tests) |
| ORM / Migrations | SQLAlchemy 2.0, Flask-SQLAlchemy, Alembic + Flask-Migrate |
| Auth | Flask-JWT-Extended, Flask-Bcrypt |
| Validation | Marshmallow + flask-marshmallow |
| Rate Limiting | Flask-Limiter (Redis-backed, falls back to memory) |
| Caching | Redis + custom `RedisCache` utility |
| Background Jobs | Celery with Redis broker/backend + Celery Beat |
| Email | Flask-Mail |
| CORS | Flask-CORS (deny-by-default in production) |
| Metrics | prometheus_client |
| Logging | python-json-logger (structured JSON) |
| Testing | pytest + pytest-cov |

## Features

| Module | Capabilities |
|--------|--------------|
| **Auth** | Register/verify email, login, JWT refresh, logout (single/all), 2FA via email OTP, password change/reset, email change, account lockout, device tracking, role claim `role_required` |
| **Tasks** | CRUD, status transitions, priorities, due dates, soft-delete/restore, archive, subtasks, advanced filtering + search, pagination, bulk ops, statistics |
| **Projects** | CRUD, task grouping, hex colors, task counts |
| **Labels** | CRUD, hex colors, many-to-many task assignment |
| **Reminders** | CRUD with status workflow (`pending` → `sent`/`failed`), async dispatch via Celery |
| **Time Tracking** | Multi-task start/stop timer (one per user), manual entries, even-split allocation, per-day/week/task/project reports |
| **Health** | liveness, health, and readiness probes under `/api/v1/monitor` |
| **Mail** | welcome, verification, password reset/change, OTP, alerts |

## Architecture

Feature-based **modular monolith** with one-way dependency flow — routes depend on services and schemas, services on repositories, repositories on models. Cross-feature calls go through services, never repositories.

```
HTTP Request
    ↓
CORS → Rate Limiter (Redis)
    ↓
Middleware: request_id / trace_id / span_id, redacted request logging
    ↓
Routes (Flask Blueprints) — Marshmallow validation, serialization
    ↓
Service layer — business logic, audit logging, Prometheus metrics, ownership guards
    ↓
Repository layer — SQLAlchemy queries, filtering, pagination
    ↓
Models (ORM) → Database (MySQL / SQLite)
```

Every write flows through a single `Database` transaction proxy that **rolls back and re-raises on commit failure** — eliminating the "zombie session" problem — and SQLAlchemy cursor events emit query-duration histograms with slow-query warnings (>0.5s).

### Request Lifecycle

1. CORS processed, rate limit checked (Redis-backed for multi-instance).
2. `before_request` middleware generates/extracts correlation + W3C trace IDs and logs the incoming request **with sensitive fields redacted**.
3. Route validates the payload/query with Marshmallow schemas and delegates to the service.
4. Service applies business logic, guards ownership, records audit events + metrics.
5. Repository executes queries; response serialized back through schemas.
6. `after_request` middleware records duration/error metrics and echoes `X-Request-ID`, `X-Trace-ID`, `X-Span-ID`.

### Project Layout

```
app/
├── __init__.py          # create_app() factory: extensions, blueprints, middleware
├── config.py            # development / testing / production configs (fail-fast on weak secrets)
├── extensions.py        # Flask extension singletons
├── features/            # auth, tasks, projects, labels, reminders, time_tracking, health, mail
├── jobs/                # Celery: FlaskContextTask, beat schedule, task definitions
├── shared/
│   ├── cache.py         # RedisCache utility (graceful degradation)
│   ├── database/        # centralized write proxy + query instrumentation
│   ├── decorators.py    # auth_required, role_required, require_json_body
│   ├── exceptions.py    # AppError hierarchy (400/401/403/404/409)
│   ├── logging/         # structured JSON logging + audit log
│   ├── middleware/      # correlation IDs, redaction
│   └── models/          # BaseModel (UUID PK, timestamps)
└── errors/              # centralized error handlers (HTTP, DB, JWT)
tests/                   # unit/ + integration/ (self-contained, SQLite in-memory)
```

## Security

The API is bearer-JWT and default-deny by ownership:

| Attack surface | Defense |
|----------------|---------|
| Token theft / replay | Short-lived access tokens (30 min) + refresh rotation + **dual revocation**: per-token `jti` blocklist for logout, `token_version` bump to invalidate all sessions (logout-all, password change, 2FA toggle, account delete) |
| Credential compromise | bcrypt hashing, password strength policy, reset/change flows that revoke sessions |
| Brute force | Per-account lockout (default 5 attempts / 15 min) + per-feature rate limits over Redis |
| Account enumeration | Generic login errors, silent ignores on unknown emails for reset/verification flows |
| Log leakage | Recursive redaction of `authorization`, cookies, passwords, tokens, keys before logging |
| IDOR / cross-user access | Ownership guards (`_guard_ownership`) on every service mutation; soft-deleted users treated as nonexistent |
| 2FA bypass | Email OTP, single-use, 5-min expiry, verified with `secrets.compare_digest` |

`ProductionConfig` **fails fast at startup** if `SECRET_KEY`/`JWT_SECRET_KEY` are unset or default values, and defaults CORS to deny-by-default (env-driven allowlist). Metrics exposure is optionally protected via `METRICS_PROTECT`, `METRICS_AUTH_TOKEN`, or IP whitelist.

> **Honest scope**: 2FA is email OTP (weaker than TOTP/WebAuthn), `role_required` checks the JWT role claim (not re-queried per request), rate limits are keyed per-IP, and auth emails (welcome/OTP/reset) are sent synchronously. The `/metrics` endpoint is unauthenticated unless `METRICS_PROTECT` is enabled.

## Async System (Celery + Redis)

```
Flask route → task.delay() → Redis broker → Celery worker → FlaskContextTask
                                                        ↓
                              (auto app context) → task body (email, cleanup, sweep)
```

- `FlaskContextTask` wraps every task in a Flask app context so SQLAlchemy/Flask-Mail work transparently; workers bootstrap the app lazily.
- `task_always_eager=True` in tests runs tasks synchronously — no broker needed.
- **Beat schedule**: reminder dispatch (30s), daily task summary (08:00), reminder cleanup (midnight), long-running-timer auto-stop (hourly).

## Testing

```bash
pytest                 # full suite
pytest tests/unit/     # services + repositories in isolation
pytest tests/integration/   # end-to-end API tests
pytest --cov=app --cov-report=html   # coverage report (91%)
```

**423 tests** across **23 files** (14 unit + 9 integration) covering authentication (lockout, revocation, 2FA), ownership guards, soft-delete, the time-tracking split invariant, Redis-independent fallbacks, and a regression test for the transaction-proxy rollback behavior. Integration tests run on in-memory SQLite with Celery in eager mode — the suite is fully self-contained.

## Getting Started

```bash
# 1. Environment
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Configuration — copy your local .env (DB creds, secrets, SMTP, Redis)
#    Development falls back to DATABASE_URL; Production REQUIRES DB_* vars + strong secrets.

# 3. Migrations
flask db upgrade          # Alembic-managed schema

# 4. Run
flask run                 # dev, http://localhost:5000
gunicorn -w 4 -b 0.0.0.0:8000 wsgi:app   # production

# 5. Workers (for background jobs)
celery -A app.jobs.celery_app:celery_app worker --beat --loglevel=info
```

Docker deployment files (`Dockerfile`, `docker-compose.yml`) and `scripts/` are included in the repo.

## Design Decisions

Architectural choices are documented as ADRs in [`.ai/decisions.md`](.ai/decisions.md) — the notable ones:

- **ADR-004**: JWT dual revocation (blocklist + token version) — fine-grained vs bulk revocation in one scheme.
- **ADR-017**: Redis for caching + rate-limit storage, with graceful degradation when Redis is down.
- **ADR-018/019**: Time-tracking even-split allocation (sum == wall-clock) and the service-level one-timer invariant with documented DB-hardening path.
- **ADR-005**: Soft-delete tombstones for referential integrity and audit trails.
- **ADR-016**: Explicit, testable API error codes.

## Roadmap

- **Done**: Phase 1 (core system), Phase 2 (security + observability), Phase 3 (pagination, Redis, Celery, Beat, time tracking).
- **Next**: async auth emails, OpenAPI/Swagger docs, type hints, search beyond tasks, CI/CD pipeline with coverage gate.

See [`.ai/progress.md`](.ai/progress.md) and [`.ai/roadmap.md`](.ai/roadmap.md) for the full status.

## Known Limitations

- Auth/sync emails are sent in the request path (only reminders are async).
- No CI/CD yet — the 423-test suite runs locally, not in a pipeline.
- No OpenAPI/Swagger documentation; no type hints (Python 3.12 project).
- `migrations/` is currently gitignored — database migrations are not version-controlled.
- MySQL-specific behavior (e.g., `FOR UPDATE`, datetimes) is verified in dev; tests run on SQLite.

## Docs

- `OBSERVABILITY.md`, `OBSERVABILITY_QUICK_REF.md` — metrics, logging, and tracing
- `.ai/` — project memory: architecture, conventions, decisions (ADRs), feature docs, progress, roadmap

## License

MIT