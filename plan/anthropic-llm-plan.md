# LLM integration ladder (Anthropic)

Copy of the generic learning plan (not tied to a specific app).

Source: [Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents) (Dec 2024).

**Rule:** Workflows = you orchestrate. Agents = the model orchestrates. Add a rung only when evals prove the previous one is not enough.

## The article’s main claim

Success is not the most sophisticated system. Start with a single prompt, measure it, then add multi-step agentic systems only when simpler solutions fall short. Prefer direct API calls over frameworks until you can debug the raw prompts.

## The one distinction that matters

| | **Workflows** (you control flow) | **Agents** (model controls flow) |
|---|---|---|
| Who chooses the next step? | Your code | The LLM |
| Shape | Chain, route, parallel, orchestrate, evaluate | Tools in a loop until done |
| Tradeoff | Predictable, cheaper to test, fail closed with gates | Flexible; cost and errors compound |

LLM calls in a workflow sit on a graph you wrote. An agent uses tools from environmental feedback in a loop. Use agents when the number of steps cannot be predicted. Use sandbox, iteration caps, and human checkpoints.

## Recommended order

Parallelization sits between routing and evaluator–optimizer in the article; do not skip it — it is often cheaper than a critic loop.

| Rung | Pattern | Who decides | When to climb | Practice task |
|---|---|---|---|---|
| 0 | Eval + single call | None — you own the path | Always start here. Often this is enough. | One call: answer using only retrieved docs; reject invented citations. |
| 1 | Prompt chaining | None — fixed sequence + gates | Task splits into easier sequential subtasks. | Extract facts → draft → format. Gate if extraction fails schema. |
| 2 | Routing | Classifier only; handlers are fixed | Distinct input types need different prompts/models/tools. | Route support: billing vs tech vs general; different prompts/models. |
| 3 | Parallelization | None — fan-out is hardcoded | Independent subtasks, or voting for confidence. | Score accuracy / tone / safety in parallel, or vote on a classification. |
| 4 | Evaluator–optimizer | Loop until rubric passes (capped) | Clear criteria; human-style feedback actually improves the draft. | Draft, then a critic scores a rubric until pass or max 3 loops. |
| 5 | Orchestrator–workers | Orchestrator chooses subtasks; still a workflow | Subtasks cannot be predicted in advance. | Planner invents research subtasks; workers fetch; synthesizer merges. |
| 6 | Agents | LLM picks tools and when to stop | Open-ended; you cannot hardcode the path. Trust + sandbox required. | LLM + tools in a loop until done, with caps and a sandbox. |

## What to master on each rung

### Rung 0 — Direct call (augmented LLM)

One model call plus retrieval, structured output, and logging. Pass only the facts the model is allowed to use. Fail closed if it cites something that was not in the payload.

- Structured JSON output
- Grounding / citations
- Latency + token log
- Golden-set eval

### Rung 1 — Prompt chaining

Decompose into easier steps. Insert a programmatic gate between steps (schema valid? retrieval non-empty?). Trade latency for accuracy. Do not chain “because agents do multi-step” — chain only when each step is a cleaner task.

### Rung 2 — Routing

Classify, then hand off to a specialized prompt, model, or tool path. Optimizing one mega-prompt for all intents hurts the others. Router can be an LLM or a cheap classifier. Log the chosen route.

### Rung 3 — Parallelization

- **Sectioning:** independent aspects in parallel.
- **Voting:** same task N times, aggregate.

Better attention per aspect. Also a common pattern for guardrails (one call answers, another screens).

### Rung 4 — Evaluator–optimizer

Generator drafts; evaluator scores against a fixed rubric and returns actionable feedback. Loop with a hard cap. Fit only if (1) a human giving that feedback would improve the draft, and (2) the model can give that feedback. Keep the evaluator on a separate context so it cannot rubber-stamp the generator’s chain of thought.

### Rung 5–6 — Orchestrator, then agents

Orchestrator-workers: a planner LLM invents subtasks, workers execute, synthesizer merges. Agents: tools in a loop until done.

Production principles: keep the design simple, show the plan, and treat tool schemas as seriously as prompts (agent-computer interface).

## Three implementation principles

1. **Simplicity** — Prefer a few lines of API code you can read over a framework graph you cannot debug.
2. **Transparency** — Surface intermediate plans, routes, scores, and tool calls. If you cannot inspect a step, you cannot improve it.
3. **Agent-computer interface** — Tool names, args, and docs are prompt engineering. Make the correct call the easy call (stable IDs, not ambiguous names).

## How to know you should not climb yet

If a better prompt, better retrieval, or a cheaper model closes the eval gap, stay. Climb when error analysis shows a structural problem: mixed intents, sequential subtasks, or an unpredictable number of tool steps.

---

## Starter project (when we implement)

**Policy reply helper** — a CLI for a fake shop. Paste a customer message; return JSON:

```json
{
  "intent": "hours | refund | product | other",
  "reply": "...",
  "citations": ["kb/hours.md"]
}
```

- Knowledge base: 3 short markdown files (hours, refunds, products).
- Stack: Python + Anthropic API. No LangChain. No database. No UI.
- v1 is **rung 0 only**. A new pattern must beat the golden tests (quality, or same quality at lower cost/latency).

| Rung | Only add if… |
|---|---|
| 0 — Direct call | Always. Stuff the 3 files into context. Fail if a citation is not a real file. |
| 1 — Chain | One prompt mangles “extract facts” and “write a kind reply” together. |
| 2 — Route | Refunds need a different prompt/tone than hours; one prompt hurts one of them. |
| 3 — Parallel | You want a separate policy/safety screen, or votes on intent. |
| 4 — Evaluator | First drafts miss policy; a rubric actually improves them. |
| 5–6 — Orchestrator / agent | You add tools (`lookup_order`, `get_hours`) and the path is no longer fixed. |
