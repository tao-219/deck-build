# deck-build

Consultancy-grade .pptx generation from a reference deck via Claude Code / Anthropic Agent SDK.

Drop in (a) meeting notes / objectives / content instructions and (b) a reference .pptx whose theme, colors, fonts, and layout vocabulary should be inherited. The plugin produces a full deck or specific slides. Output is fully editable .pptx (not flattened images), theme-faithful to the reference deck.

## Status

Alpha (v0.1.0). First reference template: Manulife project (Deloitte kickoff deck).

## Prerequisite

This plugin **delegates file-level .pptx editing to Anthropic's `document-skills:pptx` skill**. Install it first:

```
/plugin marketplace add anthropics/skills
/plugin install document-skills@anthropic-agent-skills
```

Without `document-skills` installed, the `deck-render` skill will fail.

## Installation

The plugin can be used in two ways:

### Path A — Direct script imports (no install needed)

The render helpers live as an importable Python module at `scripts/deck_helpers.py`. Any Python script in any directory can:

```python
import sys
sys.path.insert(0, "/Users/taoli/projects/deck-build/scripts")
from deck_helpers import (
    PRIMARY, two_tone_title, numbered_agenda_block, sub_callout_grid,
    spotlight_callout, target_icon, network_icon, globe_icon,
    strip_shapes, replace_title, footer_clearance,
)
```

QA the output:
```bash
python /Users/taoli/projects/deck-build/scripts/archetype_compliance.py <deck.pptx> [--plan plan.json]
```

This path works from any Claude Code session without plugin install. **Use this path when iterating on a specific deck in another project's working directory.**

### Path B — Slash command install (for `/deck-build`, `/deck-slide`, etc.)

Adds the user-level slash commands. From Claude Code:

```
/plugin marketplace add /Users/taoli/projects/deck-build
/plugin install deck-build@deck-build
```

(The marketplace name and plugin name happen to be the same since this is a single-plugin local marketplace.)

Verify install: `/plugin list` should show `deck-build@deck-build` enabled at user scope.

Or for ephemeral dev use without permanent install: launch Claude Code with `--plugin-dir /Users/taoli/projects/deck-build`.

## Components

### Skills

- **deck-orchestrator** — main entry point. Pyramid Principle, action titles, archetype selection, multi-skill flow with explicit per-phase procedure.
- **deck-extract-dna** — profile a reference deck → JSON inventory of theme + layouts + visual conventions.
- **deck-render** — two paths: (a) layout delegation to `document-skills:pptx`, (b) raw construction via importable helper recipes for archetypes the layouts can't carry.
- **deck-qa** — five-layer audit: vision LLM, action-title linter (+ optional semantic so-what judge), brand-token validator, archetype-compliance check (footer-clearance, container-clipping, two-tone title, verb test), and a whole-deck **storyline & logic** judge (Minto Pyramid: governing thought, SCQA, storyline read-through, MECE, vertical/horizontal logic).
- **deck-charts** — specialist consulting charts (Waterfall, Marimekko, Harvey Balls).

### Scripts (directly invokable, no plugin install required)

- `scripts/deck_helpers.py` — importable render-helper module: archetype recipes (`two_tone_title`, `numbered_agenda_block`, `spotlight_callout`, `sub_callout_grid`), 7 simple icons, `strip_shapes` discipline, primitives.
- `scripts/archetype_compliance.py` — runnable QA: `python archetype_compliance.py <deck.pptx> [--plan plan.json]`. Returns JSON. Exit code 0 = clean, 1 = High-severity issues.
- `scripts/storyline_check.py` — Minto **storyline** prep (deck-qa Layer 5a): deterministic governing-thought screen + a whole-deck judge packet (criteria 1, 2, 5). `python storyline_check.py <deck-plan.json> [--manifest audit_manifest.json]`. Exit 0 = governing thought is a so-what; 1 = not.
- `scripts/logic_structure_check.py` — Minto **logic** prep (deck-qa Layer 5b): deterministic MECE catch-all screen + vertical (orphans / childless pillars) + horizontal (`logic_type` / `order_basis`) + archetype↔logic fit, plus a whole-deck judge packet (criteria 6, 7, 8). `python logic_structure_check.py <deck-plan.json>`. Degrades gracefully (exit 0) on an old flat plan with no `key_line`.
- `skills/deck-extract-dna/scripts/profile_template.py` — `python profile_template.py <reference.pptx> <output_dir>` → DNA JSONs.

### Archetype recipes

Seven recipe archetypes with full anatomy/color/typography/icon specs in `skills/deck-orchestrator/references/design-archetypes.md`:

1. `stage-flow-with-signoff` — multi-stage program plan with downstream gate
2. `two-col-overview-with-subcallout` — agenda / session overview with desired-outcome panel
3. `spotlight-comparison-columns` — N-column comparison with one focus column
4. `tiered-region-coverage-table` — N×M coverage table with tier badges
5. `recommendation-hero` — single recommendation + supporting evidence cards
6. `before-after-process` — current vs proposed flow with delta callout
7. `risk-heatmap` — 2×2 plot of items by likelihood × impact

### Commands

- `/deck-build` — generate a full deck from inputs + reference
- `/deck-slide` — insert one or more slides into an existing deck
- `/deck-extract-dna` — profile a reference deck (one-time per template)

## Architecture

See `docs/research/07_synthesis_and_plan.md` (in `~/projects/aegis/outputs/research/pptx-workflow/`) for the full design rationale, including:
- Why we delegate to Anthropic's skill rather than reimplement OOXML manipulation
- Why we use raw XML (not python-pptx) for writing
- Three-layer indirection: claim_type → slide_archetype → layout_capability → layout_index
- Adversarial vision-QA with fresh subagent

## License

MIT (this plugin's original code). Note: Anthropic's `document-skills:pptx` is source-available with a restrictive license — we delegate to it but do not copy from it.
