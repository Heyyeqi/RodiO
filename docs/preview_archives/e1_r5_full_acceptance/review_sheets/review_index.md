# E1-R5 Review Sheets Index

**Generated:** 2026-06-09 16:02
**Source:** `previews/e1_r5_full_acceptance/` (no new screenshots taken)

---

## Sheet 1 — D5z_b All Regions × Time Modes

`review_d5z_b_all_regions_by_time.png`

| | |
|---|---|
| **Content** | 9 regions × 4 time modes (36 cells) |
| **Variant** | D5z_b only |
| **Source dir** | `previews/e1_r5_full_acceptance/d5z_b/` |
| **Source pattern** | `e1r5_d5z_b_{region}_{time}.png` |

**Review focus:**
- ⬡ Protected regions (amber label): Japan, Mediterranean, Caribbean, Pacific Islands — check for any visible regression
- Cross-time-mode consistency: no style jumps between morning / noon / afternoon / sunset per row
- Antarctica / Greenland: ice should be darker than baseline, remain near-neutral white (not grey/dirty)
- Sahara: noon highlight should be more controlled vs E1-R4A baseline; warm desert tone must persist
- Europe / Middle East row: verify no hard boundary line between Sahara correction zone and Mediterranean

---

## Sheet 2 — D5z_b vs Baseline, 5 Key Regions

`review_d5z_b_vs_baseline_key_regions.png`

| | |
|---|---|
| **Content** | 5 key regions × 4 time modes × 2 variants = 40 cells |
| **Variants** | D5z_b (top row, blue label) vs d5b_design_v3_2_1 (bottom row, warm label) |
| **Key regions** | Sahara / Egypt · Antarctica · Greenland / Arctic · Mediterranean · Indian Ocean |
| **Source dirs** | `d5z_b/` and `d5b_design_v3_2_1/` |

**Review focus (per region pair):**
- **Sahara:** D5z_b noon row should show reduced highlight vs baseline noon row; warm color must be preserved, not grey/green
- **Antarctica:** D5z_b ice should be visibly darker under noon/afternoon; verify no grey/dirty tint
- **Greenland:** same as Antarctica; morning/sunset rows important for checking near-white preservation
- **Mediterranean:** D5z_b and baseline should be visually indistinguishable (protected zone, zero regression allowed)
- **Indian Ocean:** D5z_b should show slightly less 'map-texture' feel in deep zone; some reduction acceptable even if incomplete

---

## Sheet 3 — UI Integration (Standard Player View)

`review_ui_integration_d5z_b.png`

| | |
|---|---|
| **Content** | 4 time modes at standard player view (lon=10 lat=20) |
| **Variant** | D5z_b only |
| **Source** | `e1r5_d5z_b_ui_player_{morning,noon,afternoon,sunset}.png` |
| **Thumbnail size** | 720×450 (50% of 1440×900) |

**Review focus:**
- **UI readability:** Waiting text / controls remain legible across all 4 time modes
- **Over-exposure:** globe must not over-expose or visually overpower the player UI elements
- **Color harmony:** noon / afternoon / sunset globe color should coordinate with the light-blue UI background (not clash)
- **Immersive feel:** the overall impression should read as 'living globe radio background', not 'GIS map application'
- Morning and sunset are the critical edge cases — low-angle lighting can either add atmosphere or create harsh contrast

---

## Verdict Template

After reviewing the 3 sheets, fill in `docs/e1_r5_full_on_globe_acceptance.md`.

**Conditional Pass requires:**
- At most 2 criteria = Partial (only Antarctica/Greenland brightness or Indian Ocean texture)
- All protected regions (⬡) = Pass
- Sahara warm color = Pass (not grey/green)
- No hard boundary in Europe/Middle East
- No cross-time-mode style jumps
- All 4 UI Integration criteria = Pass

`DAY_TEXTURE_VARIANT` remains `'bmng_d2'` — E1-R6 requires explicit RW authorization after E1-R5 verdict.