---
name: deck-qa
description: This skill should be used when the user asks to QA, audit, check, or validate a rendered .pptx deck — including "audit the deck", "check the slides for defects", "validate the deck output", "run QA on the deck", "verify archetype compliance", "check the storyline / logic / Minto compliance". Also runs automatically after deck-render. Performs a five-layer audit: vision LLM defect scan, action-title linter (with optional semantic so-what judge), brand-token validator, archetype-compliance check, and a whole-deck storyline & logic judge (Minto Pyramid: governing thought, SCQA, storyline read-through, vertical/horizontal logic, MECE). Returns a structured defect report; surfaces corrective edits when possible.
---

# Deck QA

Adversarial QA. Assume problems exist. The code-writer has confirmation bias; QA must run in a fresh context.

## When to use

- Always after deck-render completes.
- Standalone for auditing an externally-produced .pptx against a known DNA + archetype plan.
- Re-run after any slide-level fix (don't trust that the fix didn't break something else).

## Inputs

- `inputs/deck.pptx` — the rendered output to audit.
- `inputs/reference-dna.json` — the reference DNA (for color/font compliance).
- `inputs/deck-plan.json` — the structured spec (for action-title verification AND archetype compliance).

## Outputs

- `outputs/qa-report.md` — defect inventory grouped by severity and slide.
- `outputs/corrective-edits.json` — proposed fixes (renderer-consumable).

## Five-layer audit

Layers 1–4 are **per-slide / per-shape** checks (a slide can pass them in isolation). Layer 5 is the **whole-deck** judge — the only layer that can see the argument across slides. Visual quality is enforced by Layers 1–4; *logical* quality (the Minto Pyramid) is enforced by Layer 5.

### Layer 1: Vision-LLM adversarial defect scan

**Procedure (runnable from inside Claude Code):**

1. **Render slides to images.** Run the render script:
   ```bash
   python ${CLAUDE_PLUGIN_ROOT}/scripts/vision_audit_render.py <deck.pptx> <output_dir> [--plan plan.json] [--dpi 150]
   ```
   Produces `<output_dir>/slide-NN.jpg` (one per slide) plus `<output_dir>/audit_manifest.json` listing each image with its slide number, claimed title, and declared archetype.

2. **Read the manifest** to get the per-slide image paths + titles + archetypes.

3. **For each slide, spawn a fresh `Agent` subagent** (subagent_type: `general-purpose` or `Explore`) with the prompt template below. Pass the image path and slide context. Each subagent gets ONE image — fresh context per slide ensures unbiased review.

4. **Parse each subagent response** as JSON. Aggregate into a deck-wide defect report.

5. **Surface High-severity defects** for iteration; capture Medium/Low as known issues.

**Why fresh subagents per slide:** the calling Claude has implicit confirmation bias from having generated the deck. Fresh context with no awareness of how the slide was produced means the reviewer sees only what's there, not what was intended.

**Prompt template + aggregation pattern + 12-item defect checklist:** see [`references/vision-audit-prompt.md`](references/vision-audit-prompt.md). Lift verbatim and inject the relevant archetype recipe from `${CLAUDE_PLUGIN_ROOT}/skills/deck-orchestrator/references/design-archetypes.md`. Recipe injection is load-bearing — without it, auditors produce ~50% false positives.

### Layer 2: Action title linter

Script: `${CLAUDE_PLUGIN_ROOT}/scripts/action_title_lint.py`

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/action_title_lint.py <deck.pptx> [--quiet]
```

Returns JSON to stdout with per-slide title issues. Exit code 0 = no Major issues, 1 = Major issues present.

Rules applied (per `deck-orchestrator/references/action-title-pattern.md`):
- **Word count ≤ 15** (Major if exceeded)
- **Verb present** — heuristic: token in `KNOWN_VERBS` OR ends in -s/-ed/-ing/-es with length >4 (Major if no verb)
- **Not a topic title** — heuristic: first 3 tokens contain `TOPIC_HEADWORDS` AND no verb (Major)
- **No trailing period** (Minor)
- **No banned weasel words** (Minor) — leverage, harness, synergy, robust, best-in-class, holistic, strategic, etc.
- **Active voice** — heuristic: looks for `was/were/is/are <verb-ed> by` (Minor)
- **Two-tone shape** — titles with >8 words must have mixed bold/normal runs (Minor)

The verb test is a heuristic, not a POS tagger — it has false negatives on rare verbs and false positives on -ing nouns ("Rating", "Modeling"). Use as a screen, not a verdict.

Importable: other QA scripts can `from action_title_lint import extract_title, has_verb, has_two_tone, lint_title` to share the title-extraction logic — `archetype_compliance.py` does this.

**Layer 2b — semantic so-what judge (substance tier).** The rules above are string heuristics: they test verb + length, not *assertion + so-what*. A verb-bearing non-assertion ("The team will discuss next steps") or a vacuous claim ("Results show results") passes the cheap screen clean — i.e. Layer 2 covers `minto-rubric.md` Criterion 4's **mechanics**, not its **substance**. Close that gap:

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/action_title_lint.py <deck.pptx> --plan <plan.json> --semantic
```

The deterministic screen still runs and still gates (exit code unchanged). With `--semantic`, the output carries a `semantic_judge_packet` (per-title JSON + a ready-to-run prompt). Read `semantic_judge_packet.prompt` and spawn ONE fresh `Agent` (`subagent_type: general-purpose`) with it — the judge scores each content title on assertion-vs-label, presence-of-so-what, and the operative number on quantitative slides. Gate any title flagged `label` / `vacuous` / `missing-number` (a topic-label-that-merely-carries-a-verb is a **High** action-title violation the heuristic cannot catch). `--plan` is optional but lets the packet skip structural slides (cover/divider/closing) and mark quantitative archetypes.

### Layer 3: Brand-token validator

Script: `${CLAUDE_PLUGIN_ROOT}/scripts/brand_token_check.py` (walks all `<a:srgbClr val="...">` and `<a:latin typeface="...">` in the output XML). **Status: not yet implemented.** When built: walks output XML, checks colors against reference DNA palette and fonts against font scheme.

For each:
- Color ∈ reference DNA palette? (Allow ±5 RGB tolerance for anti-aliasing artifacts.)
- Font ∈ reference DNA font scheme?

Report violations with the slide and shape name where each violation occurs.

### Layer 4: Archetype compliance check

Script: `${CLAUDE_PLUGIN_ROOT}/scripts/archetype_compliance.py`

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/archetype_compliance.py <deck.pptx> [--plan plan.json] [--quiet]
```

Returns JSON. Exit code 0 = no High issues, 1 = High issues present.

Implemented checks (deterministic, no LLM call needed):
- **Footer-clearance overrun** — any non-footer shape extending past the archetype's clearance limit (defined in `deck_helpers.FOOTER_CLEARANCE` and `design-archetypes.md`).
- **Container clipping** — child shapes that extend below their parent dashed-bordered container (false positives filtered: tables, groups, placeholders excluded as containers).
- **Two-tone title** — titles with >8 words and only single-weight runs.
- **Verb test** — title with no verb-like token (heuristic).

For each slide, look up the declared `archetype` in `deck-plan.json` and verify the rendered output meets the archetype's contract from `design-archetypes.md`:

| Archetype | Required components | What to check |
|---|---|---|
| `stage-flow-with-signoff` | Action title (two-tone), N stage boxes, M workshop boxes, sign-off panel, dashed connector to sign-off | Stage row count matches plan; sign-off panel uses cream + accent border; connector is dashed and points to sign-off |
| `two-col-overview-with-subcallout` | Action title (two-tone), section headers above both columns, numbered agenda blocks (right), sub-callout grid below | Sub-callout grid exists with ≥2 items; each item has an icon + label + caption; agenda is numbered blocks (NOT a time-boxed table); section headers are centered above columns |
| `spotlight-comparison-columns` | Action title (two-tone), focus column (brand color), context columns (grey), focus marker icon + label above focus column, context label above context columns, scope qualifiers in column headers | Focus column uses primary brand color; context columns are grey (not three-state); focus marker icon present; scope qualifiers present in parens |
| `tiered-region-coverage-table` | Action title (two-tone), legend strip above table, table with header row + tier badges in cells, optional sub-block | Legend present; tier badges paired with shape (not color-only); body text doesn't restate row counts (interpretive only) |

Report archetype violations as **High severity** — these are contract breaches, not cosmetic defects.

### Layer 5: Storyline & logic (whole-deck judge)

The deck-level Minto criteria — **storyline read-through (5), vertical logic (6), horizontal logic (7), MECE (8)**, plus the support/opening-arc halves of **governing thought (1)** and **SCQA (2)** — are intrinsically whole-deck. Layer 5 is the architectural **opposite of Layer 1**: instead of a fresh subagent per slide (blind to sequence by design — see line 41), it runs **one judge that holds the entire title sequence and argument tree at once**. A per-slide reviewer structurally *cannot* judge a storyline (`minto-rubric.md` Criterion 5).

Two deterministic prep scripts emit **judge packets** (structured JSON + a ready-to-run prompt); the judge runs from here via the `Agent` tool — no API call lives in the scripts (same split as `vision_audit_render.py` + Layer 1). Both scripts **degrade gracefully** on an older flat plan (warn + skip the affected check; never crash), so Layer 5 is safe to run on any plan.

**Layer 5a — Storyline & governing thought** (criteria 1, 2, 5):

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/storyline_check.py <deck-plan.json> [--manifest <audit_manifest.json>]
```

1. Exit code 1 = the deterministic governing-thought screen failed (field absent / > 25 words / no verb / topic-shaped) → **High**; gate it.
2. Parse stdout. Surface every `deterministic_findings` entry. Read `judge_packet.prompt`.
3. Spawn ONE fresh `Agent` (`subagent_type: general-purpose`) with that prompt **verbatim**. It must see ALL titles in order — do NOT loop per slide.
4. Parse the agent's JSON verdict. Any `pass:false`, non-sequitur, off-thesis/contradicting slide, or broken opening arc → gate per its severity (storyline breaks and contradictions are **High**).

**Layer 5b — Logic structure** (criteria 6, 7, 8 + archetype↔logic fit):

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/logic_structure_check.py <deck-plan.json> [--manifest <audit_manifest.json>]
```

1. Deterministic **High** issues → exit 1; gate them: a catch-all token ("other / misc / etc"), an orphan content slide with no `supports_pillar`, a childless pillar, or render order ≠ plan order. Missing `logic_type` / `order_basis` on a declared pillar, or an archetype whose logic shape contradicts its pillar's `logic_type`, are surfaced as **Medium**. On a flat plan with no `key_line`, the script reports `degraded:[...]` and exits 0 — record it as *not evaluated*, NOT as pass-with-coverage.
2. Read `judge_packet.prompt` and spawn ONE fresh whole-deck `Agent` as in 5a. It judges **MECE** (overlap / gap / catch-all over the pillar set), **vertical logic** (each pillar's children answer its question, and only that question; no orphans), and **horizontal logic** (same-level items are one type; the stated `order_basis` is actually honored).
3. Parse + gate as in 5a.

Both judges return the same verdict shape; aggregate their findings into the deck-wide report alongside Layers 1–4. Layer 5 needs only the `deck-plan.json` (titles + argument tree) — it does not require the rendered `.pptx`, though a `--manifest` lets 5a/5b reconcile against rendered titles and verify render order.

## Iteration loop

1. Run all five audit layers.
2. Triage: any High-severity (incl. all archetype violations AND Layer 5 storyline breaks / contradictions / orphans / catch-all groupings) blocks delivery; Medium are surfaced; Low are appended as known issues.
3. If High defects exist: regenerate affected slides via deck-render with the corrective edits. A Layer-5 break usually means fixing a **title or slide order** (or the plan's `key_line` / `supports_pillar`), not a visual — re-plan in deck-orchestrator, not just re-render.
4. Re-audit the regenerated slides on Layers 1–4. **Re-run Layer 5 in full** whenever any title, slide order, or pillar linkage changed — it is whole-deck, so a single-slide fix can still break (or repair) the storyline.
5. Stop when (a) no High-severity defects remain, OR (b) iteration count ≥ 3 (escalate to user).
6. Surface remaining Medium/Low defects in the final report.

## Key heuristics for catching common quality misses

These are the failure patterns that the v1 plugin shipped without catching — encode them as hard QA rules:

| Failure pattern | Catch rule |
|---|---|
| Title is a noun phrase ("Today's Agenda", "Current State of X") | Layer 2 verb test fails → High |
| Agenda is a time-boxed table for an exec audience | Layer 4 archetype check: if archetype = `two-col-overview-with-subcallout`, confirm right column is numbered blocks not a table → High |
| Spotlight slide uses three-state (CURRENT/LATER) coloring | Layer 4: if archetype = `spotlight-comparison-columns`, confirm context columns are grey (not "LATER" cream/orange) → High |
| Sub-callout grid missing on agenda slide | Layer 4 → High |
| Icons missing in archetypes that require them | Layer 4: walk shape inventory for ovals/connectors matching icon-helper signatures → if absent, High |
| Scope qualifiers missing where the column refers to a specific tool/scope | Layer 4: column header text for `spotlight-comparison-columns` must contain "(...)" pattern → Medium |
| Two-tone title rendered as single-weight bold | Layer 2 + XML walk: title runs all have bold=True → Medium |
| Source footer overlapping logo or page number | Layer 1 vision check + Layer 1 alignment check → Medium |
| Decorative line under title that wraps to two lines | Layer 1 vision check → Medium |
| Content shape extending past the footer-clearance budget (lowest non-footer shape below y=6.65–6.85 depending on recipe) | XML walk: for every non-footer shape, check `top + height` against archetype's footer-clearance limit from `design-archetypes.md` → High |
| Container/background shape clipped above its child shapes (child extends below container) | XML walk: for each "container" shape (named `Rectangle`/`Rounded Rectangle` with dashed border), verify all shapes overlapping its x-range are bounded by its y-extent → High |
