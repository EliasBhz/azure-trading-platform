# CLAUDE.md

Operating rules for this repository. These are constraints, not suggestions.

## What this project is

`azure-trading-platform` is a portfolio project. It runs a **paper trading** bot on
Azure to demonstrate production engineering practices: infrastructure as code,
CI/CD, secret handling, observability and cost control.

**Bot profitability is explicitly a non-goal.** Never optimise strategy returns at
the cost of operational clarity.

## Non-negotiable invariants

### 1. Paper trading only

- The bot runs against exchange **testnets** or the built-in deterministic
  simulator. Nothing else.
- `Settings` validation fails and the process exits non-zero if sandbox mode is
  not active. This guard is covered by a unit test that must never be skipped or
  marked `xfail`.
- There is no code path to live trading. Do not add a `live` enum member, a
  `--force-live` flag, or an environment variable that bypasses the guard, even
  behind a feature toggle.

### 2. Credentials

- Exchange API keys are testnet keys with withdrawal permission disabled.
- Secrets live in Azure Key Vault and are read through a user-assigned managed
  identity. Never in the repository, never in GitHub Actions variables or
  secrets, never in logs.
- Log redaction is mandatory: any field whose name matches `key`, `secret`,
  `token`, `password` or `connection_string` is masked before emission.
- GitHub Actions authenticates to Azure via OIDC federated credentials. No client
  secret is ever stored.

### 3. Risk management

Enforced in code, checked every cycle, before any order is submitted:

- Maximum position size per symbol.
- Maximum daily loss, measured against the day's opening equity snapshot.
- Kill switch read from Key Vault or App Configuration. When set, the cycle
  records the decision and exits cleanly without placing orders.

### 4. Terraform

- **Never run `terraform apply` without showing the plan and waiting for explicit
  human approval.** This applies to local runs and to CI.
- Everything lives in a single resource group, with a consumption budget and the
  tags `project`, `env`, `owner`, `cost-center`.
- The stack must be destroyable and recreatable with one command. The Azure
  subscription is a 200 USD / 30 day free trial: assume credits will expire.

## Stack

| Layer | Choice |
|---|---|
| Bot | Python 3.12, ccxt in sandbox mode, Pydantic data contracts |
| Trading cycle | Azure Container Apps Job, cron scheduled |
| Dashboard | FastAPI + HTMX, Container App, scale-to-zero, Entra ID Easy Auth |
| Database | PostgreSQL Flexible Server B1ms, private access only, Alembic |
| Registry | ACR Basic, managed identity pull, admin user disabled |
| Secrets | Key Vault in RBAC mode, user-assigned managed identity |
| Network | Dedicated VNet, VNet-integrated Container Apps environment |
| Telemetry | Structured JSON logs, Log Analytics, Application Insights via OpenTelemetry |
| IaC | Terraform, azurerm provider, remote state on Storage Account |
| Region | West Europe |

## Architecture

The trading cycle is a linear pipeline. Each stage has a typed input and a typed
output, and no stage reaches backwards:

```
market data -> signal -> policy engine -> execution -> persistence
```

- `exchange/` owns all I/O with the exchange behind an `ExchangeGateway`
  protocol. Two implementations: `CcxtSandboxExchange` and `SimulatedExchange`.
- `strategy/` is pure: candles in, `Signal` out. No I/O, no clock reads.
- `policy/` is pure and deterministic: signal plus account state in, `OrderIntent`
  or a refusal with a reason out. All risk limits live here.
- `execution/` submits intents and records fills.
- Cross-stage data uses Pydantic models from `domain/`. Dicts do not cross
  module boundaries.

## Style

- Code, identifiers, commit messages and documentation in `/docs` are in English.
  The top-level README is in French with a short English section.
- Conventional Commits. The message body explains *why*, not *what*. One branch
  and one pull request per feature. Atomic commits.
- No comments that paraphrase the code. Comments explain non-obvious constraints
  or decisions.
- No emojis. No status badges for pipelines or coverage that do not exist yet.
- Never claim something works without having run it. If a command was not run,
  say so.
- Every structural decision gets an ADR in `docs/adr/`.

## Commands

    make install           # sync the virtualenv from pyproject
    make lint              # ruff check + ruff format --check
    make typecheck         # mypy
    make test              # pytest with coverage
    make check             # all of the above
    make test-integration  # start PostgreSQL, then run every test
    make cycle             # one cycle locally against PostgreSQL in Docker
    make up                # one cycle in the container, as the Job will run it
    make down              # stop everything and drop the volume

Local Python is managed by `uv` and pinned to 3.12 to match the container image.
Integration tests skip themselves unless `TEST_DATABASE_URL` is set, so `make
check` works without Docker.

The local PostgreSQL is published on host port 5433. 5432 and the 55392-55491
range are unavailable on the development machine.
