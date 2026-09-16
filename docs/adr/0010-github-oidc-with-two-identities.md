# ADR-0010: GitHub Actions authenticates through OIDC, with two separate identities

- Status: accepted
- Date: 2026-09-16

## Context

CI has to read Azure to produce a `terraform plan` on a pull request, and CD has
to create, change and delete resources on `main`. The repository is public, and
a pull request can run workflows.

The usual approach is a service principal client secret stored as a GitHub
secret. It is a long-lived credential that nothing forces anyone to rotate, it
is copied into at least two places, and its blast radius is whatever the
principal can do.

## Decision

No secret exists. GitHub Actions obtains a short-lived token from Entra ID
through OIDC federated credentials, and the repository stores only client ids,
tenant id and subscription id, as **variables rather than secrets** because none
of them is confidential: a client id is useless without a token whose subject
matches a federated credential.

Two identities, not one:

| | `plan` | `deploy` |
|---|---|---|
| Federated subject | `repo:OWNER/REPO:pull_request` | `repo:OWNER/REPO:environment:dev` |
| Subscription role | Reader | Contributor plus Role Based Access Control Administrator |
| State storage role | Storage Blob Data Reader | Storage Blob Data Contributor |
| Reachable from | any pull request | only an approved deployment |

## Alternatives considered

- **A client secret in GitHub Secrets.** Rejected. Long lived, copied, and
  nothing detects its use from somewhere else.
- **One identity with Contributor, used by both workflows.** Rejected, and this
  is the important one: any pull request could then obtain a credential able to
  destroy the environment. The protection would be "we review pull requests
  carefully", which is not a control.
- **Federating on `ref:refs/heads/main` for deployment.** Rejected. A push to
  `main` would be enough to obtain the deploy credential, with no human in the
  loop. Federating on the environment instead means GitHub does not mint a token
  with that subject until a reviewer approves, so the approval gate becomes a
  precondition for authentication rather than a step someone can skip.
- **Scoping the deploy role assignments to the resource group.** Rejected
  because the resource group does not exist before the first apply, and the
  stack is designed to be destroyed and recreated. The cost is a
  subscription-scoped Contributor, which is stated below rather than glossed
  over.

## Consequences

- There is no credential to rotate, and none to leak.
- **The deploy identity holds Role Based Access Control Administrator on the
  subscription**, because the dev stack creates role assignments of its own and
  Contributor cannot. That is the right to grant roles, therefore the right to
  self-escalate. It is the most privileged thing in this repository and a
  reviewer should challenge it. The mitigation is that the credential is
  unreachable without an approved deployment to a protected environment.
- A pull request plan runs with `-lock=false`. Acquiring a blob lease on the
  state is a write, and the plan identity cannot write. This is not a workaround
  for a permission mistake: an identity that cannot write to the state is an
  identity that cannot corrupt it, and giving up locking on a read-only
  operation is the correct side of that trade.
- A pull request **from a fork** gets no OIDC token at all. The plan step is
  skipped rather than failed, so an outside contributor does not see a red check
  for a permission GitHub deliberately withholds. The reviewer does not get an
  automatic plan for fork contributions and has to run one.
- `main` must stay a protected branch. The `dev` environment only accepts
  deployments from protected branches, so removing the protection silently
  disables deployment.
- Actions are pinned to major version tags rather than commit SHAs. SHA pinning
  is stronger and Dependabot supports both; tags were chosen for readability,
  with Dependabot keeping them current. On a repository handling real secrets
  the trade would go the other way.
