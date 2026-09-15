# ADR-0008: North Europe rather than West Europe

- Status: accepted
- Date: 2026-09-15

## Context

West Europe was the intended region: lowest prices in Europe, every service
available early, close to the operator.

The first `terraform apply` failed:

    403 RequestDisallowedByAzure: Resource 'sttfstatetradingladojwuh' was
    disallowed by Azure: The selected region is currently not accepting new
    customers.

West Europe is capacity constrained and refuses new customers on this
subscription. The restriction is not discoverable up front: the provider
metadata still advertises West Europe as an available location for
`Microsoft.Storage/storageAccounts`, so only an actual create reveals it.

## Decision

Every resource in this project is deployed to **North Europe**. The default
value of the `location` variable carries a comment naming the failure, so the
next reader does not "fix" it back to West Europe.

## Alternatives considered

- **France Central.** Known to work: the subscription already holds storage
  accounts there. It was the fallback if North Europe had failed too. Slightly
  more expensive than North Europe, and it would have spread this project across
  the same region as unrelated leftovers, making a cost breakdown by region
  harder to read.
- **Sweden Central.** Cheaper and with roomier quotas, but higher latency and no
  evidence of eligibility on this subscription.
- **Requesting a quota or region exception.** Rejected: it blocks the project on
  a support ticket for a region whose only advantage here is a few percent on
  the bill.

## Consequences

- Region is a variable, not a literal, so moving is a value change rather than a
  search and replace. Nothing in the code assumes a specific region.
- The two are not interchangeable in practice: a resource group cannot be moved
  between regions, so changing the value replaces the group and everything in
  it. That is acceptable because the stack is designed to be destroyed and
  recreated anyway.
- Anyone forking this repository onto a different subscription may hit the same
  restriction in a different region. The failure mode is documented here so the
  error message is searchable.
