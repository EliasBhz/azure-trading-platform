# ADR-0013: A server-rendered dashboard, sharing the bot's image

- Status: accepted
- Date: 2026-09-18

## Context

The equity curve, the open positions, the recent orders and the reason behind
each decision have to be visible to a person without opening a database client
or writing KQL.

The obvious shape is a single-page application calling a JSON API. The obvious
second image is a separate one for the dashboard.

## Decision

FastAPI rendering Jinja templates, HTMX swapping a fragment on a timer, and the
equity curve drawn as an SVG polyline computed on the server. No build step, no
JavaScript framework, no chart library.

It ships in **the same image as the bot**, with a different command. It runs as
a Container App scaled to zero, behind Entra ID authentication.

## Alternatives considered

- **A single-page application over a JSON API.** Rejected. The same table would
  then exist twice, once in a template and once in JavaScript, and the two
  drift. It also adds a build step, a dependency tree and a second thing for
  Trivy to scan, for a page that shows six tables.
- **Streamlit.** Rejected earlier and worth restating: it relies on websockets
  and sticky sessions, which fit badly with scale-to-zero. A cold start of ten
  to twenty seconds on a websocket connection is a blank page rather than a slow
  one.
- **A separate image for the dashboard.** Rejected. One image means one build,
  one scan, one tag, and a deployed revision that names exactly one commit for
  both the bot and the page. Two images means two supply chains to keep current,
  and the interesting risk is the one nobody remembers to rebuild.
- **A chart library.** Rejected. The curve is a polyline through a few dozen
  points. Computing it on the server keeps the page free of external scripts,
  which keeps it inside a strict content security policy and means it renders
  with JavaScript disabled.
- **Loading HTMX from a CDN.** Rejected. An external script in the request path
  of an authenticated page is a third-party dependency that can change, vanish,
  or observe who is reading. It is vendored into the image.

## Consequences

- **The dashboard reads and never writes.** Every query is a select. There is no
  endpoint that can place an order, change a limit or set the kill switch, so
  the page cannot become a second way to trade. Tripping the kill switch stays a
  deliberate Key Vault operation, recorded in the runbook.
- **Liveness does not touch the database, readiness does.** A liveness probe
  that fails during a database outage makes the platform restart replicas it
  cannot fix, turning an outage into a restart loop.
- **Scale to zero costs a cold start.** The right trade for a page a person
  opens a few times a day, and the wrong one for the trading job, which is why
  the job is a job.
- **Polling, not a websocket.** The bot writes once every fifteen minutes, so a
  socket held open buys nothing and prevents scaling to zero.
- The fragment carries its own `hx-` attributes because it replaces itself.
  Without them the page would update exactly once and then stop, which looks
  like a stale dashboard rather than a bug.
- The page shows **refusals beside orders**. A dashboard listing only trades
  cannot answer why the bot did nothing at 14:00, which is the question this
  project exists to be able to answer.
- The staleness banner uses the same forty-five minute threshold as the no-cycle
  alert. A page that looks healthy while an alert is firing is worse than no
  page.
