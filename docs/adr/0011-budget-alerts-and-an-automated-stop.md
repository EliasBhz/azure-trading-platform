# ADR-0011: Budget alerts, plus an automation that actually stops something

- Status: accepted
- Date: 2026-09-16

## Context

The subscription is Pay-As-You-Go with the spending limit off. Nothing caps what
it can charge, and the only cost control in the repository was a budget scoped
to the dev resource group.

Two problems surfaced while reading real cost data.

First, **a budget does not stop anything.** It sends a notification and billing
continues. There is no setting on a Pay-As-You-Go subscription that halts
charges at an amount; the spending limit that genuinely cut service exists only
on credit-based offers.

Second, **the resource group budget is blind to part of the environment.**
Container Apps creates its own managed environment resource group outside the
one this project declares, named `ME_<environment>_<group>_<region>`. Its cost
lands there, so a budget scoped to the project's group never sees it. The same
blindness applies to anything created outside Terraform.

## Decision

A separate `infra/governance` stack, outside the environment so that destroying
the environment does not remove what watches spending. It holds:

- a **subscription-scoped** budget, which sees every resource group;
- an Automation account with a system-assigned identity;
- a runbook that stops the project's PostgreSQL Flexible Servers;
- the action group and webhook connecting the budget to the runbook.

Only the 100 percent threshold on **actual** spend starts the automation. The
50 and 80 percent thresholds notify. The forecast threshold notifies.

The identity holds a **custom role with three actions**: read resource groups,
read PostgreSQL Flexible Servers, stop them.

## Alternatives considered

- **Alerts only.** Rejected as insufficient once it was clear that nothing else
  caps the subscription. It remains the fallback if the automation fails.
- **Deleting the resource group instead of stopping the server.** Rejected.
  Stopping is reversible and keeps the data, and a delete would desynchronise
  the Terraform state, turning a cost incident into an infrastructure incident.
- **Granting the automation `Contributor`.** Rejected, and this is the decision
  worth defending: it would mean a budget alert is able to delete the
  environment. A custom role is a few lines and changes the property from "the
  automation is trusted" to "the automation is incapable of anything worse".
- **An Azure Function or Logic App instead of Automation.** Rejected. A Function
  needs a storage account and a plan, a Logic App expresses ARM calls as JSON in
  a workflow. An Automation account with a PowerShell runbook is free at this
  volume and the logic stays readable in the repository as a normal script.
- **Az.PostgreSql cmdlets in the runbook.** Rejected in favour of
  `Invoke-AzRestMethod`. Az.Accounts ships with the Automation account;
  Az.PostgreSql would have to be imported from the PowerShell Gallery. An
  automation that only ever runs during an incident must not depend on a module
  import that could have failed quietly months earlier.
- **Restricting the Automation account to private networking.** Rejected. Jobs
  run in the Azure-managed sandbox, so private-only access requires a hybrid
  worker: a virtual machine paid for continuously so that a cost-control
  automation can run once a month.

## Consequences

- The ceiling is soft, and three gaps are accepted rather than hidden:
  - Azure rates consumption eight to twenty-four hours late, so the threshold
    fires after the money is spent. The overshoot is bounded by roughly one day.
  - Azure restarts a stopped Flexible Server by itself after seven days.
  - Container Apps, the registry and Log Analytics are not stopped. They are
    negligible next to the database and stopping them would need far broader
    permissions.
- Servers are matched by the `project` tag, never by name. A server created
  later is covered without editing the script, and a server belonging to
  something else is never touched. This makes the tagging convention a
  correctness requirement, not documentation.
- The webhook URI is a bearer credential and lives in the Terraform state. That
  is acceptable because the state account has shared keys disabled and is
  reachable only through Entra ID RBAC, and it is another reason that decision
  mattered.
- The resource group budget stays at its lower amount as an early signal. Two
  budgets at different scopes answer different questions: one asks whether this
  environment is behaving, the other asks whether the subscription is.
