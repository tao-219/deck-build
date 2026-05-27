#!/usr/bin/env python3
"""storyline_check.py — whole-deck Minto storyline + governing-thought prep.

Deterministic preparation for the deck-qa **Layer 5 — storyline & logic**
whole-deck judge. Reads a `deck-plan.json`, runs the mechanical part of
Criterion 1 (governing thought is a so-what assertion), assembles the ordered
title sequence, and emits a **judge packet** (structured JSON + a ready-to-run
prompt) covering the criteria that only a whole-deck reviewer can judge:

  Criterion 1 — governing thought   (deterministic screen here; support test in judge)
  Criterion 2 — SCQA opening arc     (deterministic answer≈governing-thought; arc in judge)
  Criterion 5 — storyline read-through (judge only — the Minto "Title test")

This is the architectural opposite of the per-slide vision audit: ONE reviewer
sees the ENTIRE title sequence at once. Per `minto-rubric.md` Criterion 5, a
per-slide reviewer structurally cannot judge the storyline.

NO API calls here. The script is deterministic and emits the packet; the
LLM-judge is run from the deck-qa Layer 5 procedure via the Agent tool (exactly
as `vision_audit_render.py` feeds Layer 1).

Usage:
  python storyline_check.py <deck-plan.json> [--manifest audit_manifest.json]
                            [--out <dir>] [--quiet]

Exit code: 0 if the deterministic governing-thought screen passes, 1 otherwise.
JSON to stdout (deterministic findings + judge_packet); human summary to stderr
unless --quiet.

Importable: `from storyline_check import build_title_sequence, screen_governing_thought,
build_packet` to reuse the prep in other tooling.
"""

import argparse
import json
import sys
from pathlib import Path

# Share title/verb logic + archetype classification with action_title_lint — never
# duplicate it. STRUCTURAL_ARCHETYPES = slides that carry no argument title.
sys.path.insert(0, str(Path(__file__).parent))
from action_title_lint import (  # noqa: E402
    has_verb, is_topic_title, tokenize, STRUCTURAL_ARCHETYPES,
)

GOVERNING_THOUGHT_MAX_WORDS = 25


# ─────────────────────────────────────────────────────────────────────────────
# Deterministic prep
# ─────────────────────────────────────────────────────────────────────────────

def slide_title(slide_spec: dict) -> str:
    """Reconstruct a slide's full title from the plan's two-tone fields."""
    bold = (slide_spec.get("title_bold") or "").strip()
    normal = (slide_spec.get("title_normal") or "").strip()
    if bold and normal:
        return f"{bold} – {normal}"
    return bold or normal


def build_title_sequence(plan: dict, manifest: dict | None = None) -> list[dict]:
    """Ordered list of {slide_number, title, archetype, structural, supports_pillar,
    answers_question}. Rendered titles from a manifest override plan titles when present.
    """
    rendered = {}
    if manifest:
        for m in manifest.get("slides", []):
            n = m.get("slide_number")
            if n is not None:
                rendered[int(n)] = (m.get("title") or "").strip()

    seq = []
    for s in plan.get("slides", []):
        n = s.get("slide_number") or s.get("index")
        archetype = s.get("archetype", "default")
        title = rendered.get(int(n)) if (n is not None and rendered.get(int(n))) else slide_title(s)
        seq.append({
            "slide_number": n,
            "title": title,
            "archetype": archetype,
            "structural": archetype in STRUCTURAL_ARCHETYPES,
            "supports_pillar": s.get("supports_pillar"),
            "answers_question": s.get("answers_question"),
        })
    return seq


def screen_governing_thought(gt: str) -> list[dict]:
    """Mechanical part of Criterion 1 — present, ≤25 words, verb-bearing assertion,
    not a bare topic. Returns a list of failure dicts (empty == pass)."""
    findings = []
    if not gt or not gt.strip():
        findings.append({
            "severity": "High", "criterion": 1, "code": "governing-thought-absent",
            "description": "deck_meta.governing_thought is empty or absent — the deck "
                           "has no stated main message.",
        })
        return findings  # nothing else testable
    wc = len(gt.split())
    if wc > GOVERNING_THOUGHT_MAX_WORDS:
        findings.append({
            "severity": "High", "criterion": 1, "code": "governing-thought-too-long",
            "description": f"Governing thought is {wc} words; a single assertion must be "
                           f"≤ {GOVERNING_THOUGHT_MAX_WORDS}. Tighten it to one claim.",
        })
    if not has_verb(gt):
        findings.append({
            "severity": "High", "criterion": 1, "code": "governing-thought-no-verb",
            "description": "No verb detected (heuristic) — the governing thought reads as a "
                           "label, not a so-what assertion. State a position.",
        })
    if is_topic_title(gt):
        findings.append({
            "severity": "High", "criterion": 1, "code": "governing-thought-is-topic",
            "description": "Governing thought opens like a topic headword (e.g. 'Overview', "
                           "'Findings') and lacks a verb — rewrite as an assertion.",
        })
    return findings


def _norm_tokens(text: str) -> set:
    stop = {"the", "a", "an", "to", "of", "and", "or", "in", "on", "for", "by",
            "is", "are", "be", "that", "this", "with", "as", "at", "it"}
    return {t for t in tokenize(text or "") if t and t not in stop}


def answer_matches_governing_thought(scqa: dict, gt: str) -> tuple[bool, float]:
    """Deterministic proxy for Criterion 2's 'answer ≈ governing_thought'.

    Token-overlap (Jaccard-ish) between the SCQA answer and the governing thought.
    Returns (passes, overlap_ratio). The judge confirms semantic equivalence; this
    just flags an answer that shares almost no content words with the thesis.
    """
    ans = (scqa or {}).get("answer") or ""
    a, g = _norm_tokens(ans), _norm_tokens(gt)
    if not a or not g:
        return False, 0.0
    overlap = len(a & g) / len(a | g)
    return overlap >= 0.30, round(overlap, 2)


# ─────────────────────────────────────────────────────────────────────────────
# Judge packet
# ─────────────────────────────────────────────────────────────────────────────

def _render_title_list(seq: list[dict]) -> str:
    lines = []
    for s in seq:
        tag = " [structural]" if s["structural"] else ""
        pillar = f" (pillar={s['supports_pillar']})" if s.get("supports_pillar") else ""
        lines.append(f'  {s["slide_number"]}. "{s["title"]}"{tag}{pillar}')
    return "\n".join(lines)


def build_judge_prompt(gt: str, scqa: dict | None, key_line: list | None,
                       seq: list[dict]) -> str:
    """Assemble the self-contained whole-deck storyline judge prompt."""
    has_scqa = bool(scqa and any((scqa.get(k) or "").strip()
                                 for k in ("situation", "complication", "answer")))
    scqa_block = ""
    if has_scqa:
        scqa_block = (
            "\nSCQA arc (stated in the plan):\n"
            f'  Situation:    {scqa.get("situation") or "(none)"}\n'
            f'  Complication: {scqa.get("complication") or "(none)"}\n'
            f'  Question:     {scqa.get("question") or "(implicit)"}\n'
            f'  Answer:       {scqa.get("answer") or "(none)"}\n'
        )
    pillar_block = ""
    if key_line:
        pillar_block = "\nKey-line pillars:\n" + "\n".join(
            f'  {p.get("id")}: {p.get("claim")}' for p in key_line) + "\n"

    crit2 = ""
    if has_scqa:
        crit2 = (
            "  C2 — SCQA opening arc: Do the first 1–3 CONTENT slides instantiate "
            "Situation → Complication → Question → Answer, in order, without skipping "
            "to detail? Is the Complication a genuine tension (not a restated Situation)? "
            "Does the Answer (the thesis) appear up front rather than being withheld?\n"
        )

    return f"""You are a strict Minto Pyramid reviewer auditing the WHOLE deck's storyline. \
You see EVERY slide title in order — this is the one review that cannot be done \
slide-by-slide. Judge the argument, not the visuals.

CRITICAL — DO NOT:
- Do NOT evaluate layout, color, fonts, or per-slide visual defects (other layers do that).
- Do NOT invent missing slides; judge only the sequence given.
- Prefer an empty findings list to a fabricated one — flag only REAL breaks.

Governing thought (the deck's single main message):
  "{gt}"
{scqa_block}{pillar_block}
Ordered slide titles (read top-to-bottom — this IS the Minto "Title test"):
{_render_title_list(seq)}

Judge these criteria over the sequence as a whole:
  C5 — Storyline read-through: Reading ONLY the titles in order, do they tell ONE \
coherent argument that arrives at the governing thought? List every non-sequitur, \
every gap/missing link between adjacent titles, and any title that does not advance \
the argument (a title you could delete with no loss). [structural] slides \
(cover / divider / closing) are scaffolding — do not count them as argument breaks.
  C1 — Support test: For each CONTENT title, does it support, build toward, or \
CONTRADICT the governing thought? Fail on ANY contradiction or if > 20% of content \
slides are off-thesis. Also state at which slide index the thesis/recommendation \
first appears, and whether that is early (answer-first) or buried in the back half.
{crit2}
Output JSON only, no prose:
{{
  "pass": true|false,
  "thesis_first_appears_at_slide": <int|null>,
  "criterion_5_storyline": {{"pass": true|false, "breaks": ["..."]}},
  "criterion_1_support":   {{"pass": true|false, "off_thesis_or_contradicting": ["slide N: why"]}},
  "criterion_2_opening_arc": {{"pass": true|false|null, "notes": "..."}},
  "findings": [
    {{"severity": "High|Medium|Low", "criterion": 1|2|5, "slide": <int|null>, "description": "..."}}
  ]
}}
"pass" is false if ANY criterion above fails. Return {{"findings": []}} content only \
when the deck genuinely passes — do not soften a real break."""


def build_packet(plan: dict, manifest: dict | None = None) -> dict:
    """Run the deterministic screen + assemble the whole-deck judge packet."""
    deck_meta = plan.get("deck_meta", {})
    gt = (deck_meta.get("governing_thought") or "").strip()
    scqa = deck_meta.get("scqa")
    key_line = deck_meta.get("key_line")

    seq = build_title_sequence(plan, manifest)

    deterministic = screen_governing_thought(gt)
    degraded = []

    # Criterion 2 deterministic proxy — only when SCQA fields exist.
    if scqa and any((scqa.get(k) or "").strip() for k in ("situation", "complication", "answer")):
        ok, overlap = answer_matches_governing_thought(scqa, gt)
        if not ok:
            deterministic.append({
                "severity": "Medium", "criterion": 2, "code": "answer-not-governing-thought",
                "description": f"SCQA answer shares little content with the governing thought "
                               f"(token overlap {overlap}); per Criterion 2 the answer must BE "
                               f"the thesis. Verify in the judge.",
            })
    else:
        # SCQA absent: if this is a pyramid plan (has key_line) the arc is genuinely
        # missing → flag; on an old flat plan, just degrade the opening-arc check.
        if key_line:
            deterministic.append({
                "severity": "High", "criterion": 2, "code": "scqa-absent",
                "description": "Plan declares a key_line pyramid but carries no deck_meta.scqa "
                               "opening arc — Criterion 2 (SCQA intro) is unmet.",
            })
        else:
            degraded.append("deck_meta.scqa absent (flat plan): opening-arc check deferred to judge")

    if not key_line:
        degraded.append("deck_meta.key_line absent (flat plan): pillar grouping omitted from packet")

    ok = not any(f["severity"] == "High" for f in deterministic)

    return {
        "script": "storyline_check",
        "ok": ok,
        "degraded": degraded,
        "deterministic_findings": deterministic,
        "judge_packet": {
            "mode": "whole-deck",
            "criteria": [1, 2, 5],
            "data": {
                "governing_thought": gt,
                "scqa": scqa,
                "key_line": key_line,
                "ordered_titles": seq,
            },
            "prompt": build_judge_prompt(gt, scqa, key_line, seq),
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("plan", help="Path to deck-plan.json")
    parser.add_argument("--manifest", help="Optional audit_manifest.json (rendered titles)")
    parser.add_argument("--out", help="Optional dir to write storyline_packet.json")
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
        (out_dir / "storyline_packet.json").write_text(json.dumps(result, indent=2))

    if not args.quiet:
        nf = len(result["deterministic_findings"])
        print(f"\n--- storyline_check: governing-thought screen "
              f"{'PASS' if result['ok'] else 'FAIL'}; {nf} deterministic finding(s); "
              f"judge packet covers criteria {result['judge_packet']['criteria']} "
              f"({len(result['judge_packet']['data']['ordered_titles'])} titles) ---",
              file=sys.stderr)
        if result["degraded"]:
            for d in result["degraded"]:
                print(f"    degraded: {d}", file=sys.stderr)

    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
