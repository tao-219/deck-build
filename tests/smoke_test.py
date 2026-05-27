#!/usr/bin/env python3
"""smoke_test.py — end-to-end check that the Minto disciplines are ENFORCED.

Part 1 (this script — deterministic, no API):
  - every Minto script runs clean and emits a valid judge packet
  - the deterministic checks FLAG bad-plan and PASS good-plan
  - an old flat plan degrades gracefully (exit 0), never crashes
  - exit codes are correct
  - the action-title linter (+ --semantic packet) runs on a rendered deck

Part 2 (E2E + judged — run ONCE via an Agent, not here):
  - the whole-deck judge PASSES the good deck and FLAGS the bad fixture.
  This script writes the judge packets to tests/_artifacts/ so the deck-qa Layer 5
  agent procedure can run them; the verdict is recorded in tests/SMOKE-RESULTS.md.

Plain python, no pytest. PASS/FAIL per check; non-zero exit if anything fails.

Usage:
  python tests/smoke_test.py
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
FIX = ROOT / "tests" / "fixtures"
ARTIFACTS = ROOT / "tests" / "_artifacts"

sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(FIX))

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    mark = "PASS" if cond else "FAIL"
    line = f"[{mark}] {name}"
    if detail:
        line += f"  — {detail}"
    print(line)
    return bool(cond)


def run(script, *args):
    """Run a script with --quiet; return (returncode, parsed_stdout_json|None)."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / script), *map(str, args)],
        capture_output=True, text=True,
    )
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        data = None
    return proc.returncode, data, proc.stderr


def codes(result):
    return [f.get("code") for f in (result or {}).get("deterministic_findings", [])]


# ─────────────────────────────────────────────────────────────────────────────
def section_storyline():
    print("\n== storyline_check.py (criteria 1, 2, 5) ==")
    rc_g, g, _ = run("storyline_check.py", FIX / "good-plan.json", "--quiet")
    rc_b, b, _ = run("storyline_check.py", FIX / "bad-plan.json", "--quiet")
    rc_f, f, _ = run("storyline_check.py", FIX / "flat-plan.json", "--quiet")

    check("storyline: good PASSES (exit 0, ok)", rc_g == 0 and g and g["ok"], f"exit={rc_g}")
    check("storyline: good emits a valid judge packet",
          g and g["judge_packet"]["prompt"] and g["judge_packet"]["criteria"] == [1, 2, 5])
    check("storyline: bad FLAGGED (exit 1, not ok)", rc_b == 1 and b and not b["ok"], f"exit={rc_b}")
    check("storyline: bad flags governing-thought (C1) + scqa-absent (C2)",
          b and "governing-thought-no-verb" in codes(b) and "scqa-absent" in codes(b),
          str(codes(b)))
    check("storyline: flat degrades gracefully (exit 0, no crash)",
          rc_f == 0 and f and f["ok"] and f["degraded"], f"exit={rc_f}")
    check("storyline: flat still emits a packet (titles + governing thought exist)",
          f and f["judge_packet"]["prompt"])
    return g, b


def section_logic():
    print("\n== logic_structure_check.py (criteria 6, 7, 8 + archetype↔logic) ==")
    rc_g, g, _ = run("logic_structure_check.py", FIX / "good-plan.json", "--quiet")
    rc_b, b, _ = run("logic_structure_check.py", FIX / "bad-plan.json", "--quiet")
    rc_f, f, _ = run("logic_structure_check.py", FIX / "flat-plan.json", "--quiet")

    check("logic: good PASSES (exit 0, ok, evaluable)",
          rc_g == 0 and g and g["ok"] and g["judge_packet"]["evaluable"], f"exit={rc_g}")
    check("logic: good emits a valid judge packet (criteria 6,7,8)",
          g and g["judge_packet"]["prompt"] and g["judge_packet"]["criteria"] == [6, 7, 8])
    check("logic: bad FLAGGED (exit 1, not ok)", rc_b == 1 and b and not b["ok"], f"exit={rc_b}")
    check("logic: bad flags MECE catch-all (C8) + orphan slide (C6)",
          b and "mece-catchall" in codes(b) and "orphan-slide" in codes(b), str(codes(b)))
    check("logic: flat degrades gracefully (exit 0, not evaluable, no crash)",
          rc_f == 0 and f and f["ok"] and not f["judge_packet"]["evaluable"] and f["degraded"],
          f"exit={rc_f}")
    return g, b


def section_titles():
    print("\n== action_title_lint.py (criterion 4 mechanics + --semantic substance) ==")
    import make_fixture_deck as mfd
    tmp = Path(tempfile.mkdtemp())
    good_plan = json.load(open(FIX / "good-plan.json"))
    bad_plan = json.load(open(FIX / "bad-plan.json"))
    good_deck = mfd.build_deck(good_plan, tmp / "good_deck.pptx")
    bad_deck = mfd.build_deck(bad_plan, tmp / "bad_deck.pptx")
    check("titles: fixture decks render via deck_helpers Path B",
          Path(good_deck).exists() and Path(bad_deck).exists())

    rc_g, g, _ = run("action_title_lint.py", good_deck, "--quiet")
    rc_b, b, _ = run("action_title_lint.py", bad_deck, "--quiet")
    g_major = [i for i in (g or {}).get("issues", []) if i.get("severity") == "Major"]
    b_major = [i for i in (b or {}).get("issues", []) if i.get("severity") == "Major"]
    check("titles: good deck PASSES the mechanical linter (exit 0, 0 Major)",
          rc_g == 0 and not g_major, f"exit={rc_g}, major={len(g_major)}")
    check("titles: bad deck FLAGGED (exit 1, topic-title Major present)",
          rc_b == 1 and any(i["rule"] == "topic-title" for i in b_major),
          f"exit={rc_b}, major rules={[i['rule'] for i in b_major]}")

    # --semantic packet on the good deck, scoped by --plan (skips structural slides)
    from action_title_lint import STRUCTURAL_ARCHETYPES
    rc_s, s, _ = run("action_title_lint.py", good_deck, "--plan", FIX / "good-plan.json",
                     "--semantic", "--quiet")
    pkt = (s or {}).get("semantic_judge_packet")
    n_content = sum(1 for sl in good_plan["slides"]
                    if sl["archetype"] not in STRUCTURAL_ARCHETYPES)
    check("titles: --semantic emits a valid judge packet (criteria 3,4)",
          pkt and pkt["prompt"] and pkt["criteria"] == [3, 4])
    check("titles: --semantic packet covers exactly the content titles (structural skipped)",
          pkt and len(pkt["data"]["titles"]) == n_content,
          f"packet={len(pkt['data']['titles']) if pkt else 'n/a'}, expected={n_content}")


def write_artifacts(g_story, b_story, g_logic, b_logic):
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    pairs = {
        "good_storyline_packet.json": g_story,
        "bad_storyline_packet.json": b_story,
        "good_logic_packet.json": g_logic,
        "bad_logic_packet.json": b_logic,
    }
    for name, data in pairs.items():
        (ARTIFACTS / name).write_text(json.dumps(data, indent=2))
    print(f"\nJudge packets written to {ARTIFACTS}/ for the Part-2 (judged) run.")


def main():
    print("=== deck-build Minto smoke test — Part 1 (deterministic) ===")
    g_story, b_story = section_storyline()
    g_logic, b_logic = section_logic()
    section_titles()
    write_artifacts(g_story, b_story, g_logic, b_logic)

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    failed = sum(1 for _, ok, _ in RESULTS if not ok)
    print(f"\n=== Part 1 summary: {passed} passed, {failed} failed ===")
    if failed:
        print("FAILED checks:")
        for name, ok, detail in RESULTS:
            if not ok:
                print(f"  - {name}  ({detail})")
    print("\nPart 2 (E2E + judged): run the deck-qa Layer 5 agent on the packets in "
          "tests/_artifacts/ — see tests/SMOKE-RESULTS.md.")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
