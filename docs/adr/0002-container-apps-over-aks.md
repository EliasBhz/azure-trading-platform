# ADR-0002: Azure Container Apps rather than AKS

- Status: accepted
- Date: 2026-09-15

## Context

The workload is a single containerised Python process that runs a short trading
cycle on a schedule, plus a small read-only dashboard. Traffic is effectively
zero between cycles.

The Azure subscription is a 200 USD / 30 day free trial. Idle cost and
operational overhead are the binding constraints, not throughput or scale.

## Decision

Run on Azure Container Apps: the trading cycle as a scheduled Container Apps Job,
the dashboard as a Container App scaled to zero, both in a VNet-integrated
environment.

## Alternatives considered

- **AKS.** Rejected. A managed control plane plus a minimum node pool costs money
  continuously whether or not anything runs, and it brings a cluster to patch,
  upgrade and secure. The workload needs no custom scheduling, operators, service
  mesh or multi-tenancy. Choosing AKS here would be resume-driven architecture,
  and a reviewer would be right to challenge it.
- **Azure Functions.** Rejected. The timer trigger fits the cycle well, but the
  programming model leaks into the bot: the pipeline would be shaped by the host
  rather than by the domain. It also pushes the container image out of the
  centre, and with it the Trivy scan and the ACR-based supply chain that this
  project exists to demonstrate.
- **Azure Container Instances plus Logic Apps for scheduling.** Rejected.
  Scheduling becomes a second system to reason about, and ACI has no native
  scale-to-zero HTTP surface for the dashboard.
- **A VM running cron.** Rejected. Cheapest to reason about, hardest to defend:
  no immutable artefacts, manual patching, and nothing demonstrated about
  container supply chains.

## Consequences

- Cold starts on the dashboard are accepted, in exchange for near-zero idle cost.
- A Consumption-only Container Apps environment requires a dedicated subnet with
  enough address space, which the VNet design must reserve up front.
- If the workload ever grew into several cooperating services with complex
  networking, this decision would need revisiting. It does not today.
