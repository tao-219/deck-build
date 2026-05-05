# Helper Internals — what each recipe in `deck_helpers.py` does

This file documents the implementation of each recipe in `${CLAUDE_PLUGIN_ROOT}/scripts/deck_helpers.py` for readers who want to understand or extend the helpers without opening the source.

**Source of truth: `${CLAUDE_PLUGIN_ROOT}/scripts/deck_helpers.py`.** The snippets below are illustrative — the module is canonical, and minor signature differences may exist (e.g., parameters added for color/font overrides). Read the module when in doubt.

## Constants block (default Manulife palette)

```python
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn
from lxml import etree

PRIMARY        = RGBColor(0x00, 0xA7, 0x58)   # Manulife green (CURRENT / focus)
LATER_FILL     = RGBColor(0xF2, 0xF2, 0xF4)
LATER_BORDER   = RGBColor(0xD9, 0xDA, 0xDF)
SIGNOFF_FILL   = RGBColor(0xFF, 0xF4, 0xE0)   # cream
SIGNOFF_ACCENT = RGBColor(0xF4, 0x96, 0x00)   # accent orange
CONTEXT_GREY   = RGBColor(0x8E, 0x90, 0xA2)
TEXT_DARK      = RGBColor(0x26, 0x26, 0x26)
TEXT_MUTED     = RGBColor(0x59, 0x59, 0x59)
WHITE          = RGBColor(0xFF, 0xFF, 0xFF)

FONT_HEADING = "Manulife JH Sans"
FONT_BODY    = "Manulife JH Sans"
```

Override via `set_palette(primary=..., context_grey=..., ...)` and `set_fonts(heading=..., body=...)` — both module-level functions.

## Recipe 1: `two_tone_title(slide, x, y, w, h, bold_text, normal_text)`

Renders an action title with bold short claim + en-dash + normal-weight elaboration in a single textbox. Two `add_run()` calls in the same paragraph; only `font.bold` differs between runs.

```python
def two_tone_title(slide, x, y, w, h, bold_text, normal_text,
                   font=FONT_HEADING, size_pt=22, color=TEXT_DARK):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Emu(0)
    tf.margin_top = tf.margin_bottom = Emu(0)
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    r1 = p.add_run()
    r1.text = bold_text
    r1.font.bold = True
    r1.font.name = font
    r1.font.size = Pt(size_pt)
    r1.font.color.rgb = color
    if normal_text:
        r2 = p.add_run()
        r2.text = " – " + normal_text
        r2.font.bold = False
        r2.font.name = font
        r2.font.size = Pt(size_pt)
        r2.font.color.rgb = color
    return box
```

## Recipe 2: `numbered_agenda_block(slide, x, y, w, h, number, topic)`

Three shapes per block: large numeral textbox (left), thin vertical accent bar (middle), topic textbox (right). All share the same y-extent so the eye reads horizontally.

```python
def numbered_agenda_block(slide, x, y, w, h, number, topic,
                          numeral_color=PRIMARY, bar_color=PRIMARY,
                          topic_color=TEXT_DARK):
    # Numeral
    num_box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(0.55), Inches(h))
    # ...sets centered 30pt bold numeral...

    # Vertical accent bar
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
        Inches(x + 0.65), Inches(y + 0.10),
        Inches(0.06), Inches(h - 0.20))
    bar.fill.solid()
    bar.fill.fore_color.rgb = bar_color

    # Topic textbox
    topic_box = slide.shapes.add_textbox(Inches(x + 0.85), Inches(y),
                                          Inches(w - 0.85), Inches(h))
    # ...sets vertically-centered 13pt topic text...
```

## Recipe 3: `spotlight_callout(slide, x, y, label, icon_fn, color)`

Icon + bold label, used above a focus column in `spotlight-comparison-columns`. Calls one of the icon-helper functions to render the glyph, then places the label textbox with `icon_size + 0.10"` horizontal offset.

## Recipe 4: `sub_callout_grid(slide, x, y, w, items)`

Renders 2–3 icon+label+caption mini-cards in a horizontal row. `items` is a list of dicts `{icon_fn, label, caption}`. Cell width = `w / len(items)`; icon centered in cell; label and caption stacked below.

## Recipe 5: simple icon constructors

Each icon is composed of primitive `add_shape(MSO_SHAPE.OVAL)` and `add_connector()` calls. Not pixel-perfect to a designed icon set, but consistent across slides. For higher-fidelity icons, embed PNGs from a brand asset library and use `slide.shapes.add_picture()` instead.

Available icons:
- `target_icon` — three concentric circles (bullseye)
- `network_icon` — three nodes + three connecting lines
- `globe_icon` — circle + meridian + equator
- `gear_icon` — circle with hub + 4 notches
- `magnifier_icon` — circle + diagonal handle
- `check_icon` — filled circle + white check stroke
- `lightning_icon` — `MSO_SHAPE.LIGHTNING_BOLT` autoshape

All take `(slide, x, y, size=0.5, color=PRIMARY)` and render at the given inch coordinates.

## Recipe 6: shape strip-and-keep

Pre-rebuild discipline. Always inventory the slide first:

```python
for s in slide.shapes:
    print(s.name, s.shape_type)
```

Then call `strip_shapes(slide, keep_names={...})` (whitelist) or `strip_shapes(slide, remove_names={...})` (blacklist). Never guess — always inventory first.

```python
def strip_shapes(slide, keep_names=None, remove_names=None):
    spTree = slide.shapes._spTree
    to_remove = []
    for shape in slide.shapes:
        if keep_names is not None and shape.name not in keep_names:
            to_remove.append(shape)
        elif remove_names is not None and shape.name in remove_names:
            to_remove.append(shape)
    for shape in to_remove:
        spTree.remove(shape._element)
```

## Recipe 7: `replace_title(slide, bold_text, normal_text)`

Replaces the existing title placeholder with a two-tone action title at the same x/y/w/h. Critically, names the replacement shape `"Title 1"` so downstream linters and QA tools that look up titles by name continue to work.

```python
def replace_title(slide, bold_text, normal_text, *, size_pt=22):
    title_shape = next((s for s in slide.shapes if s.name in ("Title 1", "Title")), None)
    if title_shape:
        x, y, w, h = (Emu(c).inches for c in (title_shape.left, title_shape.top,
                                              title_shape.width, title_shape.height))
        title_shape._element.getparent().remove(title_shape._element)
        new_box = two_tone_title(slide, x, y, w, h, bold_text, normal_text, size_pt=size_pt)
    else:
        new_box = two_tone_title(slide, 0.5, 0.55, 12.5, 0.85, bold_text, normal_text, size_pt=size_pt)
    new_box.name = "Title 1"  # Preserve name for QA tools
    return new_box
```

## Recipe 8: `add_arrow` and `add_line`

Connector helpers with optional dash + arrowhead via lxml `prstDash` and `tailEnd` elements:

```python
def add_arrow(slide, x1, y1, x2, y2, color=PRIMARY, width_pt=2.0,
              dash=False, head_size="med"):
    arrow = slide.shapes.add_connector(1, Inches(x1), Inches(y1),
                                       Inches(x2), Inches(y2))
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
```
