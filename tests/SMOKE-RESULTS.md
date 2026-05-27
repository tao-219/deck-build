# Minto Enforcement — Smoke Test Results

Proves the 8 Minto criteria (`_minto/minto-rubric.md`) are **enforced** end-to-end: each is
*generated as data* in the plan schema and *validated* by an executable check (deterministic
script and/or whole-deck LLM-judge), with the deck-level criteria *gated* into the deck-qa loop.

Run:
```bash
python tests/smoke_test.py                 # Part 1 — deterministic (16 checks)
# Part 2 — judged: deck-qa Layer 5 agents run the packets in tests/_artifacts/ (see below)
```

Fixtures (`tests/fixtures/`, synthetic / brand-neutral, no client data):
- `good-plan.json` — coherent storyline, MECE key_line, action titles, SCQA + apex + per-slide linkage.
- `bad-plan.json` — topic governing thought, no SCQA, overlapping pillars + "Other" catch-all, topic titles, orphan slide, jumbled sequence.
- `flat-plan.json` — the original pre-P1 flat schema (no scqa / key_line / supports_pillar) — for graceful-degradation.
- `make_fixture_deck.py` — renders a plan to a neutral `.pptx` via the Path-B helpers (for the title linter).

## Part 1 — Deterministic (`smoke_test.py`): **16 / 16 PASS** (exit 0)

| Check | Result |
|---|---|
| storyline: good PASSES (exit 0, ok) | PASS |
| storyline: good emits a valid judge packet (criteria 1,2,5) | PASS |
| storyline: bad FLAGGED (exit 1) | PASS |
| storyline: bad flags governing-thought (C1) + scqa-absent (C2) | PASS |
| storyline: flat degrades gracefully (exit 0, no crash) | PASS |
| storyline: flat still emits a packet | PASS |
| logic: good PASSES (exit 0, ok, evaluable) | PASS |
| logic: good emits a valid judge packet (criteria 6,7,8) | PASS |
| logic: bad FLAGGED (exit 1) | PASS |
| logic: bad flags MECE catch-all (C8) + orphan (C6) | PASS |
| logic: flat degrades gracefully (exit 0, not evaluable) | PASS |
| titles: fixture decks render via deck_helpers Path B | PASS |
| titles: good deck PASSES the mechanical linter (0 Major) | PASS |
| titles: bad deck FLAGGED (exit 1, topic-title Major) | PASS |
| titles: --semantic emits a valid judge packet (criteria 3,4) | PASS |
| titles: --semantic packet covers exactly the content titles | PASS |

## Part 2 — E2E + judged (whole-deck judge, run once via the Agent tool)

Four fresh `general-purpose` subagents ran the packet prompts emitted to `tests/_artifacts/`
(exactly as the deck-qa Layer 5 procedure spawns them). Verdicts:

| Judge run | Verdict | Evidence |
|---|---|---|
| GOOD · storyline (5a) | **pass: true** | "today's state → forcing event → recommendation → feasible → pays off… no non-sequiturs"; thesis at slide 4 (answer-first); opening arc S→C→A intact |
| GOOD · logic (5b) | **pass: true** | MECE pass (why-now / feasibility / payoff, no overlap, no catch-all); vertical pass; horizontal pass (time order honored) |
| BAD · storyline (5a) | **pass: false** | topic governing thought "Tool cost overview" (no destination); "Overview/Background" deletable scene-setters; no SCQA arc; titles never reach a thesis |
| BAD · logic (5b) | **pass: false** | P1/P2 overlap (both "cost"); P3 "Other considerations and risks" catch-all; type-mix; P3 missing order_basis; off-question children |

**Conclusion:** the whole-deck judge PASSES the good deck and FLAGS the bad fixture on both
layers — the storyline + logic disciplines are enforced, not merely documented.

## The 8 criteria → enforcing validator → result

| # | Criterion | Enforcing validator (layer) | Enforcement level | good | bad |
|---|---|---|---|---|---|
| 1 | Governing thought | `storyline_check.py` deterministic screen + storyline judge support test (5a) | Validated + Gated | PASS | FLAG (no-verb, topic) |
| 2 | SCQA intro | `storyline_check.py` deterministic (answer≈GT / scqa-absent) + opening-arc judge (5a) | Validated + Gated | PASS | FLAG (scqa-absent) |
| 3 | Answer-first / top-down | storyline judge thesis-position (5a) + `action_title_lint --semantic` slide-level (2b) | Validated + Gated | PASS | FLAG (no thesis; topic titles) |
| 4 | Action titles | `action_title_lint.py` deterministic mechanics (2) + `--semantic` substance judge (2b) | Validated + Gated | PASS | FLAG (topic-title Major) |
| 5 | Storyline read-through | `storyline_check.py` whole-deck judge (5a) | Validated + Gated | PASS | FLAG (incoherent sequence) |
| 6 | Vertical logic | `logic_structure_check.py` deterministic (orphan / childless) + judge off-question (5b) | Validated + Gated | PASS | FLAG (orphan slide) |
| 7 | Horizontal logic | `logic_structure_check.py` deterministic (logic_type/order_basis, render order, archetype↔logic) + judge type-consistency (5b) | Validated + Gated | PASS | FLAG (type-mix, order) |
| 8 | MECE | `logic_structure_check.py` deterministic catch-all + judge overlap/gap (5b) | Validated + Gated | PASS | FLAG (catch-all + overlap) |

All 8 criteria reach **Validated** and the deck-level criteria (5–8, plus the judge halves of
1–3) are **Gated** into the deck-qa iteration loop (a High Layer-5 finding blocks delivery).

## Reproducing Part 2

`tests/smoke_test.py` writes the four judge packets to `tests/_artifacts/`. For each, spawn a
fresh `general-purpose` Agent: *"Read `<packet>.json`, take `judge_packet.prompt`, follow it
exactly against `judge_packet.data`, output only the verdict JSON."* Confirm good → `pass:true`,
bad → `pass:false`. This is the same flow the deck-qa Layer 5a/5b procedure runs on a live deck.
