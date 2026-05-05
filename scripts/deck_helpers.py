"""deck_helpers.py — render-helper recipes for the deck-build plugin.

Importable module that provides the archetype recipes and primitives documented
in deck-render/SKILL.md and deck-orchestrator/references/design-archetypes.md.

Usage from a rebuild script:

    import sys
    sys.path.insert(0, "/Users/taoli/projects/deck-build/scripts")
    from deck_helpers import (
        # Constants — Manulife defaults; override per deck via set_palette() / set_fonts()
        PRIMARY, LATER_FILL, SIGNOFF_FILL, CONTEXT_GREY,
        TEXT_DARK, TEXT_MUTED, WHITE,
        FONT_HEADING, FONT_BODY,
        # Primitives
        set_run, add_rect, add_text_to_shape, add_paragraph,
        # Recipe helpers
        two_tone_title, numbered_agenda_block, section_header,
        sub_callout_grid, spotlight_callout,
        # Icons
        target_icon, network_icon, globe_icon, gear_icon, magnifier_icon,
        check_icon, lightning_icon,
        # Strip discipline
        strip_shapes, replace_title,
    )

All helpers operate in inches (Inches() conversions happen inside). EMU is
exposed only when the underlying python-pptx API requires it.

Defaults are tuned for Manulife — call `set_palette()` and `set_fonts()` once
at the top of a script to adapt to a different reference deck's DNA.
"""

from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn
from lxml import etree


# ─────────────────────────────────────────────────────────────────────────────
# Palette — Manulife defaults; override via set_palette()
# ─────────────────────────────────────────────────────────────────────────────

PRIMARY        = RGBColor(0x00, 0xA7, 0x58)
PRIMARY_LIGHT  = RGBColor(0xCC, 0xED, 0xDB)
LATER_FILL     = RGBColor(0xF2, 0xF2, 0xF4)
LATER_BORDER   = RGBColor(0xD9, 0xDA, 0xDF)
SIGNOFF_FILL   = RGBColor(0xFF, 0xF4, 0xE0)
SIGNOFF_ACCENT = RGBColor(0xF4, 0x96, 0x00)
CONTEXT_GREY   = RGBColor(0x8E, 0x90, 0xA2)
CONTEXT_FILL   = RGBColor(0x9C, 0x9F, 0xAE)
PANEL_BORDER   = RGBColor(0x66, 0xB5, 0x8E)
TEXT_DARK      = RGBColor(0x26, 0x26, 0x26)
TEXT_MUTED     = RGBColor(0x59, 0x59, 0x59)
WHITE          = RGBColor(0xFF, 0xFF, 0xFF)

FONT_HEADING = "Manulife JH Sans"
FONT_BODY    = "Manulife JH Sans"


def set_palette(*, primary=None, primary_light=None, later_fill=None,
                later_border=None, signoff_fill=None, signoff_accent=None,
                context_grey=None, context_fill=None, panel_border=None,
                text_dark=None, text_muted=None):
    """Override the module-level palette in one call. Pass RGBColor instances."""
    global PRIMARY, PRIMARY_LIGHT, LATER_FILL, LATER_BORDER
    global SIGNOFF_FILL, SIGNOFF_ACCENT, CONTEXT_GREY, CONTEXT_FILL
    global PANEL_BORDER, TEXT_DARK, TEXT_MUTED
    if primary is not None:        PRIMARY = primary
    if primary_light is not None:  PRIMARY_LIGHT = primary_light
    if later_fill is not None:     LATER_FILL = later_fill
    if later_border is not None:   LATER_BORDER = later_border
    if signoff_fill is not None:   SIGNOFF_FILL = signoff_fill
    if signoff_accent is not None: SIGNOFF_ACCENT = signoff_accent
    if context_grey is not None:   CONTEXT_GREY = context_grey
    if context_fill is not None:   CONTEXT_FILL = context_fill
    if panel_border is not None:   PANEL_BORDER = panel_border
    if text_dark is not None:      TEXT_DARK = text_dark
    if text_muted is not None:     TEXT_MUTED = text_muted


def set_fonts(*, heading=None, body=None):
    """Override the module-level fonts."""
    global FONT_HEADING, FONT_BODY
    if heading is not None: FONT_HEADING = heading
    if body is not None:    FONT_BODY = body


def apply_dna(dna_path, *, prefer_observed_fonts=True, font_override_threshold=0.5):
    """Load brand-context.json from a DNA directory and apply it in one call.

    Sets PRIMARY, PRIMARY_LIGHT, TEXT_DARK, TEXT_MUTED from the brand context's
    palette block, and FONT_HEADING / FONT_BODY from theme.fontScheme (or from
    observed-fonts if the theme font is generic ("Aptos", "Calibri") AND the
    most-observed font dominates ≥`font_override_threshold` of run usage).

    Args:
      dna_path: Path to the DNA directory (containing brand-context.json),
                OR direct path to brand-context.json.
      prefer_observed_fonts: If True, override theme font when observed font
                             clearly dominates and theme font looks generic.
      font_override_threshold: Fraction of total observed runs that the top
                               observed font must claim before overriding.

    Returns the loaded brand-context dict so callers can inspect what was applied.
    """
    import json
    from pathlib import Path

    p = Path(dna_path)
    if p.is_dir():
        p = p / "brand-context.json"
    if not p.exists():
        raise FileNotFoundError(
            f"brand-context.json not found at {p}. Run profile_template.py first."
        )

    with open(p) as f:
        ctx = json.load(f)

    # Resolve fonts
    heading = ctx.get("heading_font")
    body = ctx.get("body_font")
    observed = ctx.get("observed_fonts") or []

    if prefer_observed_fonts and observed:
        top_font, top_count = observed[0]
        total = sum(c for _, c in observed)
        if total > 0 and (top_count / total) >= font_override_threshold:
            generic = {"Aptos", "Aptos (Body)", "Calibri", "Calibri Light", None, ""}
            if heading in generic:
                heading = top_font
            if body in generic:
                body = top_font

    if heading or body:
        set_fonts(heading=heading, body=body)

    # Resolve palette
    palette = ctx.get("palette", {})
    palette_kwargs = {}

    def _to_rgb(hex_str):
        if not hex_str or not isinstance(hex_str, str):
            return None
        h = hex_str.lstrip("#")
        if len(h) != 6:
            return None
        try:
            return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
        except ValueError:
            return None

    primary = _to_rgb(palette.get("primary"))
    primary_light = _to_rgb(palette.get("primary_light"))
    text_dark = _to_rgb(palette.get("text_dark"))
    text_muted = _to_rgb(palette.get("text_muted"))

    if primary is not None:        palette_kwargs["primary"] = primary
    if primary_light is not None:  palette_kwargs["primary_light"] = primary_light
    if text_dark is not None:      palette_kwargs["text_dark"] = text_dark
    if text_muted is not None:     palette_kwargs["text_muted"] = text_muted

    if palette_kwargs:
        set_palette(**palette_kwargs)

    return ctx


# ─────────────────────────────────────────────────────────────────────────────
# Footer-clearance limits (per archetype) — never exceed these y-coords
# ─────────────────────────────────────────────────────────────────────────────

# Slide is 7.5" tall. Reserve 6.95–7.30 for footer band.
FOOTER_CLEARANCE = {
    "stage-flow-with-signoff":          6.65,
    "two-col-overview-with-subcallout": 6.65,
    "spotlight-comparison-columns":     6.85,
    "tiered-region-coverage-table":     6.55,
    "mapping-table-with-status":        6.55,
    "recommendation-hero":              6.65,
    "before-after-process":             6.55,
    "risk-heatmap":                     6.55,
    "default":                          6.65,
}


def footer_clearance(archetype: str) -> float:
    """Return the lowest y-coord (inches) any non-footer shape may occupy."""
    return FOOTER_CLEARANCE.get(archetype, FOOTER_CLEARANCE["default"])


# ─────────────────────────────────────────────────────────────────────────────
# Low-level primitives
# ─────────────────────────────────────────────────────────────────────────────

def set_run(run, text, *, font=None, size=11, bold=False, italic=False,
            color=None):
    """Set all attributes of a run in one call."""
    run.text = text
    run.font.name = font or FONT_BODY
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color or TEXT_DARK


def add_rect(slide, x, y, w, h, *, fill=None, line=None, line_w_pt=1.0,
             line_dash=False, rounded=False, corner_radius=0.08):
    """Add a rectangle (or rounded rectangle). All coords in inches."""
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE
    rect = slide.shapes.add_shape(shape_type,
        Inches(x), Inches(y), Inches(w), Inches(h))
    if rounded:
        rect.adjustments[0] = corner_radius
    if fill is None:
        rect.fill.background()
    else:
        rect.fill.solid()
        rect.fill.fore_color.rgb = fill
    if line is None:
        rect.line.fill.background()
    else:
        rect.line.color.rgb = line
        rect.line.width = Pt(line_w_pt)
        if line_dash:
            ln = rect.line._get_or_add_ln()
            prstDash = etree.SubElement(ln, qn("a:prstDash"))
            prstDash.set("val", "dash")
    return rect


def add_text_to_shape(shape, text, *, font=None, size=11, bold=False,
                      italic=False, color=None, align=PP_ALIGN.LEFT,
                      vert=MSO_ANCHOR.TOP, margin=0.05):
    """Set the text of an existing shape with formatting in one call."""
    tf = shape.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = vert
    tf.margin_left = Inches(margin)
    tf.margin_right = Inches(margin)
    tf.margin_top = Inches(margin)
    tf.margin_bottom = Inches(margin)
    p = tf.paragraphs[0]
    p.alignment = align
    r = p.add_run()
    set_run(r, text, font=font, size=size, bold=bold, italic=italic,
            color=color)
    return p


def add_paragraph(text_frame, text, *, font=None, size=11, bold=False,
                  italic=False, color=None, align=PP_ALIGN.LEFT,
                  bullet=False, space_before_pt=4):
    """Add a paragraph to an existing text_frame with formatting + optional bullet.

    Bullets use a literal "• " prefix (more reliable cross-renderer than buChar).
    """
    p = text_frame.add_paragraph()
    p.alignment = align
    if space_before_pt:
        p.space_before = Pt(space_before_pt)
    if bullet:
        text = "• " + text
    r = p.add_run()
    set_run(r, text, font=font, size=size, bold=bold, italic=italic,
            color=color)
    if bullet:
        pPr = p._p.get_or_add_pPr()
        pPr.set("indent", "-152400")
        pPr.set("marL", "228600")
    return p


# ─────────────────────────────────────────────────────────────────────────────
# Strip-and-keep discipline
# ─────────────────────────────────────────────────────────────────────────────

def strip_shapes(slide, keep_names=None, remove_names=None):
    """Delete shapes by name. Pass either keep_names (whitelist) or remove_names (blacklist).

    Always emit the inventory first to choose KEEP vs REMOVE deliberately:

        for s in slide.shapes:
            print(s.name, s.shape_type)
    """
    spTree = slide.shapes._spTree
    to_remove = []
    for shape in slide.shapes:
        if keep_names is not None and shape.name not in keep_names:
            to_remove.append(shape)
        elif remove_names is not None and shape.name in remove_names:
            to_remove.append(shape)
    for shape in to_remove:
        spTree.remove(shape._element)


def drop_slide(prs, idx):
    """Remove slide at zero-based idx from the presentation.

    Cleans up both sldIdLst and the relationship. Use as the first half of
    a replace-slide pattern:

        drop_slide(prs, 4)                          # remove old slide 5 (1-indexed)
        new_slide = prs.slides.add_slide(layout)    # append at end
        # ...build content on new_slide...
        move_slide(prs, len(prs.slides) - 1, 4)     # move to position 5
        prs.save(out)

    Or for outright deletion (no replacement):

        drop_slide(prs, idx)
        prs.save(out)
    """
    slide_id_list = prs.slides._sldIdLst
    sld_id = list(slide_id_list)[idx]
    rId = sld_id.attrib[
        "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
    ]
    slide_id_list.remove(sld_id)
    prs.part.drop_rel(rId)


def move_slide(prs, from_idx, to_idx):
    """Move slide from_idx to to_idx (zero-based). Used after appending a
    replacement slide via prs.slides.add_slide() to put it in the right place."""
    slide_id_list = prs.slides._sldIdLst
    sld = list(slide_id_list)[from_idx]
    slide_id_list.remove(sld)
    slide_id_list.insert(to_idx, sld)


def replace_slide(prs, idx, build_fn, layout=None):
    """Drop slide at idx and replace with one built by build_fn(slide).

    build_fn takes the new (empty) slide and populates it. The new slide
    inherits from `layout` (defaults to the same layout as the dropped slide).
    Returns the new slide.

    Works around a python-pptx bug where `add_slide` after `drop_slide` can
    assign a partname (slideN.xml) that collides with an existing slide.
    Uses `package.next_partname()` instead — which scans actual existing
    partnames — and creates the SlidePart directly.

    Example:

        from pptx import Presentation
        from deck_helpers import replace_slide, two_tone_title

        prs = Presentation("deck.pptx")

        def build_my_slide(slide):
            two_tone_title(slide, 0.5, 0.55, 12.5, 0.85,
                           "Today's session", "agenda for the next 90 min")
            # ...rest of slide construction...

        replace_slide(prs, 2, build_my_slide)  # replace slide 3 (1-indexed)
        prs.save("deck.pptx")
    """
    from pptx.parts.slide import SlidePart
    from pptx.opc.constants import RELATIONSHIP_TYPE as RT

    if layout is None:
        layout = prs.slides[idx].slide_layout
    layout_part = layout.part

    drop_slide(prs, idx)

    # Pick a non-colliding partname via the package-level next_partname,
    # which scans iter_parts (correct). Bypass PresentationPart._next_slide_partname
    # (broken — uses naive len(sldIdLst)+1).
    pkg = prs.part.package
    partname = pkg.next_partname("/ppt/slides/slide%d.xml")

    new_slide_part = SlidePart.new(partname, pkg, layout_part)
    rId = prs.part.relate_to(new_slide_part, RT.SLIDE)

    # Wire up the new sldId in sldIdLst
    sldIdLst = prs.slides._sldIdLst
    new_sldId = sldIdLst.add_sldId(rId)

    new_slide = new_slide_part.slide
    build_fn(new_slide)

    # Move to target position
    sldIdLst.remove(new_sldId)
    sldIdLst.insert(idx, new_sldId)

    return new_slide


def replace_title(slide, bold_text, normal_text, *, size_pt=22):
    """Replace the title placeholder with a two-tone action title at its position.

    Names the replacement shape "Title 1" so downstream linters and QA tools
    that look up titles by name continue to work.
    """
    title_shape = None
    for shape in slide.shapes:
        if shape.name in ("Title 1", "Title"):
            title_shape = shape
            break
    if title_shape is None:
        new_box = two_tone_title(slide, 0.5, 0.55, 12.5, 0.85, bold_text,
                                 normal_text, size_pt=size_pt)
    else:
        x = Emu(title_shape.left).inches
        y = Emu(title_shape.top).inches
        w = Emu(title_shape.width).inches
        h = Emu(title_shape.height).inches

        title_shape._element.getparent().remove(title_shape._element)

        new_box = two_tone_title(slide, x, y, w, h, bold_text, normal_text,
                                 size_pt=size_pt)

    # Preserve the "Title 1" name on the replacement so QA tools find it
    new_box.name = "Title 1"
    return new_box


# ─────────────────────────────────────────────────────────────────────────────
# Recipe helpers
# ─────────────────────────────────────────────────────────────────────────────

def two_tone_title(slide, x, y, w, h, bold_text, normal_text,
                   font=None, size_pt=22, color=None):
    """Bold short claim + en-dash + normal-weight elaboration in one textbox."""
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Emu(0)
    tf.margin_top = tf.margin_bottom = Emu(0)
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT

    r1 = p.add_run()
    set_run(r1, bold_text, font=font or FONT_HEADING, size=size_pt,
            bold=True, color=color or TEXT_DARK)

    if normal_text:
        r2 = p.add_run()
        set_run(r2, " – " + normal_text, font=font or FONT_HEADING,
                size=size_pt, bold=False, color=color or TEXT_DARK)
    return box


def numbered_agenda_block(slide, x, y, w, h, number, topic,
                          numeral_color=None, bar_color=None,
                          topic_color=None, numeral_size=30, topic_size=13):
    """Large numeral + thin vertical accent bar + topic text. Stack vertically."""
    numeral_color = numeral_color or PRIMARY
    bar_color = bar_color or PRIMARY
    topic_color = topic_color or TEXT_DARK

    num_box = slide.shapes.add_textbox(Inches(x), Inches(y),
                                       Inches(0.55), Inches(h))
    tf = num_box.text_frame
    tf.margin_left = tf.margin_right = Emu(0)
    tf.margin_top = tf.margin_bottom = Emu(0)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    set_run(r, str(number), font=FONT_HEADING, size=numeral_size,
            bold=True, color=numeral_color)

    bar = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(x + 0.65), Inches(y + 0.10),
        Inches(0.06), Inches(h - 0.20))
    bar.fill.solid()
    bar.fill.fore_color.rgb = bar_color
    bar.line.fill.background()

    topic_box = slide.shapes.add_textbox(
        Inches(x + 0.85), Inches(y), Inches(w - 0.85), Inches(h))
    tf = topic_box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_left = Emu(0)
    tf.margin_top = tf.margin_bottom = Emu(0)
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    r = p.add_run()
    set_run(r, topic, font=FONT_BODY, size=topic_size, color=topic_color)


def section_header(slide, x, y, w, text, color=None, size_pt=14):
    """Centered bold section header above a column or sub-block."""
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(0.4))
    tf = box.text_frame
    tf.margin_left = tf.margin_right = Emu(0)
    tf.margin_top = tf.margin_bottom = Emu(0)
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    set_run(r, text, font=FONT_HEADING, size=size_pt, bold=True,
            color=color or PRIMARY)
    return box


def spotlight_callout(slide, x, y, label, icon_fn=None, color=None,
                      label_size_pt=11.5, icon_size=0.32):
    """Icon + bold label, used above a focus column."""
    color = color or PRIMARY
    if icon_fn is not None:
        icon_fn(slide, x, y, size=icon_size, color=color)
    label_box = slide.shapes.add_textbox(
        Inches(x + icon_size + 0.10), Inches(y - 0.02),
        Inches(3.0), Inches(0.35))
    tf = label_box.text_frame
    tf.margin_left = tf.margin_right = Emu(0)
    tf.margin_top = tf.margin_bottom = Emu(0)
    p = tf.paragraphs[0]
    r = p.add_run()
    set_run(r, label, font=FONT_HEADING, size=label_size_pt, bold=True,
            color=color)


def sub_callout_grid(slide, x, y, w, items, *, color=None, icon_size=0.55,
                     label_size_pt=12, caption_size_pt=10):
    """Render 2-3 icon+label+caption mini-cards in a horizontal row.

    items: list of dicts with keys {icon_fn, label, caption}.
    """
    color = color or PRIMARY
    n = len(items)
    cell_w = w / n
    for i, item in enumerate(items):
        cx = x + i * cell_w
        icon_x = cx + cell_w / 2 - icon_size / 2
        if item.get("icon_fn"):
            item["icon_fn"](slide, icon_x, y, size=icon_size, color=color)

        lbl = slide.shapes.add_textbox(
            Inches(cx), Inches(y + icon_size + 0.05),
            Inches(cell_w), Inches(0.30))
        tf = lbl.text_frame
        tf.margin_left = tf.margin_right = Emu(0)
        tf.margin_top = tf.margin_bottom = Emu(0)
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        set_run(r, item["label"], font=FONT_HEADING, size=label_size_pt,
                bold=True, color=TEXT_DARK)

        cap = slide.shapes.add_textbox(
            Inches(cx + 0.20), Inches(y + icon_size + 0.35),
            Inches(cell_w - 0.40), Inches(0.50))
        tf = cap.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = Emu(0)
        tf.margin_top = tf.margin_bottom = Emu(0)
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        set_run(r, item["caption"], font=FONT_BODY, size=caption_size_pt,
                color=TEXT_MUTED)


# ─────────────────────────────────────────────────────────────────────────────
# Icons — primitive-shape constructions
# ─────────────────────────────────────────────────────────────────────────────

def target_icon(slide, x, y, size=0.5, color=None):
    """Bullseye — three concentric circles."""
    color = color or PRIMARY
    outer = slide.shapes.add_shape(MSO_SHAPE.OVAL,
        Inches(x), Inches(y), Inches(size), Inches(size))
    outer.fill.background()
    outer.line.color.rgb = color
    outer.line.width = Pt(2.25)

    inset_m = size * 0.22
    middle = slide.shapes.add_shape(MSO_SHAPE.OVAL,
        Inches(x + inset_m), Inches(y + inset_m),
        Inches(size - 2 * inset_m), Inches(size - 2 * inset_m))
    middle.fill.background()
    middle.line.color.rgb = color
    middle.line.width = Pt(2.0)

    inset_d = size * 0.40
    dot = slide.shapes.add_shape(MSO_SHAPE.OVAL,
        Inches(x + inset_d), Inches(y + inset_d),
        Inches(size - 2 * inset_d), Inches(size - 2 * inset_d))
    dot.fill.solid()
    dot.fill.fore_color.rgb = color
    dot.line.fill.background()


def network_icon(slide, x, y, size=0.5, color=None):
    """Three nodes with connecting lines (people/alignment glyph)."""
    color = color or PRIMARY
    node_d = size * 0.30
    n1 = (x + size / 2 - node_d / 2, y)
    n2 = (x, y + size - node_d)
    n3 = (x + size - node_d, y + size - node_d)
    centers = [(n1[0] + node_d / 2, n1[1] + node_d / 2),
               (n2[0] + node_d / 2, n2[1] + node_d / 2),
               (n3[0] + node_d / 2, n3[1] + node_d / 2)]
    for i, j in [(0, 1), (0, 2), (1, 2)]:
        line = slide.shapes.add_connector(1,
            Inches(centers[i][0]), Inches(centers[i][1]),
            Inches(centers[j][0]), Inches(centers[j][1]))
        line.line.color.rgb = color
        line.line.width = Pt(1.75)
    for nx, ny in [n1, n2, n3]:
        node = slide.shapes.add_shape(MSO_SHAPE.OVAL,
            Inches(nx), Inches(ny), Inches(node_d), Inches(node_d))
        node.fill.solid()
        node.fill.fore_color.rgb = color
        node.line.fill.background()


def globe_icon(slide, x, y, size=0.5, color=None):
    """Circle + meridian + equator."""
    color = color or CONTEXT_GREY
    outer = slide.shapes.add_shape(MSO_SHAPE.OVAL,
        Inches(x), Inches(y), Inches(size), Inches(size))
    outer.fill.background()
    outer.line.color.rgb = color
    outer.line.width = Pt(2.0)

    mer_w = size * 0.32
    meridian = slide.shapes.add_shape(MSO_SHAPE.OVAL,
        Inches(x + (size - mer_w) / 2), Inches(y),
        Inches(mer_w), Inches(size))
    meridian.fill.background()
    meridian.line.color.rgb = color
    meridian.line.width = Pt(1.5)

    eq = slide.shapes.add_connector(1,
        Inches(x), Inches(y + size / 2),
        Inches(x + size), Inches(y + size / 2))
    eq.line.color.rgb = color
    eq.line.width = Pt(1.5)


def gear_icon(slide, x, y, size=0.5, color=None):
    """Simple gear — outer toothed circle + inner hub."""
    color = color or PRIMARY
    # Outer ring (the toothed approximation — just a thicker circle for now)
    outer = slide.shapes.add_shape(MSO_SHAPE.OVAL,
        Inches(x), Inches(y), Inches(size), Inches(size))
    outer.fill.background()
    outer.line.color.rgb = color
    outer.line.width = Pt(3.0)
    # Inner hub
    hub_inset = size * 0.30
    hub = slide.shapes.add_shape(MSO_SHAPE.OVAL,
        Inches(x + hub_inset), Inches(y + hub_inset),
        Inches(size - 2 * hub_inset), Inches(size - 2 * hub_inset))
    hub.fill.solid()
    hub.fill.fore_color.rgb = color
    hub.line.fill.background()
    # Small notches at 12/3/6/9 positions
    notch_d = size * 0.15
    notch_offset = size * 0.42
    for nx, ny in [
        (x + size / 2 - notch_d / 2, y - notch_d / 3),  # top
        (x + size - notch_d / 3, y + size / 2 - notch_d / 2),  # right
        (x + size / 2 - notch_d / 2, y + size - 2 * notch_d / 3),  # bottom
        (x - notch_d / 3, y + size / 2 - notch_d / 2),  # left
    ]:
        notch = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
            Inches(nx), Inches(ny), Inches(notch_d), Inches(notch_d))
        notch.fill.solid()
        notch.fill.fore_color.rgb = color
        notch.line.fill.background()


def magnifier_icon(slide, x, y, size=0.5, color=None):
    """Magnifying glass — circle + diagonal handle line."""
    color = color or PRIMARY
    lens_d = size * 0.65
    lens = slide.shapes.add_shape(MSO_SHAPE.OVAL,
        Inches(x), Inches(y), Inches(lens_d), Inches(lens_d))
    lens.fill.background()
    lens.line.color.rgb = color
    lens.line.width = Pt(2.5)
    # Handle from lens edge to corner
    handle = slide.shapes.add_connector(1,
        Inches(x + lens_d * 0.85), Inches(y + lens_d * 0.85),
        Inches(x + size), Inches(y + size))
    handle.line.color.rgb = color
    handle.line.width = Pt(3.0)


def check_icon(slide, x, y, size=0.5, color=None):
    """Checkmark inside a circle — for sign-off / approval."""
    color = color or PRIMARY
    circle = slide.shapes.add_shape(MSO_SHAPE.OVAL,
        Inches(x), Inches(y), Inches(size), Inches(size))
    circle.fill.solid()
    circle.fill.fore_color.rgb = color
    circle.line.fill.background()
    # Check stroke (two connectors forming a check)
    stroke1 = slide.shapes.add_connector(1,
        Inches(x + size * 0.22), Inches(y + size * 0.50),
        Inches(x + size * 0.42), Inches(y + size * 0.70))
    stroke1.line.color.rgb = WHITE
    stroke1.line.width = Pt(2.5)
    stroke2 = slide.shapes.add_connector(1,
        Inches(x + size * 0.42), Inches(y + size * 0.70),
        Inches(x + size * 0.78), Inches(y + size * 0.30))
    stroke2.line.color.rgb = WHITE
    stroke2.line.width = Pt(2.5)


def lightning_icon(slide, x, y, size=0.5, color=None):
    """Lightning bolt — single filled shape (uses LIGHTNING_BOLT auto-shape)."""
    color = color or PRIMARY
    bolt = slide.shapes.add_shape(MSO_SHAPE.LIGHTNING_BOLT,
        Inches(x), Inches(y), Inches(size), Inches(size))
    bolt.fill.solid()
    bolt.fill.fore_color.rgb = color
    bolt.line.fill.background()


# ─────────────────────────────────────────────────────────────────────────────
# Connector helpers
# ─────────────────────────────────────────────────────────────────────────────

def mapping_table_with_status(slide, x, y, w, rows, *,
                              status_col_w=0.60,
                              column_headers=("Source", "Target", "Status"),
                              column_widths=None,
                              row_h=0.30,
                              category_row_h=0.30,
                              header_row_h=0.35,
                              min_row_h=0.18,
                              footer_clearance_y=6.55,
                              status_styles=None,
                              category_tint=None,
                              alt_row_fill=None):
    """Render a mapping table with status badges.

    rows: list of dicts with keys {category, source, target, status}.
          Optional extra cols handled by `column_headers` length.
    column_headers: tuple of header labels (Source, Target, Status by default).
                   The first non-status column is treated as the source label,
                   the second as the target label, the third+ as status.
    column_widths: optional list of float widths in inches summing to (w - status_col_w).
                   If None, splits remaining width evenly across non-status cols.
    row_h: starting body row height. Auto-shrunk to fit footer_clearance_y.
    category_tint: pale fill for category-grouping rows. Defaults to ~10% tint of PRIMARY.
    status_styles: dict mapping status glyph → {fill: RGBColor, text_color: RGBColor}.

    Returns dict with computed metrics: {actual_row_h, total_height, status_counts, headline}.
    """
    if status_styles is None:
        # Defaults: primary green = ✓, accent orange = ◐, context grey = ○
        status_styles = {
            "✓": {"fill": PRIMARY,        "text_color": WHITE},
            "◐": {"fill": SIGNOFF_ACCENT, "text_color": WHITE},
            "○": {"fill": CONTEXT_GREY,   "text_color": WHITE},
            "N/A": {"fill": LATER_FILL,   "text_color": TEXT_MUTED},
        }
    if category_tint is None:
        # ~12% tint of primary — manually computed for default green
        category_tint = RGBColor(0xE5, 0xF5, 0xEC)
    if alt_row_fill is None:
        alt_row_fill = RGBColor(0xF8, 0xF8, 0xFA)

    # Auto-shrink row_h to fit footer-clearance budget
    n_body_rows = len(rows)
    # Count category transitions for category rows
    category_rows = []
    last_cat = None
    for r in rows:
        cat = r.get("category", "")
        if cat and cat != last_cat:
            category_rows.append(cat)
            last_cat = cat
    n_cat_rows = len(category_rows)

    def total_h(rh, crh):
        return header_row_h + n_cat_rows * crh + n_body_rows * rh

    avail_h = footer_clearance_y - y - 0.10  # 0.10" cushion
    actual_row_h = row_h
    actual_cat_row_h = category_row_h
    while total_h(actual_row_h, actual_cat_row_h) > avail_h and actual_row_h > min_row_h:
        actual_row_h = max(min_row_h, actual_row_h - 0.02)
        actual_cat_row_h = max(min_row_h + 0.02, actual_cat_row_h - 0.02)
    if total_h(actual_row_h, actual_cat_row_h) > avail_h:
        # Cannot fit even at minimum row_h — caller should split into a continuation slide
        pass

    # Compute column widths
    n_non_status = len(column_headers) - 1
    if column_widths is None:
        non_status_w = (w - status_col_w) / n_non_status
        column_widths = [non_status_w] * n_non_status
    column_widths = list(column_widths) + [status_col_w]

    # Helper to draw a cell
    def cell(cx, cy, cw, ch, text, *, fill=None, text_color=None, bold=False,
             size=10, align=PP_ALIGN.LEFT, italic=False):
        rect = add_rect(slide, cx, cy, cw, ch,
                        fill=fill, line=LATER_BORDER, line_w_pt=0.5)
        if text:
            add_text_to_shape(rect, text, font=FONT_BODY, size=size, bold=bold,
                              italic=italic, color=text_color or TEXT_DARK,
                              align=align, vert=MSO_ANCHOR.MIDDLE, margin=0.06)
        return rect

    # Header row
    cy = y
    cx = x
    for i, header in enumerate(column_headers):
        cell(cx, cy, column_widths[i], header_row_h, header,
             fill=TEXT_DARK, text_color=WHITE, bold=True, size=10,
             align=PP_ALIGN.CENTER if i == n_non_status else PP_ALIGN.LEFT)
        cx += column_widths[i]
    cy += header_row_h

    # Body rows with category groupings
    last_cat = None
    body_row_idx = 0
    for r in rows:
        cat = r.get("category", "")
        if cat and cat != last_cat:
            # Category row spans full width
            cell(x, cy, w, actual_cat_row_h, cat,
                 fill=category_tint, bold=True, size=11, align=PP_ALIGN.LEFT)
            cy += actual_cat_row_h
            last_cat = cat

        # Body row
        row_fill = alt_row_fill if body_row_idx % 2 == 1 else WHITE
        cx = x
        # Non-status columns
        for i, key in enumerate(("source", "target")):
            text = r.get(key, "")
            cell(cx, cy, column_widths[i], actual_row_h, text,
                 fill=row_fill, size=9.5, align=PP_ALIGN.LEFT)
            cx += column_widths[i]
        # Status column
        status = r.get("status", "")
        style = status_styles.get(status, {"fill": LATER_FILL, "text_color": TEXT_MUTED})
        cell(cx, cy, column_widths[-1], actual_row_h, status,
             fill=style["fill"], text_color=style["text_color"],
             bold=True, size=11, align=PP_ALIGN.CENTER)
        cy += actual_row_h
        body_row_idx += 1

    # Compute status counts
    status_counts = {}
    for r in rows:
        s = r.get("status", "")
        status_counts[s] = status_counts.get(s, 0) + 1

    # Build headline string
    parts = []
    if "✓" in status_counts:    parts.append(f"{status_counts['✓']} ✓ mapped")
    if "◐" in status_counts:    parts.append(f"{status_counts['◐']} ◐ partial")
    if "○" in status_counts:    parts.append(f"{status_counts['○']} ○ gap")
    if "N/A" in status_counts:  parts.append(f"{status_counts['N/A']} N/A")
    headline = f"Of {len(rows)} rows: " + ", ".join(parts) if parts else f"{len(rows)} rows"

    return {
        "actual_row_h": actual_row_h,
        "total_height": cy - y,
        "bottom_y": cy,
        "status_counts": status_counts,
        "headline": headline,
    }


def tier_scale(slide, x, y, w, tiers, overlays=None, *,
               h=0.45, label_above=True, color_palette=None):
    """Horizontal tier band — 3+ adjacent boxes for Low/Med/High style scale,
    with optional overlay markers above (e.g., PEFP / Prohibitive Country / STR).

    tiers: list of dicts {label, fill (optional), text_color (optional)}.
           If fill omitted, uses gradient from light to brand-color across tiers.
    overlays: optional list of dicts {label, position (0.0-1.0 along the band),
              color (default=accent)} — small triangles + text labels above the band.

    Returns dict {bottom_y, width_each_tier}.
    """
    n = len(tiers)
    if n == 0:
        return None

    # Default palette: light grey → brand-light → brand-color
    if color_palette is None:
        # Auto-generate a 3-tier ramp; for >3 tiers, repeat the pattern
        if n == 3:
            color_palette = [LATER_FILL, RGBColor(0xCC, 0xED, 0xDB), PRIMARY]
        else:
            # Linear interp light → dark
            from_rgb = (0xF2, 0xF2, 0xF4)
            to_rgb = tuple(int(c, 16) for c in (str(PRIMARY)[0:2], str(PRIMARY)[2:4], str(PRIMARY)[4:6]))
            color_palette = []
            for i in range(n):
                frac = i / max(1, n - 1)
                r = int(from_rgb[0] + (to_rgb[0] - from_rgb[0]) * frac)
                g = int(from_rgb[1] + (to_rgb[1] - from_rgb[1]) * frac)
                b = int(from_rgb[2] + (to_rgb[2] - from_rgb[2]) * frac)
                color_palette.append(RGBColor(r, g, b))

    tier_w = w / n
    band_y = y + (0.4 if overlays and label_above else 0)

    # Tier boxes
    for i, tier in enumerate(tiers):
        tx = x + i * tier_w
        fill = tier.get("fill") or color_palette[i]
        text_color = tier.get("text_color")
        if text_color is None:
            # Auto-pick: white if fill is dark-ish, dark text otherwise
            r, g, b = (int(str(fill)[i:i+2], 16) for i in (0, 2, 4))
            luma = 0.299 * r + 0.587 * g + 0.114 * b
            text_color = WHITE if luma < 140 else TEXT_DARK
        rect = add_rect(slide, tx, band_y, tier_w, h, fill=fill,
                        line=LATER_BORDER, line_w_pt=0.5)
        add_text_to_shape(rect, tier["label"], font=FONT_HEADING, size=11,
                          bold=True, color=text_color,
                          align=PP_ALIGN.CENTER, vert=MSO_ANCHOR.MIDDLE)

    # Overlay markers (above the band)
    if overlays:
        for ov in overlays:
            pos = max(0.0, min(1.0, ov.get("position", 0.5)))
            ox = x + pos * w
            color = ov.get("color") or SIGNOFF_ACCENT
            # Small downward triangle pointing into the band
            tri_size = 0.12
            tri = slide.shapes.add_shape(MSO_SHAPE.DOWN_ARROW,
                Inches(ox - tri_size / 2), Inches(band_y - tri_size - 0.02),
                Inches(tri_size), Inches(tri_size))
            tri.fill.solid()
            tri.fill.fore_color.rgb = color
            tri.line.fill.background()
            # Label above triangle
            lbl = slide.shapes.add_textbox(
                Inches(ox - 1.0), Inches(band_y - 0.40),
                Inches(2.0), Inches(0.22))
            tf = lbl.text_frame
            tf.margin_left = tf.margin_right = Emu(0)
            tf.margin_top = tf.margin_bottom = Emu(0)
            p = tf.paragraphs[0]
            p.alignment = PP_ALIGN.CENTER
            r = p.add_run()
            set_run(r, ov["label"], font=FONT_BODY, size=8.5, bold=True,
                    color=color)

    return {"bottom_y": band_y + h, "width_each_tier": tier_w}


def process_flow(slide, x, y, w, steps, annotations=None, *,
                 step_h=0.55, fill=None, text_color=None,
                 arrow_color=None, label_above=True):
    """Boxes + arrows for left-to-right flows (e.g., Source → DMO → AML Manager → PRM).

    steps: list of strings (step labels) OR list of dicts {label, fill (optional),
           sublabel (optional)}.
    annotations: optional list of strings positioned above each step (None = no annotation).

    Returns dict {bottom_y, step_w}.
    """
    n = len(steps)
    if n == 0:
        return None

    fill = fill or PRIMARY
    text_color = text_color or WHITE
    arrow_color = arrow_color or CONTEXT_GREY

    # Reserve space for arrows: ~0.30" gap between boxes
    gap = 0.30
    step_w = (w - gap * (n - 1)) / n
    box_y = y + (0.30 if annotations else 0)

    for i, step in enumerate(steps):
        sx = x + i * (step_w + gap)
        if isinstance(step, dict):
            label = step.get("label", "")
            sub = step.get("sublabel")
            box_fill = step.get("fill") or fill
        else:
            label = str(step)
            sub = None
            box_fill = fill
        rect = add_rect(slide, sx, box_y, step_w, step_h, fill=box_fill,
                        line=box_fill, line_w_pt=0.5, rounded=True)
        # Label
        tf = rect.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        tf.margin_left = Inches(0.08)
        tf.margin_right = Inches(0.08)
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        set_run(r, label, font=FONT_HEADING, size=11.5, bold=True,
                color=text_color)
        if sub:
            p2 = tf.add_paragraph()
            p2.alignment = PP_ALIGN.CENTER
            r2 = p2.add_run()
            set_run(r2, sub, font=FONT_BODY, size=9, color=text_color)

        # Annotation above
        if annotations and i < len(annotations) and annotations[i]:
            ann = slide.shapes.add_textbox(
                Inches(sx), Inches(y),
                Inches(step_w), Inches(0.25))
            tf = ann.text_frame
            tf.margin_left = tf.margin_right = Emu(0)
            tf.margin_top = tf.margin_bottom = Emu(0)
            p = tf.paragraphs[0]
            p.alignment = PP_ALIGN.CENTER
            r = p.add_run()
            set_run(r, annotations[i], font=FONT_BODY, size=8.5, italic=True,
                    color=TEXT_MUTED)

        # Arrow to next step
        if i < n - 1:
            ax_start = sx + step_w
            ax_end = ax_start + gap
            ay = box_y + step_h / 2
            add_arrow(slide, ax_start, ay, ax_end, ay,
                      color=arrow_color, width_pt=2.0, head_size="med")

    return {"bottom_y": box_y + step_h, "step_w": step_w}


def block_list(slide, x, y, w, items, caption=None, *,
               item_h=0.35, item_fill=None, item_text_color=None,
               caption_size_pt=10, item_size_pt=10):
    """Small labeled block row — short rectangles with text, side-by-side.
    Use for input categories, dimension lists, factor groupings.

    items: list of strings.
    caption: optional caption above the block row.

    Returns dict {bottom_y, item_w}.
    """
    n = len(items)
    if n == 0:
        return None

    item_fill = item_fill or LATER_FILL
    item_text_color = item_text_color or TEXT_DARK

    cy = y
    if caption:
        cap_box = slide.shapes.add_textbox(Inches(x), Inches(cy),
                                            Inches(w), Inches(0.22))
        tf = cap_box.text_frame
        tf.margin_left = tf.margin_right = Emu(0)
        tf.margin_top = tf.margin_bottom = Emu(0)
        p = tf.paragraphs[0]
        r = p.add_run()
        set_run(r, caption, font=FONT_HEADING, size=caption_size_pt, bold=True,
                color=TEXT_DARK)
        cy += 0.28

    gap = 0.10
    item_w = (w - gap * (n - 1)) / n
    for i, item in enumerate(items):
        ix = x + i * (item_w + gap)
        rect = add_rect(slide, ix, cy, item_w, item_h,
                        fill=item_fill,
                        line=LATER_BORDER, line_w_pt=0.5,
                        rounded=True, corner_radius=0.15)
        add_text_to_shape(rect, item, font=FONT_BODY, size=item_size_pt,
                          bold=True, color=item_text_color,
                          align=PP_ALIGN.CENTER, vert=MSO_ANCHOR.MIDDLE)

    return {"bottom_y": cy + item_h, "item_w": item_w}


def add_arrow(slide, x1, y1, x2, y2, color=None, width_pt=2.0,
              dash=False, head_size="med"):
    """Straight connector with arrowhead at end."""
    color = color or PRIMARY
    arrow = slide.shapes.add_connector(1,
        Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    arrow.line.color.rgb = color
    arrow.line.width = Pt(width_pt)
    ln = arrow.line._get_or_add_ln()
    if dash:
        prstDash = etree.SubElement(ln, qn("a:prstDash"))
        prstDash.set("val", "dash")
    tail = etree.SubElement(ln, qn("a:tailEnd"))
    tail.set("type", "triangle")
    tail.set("w", head_size)
    tail.set("h", head_size)
    return arrow


def add_line(slide, x1, y1, x2, y2, color=None, width_pt=1.0, dash=False):
    """Plain straight line."""
    color = color or LATER_BORDER
    line = slide.shapes.add_connector(1,
        Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    line.line.color.rgb = color
    line.line.width = Pt(width_pt)
    if dash:
        ln = line.line._get_or_add_ln()
        prstDash = etree.SubElement(ln, qn("a:prstDash"))
        prstDash.set("val", "dash")
    return line
