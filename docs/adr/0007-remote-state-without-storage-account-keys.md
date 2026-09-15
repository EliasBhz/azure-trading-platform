# ADR-0007: Remote state on Azure Storage, with no account key anywhere

- Status: accepted
- Date: 2026-09-15

## Context

Terraform state describes the entire infrastructure and is written by both a
developer machine and, from phase 4, GitHub Actions. It has to live somewhere
both can reach, with locking and with a way back from a bad write.

The default way to use the `azurerm` backend is a storage account key or a SAS
token. Either is a long-lived credential that ends up in a shell profile, a CI
secret and, sooner or later, a support ticket.

## Decision

State lives in a blob container on a dedicated storage account with
`shared_access_key_enabled = false` and `storage_use_azuread = true`. The data
plane is reached with the caller's Entra ID identity: a user locally, a
federated workload identity in CI.

The bootstrap stack creates that account and assigns **Storage Blob Data Owner**
on it to whoever runs the bootstrap.

## Alternatives considered

- **Storage account key in an environment variable.** Rejected. It is a
  permanent credential granting full data-plane access to the state of the whole
  platform, and it cannot be scoped, audited per identity, or revoked without
  breaking everyone.
- **SAS token.** Rejected: same weakness with an expiry date attached, which
  trades a permanent leak for a rotation chore.
- **Terraform Cloud / HCP Terraform.** Rejected. It solves the problem well, but
  the project exists to demonstrate running this on Azure; outsourcing the state
  removes the part a reviewer would want to see.
- **State committed to the repository.** Not seriously considered; the
  repository is public.

## Consequences

- No storage key exists, so none can leak.
- Being subscription Owner is not sufficient to read or write state. Owner
  grants control-plane rights, not `dataActions`. This surprises people, and it
  is the reason the bootstrap assigns a data role explicitly.
- Entra ID role assignments are eventually consistent. Creating the container
  immediately after the assignment fails often enough that the stack waits sixty
  seconds, rather than leaving an operator to re-run apply and wonder why it
  worked the second time.
- The bootstrap stack keeps its own state locally, because a remote backend
  cannot store the state of the stack that creates it. That state file contains
  no secret, and the bootstrap README gives the two `terraform import` commands
  to recover from losing it.
- The storage account is geo-redundant. Losing this state blocks every future
  apply and destroy, and the state is a few kilobytes, so the premium over
  locally redundant storage is not measurable.
