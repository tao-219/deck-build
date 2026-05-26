# deck-build × Minto Pyramid Principle — Gap Analysis & Enhancement Plan

Audit of the `deck-build` plugin against the 8-criterion rubric in `minto-rubric.md`. Scope: the
**source repo** at `~/projects/deck-build/` (the edit target; a superset of the install cache, which is
missing `deck-clean`/`deck-preview` and is reference-only). Every claim cites `file:line`.

> **Scoping note.** The audit brief listed nine "skills"; the repo has **five** skills
> (`deck-orchestrator`, `deck-render`, `deck-qa`, `deck-charts`, `deck-extract-dna`) and four
> **commands** (`deck-build`, `deck-slide`, `deck-clean`, `deck-preview`) — `deck-clean`/`deck-preview`
> exist as commands only, `deck-slide`/`deck-build` are command wrappers over the skills. `deck-charts`
> is a declared **stub** (`skills/deck-charts/SKILL.md:3`). Commands are thin wrappers that *mention*
> Pyramid Principle (`commands/deck-build.md:20-22`) but delegate all logic to the orchestrator, so they
> carry no independent Minto enforcement and are folded into the orchestrator column below.

## Headline

Minto is **comprehensively documented** (`pyramid-principle.md` is genuinely strong) and **instructed**
(the orchestrator tells the model to build a pyramid, decompose MECE, order by SCQA). But of the 8
criteria, only **action titles** are actually *validated* by an executable check — and only on their
**mechanics** (verb, length, weasel), not their **substance** (assertion + so-what). The four
**deck-level logic criteria — storyline, vertical logic, horizontal logic, MECE — have zero executable
enforcement.** They live as reference prose and one-line generative instructions; nothing reads them
back, and the data model can't even represent them.

Two root causes:

1. **The plan schema can't hold a pyramid.** `deck-plan.json` (`deck-orchestrator/SKILL.md:76-108`)
   captures a single `governing_thought` string and a **flat** `slides[]` array. There is no key-line /
   pillar layer, no SCQA fields, no per-slide "supports pillar / answers question" linkage. `grep` for
   `pillar|scqa|key_line` across all `.py` and `.json` returns **only** reference prose and the Phase-2
   instruction lines — never a structured field. So the pyramid exists only as transient model reasoning,
   never as an inspectable artifact a validator could test.
2. **QA is architecturally per-slide.** The vision audit spawns **one fresh subagent per slide**
   (`deck-qa/SKILL.md:41`; `vision-audit-prompt.md:3,10`) precisely so each slide is judged without
   bias — which by construction **cannot** see the storyline. The title linter loops slide-by-slide in
   isolation (`action_title_lint.py:429-444`). **Nothing in the pipeline holds a whole-deck view**, so no
   cross-slide logic check is even possible today. (`vision_audit_render.py:126-137` *does* emit the full
   ordered title list in the manifest — the input a storyline check needs exists; no consumer reads it.)

---

## Criterion × Component matrix

`I` = Implemented (generated *and* validated) · `P` = Partial (generated or mentioned, not validated) ·
`A` = Absent (no enforcement). Columns: **ORCH** = deck-orchestrator SKILL + plan schema · **PYR** =
pyramid-principle.md · **ATP** = action-title-pattern.md · **ATL** = action_title_lint.py · **ARCH** =
archetype_compliance.py · **QA-V** = deck-qa vision audit · **Net** = highest enforcement level reached.

| # | Criterion | ORCH | PYR | ATP | ATL | ARCH | QA-V | Net enforcement |
|---|---|---|---|---|---|---|---|---|
| 1 | Governing thought | P | P | – | A | A | A | **Generated**, not validated |
| 2 | SCQA intro | P | P | – | A | A | A | **Mentioned** + 1-line instruction |
| 3 | Answer-first / top-down | P | P | P | P | P | A | **Generated**; slide-level via verb proxy only |
| 4 | Action titles | P | P | P | **I** | P | P | **Validated** (mechanics only) |
| 5 | Storyline read-through | A | P | P | A | A | A | **Mentioned** (prose test, never run) |
| 6 | Vertical logic | A | P | – | A | A | A | **Mentioned** (Pyramid test prose) |
| 7 | Horizontal logic | A | P | – | A | A | A | **Mentioned** (one anti-pattern line) |
| 8 | MECE | P | P | – | A | A | A | **Generated** as instruction; never checked |

One cell of `I` across 48. The plugin is strong on *visual* archetype enforcement
(`archetype_compliance.py` + the vision audit) and on *title mechanics* — but **logical-structure**
enforcement is essentially absent.

---

## Per-criterion findings (with citations)

### 1 — Governing thought · *Generated, not validated*
- Captured as a field: `deck_meta.governing_thought` in the plan schema (`deck-orchestrator/SKILL.md:79`)
  and surfaced at the approval gate (`SKILL.md:110`). Instruction to state it: `SKILL.md:51`. Defined in
  reference: `pyramid-principle.md:25`.
- **Gap:** no check that it is a so-what assertion (vs a topic), that it's present/non-empty in output,
  or that the slides actually support it. The "Pyramid test" that would verify pillar→thought support is
  prose only (`pyramid-principle.md:70`). No script reads the field; `action_title_lint.py` never opens
  the plan.

### 2 — SCQA intro · *Mentioned + a one-line instruction*
- Described well: `pyramid-principle.md:31-46` (SCQA and the compressed SCR). Instruction: "Order pillars
  by SCQA" (`deck-orchestrator/SKILL.md:53`).
- **Gap:** the instruction conflates *ordering pillars* with *building an opening SCQA arc*. No SCQA fields
  in the schema (`SKILL.md:76-108` has none); no scaffolder generates the Situation/Complication/Question/
  Answer opening; no check the deck opens with the arc. This is the **weakest-supported** criterion.

### 3 — Answer-first / top-down · *Generated; slide-level only via a verb proxy*
- Deck level: "Lead with the answer" (`pyramid-principle.md:5`); anti-pattern "burying the lead"
  (`:74`); orchestrator orders SCQA-first (`SKILL.md:53`).
- Slide level: action titles are the mechanism; the closest executable proxy is the verb test
  (`action_title_lint.py:209-219`, `archetype_compliance.py:91-95`).
- **Gap:** no positional check that the thesis appears early (vs buried); "verb present" ≠ "title is the
  slide's conclusion"; nothing checks the body supports the title rather than a different point.

### 4 — Action titles · *Validated — but mechanics only* (the one real win)
- Generated: `deck-orchestrator/SKILL.md:60-62`; full reference `action-title-pattern.md` (so-what test
  `:7-9`, two-tone `:21-38`, topic-vs-action table `:55-65`, banned weasels `:101-114`). Hard rule
  `SKILL.md:172`.
- Validated: `action_title_lint.py` — word-count ≤15 (`:340-348`), verb (`:209-219, 351-359`), topic-title
  (`:311-324, 362-370`), trailing period (`:373-378`), weasel (`:222-236, 381-390`), passive (`:239-255`),
  two-tone (`:258-263, 403-420`). Duplicated for the compliance gate in `archetype_compliance.py:91-95,
  222-256`. Gated into the loop (`deck-qa/SKILL.md:52-72, 111-118`).
- **Gap (depth):** every check is a string heuristic — the file says so itself (`action_title_lint.py:70`:
  "not a POS tagger… use as a screen, not a verdict"). It tests **verb + length**, not **assertion +
  so-what**. The `is_topic_title` screen only fires when a title *both* lacks a verb *and* opens with one
  of ~20 fixed headwords (`:128-134, 311-324`) — so a verb-bearing non-assertion ("The team will discuss
  next steps") or a vacuous claim passes clean. Answering the brief's probe directly: the linter is
  **substantive on verb + length, cosmetic/absent on assertion + so-what.**

### 5 — Storyline read-through · *Mentioned; never executed* (the signature gap)
- The exact Minto "Title test" is documented twice: `pyramid-principle.md:68` ("read only slide titles
  top-to-bottom. Do they tell the story?") and `action-title-pattern.md:7-9, 98`.
- **Gap:** nothing runs it. `action_title_lint.py:429-444` audits each title in isolation; the vision
  audit is fresh-subagent-per-slide (`deck-qa/SKILL.md:41`) and so is *structurally blind* to sequence.
  The ordered title list needed to run the test is already produced (`vision_audit_render.py:126-137`)
  but has no consumer. This is the single most distinctive Minto deck-level discipline and it is entirely
  unenforced.

### 6 — Vertical logic · *Mentioned (Pyramid-test prose)*
- Gestured at by the structure diagram (`pyramid-principle.md:11-23`) and the Pyramid test
  (`:70`, "does each pillar's evidence support the pillar?").
- **Gap:** the plan has no parent→child structure to test against — `slides[]` is flat
  (`deck-orchestrator/SKILL.md:84-107`), no `supports_pillar`, no "question this slide answers". No check
  for orphan slides or off-question support. Not representable, let alone validated.

### 7 — Horizontal logic · *Mentioned (one anti-pattern line)*
- Only touchpoint: the anti-pattern "Bullets that aren't grouped (random order vs logical order)"
  (`pyramid-principle.md:78`). `visual-types.md` / `design-archetypes.md` ordering rules are *visual*
  (selection meta-rules `design-archetypes.md:17-24`), not argument-logic.
- **Gap:** no concept of same-level type-consistency or order basis (deductive/inductive; time/structure/
  degree). Not in the schema, not checked.

### 8 — MECE · *Generated as instruction; never checked*
- Well-described: the MECE check and its classic failure modes (`pyramid-principle.md:56-65`). Instructed:
  "Decompose into 3–5 MECE supporting pillars" (`deck-orchestrator/SKILL.md:52`).
- **Gap:** no MECE checker anywhere. Nothing flags an "Other/Miscellaneous" catch-all, overlapping
  pillars, or coverage gaps; the pillar set isn't even captured as a discrete list to test
  (`SKILL.md:76-108`).

---

## What this means

- **Visual quality is enforced; logical quality is trusted.** The plugin will reliably catch a footer
  overrun, an off-brand color, a missing focus marker, or a periodless... a period on a title — and will
  *assume* the argument is sound because the model was told to make it sound. For a "consultancy-grade"
  /McKinsey-standard tool, the argument is the product; today it's the unchecked half.
- **The fix is enabler-then-checks.** Almost every deck-level gap (5–8, plus real validation of 1–3) is
  blocked on the same missing thing: a structured argument tree in `deck-plan.json`. Build that once, and
  the individual validators become tractable.
- **One new QA mode unlocks the signature test.** A single **whole-deck** judge (the architectural
  opposite of the per-slide vision audit) covers storyline today on titles alone, and covers vertical/
  horizontal/MECE once the schema exists.

---

## Prioritized enhancement plan

Effort: **S** ≈ <½ day · **M** ≈ ½–1 day · **L** ≈ 1–2 days. Each item names what changes, the file(s),
effort, and impact. Ordered by impact-given-dependencies.

| P | Item | Files | Effort | Impact | Depends on |
|---|---|---|---|---|---|
| 1 | **Pyramid + SCQA plan schema** (the enabler) | `deck-orchestrator/SKILL.md` | M | Unlocks 1,2,5,6,7,8 | — |
| 2 | **Storyline read-through validator** (whole-deck judge) | new `scripts/storyline_check.py`; `deck-qa/SKILL.md` | M | Highest single win (crit 5) | governing_thought (exists) |
| 3 | **Deepen action-title linter → assertion+so-what** | `action_title_lint.py`; `deck-qa/SKILL.md` | M | Closes crit-4 depth gap | — |
| 4 | **MECE + vertical/horizontal logic checker** | new `scripts/logic_structure_check.py`; `deck-qa/SKILL.md` | L | Covers crit 6,7,8 | P1 |
| 5 | **SCQA scaffolder + opening-arc check** | `deck-orchestrator/SKILL.md`; reuse P2 judge | M | Covers crit 2; strengthens 1,3 | P1 |
| 6 | **Archetype ↔ logic-structure mapping** | `design-archetypes.md`, `visual-types.md`; check in P4 | S | Makes archetype choice logic-driven; aids 7 | P1,P4 |

### P1 — Extend `deck-plan.json` to encode the real pyramid + SCQA *(enabler)*
- **What:** add to `deck_meta`: `scqa: {situation, complication, question, answer}` and
  `key_line: [{id, claim, logic_type: deductive|inductive, order_basis: time|structure|degree}]`. Add to
  each slide: `supports_pillar: <key_line.id>` and `answers_question: "<question this slide answers>"`.
  Update Phase 2 (`SKILL.md:48-55`) to *populate* these (build governing thought → key line → support as
  data, not just prose) and the approval gate (`:110`) to show the pyramid.
- **Why first:** criteria 1, 2, 5, 6, 7, 8 are untestable until the argument is a structured artifact.
  This is the single highest-leverage change; it converts "Generated-as-reasoning" into
  "Generated-as-data" so downstream validators have something to read.
- **Effort M · Impact: foundational.**

### P2 — Storyline read-through validator *(highest single enforcement win)*
- **What:** new `scripts/storyline_check.py` that emits the ordered title list + `governing_thought`
  (titles already available via `vision_audit_render.py:126-137` / the plan), and a new **deck-qa Layer 5**
  that passes the *entire* sequence to **one** whole-deck subagent (explicitly *not* per-slide) with the
  rubric's storyline prompt: flag non-sequiturs, gaps, titles that don't advance the argument, and confirm
  the chain lands the governing thought. Gate High findings into the iteration loop (`deck-qa/SKILL.md:111-118`).
- **Why #2:** it's the signature Minto deck test (`pyramid-principle.md:68`), runs on artifacts that
  already exist, and needs only `governing_thought` (no P1 dependency to start). Establishes the
  whole-deck QA mode that P4 reuses.
- **Effort M · Impact: high.**

### P3 — Deepen the action-title linter from mechanics to substance
- **What:** keep the fast deterministic screen; add an opt-in `--semantic` LLM-judge tier (surfaced as a
  deck-qa Layer-2 sub-step) scoring each title on assertion-vs-label and presence-of-so-what (and a number
  on quantitative slides). Two-tier so the cheap screen still gates and the judge catches verb-bearing
  non-assertions the heuristic (`action_title_lint.py:311-324`) cannot.
- **Why:** criterion 4 is the one "win" but it's shallow; this is the only gap fixable without P1 and it
  hardens the most-used check.
- **Effort M · Impact: medium-high.**

### P4 — MECE + vertical/horizontal logic checker
- **What:** new `scripts/logic_structure_check.py` + a deck-qa layer that, given the P1 schema, runs:
  **MECE** (deterministic catch-all-token screen — "other/misc/etc" — plus an LLM-judge for overlap/gap on
  the `key_line` set); **vertical** (every slide has a `supports_pillar`; each pillar's children answer its
  `answers_question`); **horizontal** (`logic_type`/`order_basis` present, type-consistent, render order
  honors basis). Encodes `pyramid-principle.md:56-70` as executable checks.
- **Why:** covers three whole criteria at once, but only meaningful after P1.
- **Effort L · Impact: high (gated on P1).**

### P5 — SCQA scaffolder + opening-arc check
- **What:** a Phase-2 sub-procedure that drafts S/C/Q/A explicitly and generates the opening slide
  sequence from it (populating the P1 `scqa` fields), plus a check (reusing the P2 whole-deck judge) that
  the first 1–3 slides instantiate the arc and that `answer` ≈ `governing_thought`.
- **Why:** turns the weakest criterion (2) from a one-line instruction into a generated, checked artifact;
  also strengthens 1 and 3.
- **Effort M · Impact: medium (gated on P1).**

### P6 — Archetype ↔ logic-structure mapping
- **What:** annotate each archetype in `design-archetypes.md` / `visual-types.md` with the logic shape it
  implies (e.g., `before-after-process` → deductive/time-ordered; `spotlight-comparison-columns` →
  inductive/parallel; `recommendation-hero` → answer-first thesis slide), and add a consistency check
  (inside P4) that a slide's chosen archetype matches its `logic_type`.
- **Why:** today archetype selection is purely visual (`design-archetypes.md:17-24`); this ties it to the
  argument, catching e.g. a parallel-comparison visual used for a sequential/deductive point. Lowest
  priority — polish once the logic layer exists.
- **Effort S · Impact: medium (gated on P1, P4).**

### Out-of-scope flags (noted, not Minto)
- **Layer 3 brand-token validator is documented but unbuilt** (`deck-qa/SKILL.md:76`,
  `brand_token_check.py` does not exist). Separate pre-existing gap.
- **Install cache is stale** vs the source repo (missing `deck-clean`/`deck-preview`). Re-run
  `/plugin marketplace update deck-build` after any edits land.

---

## Recommended sequencing

**P1 → P2 → P3** delivers the biggest enforcement gain fastest: a structured pyramid, the signature
storyline check gated into QA, and a title linter that finally tests the so-what. **P4 → P5 → P6** then
complete deck-level coverage (MECE, vertical/horizontal logic, SCQA, archetype-logic fit). P2 and P3 can
proceed in parallel with P1 since neither strictly requires the new schema to begin.

**STOP — awaiting approval before editing any plugin file.**
