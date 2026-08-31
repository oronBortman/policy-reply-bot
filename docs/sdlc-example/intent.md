# Intent: Stage 1 Policy Reply Bot

> Learning example — shows how our existing plan maps onto Anthropic's
> AI-Native SDLC playbook's `intent.md` → `spec.md` → `plan.md` split.
> This is illustrative, not a new source of truth; the actual build stays
> driven by `docs/superpowers/plans/2026-08-23-stage1-policy-reply-bot.md`.

## Problem

Customers ask an online shop simple questions (hours, refunds, products) and
expect an accurate answer grounded in the shop's real policies — never a
guess. There's no automated way to answer these yet, and the eventual system
should be able to grow into a fuller assistant without over-building before
that's proven necessary.

## Proposed Outcome

A working CLI that reads one customer question and returns a grounded
answer: correct facts for hours/refund/product questions, and a polite
decline for anything the knowledge base doesn't cover. This is Stage 1 of a
six-stage roadmap ([PLAN.md](../../PLAN.md)) — later stages (multi-topic
questions, tone routing, double-checking, self-review, live lookups) are
deliberately not started until Stage 1's limits are shown failing for real.

## Affected Users and Systems

- **Customers** — the people asking questions; they see only the final
  reply.
- **The knowledge base** (`data/kb/*.md`) — read-only input; hours,
  refunds, products.
- **The Anthropic API** — the one external system this stage depends on.

## Constraints

- Single LLM call only (rung 0 on the ladder in
  [plan/anthropic-llm-plan.md](../../plan/anthropic-llm-plan.md)) — no
  chaining, routing, or agent loops yet.
- Python + Anthropic SDK + CLI only — no LangChain, no database, no UI.
- Must fail closed: an ungrounded or invented fact must never reach the
  customer.

## Open Questions

- How will the eventual live-order-lookup stage (Stage 6) authenticate
  against a real order system? Not yet relevant to Stage 1.
- Should the knowledge base ever grow large enough to need retrieval
  instead of "stuff everything into the prompt"? Not yet — KB is 3 short
  files.
