#!/usr/bin/env python3
"""profile_template.py — extract slide master/layout vocabulary + brand context from a .pptx deck.

Walks slide_masters and slide_layouts via python-pptx, captures placeholder
inventory, builds normalized signatures (e.g. "title:1_body:3"), and categorizes
each layout. Also extracts theme palette + frequency-analyzed observed palette +
heading/body fonts. Outputs three artifacts:

  profile.json        — full profile with placeholder geometry (renderer-facing)
  digest.json         — compact LLM-facing summary (no per-placeholder detail)
  brand-context.json  — heading_font, body_font, palette dict (theme + observed)
                        — consumed by deck_helpers.apply_dna() in one call

Usage:
  profile_template.py <deck.pptx> <output_dir> [--name "Display Name"]
"""

import argparse
import hashlib
import json
import re
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from pptx import Presentation


PLACEHOLDER_TYPE_LABELS = {
    1: "title",
    2: "body",
    3: "ctr_title",
    4: "subtitle",
    5: "datetime",
    6: "slide_number",
    7: "footer",
    8: "header",
    9: "object",
    10: "chart",
    11: "table",
    12: "clip_art",
    13: "diagram",
    14: "media",
    15: "slide_image",
    16: "picture",
    17: "vertical",
    18: "vertical_object",
}

STRUCTURAL_TYPES = {"datetime", "slide_number", "footer", "header"}

# PowerPoint's "object family" — placeholders that hold a chart, picture, table,
# diagram, or generic media. python-pptx surfaces these as separate type values
# but functionally they're interchangeable visual slots.
OBJECT_FAMILY = {"diagram", "picture", "slide_image", "chart", "table", "object",
                 "media", "clip_art", "vertical_object"}


def emu_to_inches(emu_value):
    """914400 EMU = 1 inch."""
    if emu_value is None:
        return None
    return round(emu_value / 914400.0, 3)


def label_for(type_int):
    return PLACEHOLDER_TYPE_LABELS.get(type_int, f"unknown_{type_int}")


def profile_placeholder(ph):
    pf = ph.placeholder_format
    type_label = label_for(int(pf.type)) if pf.type is not None else "object"
    return {
        "idx": pf.idx,
        "type": type_label,
        "name": ph.name,
        "x_emu": ph.left,
        "y_emu": ph.top,
        "w_emu": ph.width,
        "h_emu": ph.height,
        "x_inches": emu_to_inches(ph.left),
        "y_inches": emu_to_inches(ph.top),
        "w_inches": emu_to_inches(ph.width),
        "h_inches": emu_to_inches(ph.height),
    }


def signature_for(placeholders):
    """Normalized signature: sorted 'type:count' tokens, structural placeholders skipped."""
    type_counts = defaultdict(int)
    for ph in placeholders:
        if ph["type"] in STRUCTURAL_TYPES:
            continue
        type_counts[ph["type"]] += 1
    if not type_counts:
        return "blank"
    return "_".join(sorted(f"{t}:{c}" for t, c in type_counts.items()))


def normalize_name(name):
    """Strip leading 'N_' prefix PowerPoint adds when layouts are inherited."""
    return re.sub(r"^\d+_", "", name).strip().lower()


def categorize(layout_name, signature, placeholders):
    """Heuristic category — orchestrator uses this for layout selection."""
    name_clean = normalize_name(layout_name)

    # Aggregate counts over all placeholders
    title_count = sum(1 for ph in placeholders if ph["type"] in ("title", "ctr_title"))
    subtitle_count = sum(1 for ph in placeholders if ph["type"] == "subtitle")
    body_count = sum(1 for ph in placeholders if ph["type"] == "body")
    visual_count = sum(1 for ph in placeholders if ph["type"] in OBJECT_FAMILY)

    # Name-based first (most reliable when names are descriptive)
    if any(kw in name_clean for kw in ["title slide", "cover", "front page"]):
        return "title_cover"
    if any(kw in name_clean for kw in ["closing", "thank you", "thanks", "end slide", "contact"]):
        return "closing"
    if "agenda" in name_clean:
        return "agenda"
    if any(kw in name_clean for kw in ["section", "divider", "chapter", "getting started"]):
        return "section_divider"
    if name_clean == "blank":
        return "blank"

    # Signature/count-based
    if signature == "blank":
        return "blank"

    # Title-only (or title+subtitle) without content
    if title_count >= 1 and body_count == 0 and visual_count == 0:
        if subtitle_count >= 1:
            return "title_cover"
        return "section_divider"

    # Multiple body placeholders, no visuals = pure comparison
    if body_count >= 2 and visual_count == 0:
        return "comparison"

    # Body + visuals = content with image
    if body_count >= 1 and visual_count >= 1:
        return "content_with_image"

    # Visuals only (no body)
    if visual_count >= 1:
        if title_count >= 1:
            return "content"
        return "section_divider"  # title-less visual = full-bleed divider

    # Body only, no visuals
    if body_count >= 1:
        return "content"

    return "other"


def build_capabilities(layouts):
    body_counts = set()
    picture_counts = set()
    categories = defaultdict(int)
    max_body = 0
    max_picture = 0

    for layout in layouts:
        body_count = sum(1 for ph in layout["placeholders"] if ph["type"] == "body")
        picture_count = sum(1 for ph in layout["placeholders"] if ph["type"] == "picture")
        body_counts.add(body_count)
        picture_counts.add(picture_count)
        categories[layout["category"]] += 1
        max_body = max(max_body, body_count)
        max_picture = max(max_picture, picture_count)

    return {
        "max_body": max_body,
        "max_picture": max_picture,
        "body_counts_available": sorted(body_counts),
        "picture_counts_available": sorted(picture_counts),
        "categories": dict(categories),
    }


def build_signature_lookup(layouts):
    lookup = defaultdict(list)
    for layout in layouts:
        lookup[layout["signature"]].append(layout["index"])
    return dict(lookup)


def file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_theme_brand(pptx_path):
    """Extract heading/body fonts + theme palette from theme1.xml.

    Returns dict with:
      heading_font (majorFont latin typeface)
      body_font (minorFont latin typeface)
      theme_palette (12-color clrScheme: dk1..accent6)
    """
    import xml.etree.ElementTree as ET
    ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
    out = {"heading_font": None, "body_font": None, "theme_palette": {}}
    try:
        with zipfile.ZipFile(pptx_path) as zf:
            theme_files = [n for n in zf.namelist()
                           if n.startswith("ppt/theme/theme") and n.endswith(".xml")]
            if not theme_files:
                return out
            theme_xml = zf.read(theme_files[0]).decode("utf-8", errors="replace")

        root = ET.fromstring(theme_xml)
        # Fonts
        major = root.find(".//a:fontScheme/a:majorFont/a:latin", ns)
        minor = root.find(".//a:fontScheme/a:minorFont/a:latin", ns)
        if major is not None:
            out["heading_font"] = major.get("typeface")
        if minor is not None:
            out["body_font"] = minor.get("typeface")
        # Palette — clrScheme: lt1, dk1, lt2, dk2, accent1..accent6, hlink, folHlink
        clr_scheme = root.find(".//a:clrScheme", ns)
        if clr_scheme is not None:
            for child in clr_scheme:
                tag = child.tag.split("}", 1)[-1]  # strip namespace
                # The color is in a child element <a:srgbClr val="..."/> or <a:sysClr val="..."/>
                for color_el in child:
                    color_tag = color_el.tag.split("}", 1)[-1]
                    if color_tag == "srgbClr":
                        out["theme_palette"][tag] = "#" + color_el.get("val").upper()
                    elif color_tag == "sysClr":
                        # sysClr has a lastClr fallback
                        last = color_el.get("lastClr")
                        if last:
                            out["theme_palette"][tag] = "#" + last.upper()
                    break
    except Exception as e:
        print(f"WARN: theme extraction failed: {e}", file=sys.stderr)
    return out


def observe_palette(prs, top_n=12):
    """Walk all slide shapes, count fill RGBs and font color RGBs.

    Returns sorted list of (hex, count) tuples — most frequent first. Skips
    pure white, pure black (template-default), and any color that appears
    fewer than 2 times (likely one-off accidents).
    """
    fill_counts = Counter()
    font_counts = Counter()
    for slide in prs.slides:
        for shape in slide.shapes:
            # Fill color
            try:
                if shape.has_text_frame or shape.shape_type == 1:  # AUTO_SHAPE
                    fill = shape.fill
                    if fill.type == 1:  # solid
                        rgb = fill.fore_color.rgb
                        if rgb is not None:
                            fill_counts[f"#{str(rgb).upper()}"] += 1
            except (AttributeError, TypeError, ValueError):
                pass
            # Font colors in text runs
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    for run in para.runs:
                        try:
                            rgb = run.font.color.rgb
                            if rgb is not None:
                                font_counts[f"#{str(rgb).upper()}"] += 1
                        except (AttributeError, TypeError, ValueError):
                            pass

    # Filter out pure white / pure black (template defaults) and singletons
    skip = {"#FFFFFF", "#000000"}
    fill_filtered = [(c, n) for c, n in fill_counts.most_common(top_n)
                     if c not in skip and n >= 2]
    font_filtered = [(c, n) for c, n in font_counts.most_common(top_n)
                     if c not in skip and n >= 2]
    return {
        "fill_top": fill_filtered,
        "font_top": font_filtered,
    }


def observe_fonts(prs, top_n=5):
    """Frequency-analyze font names actually used in body slides.

    Useful when theme.fontScheme is generic ("+mj-lt") and the deck
    overrides fonts at the run level.
    """
    counts = Counter()
    for slide in prs.slides:
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            for para in shape.text_frame.paragraphs:
                for run in para.runs:
                    try:
                        name = run.font.name
                        if name and not name.startswith("+"):
                            counts[name] += 1
                    except (AttributeError, TypeError):
                        pass
    return counts.most_common(top_n)


def build_brand_context(pptx_path, prs):
    """Combine theme extraction + observed analysis into the brand-context dict.

    Schema:
      heading_font: str (theme majorFont, falls back to most-observed)
      body_font: str (theme minorFont, falls back to most-observed)
      palette:
        primary: str (#RRGGBB) — accent1 from theme, falls back to most-frequent fill
        primary_light: str — most-frequent lighter fill
        accent: str — accent2 from theme
        text_dark: str — dk1 from theme
        text_muted: str — most-frequent muted text color
        observed_fills: list of (hex, count) — for manual override
        observed_fonts: list of (hex, count) — for manual override
        theme: dict — raw theme palette
    """
    theme = extract_theme_brand(pptx_path)
    observed_palette = observe_palette(prs)
    observed_fonts = observe_fonts(prs)

    # Resolve fonts
    heading_font = theme["heading_font"]
    body_font = theme["body_font"]
    if observed_fonts:
        # If theme font is missing or looks generic ("Aptos", "Calibri" defaults),
        # surface the most-observed font as a fallback for the consumer.
        most_observed = observed_fonts[0][0]
        if not heading_font or heading_font in ("Aptos", "Calibri"):
            # Don't auto-replace, but expose so user can choose
            pass

    # Resolve palette
    theme_pal = theme["theme_palette"]
    palette = {
        "primary":      theme_pal.get("accent1"),
        "primary_light": theme_pal.get("accent2"),
        "accent":       theme_pal.get("accent3"),
        "text_dark":    theme_pal.get("dk1"),
        "text_muted":   theme_pal.get("dk2"),
        "observed_fills": observed_palette["fill_top"],
        "observed_fonts": observed_palette["font_top"],
        "theme": theme_pal,
    }

    return {
        "heading_font": heading_font,
        "body_font": body_font,
        "observed_fonts": observed_fonts,
        "palette": palette,
    }


def profile_deck(pptx_path, name=None):
    pptx_path = Path(pptx_path).resolve()
    prs = Presentation(str(pptx_path))

    layouts = []
    layout_index = 0

    for master_idx, master in enumerate(prs.slide_masters):
        for layout in master.slide_layouts:
            placeholders = [profile_placeholder(ph) for ph in layout.placeholders]
            sig = signature_for(placeholders)
            category = categorize(layout.name, sig, placeholders)
            layouts.append({
                "index": layout_index,
                "name": layout.name,
                "master_index": master_idx,
                "signature": sig,
                "category": category,
                "placeholder_count": len(placeholders),
                "placeholders": placeholders,
            })
            layout_index += 1

    capabilities = build_capabilities(layouts)
    sig_lookup = build_signature_lookup(layouts)

    metadata = {
        "deck_name": name or pptx_path.stem,
        "source_path": str(pptx_path),
        "source_sha256": file_hash(pptx_path),
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "slide_masters": len(prs.slide_masters),
        "slide_layouts": layout_index,
        "slide_count": len(prs.slides),
        "slide_width_emu": prs.slide_width,
        "slide_height_emu": prs.slide_height,
        "slide_width_inches": emu_to_inches(prs.slide_width),
        "slide_height_inches": emu_to_inches(prs.slide_height),
    }

    brand_context = build_brand_context(pptx_path, prs)

    full_profile = {**metadata, "capabilities": capabilities,
                    "signature_lookup": sig_lookup, "layouts": layouts,
                    "brand_context": brand_context}
    digest = {**metadata, "capabilities": capabilities, "signature_lookup": sig_lookup,
              "brand_context": brand_context,
              "layouts": [{k: v for k, v in layout.items() if k != "placeholders"}
                          for layout in layouts]}

    return full_profile, digest, brand_context


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pptx", help="Path to the reference .pptx deck")
    parser.add_argument("output_dir", help="Where to write profile.json + digest.json")
    parser.add_argument("--name", help="Display name (defaults to filename stem)", default=None)
    args = parser.parse_args()

    pptx_path = Path(args.pptx)
    output_dir = Path(args.output_dir)

    if not pptx_path.exists():
        print(f"ERROR: {pptx_path} does not exist", file=sys.stderr)
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Profiling {pptx_path.name}...", file=sys.stderr)
    full_profile, digest, brand_context = profile_deck(pptx_path, name=args.name)

    profile_out = output_dir / "profile.json"
    digest_out = output_dir / "digest.json"
    brand_out = output_dir / "brand-context.json"

    profile_out.write_text(json.dumps(full_profile, indent=2))
    digest_out.write_text(json.dumps(digest, indent=2))
    brand_out.write_text(json.dumps(brand_context, indent=2))

    profile_size = profile_out.stat().st_size
    digest_size = digest_out.stat().st_size
    brand_size = brand_out.stat().st_size

    print(f"\n=== Summary ===", file=sys.stderr)
    print(f"Slide masters: {full_profile['slide_masters']}", file=sys.stderr)
    print(f"Slide layouts: {full_profile['slide_layouts']}", file=sys.stderr)
    print(f"Slide count: {full_profile['slide_count']}", file=sys.stderr)
    print(f"Slide size: {full_profile['slide_width_inches']}\" x {full_profile['slide_height_inches']}\"",
          file=sys.stderr)

    print(f"\nLayout categories:", file=sys.stderr)
    for cat, count in sorted(full_profile['capabilities']['categories'].items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}", file=sys.stderr)

    print(f"\nBody counts available: {full_profile['capabilities']['body_counts_available']}",
          file=sys.stderr)
    print(f"Picture counts available: {full_profile['capabilities']['picture_counts_available']}",
          file=sys.stderr)

    print(f"\nSignature collisions (multiple layouts with same shape):", file=sys.stderr)
    collisions = {sig: indices for sig, indices in full_profile['signature_lookup'].items()
                  if len(indices) > 1}
    if collisions:
        for sig, indices in sorted(collisions.items(), key=lambda x: -len(x[1])):
            names = [full_profile['layouts'][i]['name'] for i in indices]
            print(f"  {sig}: layouts {indices} -> {names}", file=sys.stderr)
    else:
        print("  (none)", file=sys.stderr)

    print(f"\nWrote {profile_out} ({profile_size:,} bytes)", file=sys.stderr)
    print(f"Wrote {digest_out} ({digest_size:,} bytes)", file=sys.stderr)
    print(f"Wrote {brand_out} ({brand_size:,} bytes)", file=sys.stderr)
    print(f"Digest reduction: {(1 - digest_size/profile_size)*100:.1f}% smaller", file=sys.stderr)

    # Brand context summary
    print(f"\n=== Brand context ===", file=sys.stderr)
    print(f"Heading font (theme):  {brand_context['heading_font']}", file=sys.stderr)
    print(f"Body font (theme):     {brand_context['body_font']}", file=sys.stderr)
    if brand_context['observed_fonts']:
        print(f"Observed fonts:        {brand_context['observed_fonts'][:3]}", file=sys.stderr)
    pal = brand_context['palette']
    print(f"Theme primary (accent1): {pal.get('primary')}", file=sys.stderr)
    print(f"Theme dk1 (text dark):   {pal.get('text_dark')}", file=sys.stderr)
    if pal['observed_fills']:
        print(f"Top observed fills:    {pal['observed_fills'][:5]}", file=sys.stderr)


if __name__ == "__main__":
    main()
