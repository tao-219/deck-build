#!/usr/bin/env python3
"""vision_audit_render.py — render slides to images for vision-LLM defect scan.

Pipeline: .pptx → .pdf via LibreOffice → per-slide .jpg via pdftoppm. Output
images live in <output_dir>/slide-NN.jpg, padded to two digits, ready to be
fed to a vision subagent one at a time (or in batches).

Also emits an `audit_manifest.json` listing each image with its slide number,
the title text extracted from that slide (so the subagent can ground its
evaluation against the claimed title), and the archetype if a plan.json was
supplied.

Usage:
  python vision_audit_render.py <deck.pptx> <output_dir> [--plan plan.json] [--dpi 150]

The vision-LLM scan itself is invoked from the calling Claude session (it
needs the Agent tool + image-aware model). See `skills/deck-qa/SKILL.md`
section "Layer 1: Vision-LLM defect scan" for the procedure and prompt template.
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from pptx import Presentation


SOFFICE_CANDIDATES = [
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    "/usr/bin/soffice",
    shutil.which("soffice") or "",
    shutil.which("libreoffice") or "",
]


def find_soffice() -> str:
    for cand in SOFFICE_CANDIDATES:
        if cand and Path(cand).exists():
            return cand
    raise FileNotFoundError(
        "LibreOffice (soffice) not found. Install via "
        "`brew install --cask libreoffice` (macOS) or your platform equivalent."
    )


def find_pdftoppm() -> str:
    cand = shutil.which("pdftoppm")
    if not cand:
        raise FileNotFoundError(
            "pdftoppm not found. Install poppler: `brew install poppler` (macOS)."
        )
    return cand


def render_to_pdf(deck_path: Path, output_dir: Path) -> Path:
    soffice = find_soffice()
    # LibreOffice writes the PDF next to where it's invoked; use an isolated cwd.
    output_dir.mkdir(parents=True, exist_ok=True)
    work_dir = output_dir / "_work"
    work_dir.mkdir(exist_ok=True)
    # Copy the .pptx into work_dir so soffice writes the .pdf alongside.
    work_pptx = work_dir / deck_path.name
    shutil.copy2(deck_path, work_pptx)
    result = subprocess.run(
        [soffice, "--headless", "--convert-to", "pdf",
         "--outdir", str(work_dir), str(work_pptx)],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"LibreOffice conversion failed:\n{result.stderr}\n{result.stdout}")
    pdf_path = work_dir / (deck_path.stem + ".pdf")
    if not pdf_path.exists():
        raise RuntimeError(f"Expected PDF at {pdf_path} not produced.")
    # Move the PDF to the output dir
    final_pdf = output_dir / (deck_path.stem + ".pdf")
    shutil.move(str(pdf_path), str(final_pdf))
    return final_pdf


def render_pdf_to_jpegs(pdf_path: Path, output_dir: Path, dpi: int = 150) -> list[Path]:
    pdftoppm = find_pdftoppm()
    prefix = output_dir / "slide"
    result = subprocess.run(
        [pdftoppm, "-jpeg", "-r", str(dpi), str(pdf_path), str(prefix)],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"pdftoppm failed:\n{result.stderr}\n{result.stdout}")
    jpegs = sorted(output_dir.glob("slide-*.jpg"))
    # Normalize names to two-digit zero-padded for stable ordering
    normalized = []
    for j in jpegs:
        # pdftoppm uses variable padding (slide-1.jpg, slide-10.jpg)
        stem = j.stem  # "slide-N"
        n = int(stem.split("-")[-1])
        new = output_dir / f"slide-{n:02d}.jpg"
        if j != new:
            j.rename(new)
        normalized.append(new)
    return sorted(normalized)


def extract_title_text(slide) -> str:
    """Pull title text — uses the same fallback chain as action_title_lint."""
    sys.path.insert(0, str(Path(__file__).parent))
    from action_title_lint import extract_title
    text, _ = extract_title(slide)
    return text or ""


def build_manifest(deck_path: Path, jpegs: list[Path], plan_path: Path | None) -> dict:
    prs = Presentation(str(deck_path))
    plan_archetypes = {}
    if plan_path is not None and plan_path.exists():
        with open(plan_path) as f:
            plan_data = json.load(f)
        for slide_spec in plan_data.get("slides", []):
            idx = slide_spec.get("slide_number") or slide_spec.get("index")
            if idx is not None:
                plan_archetypes[int(idx)] = slide_spec.get("archetype", "default")

    slides = []
    for i, slide in enumerate(prs.slides, 1):
        # Find the matching jpeg by index
        matching = [j for j in jpegs if j.stem == f"slide-{i:02d}"]
        if not matching:
            continue
        slides.append({
            "slide_number": i,
            "image": str(matching[0]),
            "title": extract_title_text(slide),
            "archetype": plan_archetypes.get(i, "default"),
        })

    return {
        "deck": str(deck_path),
        "slide_count": len(slides),
        "dpi": None,  # populated by caller
        "slides": slides,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("deck", help="Path to .pptx to render")
    parser.add_argument("output_dir", help="Where to write images + manifest")
    parser.add_argument("--plan", help="Optional plan.json mapping slide_num → archetype")
    parser.add_argument("--dpi", type=int, default=150, help="Render DPI (default 150)")
    args = parser.parse_args()

    deck_path = Path(args.deck).resolve()
    output_dir = Path(args.output_dir).resolve()
    plan_path = Path(args.plan).resolve() if args.plan else None

    if not deck_path.exists():
        print(f"ERROR: {deck_path} does not exist", file=sys.stderr)
        sys.exit(2)

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Rendering {deck_path.name} to PDF...", file=sys.stderr)
    pdf_path = render_to_pdf(deck_path, output_dir)

    print(f"Rasterizing to {args.dpi} dpi JPEGs...", file=sys.stderr)
    jpegs = render_pdf_to_jpegs(pdf_path, output_dir, dpi=args.dpi)

    print(f"Building audit manifest...", file=sys.stderr)
    manifest = build_manifest(deck_path, jpegs, plan_path)
    manifest["dpi"] = args.dpi

    manifest_path = output_dir / "audit_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))

    # Clean up work_dir
    work_dir = output_dir / "_work"
    if work_dir.exists():
        shutil.rmtree(work_dir)

    print(f"\n=== Done ===", file=sys.stderr)
    print(f"Slides:   {manifest['slide_count']}", file=sys.stderr)
    print(f"Images:   {output_dir}/slide-NN.jpg", file=sys.stderr)
    print(f"Manifest: {manifest_path}", file=sys.stderr)
    print(f"\nNext: feed each image to a fresh vision subagent. "
          f"See deck-qa/SKILL.md for the prompt template.", file=sys.stderr)
    print(json.dumps({"manifest": str(manifest_path),
                      "slide_count": manifest["slide_count"]}, indent=2))


if __name__ == "__main__":
    main()
