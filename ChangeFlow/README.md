# ChangeFlow

ChangeFlow is a backend HTTP API for creating and reviewing change requests. It uses
Python 3.12, FastAPI, SQLAlchemy 2, SQLite, JWT bearer authentication, and
server-side current-role authorization.

## Features

- Requester ownership and Draft create/edit/submit behavior.
- Reviewer approval and request-changes decisions.
- Self-approval and blank-feedback rejection.
- Mandatory content change before resubmitting a reviewed request.
- Immutable approved requests and transition history.
- ETag/If-Match optimistic concurrency with no silent lost updates.
- Request/history visibility inherited from current server-side roles.
- No request-deletion operation; DELETE returns `405 DELETION_NOT_SUPPORTED`.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
```

Configure a JWT issuer, audience, and JWKS endpoint:

```powershell
$env:CHANGEFLOW_JWT_ISSUER = "https://identity.example/"
$env:CHANGEFLOW_JWT_AUDIENCE = "changeflow-api"
$env:CHANGEFLOW_JWT_JWKS_URL = "https://identity.example/.well-known/jwks.json"
$env:CHANGEFLOW_DATABASE_URL = "sqlite:///changeflow.dev.db"
```

Provision a user that corresponds to the token `sub` claim:

```powershell
.\.venv\Scripts\python.exe -m changeflow.cli.provision_user `
  --user-id "user-123" --roles Requester,Reviewer
```

Apply migrations and start the API:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn changeflow.api.main:app --port 5001
```

Interactive API documentation is available at `http://localhost:5001/docs`.

## Validation

```powershell
.\.venv\Scripts\ruff.exe check src tests
.\.venv\Scripts\mypy.exe src
.\.venv\Scripts\python.exe -m pytest
```

Detailed acceptance scenarios and expected outcomes are documented in
`specs/001-change-request-workflow/quickstart.md`.

## Architecture

- `domain/`: framework-independent state, content, and transition rules.
- `application/`: use cases, authorization orchestration, and ports.
- `infrastructure/`: SQLAlchemy, JWT, settings, migrations, and provisioning.
- `api/`: FastAPI routes, schemas, dependencies, and Problem Details mapping.

Approved requests and accepted transition history are never edited by normal API
operations. Role checks use current server-side assignments rather than roles copied
from JWT claims.
