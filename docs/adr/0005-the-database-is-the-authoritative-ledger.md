# ADR-0005: The database is the authoritative ledger, not the venue

- Status: accepted
- Date: 2026-09-15

## Context

Every cycle needs to know how much cash and inventory the bot holds, because the
policy engine sizes orders against those numbers and enforces the position and
daily-loss limits with them.

That state could be read from the venue on each cycle, or kept in our own
database and derived from the fills we recorded.

## Decision

The PostgreSQL database is authoritative. `ExchangeGateway` returns market data
and order executions; it does not report balances. Cash and position are derived
from the fills the bot recorded, and cash is carried forward by the most recent
`equity_snapshots` row.

## Alternatives considered

- **Read balances from the venue each cycle.** Rejected for three reasons. A
  venue outage or a rate limit would make the risk calculation unavailable
  exactly when the bot is deciding whether to trade. The testnet resets accounts
  periodically, so the balance can change for reasons unrelated to our trading.
  And the simulator has no balance endpoint to be faithful to, so the two
  backends would diverge in behaviour.
- **A dedicated balances table alongside the snapshots.** Rejected: two records
  of the same number drift, and the equity snapshot already exists as the audit
  record of what the bot believed at a point in time.

## Consequences

- The bot's view can diverge from the venue's. That is a real risk and it is
  accepted here because the venue is a testnet and the money is not real. A
  system trading real money would need a reconciliation job comparing the two
  and alerting on the difference; this project does not have one, and the
  runbook says so rather than implying otherwise.
- Every number the dashboard displays comes from one place.
- The daily-loss limit is measured against the first equity snapshot of the UTC
  day, which makes the boundary explicit and identical in every environment.
