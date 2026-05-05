#!/usr/bin/env python3
"""deck_preview.py — render a .pptx for human visual review.

Outputs a PDF next to the source .pptx (default), plus per-slide JPEGs in an
output directory. Optionally opens the result in macOS Preview.

Distinct from `vision_audit_render.py` (which writes to a temp dir + manifest
for AI consumption). This one is for *you* — sized for browser/Preview viewing
and placed somewhere you'd naturally find it.

Usage:
  deck_preview.py <input.pptx> [--out <dir>] [--slide N] [--dpi 150] [--open]

Defaults:
  --out: same directory as input.pptx, in a `<stem>-preview/` subfolder
  --dpi: 150
  --slide: render all slides (1-indexed if specified)
  --open: don't open (pass to launch macOS Preview after render)
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


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
        "`brew install --cask libreoffice` (macOS)."
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
    output_dir.mkdir(parents=True, exist_ok=True)
    work_dir = output_dir / "_work"
    work_dir.mkdir(exist_ok=True)
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
    pdf_src = work_dir / (deck_path.stem + ".pdf")
    if not pdf_src.exists():
        raise RuntimeError(f"Expected PDF at {pdf_src} not produced.")
    final_pdf = output_dir / (deck_path.stem + ".pdf")
    shutil.move(str(pdf_src), str(final_pdf))
    shutil.rmtree(work_dir, ignore_errors=True)
    return final_pdf


def render_pdf_to_jpegs(pdf_path: Path, output_dir: Path,
                        dpi: int, slide_n: int | None) -> list[Path]:
    pdftoppm = find_pdftoppm()
    prefix = output_dir / "slide"
    cmd = [pdftoppm, "-jpeg", "-r", str(dpi)]
    if slide_n is not None:
        cmd.extend(["-f", str(slide_n), "-l", str(slide_n)])
    cmd.extend([str(pdf_path), str(prefix)])
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"pdftoppm failed:\n{result.stderr}\n{result.stdout}")
    jpegs = sorted(output_dir.glob("slide-*.jpg"))
    # Normalize to two-digit zero-padded
    normalized = []
    for j in jpegs:
        stem = j.stem
        n = int(stem.split("-")[-1])
        new = output_dir / f"slide-{n:02d}.jpg"
        if j != new:
            j.rename(new)
        normalized.append(new)
    return sorted(normalized)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("deck", help="Path to .pptx to preview")
    parser.add_argument("--out", help="Output directory (default: <deck>-preview/ next to source)")
    parser.add_argument("--slide", type=int, help="Render only this slide (1-indexed)")
    parser.add_argument("--dpi", type=int, default=150, help="Render DPI (default 150)")
    parser.add_argument("--open", action="store_true",
                        help="Open the output PDF in macOS Preview after render")
    parser.add_argument("--quiet", action="store_true", help="JSON-only output")
    args = parser.parse_args()

    deck_path = Path(args.deck).resolve()
    if not deck_path.exists():
        print(f"ERROR: {deck_path} does not exist", file=sys.stderr)
        sys.exit(2)

    if args.out:
        output_dir = Path(args.out).resolve()
    else:
        output_dir = deck_path.parent / f"{deck_path.stem}-preview"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not args.quiet:
        print(f"Rendering {deck_path.name} → {output_dir}/", file=sys.stderr)

    pdf_path = render_to_pdf(deck_path, output_dir)
    jpegs = render_pdf_to_jpegs(pdf_path, output_dir, args.dpi, args.slide)

    summary = {
        "deck": str(deck_path),
        "output_dir": str(output_dir),
        "pdf": str(pdf_path),
        "images": [str(j) for j in jpegs],
        "slide_count": len(jpegs),
        "dpi": args.dpi,
    }
    print(json.dumps(summary, indent=2))

    if args.open:
        if sys.platform == "darwin":
            subprocess.run(["open", str(pdf_path)])
            if not args.quiet:
                print(f"\nOpened {pdf_path.name} in Preview.", file=sys.stderr)
        else:
            print(f"\n--open only supported on macOS. PDF at {pdf_path}",
                  file=sys.stderr)

    if not args.quiet:
        print(f"\nPDF: {pdf_path}", file=sys.stderr)
        print(f"JPEGs: {len(jpegs)} slide image(s) in {output_dir}/", file=sys.stderr)


if __name__ == "__main__":
    main()
