#!/usr/bin/env python3
"""action_title_lint.py — audit slide titles against the action-title pattern.

Walks every slide in a .pptx, extracts the title, and applies the rules from
`skills/deck-orchestrator/references/action-title-pattern.md`:

  R1 — Verb present (heuristic: known verb OR verb-like suffix on a non-stop token)
  R2 — Word count ≤ 15
  R3 — No trailing period
  R4 — No banned weasel words
  R5 — Active voice (heuristic: looks for "was/were/is/are <past-participle> by")
  R6 — Two-tone shape for titles > 8 words (mixed bold/normal runs in same paragraph)
  R7 — Not a topic title (heuristic: lacks a verb AND looks like a noun phrase)

Usage:
  python action_title_lint.py <deck.pptx> [--quiet]

Exit code: 0 if no Major issues, 1 otherwise. Each issue carries Major/Minor.
JSON output to stdout; human summary to stderr unless --quiet.

Importable: other QA scripts can `from action_title_lint import (
    extract_title, lint_title, BANNED_WEASEL_WORDS, KNOWN_VERBS
)` to share the rules.
"""

import argparse
import json
import sys
from pathlib import Path

from pptx import Presentation
from pptx.util import Emu


# ─────────────────────────────────────────────────────────────────────────────
# Rule constants
# ─────────────────────────────────────────────────────────────────────────────

MAX_WORD_COUNT = 15
TWO_TONE_THRESHOLD = 8

# Banned weasel words from action-title-pattern.md
BANNED_WEASEL_WORDS = {
    "leverage", "leverages", "leveraging", "leveraged",
    "harness", "harnesses", "harnessing", "harnessed",
    "synergy", "synergies", "synergistic", "synergize",
    "robust",  # unless quantified — script flags; reviewer judges
    "best-in-class", "industry-leading", "world-class",
    "going forward", "at the end of the day",
    "holistic", "holistically",
    "strategic", "strategically",  # often filler
    "innovative", "cutting-edge", "state-of-the-art",
    "value-add", "value-added",
    "thought leadership",
    "moving the needle",
    "drill down", "drill-down",
    "low-hanging fruit",
}

# Multi-word weasel phrases — checked separately
BANNED_WEASEL_PHRASES = [
    "going forward",
    "at the end of the day",
    "thought leadership",
    "moving the needle",
    "low-hanging fruit",
    "best in class",
    "best-in-class",
    "industry leading",
    "industry-leading",
]

VERB_LIKE_SUFFIXES = ("s", "ed", "ing", "es")

# Known-verb seed list — common verbs in consulting decks
KNOWN_VERBS = {
    # be / have / do
    "is", "are", "be", "been", "being", "was", "were",
    "has", "have", "had", "having",
    "do", "does", "did", "done",
    "will", "would", "can", "could", "should", "must", "may", "might", "shall",
    # state / observation
    "shows", "show", "shown", "indicates", "indicate", "suggests", "suggest",
    "reflects", "reflect", "reveals", "reveal", "demonstrates", "demonstrate",
    "confirms", "confirm", "underscores", "underscore",
    # change / movement
    "rose", "rises", "rise", "fell", "falls", "fall", "grew", "grows", "grow",
    "shrinks", "shrank", "expands", "expand", "expanded",
    "increased", "decreased", "doubled", "tripled", "halved",
    "shifted", "shifts", "shift", "moved", "moves", "move",
    # action
    "drives", "drive", "drove", "driven",
    "covers", "cover", "covered",
    "operates", "operate", "operated",
    "cuts", "cut", "splits", "split",
    "compresses", "compress", "compressed",
    "lacks", "lack", "lacked", "needs", "need", "requires", "require",
    "feeds", "feed", "fed", "informs", "inform", "informed",
    "identifies", "identify", "identified",
    "captures", "capture", "captured",
    "establishes", "establish", "established",
    "surfaces", "surface", "surfaced",
    "walks", "walk", "walked",
    "raises", "raise", "raised",
    "remediates", "remediate", "remediated",
    "approves", "approve", "approved",
    "adopts", "adopt", "adopted",
    "rejects", "reject", "rejected",
    "delivers", "deliver", "delivered",
    "produces", "produce", "produced",
    "defines", "define", "defined",
    "designs", "design", "designed",
    "implements", "implement", "implemented",
    "tests", "test", "tested",
    "validates", "validate", "validated",
    "scopes", "scope", "scoped",
    "targets", "target", "targeted",
    "lands", "land", "landed",
    "exposes", "expose", "exposed",
    "creates", "create", "created",
    "blocks", "block", "blocked",
    "enables", "enable", "enabled",
    "supports", "support", "supported",
    "outpaces", "outpace", "outpaced",
}

# Tokens commonly seen in topic titles (noun-phrase signals)
TOPIC_HEADWORDS = {
    "overview", "background", "approach", "methodology", "framework",
    "findings", "results", "analysis", "summary", "introduction",
    "agenda", "goals", "objectives", "scope", "context",
    "considerations", "recommendations", "next", "steps",
    "outline", "outlook",
}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def emu_to_inches(value):
    if value is None:
        return None
    return value / 914400.0


def extract_title(slide):
    """Return (title_text, paragraph) — paragraph used for two-tone weight inspection.

    Resolution order:
      1. Shape named exactly "Title 1" or "Title".
      2. Shape whose name starts with "Title" (any suffix).
      3. Largest-font textbox in the upper third (y < 1.6") whose font size
         is ≥18pt — picks the action title even if it's a renamed textbox,
         skips the smaller workstream banner / category strip above it.
      4. First textbox in the upper third (last resort).
    """
    # Priority 1 + 2: title-named shapes
    for shape in slide.shapes:
        if shape.has_text_frame and shape.name.startswith("Title"):
            text = shape.text_frame.text.strip()
            if text:
                return text, shape.text_frame.paragraphs[0]

    # Priority 3: largest-font textbox in the upper third
    candidates = []
    for shape in slide.shapes:
        if not shape.has_text_frame:
            continue
        if shape.top is None or emu_to_inches(shape.top) is None:
            continue
        if emu_to_inches(shape.top) >= 1.6:
            continue
        text = shape.text_frame.text.strip()
        if not text:
            continue
        # Get max font size across runs in first paragraph
        max_size = 0
        for run in shape.text_frame.paragraphs[0].runs:
            try:
                pt = run.font.size.pt if run.font.size else 0
                if pt > max_size:
                    max_size = pt
            except (AttributeError, TypeError):
                pass
        candidates.append((max_size, shape, text))

    # Pick the largest-font candidate ≥18pt
    candidates.sort(key=lambda c: -c[0])
    for size, shape, text in candidates:
        if size >= 18:
            return text, shape.text_frame.paragraphs[0]

    # Priority 4: first textbox in upper third (any size)
    for shape in slide.shapes:
        if (shape.has_text_frame and shape.top is not None
                and emu_to_inches(shape.top) is not None
                and emu_to_inches(shape.top) < 1.6):
            text = shape.text_frame.text.strip()
            if text:
                return text, shape.text_frame.paragraphs[0]
    return None, None


def tokenize(text):
    return [t.strip(".,;:–-—()\"'").lower() for t in text.split() if t.strip()]


def has_verb(text):
    """Heuristic: title contains at least one verb-like token."""
    if not text:
        return False
    for tok in tokenize(text):
        if tok in KNOWN_VERBS:
            return True
        if any(tok.endswith(suf) for suf in VERB_LIKE_SUFFIXES) and len(tok) > 4:
            # Crude check — ends with -s/-ed/-ing/-es and longer than 4 chars
            return True
    return False


def has_weasel_words(text):
    """Return list of detected weasel words/phrases."""
    if not text:
        return []
    found = []
    text_lower = text.lower()
    for phrase in BANNED_WEASEL_PHRASES:
        if phrase in text_lower:
            found.append(phrase)
    for tok in tokenize(text):
        if tok in BANNED_WEASEL_WORDS:
            found.append(tok)
    # Dedupe while preserving order
    seen = set()
    return [x for x in found if not (x in seen or seen.add(x))]


def is_passive_voice(text):
    """Crude heuristic — looks for 'was/were/is/are/been <verb-ed> by'.

    Doesn't catch all passive constructions but flags the common ones.
    """
    if not text:
        return False
    tokens = tokenize(text)
    aux = {"was", "were", "is", "are", "been", "being", "be"}
    for i in range(len(tokens) - 2):
        if tokens[i] in aux:
            # next token ends in -ed AND there's "by" within next 4 tokens
            if tokens[i + 1].endswith("ed") and len(tokens[i + 1]) > 4:
                window = tokens[i + 2:i + 6]
                if "by" in window:
                    return True
    return False


def has_two_tone(paragraph):
    """Return True if paragraph has runs with mixed bold weight."""
    if paragraph is None or not paragraph.runs:
        return False
    bolds = {bool(r.font.bold) for r in paragraph.runs if r.text.strip()}
    return len(bolds) > 1


def propose_two_tone_split(text):
    """Propose a bold/normal split point for a long action title.

    Resolution order:
      1. First em-dash (—), en-dash (–), or hyphen-with-spaces (" - ") in the title
         → split there; bold = before, normal = after.
      2. First colon (":") followed by a space.
      3. Word boundary nearest to 50% of text length.

    Returns dict {bold, normal, rationale} or None if no split is sensible
    (text too short).
    """
    if not text or len(text.split()) < 6:
        return None
    text = text.strip()

    # Priority 1: dashes
    for sep in [" — ", " – ", " - "]:
        idx = text.find(sep)
        if idx > 0:
            return {
                "bold": text[:idx].strip(),
                "normal": text[idx + len(sep):].strip(),
                "rationale": f"existing dash separator '{sep.strip()}'",
            }

    # Priority 2: colon
    idx = text.find(": ")
    if idx > 0:
        return {
            "bold": text[:idx].strip(),
            "normal": text[idx + 2:].strip(),
            "rationale": "colon separator",
        }

    # Priority 3: word boundary near 50% length
    words = text.split()
    target = len(words) // 2
    return {
        "bold": " ".join(words[:target]),
        "normal": " ".join(words[target:]),
        "rationale": f"word boundary at position {target} of {len(words)}",
    }


def is_topic_title(text):
    """Heuristic — first significant token is a known topic headword AND no verb."""
    if not text:
        return False
    if has_verb(text):
        return False
    tokens = tokenize(text)
    if not tokens:
        return False
    # Look at first 3 tokens
    for tok in tokens[:3]:
        if tok in TOPIC_HEADWORDS:
            return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Lint
# ─────────────────────────────────────────────────────────────────────────────

def lint_title(text, paragraph=None):
    """Run all rules on a title. Return list of issue dicts (severity, rule, description)."""
    issues = []
    if not text:
        return issues

    word_count = len(text.split())

    # R2 — Word count
    if word_count > MAX_WORD_COUNT:
        issues.append({
            "severity": "Major",
            "rule": "word-count",
            "description": (
                f"Title is {word_count} words; max is {MAX_WORD_COUNT}. "
                "Tighten or split."
            ),
        })

    # R1 — Verb test
    if not has_verb(text):
        issues.append({
            "severity": "Major",
            "rule": "verb-test",
            "description": (
                "No verb detected (heuristic). Action titles state a "
                "conclusion with an active verb."
            ),
        })

    # R7 — Topic title
    if is_topic_title(text):
        issues.append({
            "severity": "Major",
            "rule": "topic-title",
            "description": (
                "Looks like a topic title (noun-phrase headword, no verb). "
                "Rewrite to state the conclusion."
            ),
        })

    # R3 — Trailing period
    if text.rstrip().endswith("."):
        issues.append({
            "severity": "Minor",
            "rule": "trailing-period",
            "description": "Action titles do not end with a period.",
        })

    # R4 — Weasel words
    weasels = has_weasel_words(text)
    if weasels:
        issues.append({
            "severity": "Minor",
            "rule": "weasel-words",
            "description": (
                f"Banned weasel word(s) detected: {', '.join(weasels)}. "
                "Strip or replace with a specific term."
            ),
        })

    # R5 — Passive voice
    if is_passive_voice(text):
        issues.append({
            "severity": "Minor",
            "rule": "passive-voice",
            "description": (
                "Passive construction detected. Prefer active voice."
            ),
        })

    # R6 — Two-tone shape (only checked if paragraph supplied)
    if paragraph is not None and word_count > TWO_TONE_THRESHOLD:
        if not has_two_tone(paragraph):
            issue = {
                "severity": "Minor",
                "rule": "two-tone-shape",
                "description": (
                    f"Title is {word_count} words but rendered as a single "
                    "weight throughout. Apply the two-tone pattern (bold "
                    "short claim + en-dash + normal-weight elaboration)."
                ),
            }
            split = propose_two_tone_split(text)
            if split:
                issue["suggested_fix"] = (
                    f"Split as bold='{split['bold']}' + normal='{split['normal']}' "
                    f"(at {split['rationale']})"
                )
            issues.append(issue)

    return issues


def audit_deck(deck_path):
    """Walk every slide; return aggregate report."""
    prs = Presentation(str(deck_path))
    all_issues = []
    for i, slide in enumerate(prs.slides, 1):
        title, paragraph = extract_title(slide)
        if title is None:
            all_issues.append({
                "slide": i,
                "severity": "Minor",
                "rule": "no-title",
                "title": None,
                "description": "No title shape found on this slide.",
            })
            continue
        issues = lint_title(title, paragraph)
        for issue in issues:
            issue["slide"] = i
            issue["title"] = title
            all_issues.append(issue)
    return {
        "deck": str(deck_path),
        "slide_count": len(prs.slides),
        "issues": all_issues,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("deck", help="Path to .pptx to audit")
    parser.add_argument("--quiet", action="store_true",
                        help="Only print JSON, not human summary")
    args = parser.parse_args()

    deck_path = Path(args.deck)
    if not deck_path.exists():
        print(f"ERROR: {deck_path} does not exist", file=sys.stderr)
        sys.exit(2)

    result = audit_deck(deck_path)
    print(json.dumps(result, indent=2))

    if not args.quiet:
        major = sum(1 for i in result["issues"] if i["severity"] == "Major")
        minor = sum(1 for i in result["issues"] if i["severity"] == "Minor")
        print(f"\n--- Summary: {len(result['issues'])} issues "
              f"({major} Major, {minor} Minor) ---", file=sys.stderr)

    sys.exit(1 if any(i["severity"] == "Major" for i in result["issues"]) else 0)


if __name__ == "__main__":
    main()
