# Plan: Stage 1 Policy Reply Bot

> Learning example — the technical/operational layer: files that change,
> order of work, risks, proof. Written after `spec.md` is approved, before
> any code exists. The actual, fully-detailed version of this is
> `docs/superpowers/plans/2026-08-23-stage1-policy-reply-bot.md`; this is a
> condensed illustration of the same artifact type.

## Architecture

A CLI loads the 3 KB files into a system prompt, makes one Anthropic API
call instructing structured JSON output (intent/reply/citations), then
validates the response before printing it. `temperature=0`, `max_tokens`
capped, assistant-turn prefilled with `{` to bias toward pure JSON.

## Files that Change

- `src/policy_bot/kb.py` — new. KB loader.
- `src/policy_bot/client.py` — new. Prompt builder, API call, response
  validation.
- `src/policy_bot/cli.py` — new. Wiring + exit codes.
- `tests/` — new, three levels: unit (mocked), integration (only the SDK
  call mocked), e2e (real API, opt-in marker).
- `pytest.ini`, `requirements.txt` — new, config/pins.

## Order of Work

1. KB loader (Task 1) — no dependencies.
2. Response parsing/validation (Task 2) — pure logic, testable without a
   network call.
3. Prompt builder + live API call (Task 3) — extends Task 2's file.
4. CLI entry point (Task 4) — wires Tasks 1 and 3 together.
5. Integration test (Task 5) — proves the real wiring, only the SDK mocked.
6. E2E test (Task 6) — real API, golden questions, opt-in.

## Risks

- A single-intent question needing two KB files (accepted spec limitation,
  not solved here).
- Grounding validation can't catch a wrong *fact* cited from a real file
  (accepted spec limitation — Stage 4's problem).
- Sandbox/local SDK version drift on parameters like `temperature` — mitigate
  by using the SDK's `extra_body` escape hatch rather than a typed kwarg,
  so the code stays correct against the real published SDK either way.

## Proof (Definition of Done)

- Every task's tests pass, TDD RED shown before GREEN.
- `pytest` (no `-m e2e`) is green with zero network calls.
- `pytest -m e2e` matches all 4 golden questions on `intent`/`citations`;
  reply wording checked by hand.
- Off-topic sample question declines rather than guesses.
