# ADR-0006: One bar, one cycle identifier

- Status: accepted
- Date: 2026-09-15

## Context

Container Apps Jobs retry a failed execution. A cron schedule can also fire twice
for the same period, and an operator can trigger a job by hand. Any of these can
run the pipeline twice over the same market data.

Without a defence, the second run computes the same signal, the policy engine
approves the same order, and the position doubles.

## Decision

A cycle is identified by the bar it acted on, not by the wall clock:
`{SYMBOL}-{timeframe}-{bar_open_epoch}`. The client order id is derived from it.

Two defences follow, in order:

1. The venue rejects a repeated client order id. This is the guarantee.
2. Before submitting, the cycle looks for an order with that id in the database
   and stops if it finds one. This is a local fast path.

## Alternatives considered

- **A random or timestamp-based cycle id.** Rejected: it makes every run look
  new, which is precisely the property we do not want.
- **A distributed lock or a leader election.** Rejected: it adds a component
  whose failure modes are worse than the problem, for a job that runs every
  fifteen minutes.
- **Relying on the database check alone.** Rejected, and this is the subtle
  part: if the process dies between submitting the order and committing the
  transaction, the row is rolled back and the check finds nothing on retry. Only
  the venue-side rejection covers that window.

## Consequences

- The cadence is bounded by the timeframe: two cycles within one bar are, by
  construction, one cycle. That is the intended behaviour, not a limitation to
  work around.
- `SimulatedExchange` does not reject duplicate client order ids, so the
  simulated backend relies on the database check alone. The integration test
  covers the committed case; the crash window is only protected on a real venue.
  This asymmetry is documented rather than hidden.
