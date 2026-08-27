# Plan — shop support chatbot

## What this is

A chatbot for an online shop. Customer asks about hours, refunds, or products. It answers only from a small knowledge base — never makes things up. Learning project: start simple, add a pattern only when proven needed.

## Hard rule

Build stage 1 only, first. Every later stage stays below, unbuilt, until its RED case is shown failing for real. Nothing gets built yet.

---

## Stage 1 — Basic answer bot

**Feature (business):**
- User does: types any question into the chat.
- Options: ask about hours, refunds, or products.
- Gets: one direct answer, grounded only in the shop's real policies. Off-topic question gets a polite "can't help with that," never a guess.

**How it works (high level):** One AI call reads the question together with all the policy information at once, and answers directly.

**Acceptance criteria:**
- Correct answer for a plain hours/refund/product question.
- Reply only uses facts that exist in the policy docs.
- Off-topic question gets a polite decline, not a guess.

**RED:** *(none — this is the starting point)*

**GREEN:** Customer asks "are you open Sundays?" → reply states the real Sunday hours, nothing invented.

---

## Stage 2 — Two-step thinking

**Feature (business):**
- User does: same as stage 1, but can now ask a question that mixes more than one topic in a single message.
- Options: same topics as before, now combinable in one question.
- Gets: one coherent reply that correctly covers every fact asked for, even when the question mixes topics.

**How it works (high level):** The request goes through two AI steps in sequence — first pulling out the relevant facts, then turning those facts into a reply — instead of doing both in one pass.

**Acceptance criteria:**
- Facts used in the reply match facts actually in the docs.
- Reply reads naturally, not just a list of facts pasted together.

**RED:** Customer asks a two-topic question ("can I return this jacket and are you open to accept it in person Sunday?") → stage 1 blends fact-finding and reply-writing into one pass and drops or garbles one of the two facts.

**GREEN:** Same question → both facts (return policy + Sunday hours) show up correctly in one coherent reply.

---

## Stage 3 — Specialist routing

**Feature (business):**
- User does: types a question, same as before.
- Options: same topics as before.
- Gets: a reply whose tone matches the topic — careful/formal for refund matters, friendly/casual for everyday questions like hours or products.

**How it works (high level):** The question is first sorted by topic, then handled by a topic-specific way of answering — a different set of instructions per topic — instead of one instruction trying to cover everything.

**Acceptance criteria:**
- Refund replies sound careful/precise.
- Hours/product replies sound casual/friendly.
- Same underlying facts, different tone per topic.

**RED:** Ask an hours question and a refund question with the same setup → both come back in the same tone, and the refund answer feels too casual for a policy matter (or the hours answer feels stiff).

**GREEN:** Same two questions → refund reply reads carefully/formally, hours reply reads warmly — same accuracy, different tone.

---

## Stage 4 — Double-checking

**Feature (business):**
- User does: types a question, same as before.
- Options: same as before — nothing new to choose.
- Gets: the same kind of reply as before, but with an extra guarantee — a wrong or risky answer gets caught and corrected before they ever see it.

**How it works (high level):** After a reply is drafted, a second, independent check reviews it against the policies before it's sent. Only reviewed replies reach the user.

**Acceptance criteria:**
- A wrong or risky first-draft reply gets caught and corrected before reaching the customer.
- Correct replies pass through unchanged (no unnecessary rewriting).

**RED:** A sample question where the first draft looks fine but is subtly wrong (e.g. states the wrong refund window) — nothing catches it, wrong answer goes out.

**GREEN:** Same question → the check flags the mistake, corrected reply goes out instead.

---

## Stage 5 — Self-review loop

**Feature (business):**
- User does: types a question, same as before.
- Options: same as before.
- Gets: a reply that's been graded against a policy checklist and rewritten if it fell short, so required details (like disclaimers) are never missing.

**How it works (high level):** The draft reply is scored against a checklist; if it doesn't pass, it's revised and re-scored, up to a small fixed number of tries, before being sent.

**Acceptance criteria:**
- Draft that misses a policy detail gets caught by the checklist.
- Rewriting stops once the checklist passes (or after a small fixed number of tries).

**RED:** A draft reply that's missing a required disclaimer (e.g. "sale items are final") — a human checking against the policy checklist would catch it, but nothing today does.

**GREEN:** Same draft → self-review catches the missing disclaimer, rewrite adds it, final reply passes the checklist.

---

## Stage 6 — Full assistant

**Feature (business):**
- User does: types a question, now including ones that need real, current info (e.g. their own order status).
- Options: can ask things that need a live lookup, not just static policy info.
- Gets: an answer based on real, current data — not just what's written in the fixed documents.

**How it works (high level):** The system can decide on its own to look things up (e.g. check an order, check today's hours) and take a variable number of steps before answering, instead of following one fixed sequence every time.

**Acceptance criteria:**
- Handles a question that needs live/real data, not just the static docs.
- Number of steps taken isn't fixed in advance — decided based on what's found along the way.

**RED:** Customer asks "where's my order #4521?" → no static doc has this, every earlier stage fails or refuses.

**GREEN:** Same question → real order looked up, actual status reported.

---

## Next step

Nothing gets built yet. When a stage's RED case is shown true with a real example, that's the signal to start that stage.
