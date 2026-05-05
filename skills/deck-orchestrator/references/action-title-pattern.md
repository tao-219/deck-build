# Action Title Pattern

Every slide title must be a **complete sentence with a verb** that states a conclusion. Not a topic.

## The "So What?" test

If an executive read only the slide titles top-to-bottom, would they understand the entire argument?

If not, the titles are topic-based (failure). Fix them.

## Hard rules

- Maximum **15 words**.
- Maximum **2 lines** when rendered.
- Active voice. ("Sales grew 22%" not "There was 22% growth in sales").
- Specific numbers when defending a quantitative claim.
- Verb in the sentence (declarative, not nominal).
- No trailing period.

## Visual rendering: two-tone titles

The default rendering for action titles is **two-tone**: a bold short claim, then an en-dash (`–`), then a normal-weight elaboration. This creates a clear visual hierarchy between the headline and the supporting context.

```
[BOLD short claim] – [normal-weight elaboration / qualifier list]
```

Examples (boldfaced runs marked):

- **`Workshop 1 of 4 within Stage 1`** – `together these workshops inform Stage 1 sign-off on the conceptual CRR risk factor list per jurisdiction and the number of models decision for Canada`
- **`Three regional CRR schemes operate today`** – `Canada 3-tier point based, and APAC tiered (varies by jurisdiction), US trigger-based without CRR`
- **`SAI OOTB covers 70% of AML Manager factors`** – `six factors require custom configuration, concentrated in Geography and Product`

**When NOT to use two-tone:**
- The title is short (≤8 words) and entirely the claim — no supporting context to subordinate.
- The slide is a section divider or title cover (different typography rules apply).

**Implementation note:** in python-pptx, two-tone is rendered as two runs in the same paragraph — the first run with `font.bold = True`, the second with `font.bold = False`. Both runs share the same font family and size; weight is the only variable.

## Inline scope qualifier convention

When a header, column label, or row label needs context, append the qualifier in parens:

```
Canada Market (AML Manager)
APAC (AML Manager)
US (No CRR Model)
```

The qualifier names the tool, scope, jurisdiction, or other context that prevents the reader from having to ask "in what scope?" Use this for column headers in `spotlight-comparison-columns`, row labels in coverage tables, and anywhere a reader might otherwise be confused.

Do NOT push the qualifier into the action title — the title carries the conclusion; qualifiers live with the data they describe.

## Topic title vs action title

| Topic title (BAD) | Action title (GOOD) |
|---|---|
| Market Overview | The North American AML software market grew 18% in 2025, outpacing Europe |
| Our Approach | A two-phase rollout cuts implementation risk by sequencing data quality before model tuning |
| Findings | Three of the model's five risk factors lack documented thresholds, creating audit exposure |
| Next Steps | The MAA approves Phase 2 by March 15 to keep the implementation on schedule |
| Q3 Results | Q3 alert volume rose 22% but escalation rate held at 12%, indicating tuning is working |
| Recommendation | Adopt the SAI CDD module on Stage 1 (configuration over BYOM) to compress timeline by 4 months |
| Background | The 2025 OSFI audit flagged seven high-priority CRR gaps; six are now remediated |
| Risk Assessment | The proposed threshold cutover at 90th percentile creates a 4x alert volume spike — lower it to 75th |

## Diagnostic questions when writing a title

1. Is there a verb? (If no: rewrite.)
2. Is there a number? (If the slide is quantitative: yes.)
3. Does it state the conclusion, not the topic? (Read it aloud — does it answer "so what?")
4. Could this title appear in the executive summary verbatim? (If yes: good. If it sounds like a section header in a textbook: rewrite.)

## When the slide is qualitative

Qualitative slides (frameworks, comparisons, narratives) still get action titles — they just describe the relationship rather than a number.

| Topic | Action |
|---|---|
| Operating Model | The proposed operating model splits Tier 1 alerts to a centralized hub; Tier 2/3 stay regional |
| Regulatory Landscape | Three new 2026 regulations (FINTRAC 24-hour, OSFI E-23, SR 26-2) require model updates by June |
| Stakeholder Map | Deloitte runs implementation; Manulife owns governance; FCMV provides validation oversight |

## Common failure modes

- **The "and" trap**: "Approach and Findings" → split into two slides, each with its own action title.
- **The hedge**: "Initial findings suggest" → drop the hedge, state the finding.
- **The throat-clear**: "An overview of the methodology" → drop "an overview of"; just describe the methodology.
- **The compound subject**: "Risk, Cost, and Timing Considerations" → pick the one that matters most for this slide; the others go elsewhere.
- **The label**: "Phase 1: Discovery" → "Phase 1 (Discovery) maps source-system data quality before scoping the rule set" — explain what's discovered and why.

## Title writing process

1. Draft the slide content first.
2. Write the conclusion in one sentence ("so what?").
3. Compress to ≤15 words.
4. Verify: verb present, active voice, specific.
5. Read it as part of the title sequence — does it advance the argument?

## Banned weasel words

These are vague and add no information. Strip them.

- "Leverage"
- "Harness"
- "Synergy"
- "Robust" (unless quantified)
- "Best-in-class"
- "Industry-leading"
- "Going forward"
- "At the end of the day"
- "Holistic approach"
- "Strategic" (used as filler — only keep if it's the actual subject)
