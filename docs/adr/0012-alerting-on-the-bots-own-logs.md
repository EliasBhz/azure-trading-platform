# ADR-0012: Alert on the bot's own logs, not on the platform's

- Status: accepted
- Date: 2026-09-16

## Context

Three things have to be noticed without anyone watching: a cycle that failed, a
bot that has silently stopped trading, and a drawdown past the point where the
policy engine refuses to trade.

Azure offers each of these from the platform side. A Container Apps Job
execution has a status, the container runtime emits metrics, and Azure Monitor
can alert on both without the application knowing anything about it.

## Decision

Every alert queries the bot's own structured logs in Log Analytics, matching on
the event names the bot emits: `cycle.completed`, `cycle.failed`,
`cycle.crashed`, and the `drawdown_ratio` field on the completed event.

The bot also exports custom metrics through OpenTelemetry to Application
Insights: equity, drawdown, decision counts, order latency, cycle duration and
errors. Those exist for the workbook and for asking questions after the fact.
**The alerts do not depend on them.**

## Alternatives considered

- **Alert on the Container Apps Job execution status.** Rejected as the primary
  signal. It answers "did the process exit non-zero", which is necessary but not
  sufficient: a cycle that runs, decides nothing and exits zero for a bad reason
  is invisible to it. It is also a platform schema Azure can change underneath
  the alert.
- **Alert on the custom metrics instead of the logs.** Rejected. A metric
  reaches Application Insights only if the exporter is configured, the
  connection string is valid, and the process flushes before exiting. Every one
  of those can fail silently, and the failure mode is an alert that stops
  firing rather than an alert that fires. Logs are written by the process
  itself, synchronously, with no exporter in the path.
- **Alert on a drawdown metric rather than the logged field.** Same reason, and
  the logged value is the one a human reads during an incident, so alerting on
  a different number would mean the alert and the investigation disagree.

## Consequences

- The alert contract is the bot's event names. Renaming `cycle.completed`
  silently breaks three alerts and the workbook. That is a real coupling, and
  the alternative was coupling to a schema owned by Azure instead of by this
  repository.
- **The absence alert needs a query that returns a row when nothing matches.**
  `summarize count()` with no `by` clause always returns exactly one row,
  including zero. With a `by` clause it returns no rows at all, and an alert on
  an empty result set never fires, which is precisely the case being watched
  for. This was verified against the live workspace rather than assumed:

      summarize count()            -> 0        the alert can fire
      summarize count() by X       -> no rows  the alert is blind

- The absence alert waits three missed cycles, not one. One missed cycle is a
  transient, and an alert that fires on transients trains its reader to ignore
  it.
- Telemetry must never be able to stop the bot. An unusable connection string
  produces a no-op exporter and a warning, because a trading cycle that fails
  because a monitoring dependency is down turns an observability problem into an
  outage.
- Metrics from a short-lived job need an explicit flush. The SDK exports on a
  timer measured in tens of seconds and a cycle lasts about two, so without
  `flush()` before the process exits every metric is lost with no error
  anywhere.
