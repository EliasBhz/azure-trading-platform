# ADR-0003: A scheduled job rather than a long-running process

- Status: accepted
- Date: 2026-09-15

## Context

The trading cycle could be a daemon holding an event loop and sleeping between
iterations, or a process that runs once and exits.

## Decision

The cycle is a Container Apps Job triggered by cron. One invocation performs
exactly one cycle: fetch market data, compute a signal, apply the policy engine,
execute, persist, exit.

## Alternatives considered

- **A long-running container with an internal scheduler.** Rejected. It must be
  kept alive and therefore paid for continuously, it accumulates in-process state
  that hides bugs, and a crash between iterations is silent unless extra liveness
  machinery is added. Restart semantics become the application's problem.
- **A long-running process with an external heartbeat.** Rejected: same cost, and
  the heartbeat adds a second failure mode.

## Consequences

- Every cycle starts from a clean process. All state lives in PostgreSQL, which
  makes the system auditable and each cycle reproducible from persisted inputs.
- Failure detection is free: a non-zero exit is a failed job execution, directly
  alertable. "No execution in the last N minutes" becomes a meaningful alert.
- Startup cost is paid every invocation. At a 15 minute cadence this is
  negligible; at one second it would not be. The strategy cadence is therefore a
  deliberate constraint of this design, and is documented as such.
- Anything that must survive between cycles has to be written down. That is a
  feature, not a limitation.
