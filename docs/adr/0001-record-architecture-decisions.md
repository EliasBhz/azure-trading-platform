# ADR-0001: Record architecture decisions

- Status: accepted
- Date: 2026-09-15

## Context

This repository is a portfolio artefact. Its value is not the running bot, it is
the visible reasoning behind each engineering choice. A reader who opens the repo
should be able to reconstruct why the stack looks the way it does without asking
the author.

## Decision

Every structural decision is recorded as a numbered, immutable Markdown file in
`docs/adr/`. Files are not edited after acceptance: a decision that changes is
superseded by a new ADR that links back to the old one.

"Structural" means anything that would be expensive to reverse, or anything a
reviewer would reasonably question.

## Alternatives considered

- **A single DESIGN.md.** Rejected: it drifts into a description of the current
  state and loses the rejected alternatives, which is the part that carries the
  reasoning.
- **Decisions explained in commit messages only.** Rejected: a commit explains a
  change, not a standing constraint, and it is not discoverable later.
- **A wiki or external documentation site.** Rejected: it desynchronises from the
  code and is not reviewable inside a pull request.

## Consequences

Each structural pull request carries an ADR, which adds friction. That friction
is the point: it forces the alternatives to be written down while they are still
fresh.
