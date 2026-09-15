# ADR-0004: Exchange access behind a gateway, with a deterministic simulator

- Status: accepted
- Date: 2026-09-15

## Context

The default venue is Binance Spot Testnet through ccxt in sandbox mode. That
testnet is operationally fragile for a demonstration project: credentials are
issued through a third-party login flow, and accounts are reset periodically.

Separately, CI must be able to run the full pipeline with no network access and
no credentials, and tests must be reproducible.

## Decision

All exchange I/O goes through a single `ExchangeGateway` protocol in
`exchange/`. Two implementations satisfy it:

- `SimulatedExchange`: deterministic and in-process. It replays recorded or
  generated candles and fills orders against them. Default locally and in CI.
- `CcxtSandboxExchange`: ccxt with `set_sandbox_mode(True)`, used against the
  exchange testnet.

The backend is selected by `BOT_EXCHANGE_BACKEND`, whose enum has no live member.

## Alternatives considered

- **Call ccxt directly from the pipeline.** Rejected. It couples strategy and
  policy code to a third-party client, forces tests to reach the network, and
  removes the single choke point where the sandbox invariant is enforced.
- **Mock ccxt in tests instead of writing a simulator.** Rejected. Mocks encode
  our assumptions about the exchange rather than its behaviour, and they cannot
  be run as an end-to-end pipeline to populate the dashboard.
- **Support several live-capable exchanges behind the same interface.** Rejected:
  that is precisely the generalisation that would make a live code path cheap to
  add.

## Consequences

- The paper-trading invariant has one place to be enforced and one place to be
  audited.
- The demonstration never depends on testnet availability.
- The simulator is code that must itself be maintained and kept honest about
  fees, slippage and partial fills. It is explicitly a simplification, and the
  README says so.
