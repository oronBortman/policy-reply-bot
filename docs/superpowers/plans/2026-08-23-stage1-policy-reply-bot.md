# Stage 1 Policy Reply Bot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development for every task below — RED (failing test) before GREEN (minimal code), no exceptions.

**Goal:** Build Stage 1 of the shop support chatbot — a single Anthropic API call that answers hours/refund/product questions grounded only in the local knowledge base, and declines off-topic questions.

**Spec:** [PLAN.md](../../../PLAN.md) (Stage 1 section) and [plan/anthropic-llm-plan.md](../../../plan/anthropic-llm-plan.md) (Rung 0 + Starter project sections)

**Known limitation of a single-call design (by design, not a bug to fix here):** Stage 1 is exactly one LLM call — it can check that a citation names a real KB file, but it cannot check that the specific fact stated in `reply` actually matches that file's content (e.g. a reply citing `refunds.md` while stating "14 days" instead of the real "30 days" would pass Stage 1's validation untouched). Catching that requires a *second*, independent call that reads the draft reply and the source file and judges whether they agree — that's `PLAN.md`'s **Stage 4 (Double-checking)**, not built yet. This isn't a flaw to patch here — it's the concrete, real mechanism behind Stage 4's own RED case ("a first draft that looks fine but is subtly wrong, e.g. states the wrong refund window — nothing catches it"). If Task 6's manual review ever actually catches a reply making this exact kind of mistake, that's the real-world RED case `PLAN.md`'s hard rule requires before Stage 4 gets built — not before.

---

## Behavior

### Input

| Field | Type | Meaning |
|---|---|---|
| `message` | string | One customer question, plain text, passed as the CLI argument. |

**Constraints:**
- Single-turn — no conversation history, no session/user ID. Each call is stateless.
- One question per call — Stage 1 doesn't handle multi-topic messages (that's Stage 2, not built yet).
- No attachments, no structured fields — raw text only.

### Output Fields

| Field | Type | Meaning |
|---|---|---|
| `intent` | enum: `hours` \| `refund` \| `product` \| `other` | Which KB topic the question falls under. `other` = not covered by any KB file. |
| `reply` | string | The actual text shown to the customer. |
| `citations` | list of filenames, max 1 entry | Which KB file the reply's facts came from. Exactly 1 entry when `intent` is `hours`/`refund`/`product`; empty list when `intent` is `other`. |

### Use Cases

| # | Use case | Example question | `intent` | `citations` | Acceptance criteria |
|---|---|---|---|---|---|
| 1 | Hours question | "Are you open on Sundays?" | `hours` | `["hours.md"]` | Reply states real hours from `hours.md` (closed Sun, Mon-Fri 9-18, Sat 10-16). No hours not in the file. |
| 2 | Refund question | "I bought a jacket 10 days ago, can I get my money back?" | `refund` | `["refunds.md"]` | Reply states real refund terms from `refunds.md` (30-day window, unused/original packaging, 5 business days to original payment method). |
| 3 | Product question | "What backpacks do you sell?" | `product` | `["products.md"]` | Reply lists only products/prices/attributes that exist in `products.md`. No invented product. |
| 4 | Off-topic question | "Can you help me file my taxes?" | `other` | `[]` | Reply is a polite decline. No fact from any KB file is asserted as if it answers the question. |

**Cross-cutting acceptance criteria (all use cases):**
- Every string in `citations` must be a real filename in `data/kb/`.
- `citations` has at most 1 entry — Stage 1 answers draw from exactly one KB file. A response citing more than one file is rejected as a grounding failure, same as citing a file that doesn't exist.
- No fact in `reply` may be absent from the cited file — no invention, no guessing.
- Exactly one `intent` per question (Stage 1 doesn't split mixed-topic questions — that's Stage 2, not built yet).

**Known scope limitation (accepted, not solved):** some single-intent questions need facts from two KB files to answer fully correctly — e.g. "Can I return the Camp Stove Mini?" is intent `refund`, but the correct answer depends on `products.md` marking it "on sale" before applying `refunds.md`'s sale-item exception. The one-citation cap means Stage 1 cannot express that cross-reference; it will cite only one file (whichever the model picks) and may miss the exception. This is intentional for now, per the project's build-only-what's-proven-needed rule — not covered by the golden test set, not fixed until a real failure shows it's needed.

These four use cases map directly to the golden questions `s1-01`..`s1-04` in `data/sample_questions.json`, used by Task 5's integration test and Task 6's e2e test.

---

## Implementation

**Architecture:** A CLI reads one customer message, loads the three knowledge-base markdown files into a system prompt, makes one Anthropic Messages API call instructing the model to return structured JSON (intent, reply, citations), then validates the response — every citation must name a real KB file, or the call fails closed. An integration test wires the pipeline together with only the API mocked; a separate e2e test runs the stage-1 golden questions against the live API for automated intent/citations checks plus manual reply review.

**Tech Stack:** Python 3.13, `anthropic` SDK, `pytest`. No LangChain, no database, no web UI — CLI only, per the starter-project spec.

## Global Constraints

- v1 is rung 0 only: one direct API call, no chaining/routing/loops.
- No LangChain, no database, no UI — Python + Anthropic API + CLI only.
- Fail closed: a citation not in the KB, or more than one citation, is a grounding failure, never an invented fact shown to the user.
- Off-topic questions get a polite decline (`intent: other`), never a guess.
- Model: `claude-sonnet-5` — this line is the single source of truth for model choice; the `client.py` function signature's default parameter reads from here, never hardcoded a second place.
- `temperature: 0` on every API call — Task 6's e2e test asserts `intent`/`citations` deterministically; unpinned sampling would make that assertion flaky.
- `max_tokens: 1024` on every API call — generous for a short grounded answer, small enough to fail fast (truncated/malformed JSON, caught by Task 2) rather than hang or run up cost on a runaway response.
- Knowledge base: `data/kb/*.md` (hours, products, refunds) — read-only input.
- Golden test questions: `data/sample_questions.json`, filtered to `stage: 1`.
- Every task follows RED (failing test) → GREEN (minimal code) → verify pass, per superpowers:test-driven-development. No production code before its test exists and has been watched to fail.
- Grounding validation is filename-level only (see the known limitation noted at the top of this plan) — fact-level accuracy relies on Task 6's manual read, not automated validation.

---

## File Structure

- `src/policy_bot/kb.py` — loads the KB markdown files into memory.
- `src/policy_bot/client.py` — builds the system prompt, calls the Anthropic API, parses and validates the response (grounding check), logs latency/token usage.
- `src/policy_bot/cli.py` — reads a message from the command line, wires the loader and client together, prints the answer as JSON.
- `tests/` — three levels:
  - unit tests for each module above (Tasks 1-4): each module tested in isolation, its own dependencies mocked.
  - `tests/test_stage1_integration.py` (Task 5): real KB files, real prompt builder, real parser, all wired together — only the Anthropic API call is mocked, at the SDK boundary.
  - `tests/test_stage1_e2e.py` (Task 6): real API calls, marked `e2e`, excluded from the default test run.
- `pytest.ini` — registers the `e2e` marker and excludes it by default (`addopts = -m "not e2e"`), so `pytest` alone runs unit + integration tests only (fast, free, no network), and `pytest -m e2e` runs the golden-set e2e tests deliberately.
- `requirements.txt` — pins `anthropic>=1.0.0,<2.0.0` and `pytest>=9.1.1,<10.0.0` (lower bound matches what's installed now; upper bound blocks an unreviewed major-version jump).

---

### Task 0: Repo setup

This directory is not yet a git repo. Initialize git, add a `.gitignore` (`__pycache__/`, `*.pyc`, `.pytest_cache/`, `.venv/`), commit the existing plan/data files as a baseline before any code is written.

---

### Task 1: Knowledge base loader

**Files:** create `src/policy_bot/kb.py`, test `tests/test_kb.py`.

**Responsibility:** Read every `.md` file out of the KB folder into a filename-to-content mapping, so later tasks have a single, testable source of KB data instead of touching the filesystem themselves.

**RED — failing tests to write first:**
- Loading the KB directory returns all three filenames (hours, products, refunds).
- Loaded content matches what's actually on disk for each file.
- Result order is deterministic — sorted by filename — so prompt output is stable across runs.

**GREEN — minimal behavior to satisfy them:** read each `.md` file in the KB directory into `{filename: content}`, sorted by filename.

**Acceptance criteria:** all three RED tests pass; no other KB files silently ignored or duplicated.

---

### Task 2: Response parsing and grounding validation

**Files:** create/extend `src/policy_bot/client.py`, `tests/test_client.py`.

**Responsibility:** Turn the model's raw JSON text into a validated answer, independent of the network call — so this logic is testable without hitting the API. Must reject (raise, not silently fix) any response whose intent isn't one of hours/refund/product/other, whose citations name a file outside the KB, or whose citation count doesn't match its intent (exactly 1 for `hours`/`refund`/`product`, exactly 0 for `other`).

**RED — failing tests to write first:**
- A well-formed response with a real citation parses into an answer with matching intent/reply/citations.
- A citation naming a file that isn't in the KB is rejected as a grounding failure.
- An intent value outside the four allowed values is rejected.
- An off-topic answer (`intent: other`) is allowed to have empty citations.
- A non-`other` intent (`hours`/`refund`/`product`) with **empty** citations is rejected as a grounding failure — this is what forces the model to cite its topic's file even when reporting an item isn't carried (see the "topic covered but item not found" case in the Use Cases section).
- A non-`other` intent with **more than one** citation is rejected as a grounding failure — enforces the one-citation cap from the Behavior section.
- Malformed JSON is rejected with a clear error.
- JSON missing a required field (intent/reply/citations) is rejected with a clear error.

**GREEN — minimal behavior to satisfy them:** parse JSON, validate intent against the fixed set, validate every citation against the KB's known filenames, validate citation count against intent (1 for topic intents, 0 for `other`), raise on any violation, otherwise return the validated answer.

**Acceptance criteria:** all eight RED tests pass; no valid response is ever silently downgraded (grounding failures always raise, never return a partial/guessed answer).

---

### Task 3: System prompt builder and live API call

**Files:** extend `src/policy_bot/client.py`, `tests/test_client.py`.

**Responsibility:** Build the system prompt from the loaded KB content plus the JSON-output instructions, and make the actual Anthropic API call (model, message, system prompt, `temperature=0`, `max_tokens=1024`) through an injected client so tests run against a mock, never the network. To reduce the chance of the model wrapping its JSON in prose or markdown fences, the call prefills the assistant turn with an opening `{` so the response continues directly as JSON. The system prompt also explicitly instructs the model how to handle a topic-covered-but-item-not-found question (e.g. "do you sell shoes?" when only backpacks/jackets/stoves are listed): still use that topic's `intent`, still cite that topic's file (it was consulted to determine the item isn't there), and state in `reply` that the specific item isn't carried. Log latency and token usage for every call. Feed the response text through Task 2's parser/validator before returning.

**RED — failing tests to write first:**
- The built system prompt includes every KB file's name and content.
- The built system prompt includes the topic-covered-but-item-not-found instruction described above.
- A successful mocked API call returns a validated answer.
- A mocked API call whose response cites a file outside the KB surfaces as a grounding failure (via Task 2's validator), not a returned answer.
- The API call is made with `temperature=0` and `max_tokens=1024` (assert on the mocked call's kwargs).
- The API call's message list includes an assistant-role prefill starting with `{` (assert on the mocked call's kwargs).
- Latency and token counts are logged for every call (assert the log call happens, not its exact text).

**GREEN — minimal behavior to satisfy them:** build the prompt from KB content (including the absence-case instruction), call the injected client's message-create method with model/system/message/temperature/max_tokens/assistant-prefill, log latency + token usage, parse+validate the response via Task 2.

**Acceptance criteria:** all seven RED tests pass; test suite makes zero live network calls.

---

### Task 4: CLI entry point

**Files:** create `src/policy_bot/cli.py`, `tests/test_cli.py`, `requirements.txt`.

**Responsibility:** Command-line wiring — take a message argument, load the KB, call the client, print the resulting answer as JSON. Exit non-zero with a clear stderr message on any failure at the API call site — grounding failure, malformed response, or a network-level error (timeout, rate limit, connection error) — so a bad call never crashes with a raw traceback or silently succeeds.

**RED — failing tests to write first:**
- Running the CLI with a message (client mocked) prints a JSON object with intent/reply/citations and exits 0.
- Running the CLI when the client raises a grounding failure prints the error to stderr and exits non-zero.
- Running the CLI when the client raises a network-level error (e.g. a mocked timeout/connection error) prints a clear stderr message (not a raw traceback) and exits non-zero.

**GREEN — minimal behavior to satisfy them:** load KB, build real Anthropic client, call Task 3's function inside a try/except covering grounding failures, response-validation errors, and API/network errors; print JSON on success, print error + non-zero exit on any of those failures.

**Acceptance criteria:** all three RED tests pass.

---

### Task 5: Full-pipeline integration test (API mocked)

**Files:** create `tests/test_stage1_integration.py`.

**Responsibility:** Tasks 1-4's unit tests mock at the module boundary (e.g. Task 4 mocks `answer_question` itself, never touching the real `client.py`/`kb.py`). This task wires the real `load_kb`, `build_system_prompt`, `answer_question`, and `cli.main` together — only the Anthropic SDK call (`client.messages.create`) is mocked. It proves the pieces actually integrate (real KB path resolves, real KB content reaches the real prompt builder, the real parser handles the real CLI's output path) without spending real API calls. Sits between the unit tests (Tasks 1-4) and the e2e test (Task 6) in the test pyramid.

**RED — failing tests to write first:**
- For each of the 4 stage-1 questions: with the Anthropic client mocked to return a canned response matching that question's `expected_intent`/`expected_citations`, running the CLI end-to-end (real KB directory on disk, real prompt builder, real parser — only the network call mocked) prints the correct JSON and exits 0.
- The prompt actually sent to the mocked client (inspected via the mock's recorded call) contains real content from all 3 KB files on disk — proves `cli.py` → `client.py` → `kb.py` are genuinely wired, not each individually mocked in isolation.

**GREEN — minimal behavior to satisfy them:** none expected — Tasks 1-4 already built every piece; this task should pass once the tests are written, proving the wiring is correct. A failure here means a real integration bug between modules, not a missing feature.

**Acceptance criteria:** all integration tests pass; zero live network calls; running plain `pytest` (no `-m e2e`) includes these tests.

---

### Task 6: Stage 1 golden-set e2e test

**Files:** modify `data/sample_questions.json` (add `expected_intent` and `expected_citations` to each stage-1 entry, per the Use Cases table), create `tests/test_stage1_e2e.py`, create `pytest.ini`.

**Responsibility:** This is an e2e test — real KB, real Anthropic API, no mocks — as opposed to Tasks 1-4's unit tests, which mock the client. It's marked `@pytest.mark.e2e` and excluded from the default `pytest` run (registered + excluded via `pytest.ini`) since it costs real API calls per run; it's invoked deliberately with `pytest -m e2e`. One test per stage-1 question (parametrized over `data/sample_questions.json` filtered to `stage: 1`): call the real API, `assert` actual `intent`/`citations` equal `expected_intent`/`expected_citations` (deterministic, real pass/fail) and assert no `GroundingError` is raised. `reply` wording is not deterministic (same question, different phrasing each run) — print the actual reply next to `expected_answer` (run with `pytest -m e2e -s` so prints show even on pass) for a human to judge on facts/tone; this part isn't asserted.

Unlike Tasks 1-4, this isn't classic RED-then-GREEN — the code under test already exists by this point (Tasks 1-4). This task is acceptance/validation of the already-built system against the real API, not a driver for new production code.

**Acceptance criteria:**
- All 4 stage-1 e2e tests pass: `intent`/`citations` auto-match expected values, no grounding error.
- The off-topic test (tax filing) asserts `intent: other`, `citations: []`.
- Each reply's wording is checked by hand against `expected_answer` (via the printed output) before Stage 1 is called done — this part stays manual.
- `pytest` alone (no `-m e2e`) does not run these tests or make any network call.

---

## Definition of done

- Every task's RED tests were watched to fail before their GREEN code was written (Tasks 1-5; Task 6 validates already-built code, see its note).
- Unit tests (Tasks 1-4) and the integration test (Task 5) all pass with zero live network calls (`pytest`, no `-m e2e`).
- The e2e golden-set test (Task 6, `pytest -m e2e`) passes: `intent`/`citations` auto-match for all 4 questions, and every reply matches its expected answer on manual read.
- The off-topic sample question declines rather than guesses.
- Every citation the model returns names a real file under `data/kb/`.
