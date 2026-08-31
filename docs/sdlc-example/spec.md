# Spec: Stage 1 Policy Reply Bot

> Learning example — the "what and why, under what constraints" layer.
> No implementation detail here; that's `plan.md`. Derived from the
> Behavior section of the actual plan doc.

## Input

| Field | Type | Meaning |
|---|---|---|
| `message` | string | One customer question, plain text, passed as the CLI argument. |

**Constraints:** single-turn, no history; one question per call (no
multi-topic — that's Stage 2); raw text only, no attachments.

## Output

| Field | Type | Meaning |
|---|---|---|
| `intent` | enum: `hours` \| `refund` \| `product` \| `other` | Which KB topic the question falls under. |
| `reply` | string | The text shown to the customer. |
| `citations` | list of filenames, max 1 entry | Which KB file the reply's facts came from. |

## Use Cases

| # | Use case | Example question | `intent` | `citations` |
|---|---|---|---|---|
| 1 | Hours | "Are you open on Sundays?" | `hours` | `["hours.md"]` |
| 2 | Refund | "I bought a jacket 10 days ago, can I get my money back?" | `refund` | `["refunds.md"]` |
| 3 | Product | "What backpacks do you sell?" | `product` | `["products.md"]` |
| 4 | Off-topic | "Can you help me file my taxes?" | `other` | `[]` |

## Design Constraints (policy flags)

- **Fail closed:** a citation not in the KB, or more than one citation, is a
  grounding failure — never shown to the customer.
- **Off-topic → decline, never guess.**
- **Single-citation cap:** every answer draws from exactly one KB file.
  Accepted limitation: a question needing two files (e.g. a sale-item
  refund exception) isn't handled correctly yet — deferred until proven
  necessary, not solved here.
- **Grounding is filename-level only**, not fact-level — validated that a
  citation names a real file, not that the stated fact matches its content.
  Closing that gap needs a second, independent LLM call (Stage 4 —
  Double-checking), out of scope for this spec.

## Open Design Question Resolved

Topic-covered-but-item-not-found (e.g. "do you sell shoes?"): still use the
topic's `intent`, still cite that topic's file, state the item isn't
carried — resolved here so engineering doesn't have to guess.
