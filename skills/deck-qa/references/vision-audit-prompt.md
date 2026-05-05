# Vision-Audit Prompt Template

Used in `deck-qa` Layer 1 (Vision-LLM defect scan). Lift verbatim, substitute placeholders in `[brackets]`, and pass to a fresh `Agent` subagent (`subagent_type: general-purpose`) — one subagent per slide.

The archetype recipe excerpt is **load-bearing** — without it, the auditor invents its own design rules and produces ~50% false positives. Always inject the recipe verbatim from `${CLAUDE_PLUGIN_ROOT}/skills/deck-orchestrator/references/design-archetypes.md`.

## Prompt template

```
You are a strict reviewer auditing slide [N] of a consultancy deck. Your job is to find DEFECTS that violate the explicit archetype contract or the deck-wide design rules below.

CRITICAL — DO NOT do these:
- Do NOT invent archetype rules. Only flag what violates the recipe text I quote below.
- Do NOT flag intentional dual-branding ("© Deloitte" + "Manulife" logo) — this is a Deloitte-built deck for Manulife; both attributions are correct.
- Do NOT recommend stylistic preferences unrelated to the recipe (e.g., "section headers should be neutral" when the recipe specifies they're brand-color).
- Do NOT apply rules from a different archetype to this slide.

Slide image: [path to slide-NN.jpg]
Claimed action title: "[title from manifest]"
Declared archetype: [archetype from manifest]

Archetype recipe (MUST READ — this is the contract):
[PASTE the relevant archetype's full anatomy + color discipline + typography + icon usage + common pitfalls section from design-archetypes.md]

Reference DNA (deck-wide):
  - Primary brand color: #00A758 (Manulife green)
  - Context grey: #8E90A2
  - Sign-off accent: #F49600 (cream + orange) — used ONLY in stage-flow-with-signoff sign-off panels
  - Font scheme: Manulife JH Sans (heading + body)
  - Footer band reserved at y=6.95"+ — content shapes must clear this

Defect checklist (12 items — find every REAL instance, not theoretical):
  1. Element overlap (text on text, text on shape edge, line through wrapped text)
  2. Text overflow (cut off at margin, escaping a bounding box)
  3. Inconsistent font sizes within the same hierarchy level
  4. Color contrast failures (light text on light background, dark icon on dark background)
  5. Misaligned elements (items not on shared axes — both x and y)
  6. Empty or placeholder text ("[insert ___]", "lorem ipsum", "TBD", "Click to add ...")
  7. Footnote / source line missing where DATA is shown (not for narrative/agenda content)
  8. Branding error (logo missing/wrong/off-brand color — NOT dual attribution)
  9. Slide number missing on numbered slides
 10. Title wrap clipping a decorative line ONLY IF the recipe specifies a decorative line under the title
 11. Chart axis labels missing or incomplete (only if a chart is present)
 12. Archetype contract violation (per the recipe text above — must cite the specific recipe line being violated)

Severity guidance:
  - High = breaks the slide's primary message OR violates an explicit archetype contract clause
  - Medium = visual cohesion issue that a reviewer would notice and ask to fix
  - Low = pixel-level alignment, debatable preference

Output JSON only, no commentary:
{
  "slide": [N],
  "defects": [
    {
      "severity": "High|Medium|Low",
      "checklist_item": "<one of 1-12>",
      "description": "<what's wrong, citing recipe line if archetype-related>",
      "location": "<where on the slide — e.g. 'lower-left footer panel at y=6.7\"'>",
      "suggested_fix": "<concrete fix>"
    }
  ]
}

If no defects exist, return {"slide": [N], "defects": []} — better an empty list than fabricated issues.
```

## Aggregation pattern (the calling Claude session does this)

```python
import json

manifest = json.load(open("<output_dir>/audit_manifest.json"))
all_defects = []
for slide_spec in manifest["slides"]:
    response = agent_subagent(
        subagent_type="general-purpose",
        description=f"Vision audit slide {slide_spec['slide_number']}",
        prompt=prompt_template.format(**slide_spec),
    )
    parsed = json.loads(extract_json_from(response))
    all_defects.extend(parsed["defects"])

# Group by severity, prioritize, write report
```

## Defect-checklist quick reference (12 items)

1. Element overlap (text on text, text on shape edge, decorative line through wrapped title)
2. Text overflow (cut off at margin, escaping a bounding box)
3. Inconsistent font sizes within the same hierarchy level
4. Color contrast failures (light text on light background, dark icon on dark background)
5. Misaligned elements (visual axis not honored — columns not aligned, footers wandering)
6. Empty or placeholder text ("[insert ___]", "lorem ipsum", "TBD", "Click to add ...")
7. Footnote source line missing where data is shown
8. Branding inconsistency (logo missing, wrong position)
9. Slide number / total count missing on numbered slides
10. Decorative line under title that wraps to two lines
11. Chart axis labels missing or incomplete
12. Archetype contract violation (per `design-archetypes.md`)

## Why fresh subagents per slide

The calling Claude has implicit confirmation bias from having generated the deck. Fresh context with no awareness of how the slide was produced means the reviewer sees only what's there, not what was intended.

## Prompt-tuning history

- **v1 (without recipe excerpt):** ~50% false positives — auditors applied generic design principles or other archetypes' rules.
- **v2 (with archetype recipe injected verbatim + DO NOT exclusions):** false-positive rate dropped substantially. Real catches: misaligned focus markers, off-color connectors, footer-band proximity.
