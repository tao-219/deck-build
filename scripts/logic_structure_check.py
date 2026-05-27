#!/usr/bin/env python3
"""logic_structure_check.py — deterministic MECE / vertical / horizontal logic checks
+ whole-deck logic judge packet for deck-qa Layer 5b.

Encodes the Pyramid Principle's logic tests (`pyramid-principle.md:56-70`) as
executable checks over the P1 argument tree in `deck-plan.json`:

  Criterion 8 — MECE             : flag catch-all tokens ("other/misc/etc") in any
                                    grouping; judge handles overlap / gap.
  Criterion 6 — Vertical logic   : every content slide has a resolvable supports_pillar;
                                    every pillar has ≥ 1 child; no orphans.
  Criterion 7 — Horizontal logic : every pillar declares logic_type ∈ {deductive,
                                    inductive} and order_basis ∈ {time, structure,
                                    degree}; render order == plan order; same-level
                                    type-consistency judged by the LLM.
  + Archetype ↔ logic fit (P6)   : a slide's archetype implies a logic shape; flag a
                                    parallel-comparison archetype used for a deductive/
                                    sequential point (and vice-versa).

NO API calls here. Deterministic checks + a judge packet (JSON + ready-to-run
prompt); the LLM-judge runs from the deck-qa Layer 5b procedure via the Agent tool.

**Graceful degradation:** an older flat plan with no `deck_meta.key_line` is not
representable as a pyramid — the script reports `degraded`, skips the pillar checks,
and exits 0 (never crashes). Only the catch-all-on-titles and render-order checks
(the ones that don't need a key_line) still run.

Usage:
  python logic_structure_check.py <deck-plan.json> [--manifest audit_manifest.json]
                                  [--out <dir>] [--quiet]

Exit code: 0 if no High deterministic findings (or degraded), 1 otherwise.

Importable: `from logic_structure_check import build_packet, ARCHETYPE_LOGIC`.
"""

import argparse
import json
import sys
from pathlib import Path

# Share tokenization + archetype classification with action_title_lint — one copy.
sys.path.insert(0, str(Path(__file__).parent))
from action_title_lint import tokenize, STRUCTURAL_ARCHETYPES  # noqa: E402


# Catch-all signals — a grouping that uses these is not Collectively Exhaustive by
# structure; it parks unstructured items in a refuge (rubric Criterion 8).
CATCHALL_TOKENS = {
    "other", "others", "misc", "miscellaneous", "etc", "various",
    "sundry", "assorted", "etcetera",
}
CATCHALL_PHRASES = [
    "and more", "among others", "amongst others", "and so on",
    "and others", "and the rest", "and such",
]

VALID_LOGIC_TYPES = {"deductive", "inductive"}
VALID_ORDER_BASES = {"time", "structure", "degree"}

# A content slide that PRESENTS the governing thought (the pyramid apex / the SCQA
# "Answer" slide) sits ABOVE the pillars, not under one. It declares supports_pillar
# = APEX_MARKER so the orphan check exempts it without counting it as a pillar child.
APEX_MARKER = "governing_thought"

# Archetype → the logic shape it implies (P6). None = single-claim / positioning slide
# with no same-level grouping, so no consistency constraint. Sequential/causal shapes
# are deductive; parallel/comparison shapes are inductive.
ARCHETYPE_LOGIC = {
    # deductive / sequential
    "before-after-process":              "deductive",
    "stage-flow-with-signoff":           "deductive",
    "process-2-phase":                   "deductive",
    "process-3-phase":                   "deductive",
    "process-4-phase":                   "deductive",
    "process-5-phase":                   "deductive",
    "timeline-horizontal":               "deductive",
    # inductive / parallel
    "spotlight-comparison-columns":      "inductive",
    "comparison-2":                      "inductive",
    "comparison-3":                      "inductive",
    "comparison-4":                      "inductive",
    "comparison-5":                      "inductive",
    "comparison-tables":                 "inductive",
    "cards-2":                           "inductive",
    "cards-3":                           "inductive",
    "cards-4":                           "inductive",
    "cards-5":                           "inductive",
    "tiered-region-coverage-table":      "inductive",
    "mapping-table-with-status":         "inductive",
    "two-col-overview-with-subcallout":  "inductive",
    # single-claim / positioning — no same-level grouping → no constraint
    "recommendation-hero":               None,
    "hero-statement":                    None,
    "data-contrast":                     None,
    "quote-hero":                        None,
    "risk-heatmap":                      None,
    "framework":                         None,
    "pyramid":                           None,
    "content-with-image":                None,
    "bullets":                           None,
}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def is_content_slide(archetype: str) -> bool:
    return archetype not in STRUCTURAL_ARCHETYPES


def catchall_hits(text: str) -> list:
    """Return catch-all tokens/phrases present in text (whole-token + phrase match)."""
    if not text:
        return []
    hits = []
    toks = set(tokenize(text))
    for t in sorted(toks & CATCHALL_TOKENS):
        hits.append(t)
    low = text.lower()
    for ph in CATCHALL_PHRASES:
        if ph in low:
            hits.append(ph)
    return hits


def _list_of_str(v) -> list:
    return [x for x in v if isinstance(x, str)] if isinstance(v, list) else []


def collect_grouping_strings(plan: dict) -> list:
    """Gather strings that represent GROUPINGS subject to MECE: pillar claims, and
    on-slide list-of-string content fields (agenda topics, columns, factor lists).
    Returns [(where, text)] for targeted catch-all scanning.
    """
    out = []
    for p in plan.get("deck_meta", {}).get("key_line", []) or []:
        if p.get("claim"):
            out.append((f"pillar {p.get('id')}", p["claim"]))
    for s in plan.get("slides", []):
        n = s.get("slide_number")
        content = s.get("content") or {}
        if not isinstance(content, dict):
            continue
        for key, val in content.items():
            for item in _list_of_str(val):
                out.append((f"slide {n} content.{key}", item))
            # one level deeper for dict-of-list (e.g. left.objectives)
            if isinstance(val, dict):
                for k2, v2 in val.items():
                    for item in _list_of_str(v2):
                        out.append((f"slide {n} content.{key}.{k2}", item))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Deterministic checks
# ─────────────────────────────────────────────────────────────────────────────

def check_mece(plan: dict) -> list:
    """Criterion 8 — deterministic catch-all screen over groupings."""
    findings = []
    for where, text in collect_grouping_strings(plan):
        hits = catchall_hits(text)
        if hits:
            findings.append({
                "severity": "High", "criterion": 8, "code": "mece-catchall",
                "where": where,
                "description": f'Catch-all token {hits} in {where}: "{text[:80]}". A '
                               f'"{hits[0]}" bucket is not MECE — name the real categories '
                               f'or scope the exclusion explicitly.',
            })
    return findings


def check_vertical(plan: dict) -> list:
    """Criterion 6 — every content slide maps to a pillar; every pillar has ≥1 child."""
    findings = []
    pillars = plan.get("deck_meta", {}).get("key_line", []) or []
    pillar_ids = {p.get("id") for p in pillars if p.get("id")}
    seen_children = set()

    for s in plan.get("slides", []):
        archetype = s.get("archetype", "default")
        if not is_content_slide(archetype):
            continue
        n = s.get("slide_number")
        sp = s.get("supports_pillar")
        if sp is None or sp == "":
            findings.append({
                "severity": "High", "criterion": 6, "code": "orphan-slide",
                "slide": n,
                "description": f"Content slide {n} ({archetype}) has no supports_pillar — "
                               f"orphan. Every content slide must sit under a key-line pillar.",
            })
        elif sp == APEX_MARKER:
            continue  # apex slide — presents the governing thought, not pillar evidence
        elif sp not in pillar_ids:
            findings.append({
                "severity": "High", "criterion": 6, "code": "dangling-pillar-ref",
                "slide": n,
                "description": f"Content slide {n} references supports_pillar='{sp}', which is "
                               f"not a declared key_line id ({sorted(pillar_ids)}).",
            })
        else:
            seen_children.add(sp)

    for pid in sorted(pillar_ids):
        if pid not in seen_children:
            findings.append({
                "severity": "High", "criterion": 6, "code": "childless-pillar",
                "pillar": pid,
                "description": f"Pillar '{pid}' has no child slides — a pillar with no "
                               f"supporting evidence is an empty branch. Add support or drop it.",
            })
    return findings


def check_horizontal(plan: dict) -> list:
    """Criterion 7 — each pillar declares a valid logic_type + order_basis."""
    findings = []
    for p in plan.get("deck_meta", {}).get("key_line", []) or []:
        pid = p.get("id")
        lt = p.get("logic_type")
        ob = p.get("order_basis")
        if lt not in VALID_LOGIC_TYPES:
            findings.append({
                "severity": "Medium", "criterion": 7, "code": "logic-type-missing-or-invalid",
                "pillar": pid,
                "description": f"Pillar '{pid}' logic_type={lt!r}; must be one of "
                               f"{sorted(VALID_LOGIC_TYPES)} (deductive = premise→conclusion; "
                               f"inductive = parallel items of one class).",
            })
        if ob not in VALID_ORDER_BASES:
            findings.append({
                "severity": "Medium", "criterion": 7, "code": "order-basis-missing-or-invalid",
                "pillar": pid,
                "description": f"Pillar '{pid}' order_basis={ob!r}; must be one of "
                               f"{sorted(VALID_ORDER_BASES)} (time / structure / degree).",
            })
    return findings


def check_render_order(plan: dict, manifest: dict | None) -> list:
    """Criterion 7 (integrity) — rendered slide order matches plan order."""
    if not manifest:
        return []
    plan_order = [s.get("slide_number") for s in plan.get("slides", [])
                  if s.get("slide_number") is not None]
    rendered_order = [m.get("slide_number") for m in manifest.get("slides", [])
                      if m.get("slide_number") is not None]
    if plan_order and rendered_order and plan_order != rendered_order:
        return [{
            "severity": "High", "criterion": 7, "code": "render-order-mismatch",
            "description": f"Rendered slide order {rendered_order} diverges from plan order "
                           f"{plan_order} — the deck does not present the argument in the "
                           f"planned sequence.",
        }]
    return []


def check_archetype_logic(plan: dict) -> list:
    """P6 — a slide's archetype implies a logic shape; flag contradiction with its
    pillar's (or its own override) logic_type."""
    findings = []
    pillar_logic = {p.get("id"): p.get("logic_type")
                    for p in plan.get("deck_meta", {}).get("key_line", []) or []}
    for s in plan.get("slides", []):
        archetype = s.get("archetype", "default")
        if not is_content_slide(archetype):
            continue
        implied = ARCHETYPE_LOGIC.get(archetype)
        if implied is None:  # no constraint for single-claim/positioning archetypes
            continue
        resolved = s.get("logic_type") or pillar_logic.get(s.get("supports_pillar"))
        if resolved in VALID_LOGIC_TYPES and resolved != implied:
            findings.append({
                "severity": "Medium", "criterion": 7, "code": "archetype-logic-mismatch",
                "slide": s.get("slide_number"),
                "description": f"Slide {s.get('slide_number')} uses '{archetype}' (implies "
                               f"{implied} / {'sequential' if implied=='deductive' else 'parallel'}) "
                               f"but its logic_type resolves to '{resolved}'. Match the visual to "
                               f"the argument shape, or re-tag the logic_type.",
            })
    return findings


# ─────────────────────────────────────────────────────────────────────────────
# Judge packet
# ─────────────────────────────────────────────────────────────────────────────

def build_pillar_tree(plan: dict) -> list:
    """Pillars with their child slides, for the judge packet."""
    children_by_pillar = {}
    for s in plan.get("slides", []):
        if not is_content_slide(s.get("archetype", "default")):
            continue
        sp = s.get("supports_pillar")
        if sp:
            children_by_pillar.setdefault(sp, []).append({
                "slide_number": s.get("slide_number"),
                "title": (s.get("title_bold") or ""),
                "answers_question": s.get("answers_question"),
            })
    tree = []
    for p in plan.get("deck_meta", {}).get("key_line", []) or []:
        tree.append({
            "id": p.get("id"),
            "claim": p.get("claim"),
            "logic_type": p.get("logic_type"),
            "order_basis": p.get("order_basis"),
            "children": children_by_pillar.get(p.get("id"), []),
        })
    return tree


def build_judge_prompt(gt: str, tree: list) -> str:
    blocks = []
    for p in tree:
        kids = "\n".join(
            f'      - slide {c["slide_number"]}: "{c["title"]}"'
            f'{" [answers: " + c["answers_question"] + "]" if c.get("answers_question") else ""}'
            for c in p["children"]) or "      (no child slides)"
        blocks.append(
            f'  {p["id"]} [{p.get("logic_type")}/{p.get("order_basis")}]: {p.get("claim")}\n{kids}')
    tree_str = "\n".join(blocks)
    pillar_claims = "; ".join(f'{p["id"]}: {p.get("claim")}' for p in tree)

    return f"""You are a strict Minto Pyramid reviewer auditing the deck's LOGIC STRUCTURE \
across all slides (whole-deck — not per slide). Judge the argument tree below.

Governing thought: "{gt}"

Argument tree (pillar [logic_type/order_basis]: claim → child slides):
{tree_str}

Judge three criteria:
  C8 — MECE: Over the pillar set [{pillar_claims}] — do any two pillars OVERLAP in scope? \
Is anything MATERIAL missing (a gap not explicitly scoped out)? Is any pillar a catch-all? \
Fail on overlap, unstated gap, or catch-all.
  C6 — Vertical logic: For EACH pillar, do its child slides answer the question that pillar \
raises (Why? / How? / How do we know?) — and ONLY that question? Flag a child parked under \
the wrong pillar, or one answering a question its pillar didn't raise.
  C7 — Horizontal logic: Are the pillars the SAME KIND of thing (all causes, OR all steps, \
OR all options, OR all components — not a mix)? Is each pillar's declared order_basis \
(time / structure / degree) actually honored by its children's order?

Output JSON only, no prose:
{{
  "pass": true|false,
  "criterion_8_mece":       {{"pass": true|false, "overlaps": ["..."], "gaps": ["..."], "catchalls": ["..."]}},
  "criterion_6_vertical":   {{"pass": true|false, "misplaced_or_offquestion": ["pillar X / slide N: why"]}},
  "criterion_7_horizontal": {{"pass": true|false, "type_mix": ["..."], "order_violations": ["..."]}},
  "findings": [
    {{"severity": "High|Medium|Low", "criterion": 6|7|8, "description": "..."}}
  ]
}}
"pass" is false if ANY criterion fails. Flag only REAL issues; an empty findings list \
beats a fabricated one."""


# ─────────────────────────────────────────────────────────────────────────────
# Orchestration
# ─────────────────────────────────────────────────────────────────────────────

def build_packet(plan: dict, manifest: dict | None = None) -> dict:
    deck_meta = plan.get("deck_meta", {})
    gt = (deck_meta.get("governing_thought") or "").strip()
    key_line = deck_meta.get("key_line")

    deterministic = []
    degraded = []

    if not key_line:
        # Old flat plan: pyramid not representable. Skip pillar-dependent checks.
        degraded.append("deck_meta.key_line absent (flat plan): MECE / vertical / horizontal / "
                        "archetype-logic checks skipped — logic structure not evaluable")
        # render-order is plan-vs-manifest integrity and still meaningful
        deterministic += check_render_order(plan, manifest)
        ok = not any(f["severity"] == "High" for f in deterministic)
        return {
            "script": "logic_structure_check",
            "ok": ok,
            "degraded": degraded,
            "deterministic_findings": deterministic,
            "judge_packet": {
                "mode": "whole-deck",
                "criteria": [6, 7, 8],
                "evaluable": False,
                "data": {"governing_thought": gt, "key_line": None, "pillar_tree": []},
                "prompt": None,
            },
        }

    deterministic += check_mece(plan)
    deterministic += check_vertical(plan)
    deterministic += check_horizontal(plan)
    deterministic += check_render_order(plan, manifest)
    deterministic += check_archetype_logic(plan)

    tree = build_pillar_tree(plan)
    ok = not any(f["severity"] == "High" for f in deterministic)

    return {
        "script": "logic_structure_check",
        "ok": ok,
        "degraded": degraded,
        "deterministic_findings": deterministic,
        "judge_packet": {
            "mode": "whole-deck",
            "criteria": [6, 7, 8],
            "evaluable": True,
            "data": {"governing_thought": gt, "key_line": key_line, "pillar_tree": tree},
            "prompt": build_judge_prompt(gt, tree),
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("plan", help="Path to deck-plan.json")
    parser.add_argument("--manifest", help="Optional audit_manifest.json (verifies render order)")
    parser.add_argument("--out", help="Optional dir to write logic_packet.json")
    parser.add_argument("--quiet", action="store_true", help="Only print JSON, not human summary")
    args = parser.parse_args()

    plan_path = Path(args.plan)
    if not plan_path.exists():
        print(f"ERROR: {plan_path} does not exist", file=sys.stderr)
        sys.exit(2)
    with open(plan_path) as f:
        plan = json.load(f)

    manifest = None
    if args.manifest:
        mp = Path(args.manifest)
        if mp.exists():
            with open(mp) as f:
                manifest = json.load(f)

    result = build_packet(plan, manifest)
    result["plan"] = str(plan_path)
    print(json.dumps(result, indent=2))

    if args.out:
        out_dir = Path(args.out)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "logic_packet.json").write_text(json.dumps(result, indent=2))

    if not args.quiet:
        df = result["deterministic_findings"]
        high = sum(1 for f in df if f["severity"] == "High")
        med = sum(1 for f in df if f["severity"] == "Medium")
        state = "DEGRADED (flat plan)" if result["degraded"] and not result["judge_packet"]["evaluable"] else \
                ("PASS" if result["ok"] else "FAIL")
        print(f"\n--- logic_structure_check: {state}; {len(df)} deterministic finding(s) "
              f"({high} High, {med} Medium) ---", file=sys.stderr)
        for d in result["degraded"]:
            print(f"    degraded: {d}", file=sys.stderr)

    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
