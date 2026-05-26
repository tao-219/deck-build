# Minto Pyramid Principle — Testable Rubric for a Generated Deck

This rubric defines the standard a deck-build output must meet to be **Minto-compliant**. Each
criterion is written as a **testable pass-condition** over concrete artifacts: the `deck-plan.json`
(argument structure), the ordered slide-title sequence, and the rendered `.pptx`. It is the *standard* —
the companion `minto-gap-analysis.md` measures how much of it the plugin currently enforces.

Acronyms used here: **MECE** (Mutually Exclusive, Collectively Exhaustive); **SCQA**
(Situation–Complication–Question–Answer); **SCR** (Situation–Complication–Resolution); **so-what**
(the conclusion/takeaway a slide or deck asserts).

## Enforcement ladder (vocabulary for scoring)

A criterion can be supported at four escalating levels. "First-class, enforced" means level 3+.

1. **Mentioned** — described in a reference doc the author reads; no obligation to produce or check it.
2. **Generated** — the orchestrator instructs the model to produce it and (ideally) captures it as a
   structured field in `deck-plan.json`.
3. **Validated** — an executable check (deterministic script *or* LLM-as-judge) tests the artifact and
   can fail the deck.
4. **Gated** — a failed validation blocks delivery / forces regeneration (the QA iteration loop).

Each test below names the **artifact** it reads and the **method** (deterministic / LLM-judge / manual).
Deterministic screens are fast and catch mechanical failures; LLM-judge passes cover meaning
(assertion, so-what, coherence) that string heuristics cannot reach. A criterion is "enforced" only
when a judge of the right kind actually runs.

---

## Criterion 1 — Governing thought

**Definition.** The deck has exactly one main message; everything in it exists to support that message.

**Pass condition.**
- `deck_meta.governing_thought` is present and non-empty.
- It is a single declarative **assertion** (has a verb; states a position/recommendation), not a topic
  label, ≤ 25 words.
- ≥ 80% of content slides, read against it, plausibly support or build toward it; **zero** content
  slide contradicts it or is off-thesis.

**How to test.**
- *Deterministic:* field present + non-empty + word-count ≤ 25 + `has_verb()` true + not a bare
  topic headword.
- *LLM-judge:* "Is this a so-what assertion or a topic? For each slide title, does it support, build
  toward, or contradict this governing thought?" Fail on any contradiction or > 20% off-thesis slides.

**Fail signals.** Empty/absent field; a topic ("Q3 review", "CRR landscape"); two competing theses; a
deck where the title sequence implies a different main message than the stated one.

---

## Criterion 2 — SCQA intro

**Definition.** The opening sets up the governing thought via Situation → Complication → Question →
Answer (or the compressed SCR), so the audience arrives at the answer already primed.

**Pass condition.**
- `deck_meta.scqa` carries non-empty `situation`, `complication`, `question`, `answer` (SCR may leave
  `question` implicit but must carry `resolution`).
- `answer` is consistent with `governing_thought` (the answer *is* the thesis).
- The first 1–3 content slides instantiate that arc in order: a Situation the audience accepts → a
  Complication that destabilizes it → (Question) → the Answer/recommendation.

**How to test.**
- *Deterministic:* the four (or three) SCQA fields exist and are non-empty; `answer` ≈ `governing_thought`.
- *LLM-judge:* "Do the opening slides move Situation → Complication → Question → Answer without skipping
  to detail? Is the Complication a genuine tension, not a restated Situation?"

**Fail signals.** Deck opens on an agenda or background dump with no tension; Complication is a
paraphrase of the Situation; the Answer never appears up front; SCQA fields absent.

---

## Criterion 3 — Answer-first / top-down (deck AND slide level)

**Definition.** The conclusion precedes its support — at the deck level (thesis early, evidence later)
and at every slide (title states the takeaway; body defends it).

**Pass condition.**
- *Deck level:* the slide carrying the governing thought / recommendation appears within the first
  ~20% of content slides (after SCQA setup), never buried in the back half.
- *Slide level:* for every content slide, the **title states the slide's conclusion** and the body
  supplies support for *that* conclusion (body does not introduce a different, unstated takeaway).

**How to test.**
- *Deterministic (deck):* index of the recommendation/governing-thought slide ≤ ceil(0.2 × N_content).
- *LLM-judge (slide):* "Is the title the slide's actual conclusion? Does the body support the title
  rather than a different point?" Fail any slide where body and title argue different things.

**Fail signals.** "Burying the lead" (thesis on slide 18 of 20); data-dump slides whose title is a topic
and whose so-what is left for the reader to infer; title says X, body argues Y.

---

## Criterion 4 — Action titles

**Definition.** Every slide title is a full-sentence **assertion** that states the so-what — never a
topic label.

**Pass condition (all of):**
- Verb present; ≤ 15 words; active voice; no trailing period; no banned weasel words.
- Not a topic title (no bare noun-phrase headword).
- **Assertion + so-what:** the title makes a claim that carries a takeaway — not a verb-bearing
  non-statement ("The team will discuss next steps") and not a vacuous one ("Results show results").
- For a quantitative slide, the title carries the operative number.

**How to test.**
- *Deterministic:* the action-title linter — verb, word-count, topic-headword screen, weasel, passive,
  trailing period. 100% of content slides must pass.
- *LLM-judge:* "Is this an assertion that states a so-what, or merely a grammatically-complete label?"
  ≥ 90% must pass; any topic-label-with-a-verb is a fail.

**Fail signals.** "Overview", "Our approach", "Findings"; verb present but no claim ("We reviewed the
data"); claim present but no number on a numeric slide; > 15 words.

---

## Criterion 5 — Storyline (title read-through)

**Definition.** Read top-to-bottom with nothing but the titles, the deck is one coherent argument that
lands the governing thought. *(Minto's "Title test".)*

**Pass condition.**
- The ordered title sequence reads as a connected argument chain: each title follows from / advances the
  prior ones; there are no non-sequiturs and no missing links.
- The sequence demonstrably builds to (and is consistent with) `governing_thought`.
- Removing any single title would break the chain (no purely decorative titles).

**How to test.**
- *LLM-judge over the whole sequence (NOT per-slide):* feed the ordered title list + governing thought;
  ask "Do these titles, in order, tell one coherent story that arrives at the governing thought? List
  every gap, non-sequitur, or title that doesn't advance the argument." Fail on any flagged break.
- *Manual:* the same read-through by a human reviewer.

**Fail signals.** Titles that are individually fine but jump topics; a chain that never reaches the
thesis; two adjacent titles with no logical link; a title that could be deleted with no loss.

> This test is intrinsically deck-wide. A per-slide reviewer (one slide, fresh context) **cannot** judge
> it — the validator must hold the entire title sequence at once.

---

## Criterion 6 — Vertical logic

**Definition.** Each group of slides answers exactly the question its parent point raises — support sits
directly under the claim it supports.

**Pass condition.**
- `deck-plan.json` encodes a parent→child structure: governing thought → key-line pillars → supporting
  slides, with each slide tagged to the pillar it serves and the question it answers.
- For every pillar, its child slides collectively **answer the question the pillar raises** ("Why?",
  "How?", "How do we know?") and nothing more.
- No orphan slides (every content slide maps to a pillar); no slide answers a question its parent didn't
  raise.

**How to test.**
- *Deterministic:* every content slide has a non-null `supports_pillar`; every pillar has ≥ 1 child.
- *LLM-judge:* per pillar, "Do these child slides answer the question this pillar raises, and only that
  question?" Fail orphans and off-question children.

**Fail signals.** A slide that belongs to no pillar; evidence parked under the wrong claim; a pillar
whose children answer a different question than the pillar implies.

---

## Criterion 7 — Horizontal logic

**Definition.** Points at the same level are the same *kind* of thing and are arranged in a deliberate,
stated order.

**Pass condition.**
- Same-level items (the pillar set; any in-slide grouping) are type-consistent: all causes, **or** all
  steps, **or** all options, **or** all components — not a mix.
- The grouping declares its logic and honors it: **deductive** (premise → premise → conclusion) **or
  inductive** (parallel items of one class), and an order basis — **time** (chronological), **structure**
  (geography/org/component), or **degree** (most→least important).
- The rendered order matches the declared basis.

**How to test.**
- *Deterministic:* `key_line[*].logic_type` ∈ {deductive, inductive} and `order_basis` ∈
  {time, structure, degree} are present; render order equals plan order.
- *LLM-judge:* "Are these same-level points the same type? Is the stated order basis actually followed?"

**Fail signals.** A pillar list mixing a cause, a step, and an option; "short-term / long-term" with no
medium; items in arbitrary order with no rationale; declared `order_basis: degree` but items are random.

---

## Criterion 8 — MECE

**Definition.** Every grouping is Mutually Exclusive (no overlap) and Collectively Exhaustive (nothing
material missing; no catch-all refuge).

**Pass condition.**
- Pillars (and any decomposition shown on a slide) do not overlap in scope.
- The set covers the relevant universe, or any deliberate exclusion is stated explicitly ("out of
  scope: X").
- No "Other / Miscellaneous / etc." bucket used to absorb unstructured items.

**How to test.**
- *Deterministic screen:* flag any grouping containing a catch-all token ("other", "misc",
  "miscellaneous", "etc", "and more").
- *LLM-judge:* "Do any two items in this grouping overlap? Is anything material missing? Is any item a
  catch-all?" Fail on overlap, gap (unless explicitly scoped out), or catch-all.

**Fail signals.** "Customer A, Customer B, Other customers"; "Cost, Time, Risk, Other"; two pillars that
both cover the same sub-topic; a four-region split that silently omits a fifth operating region.

---

## Scoring

Per criterion, record the **highest enforcement level reached** (Mentioned / Generated / Validated /
Gated) and a **pass/fail** when a validator of the right kind exists. A deck is **Minto-compliant** only
when criteria 1–8 each reach Validated *and* pass. "First-class discipline" for the *plugin* means every
criterion is at least Validated (level 3) with the deck-level criteria (5–8) gated into the QA loop.
