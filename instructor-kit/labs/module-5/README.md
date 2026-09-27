# Module 5 Labs: Design Systems & Type (Session 5)

Module 5 turns one good design into a small production system, around one running brand:
**Northwind · Coastal Coffee Roasters** (the example from Lesson 5.1). Learners build a type
system from a modular scale, named styles and a grid (L13), a reusable Smart-Object mockup
and a linked logo that updates itself (L14), then a full campaign (poster, IG square, story,
banner) from one master file with linked art and shared styles, exported in one pass (L15,
the Module 5 deliverable).

**Save chain.** Everything lives in ONE project folder that never moves (suggested name
`northwind-campaign/`). At the start of the session learners copy `l14-logo-v1.png` into it
as `logo.png`.

| Lesson | Suggested file (in the project folder) | Used again in |
|---|---|---|
| L13 (5.1) | `type-system.psd` (its Paragraph/Character Styles) | L15: copy a styled text layer in and its styles come along |
| L14 (5.2) | `mockup-template.psd` + `logo.png` (linked) | L15: the same `logo.png` is placed linked on every artboard |
| L15 (5.3) | `campaign-master.psd` + its linked files | Module 6 (data-driven variations) |

The lessons do not name these files; the names above are suggestions so the room shares one vocabulary.

```
labs/module-5/
├─ README.md                                this file
├─ practice/                                synthetic practice files (hand these out)
│  ├─ l13-layout-copy.txt                   copy deck: every role + the lesson's scale (and a x3 version)
│  ├─ l13-ransom-note-before.png            the same copy with no system, to diagnose
│  ├─ l14-mockup-poster-wall.jpg            blank folded poster on a wall, in perspective
│  ├─ l14-mockup-tote-bag.jpg               plain canvas tote with folds (curved surface for Warp)
│  ├─ l14-art-a-sunrise-1200x1800.png       swappable design A (placeholder size)
│  ├─ l14-art-b-geometric-1200x1800.png     swappable design B (placeholder size)
│  ├─ l14-art-c-typographic-1200x1800.png   swappable design C (placeholder size)
│  ├─ l14-art-d-landscape-1800x1200.png     WRONG-shape design, for the Replace Contents size trap
│  ├─ l14-logo-v1.png                       Northwind logo, version 1 (becomes logo.png)
│  ├─ l14-logo-v2.png                       the rebrand: same canvas, new colors and mark
│  ├─ l15-key-art.png                       transparent hero: cup, steam and sun disk
│  ├─ l15-background-light.jpg              coastal dawn background (swappable)
│  ├─ l15-background-dark.jpg               the same background at night (light/dark variant)
│  ├─ l15-campaign-copy.txt                 campaign brief: sizes, copy, recomposition notes
│  ├─ l15-safe-zones-story.png              temporary overlay for the 1080 x 1920 story
│  └─ l15-safe-zones-banner.png             temporary overlay for the 1500 x 500 banner
└─ instructor/                              model results: your screen only
   ├─ l13-system-layout-INSTRUCTOR.png      the copy deck rebuilt on scale x3, 6 columns, 72 px grid
   └─ l15-campaign-reference-INSTRUCTOR.png the four recomposed artboards from the same assets
```

Regenerate with `python3 labs/build_practice_files.py --module 5` (deterministic).

> **Image licensing.** Do **not** use or hand out anything from the course site's `images/`
> folder. Those photos are Adobe Stock licensed to the author for the website only. Labs use
> only the synthetic files below or the learner's own images. "Northwind" and
> `northwindroasters.example` are fictional (the `.example` domain is reserved and never resolves).

---

## What to bring (Session 5)

- **Your Module 4 composite**, ideally the layered PSD (or a full-resolution export). It is the
  lesson's preferred campaign key art. At full resolution it should be at least as large as the
  poster area it will fill; if it is smaller, use it on the social sizes and `l15-key-art.png`
  on the poster.
- **Your own logo** (optional): a transparent PNG, or a PSD. Put it in the project folder and
  never move it.
- **A photo of a surface you want to brand** (optional): a mug, a poster on a wall, a laptop
  lid. Your own photo, or a free-license one (Pexels, Unsplash) after checking the license.
- **Your Module 4 LUT** (optional) for a shared grade across the artboards.
- **A Creative Cloud sign-in** so Adobe Fonts can activate a display face and a text face.

No consent issues in this module (no people in the practice files). If learners bring
photos of people for key art, the Module 3/4 consent rule applies: only people who agreed.

---

## Lab summaries

**L13 · A Type System (26 min in class).** Preferences ▸ Units & Rulers ▸ Type ▸ Pixels.
Write the scale (16 × 1.25 → 13 / 16 / 20 / 25 / 31 / 39) and assign roles. View ▸ Guides ▸
New Guide Layout (older versions: View ▸ New Guide Layout) for columns; Preferences ▸ Guides,
Grid & Slices: Gridline Every = body leading (24 px), Subdivisions 1; show with Ctrl/⌘+'.
One line per role → new Paragraph Style; Character Styles for emphasis/links; real OpenType
on, no faux bold/italic. Lay out `l13-layout-copy.txt` with styles only, first baselines on
gridlines (by eye: text never snaps to the grid). Edit the Body style and watch the page
re-flow. **Done when** one style edit updates every instance.

**L14 · A Reusable Template (25 min).** On `l14-mockup-poster-wall.jpg`: a 1200 × 1800 px
rectangle → Convert to Smart Object → Free Transform ▸ Warp onto the poster corners →
Multiply layer (folds, window-bar shadow) and Screen layer (fold ridges), both clipped →
double-click to place a design, then Layer ▸ Smart Objects ▸ Replace Contents with another
`…-1200x1800.png`. Try `l14-art-d-landscape-1800x1200.png` to see the size trap. Link test:
Place Linked `logo.png` twice in a new document, change the source, watch both update.
**Done when** a swap keeps the warp and lighting and the template is saved.

**L15 · The Campaign (38 min), Module 5 deliverable.** New document (RGB), Artboards on:
Poster 3300 × 5100, IG square 1080 × 1080, Story 1080 × 1920, Banner 1500 × 500. Poster
first. Place Linked `logo.png` and the key art into every artboard; bring in the L13 styles;
recompose per aspect ratio (stack / center / spread) inside the safe zones; File ▸ Export ▸
Export As, all artboards. Change the linked logo, save, see every artboard update (else
Layer ▸ Smart Objects ▸ Update All Modified Content), re-export. **Done when** all six
checklist items in the lesson are ticked.

**If time / homework:** the lessons' "Now You" variations: two scales (1.2 vs 1.618) and a
one-typeface hierarchy (L13); a three-surface mockup (wall + tote + your own) fed by one
linked file, a brand sheet, a retunable Smart Filter (L14); two extra sizes, a light/dark
set by relinking `l15-background-light.jpg` → `l15-background-dark.jpg`, and a Packaged
handoff to a "client" (L15).

---

## Practice file specs (for the generator script)

All images are sRGB. JPG quality 90. PNGs are lossless; the logo, key art and safe-zone
overlays are RGBA with transparent backgrounds. Coordinates are in pixels from the top-left.
Fonts are DejaVu (Sans, Serif, Mono) and Ubuntu (Condensed, Light) where installed, with
common system fallbacks; exact glyph shapes may differ by machine, which does not matter
for the labs.

### L13 · Type Systems, Styles & Grids

**`l13-layout-copy.txt`** · UTF-8 plain text. The Northwind copy deck, one line per role on
the lesson's scale: Display 39 "Northwind"; H1 31 "Slow-roasted, small batch"; Subhead 20
"COASTAL COFFEE ROASTERS" (tracked caps); two feature blocks, each an H2 25 ("Single
estate", "Roasted to order") plus a two-to-three-line Body 16 paragraph; CTA "Order a sample
box" (Subhead + an Emphasis Character Style); Caption 13 "EST. 2019 · PORTLAND" and
"northwindroasters.example"; tagline "Tasted, not guessed." (H2). Also lists the grid (24 px,
Subdivisions 1) and an optional 1800 × 2400 px practice poster version with every number ×3
(Caption 39, Body 48, Subhead 60, H2 75, H1 93, Display 117; grid 72 px; 6 columns, gutter
48 px, margins 144/120/144/120). Two families only, no faux styling, ligatures and oldstyle
figures on for Body.

**`l13-ransom-note-before.png`** · 1800 × 2400 px, paper background `#f2eee6`.
- The same copy with **no system**: a bold serif "Northwind" (170 px, brick red, centered);
  "COASTAL" in a condensed face stretched to 170 % width (distorted type, purple, left);
  "COFFEE" in bold monospace (112 px, blue, right-aligned); "Slow-roasted, small batch" in a
  condensed face **sheared to fake an italic** (green); four centered body lines in a regular
  sans thickened with a stroke (**faux bold**) with uneven line spacing (85 / 113 / 72 px);
  "Tasted!" in a light face, faux-italic and rotated 7° (mustard); "ORDER NOW!!!" in bold
  serif, red, underlined, flush left; the URL in monospace, off-center; "Tasted, not
  guessed." in a light face, indented; "EST 2019 portland" tiny and gray, bottom right.
- **The flaws to diagnose:** six-plus families, sizes from no scale, four different
  alignments, six colors, faux italic, faux bold, stretched type, inconsistent line spacing.
- Use: projected at the L13 frame; the "rebuild an ugly flyer" solo variation. It is a raster
  reference, not an editable file.

**`instructor/l13-system-layout-INSTRUCTOR.png`** · 1800 × 2400 px, `#f6f3ee`. The copy deck
rebuilt as the model answer: every baseline on a 72 px gridline (grid drawn faintly), 6 faint
column guides (margins 120 px, gutter 48 px), tracked coral Subhead, navy serif Display and
H1, a flat sunrise image band across all columns, two feature blocks three columns wide (serif
H2 + sans Body 48/72), coral tagline, bold CTA with an arrow, tracked Caption and URL. Small
monospace notes in the right margin name each role and size.

### L14 · Smart-Object Templates & Linked Assets

**`l14-mockup-poster-wall.jpg`** · 2400 × 1600 px.
- Warm-gray plaster wall (`#c9c2b8`) lit from the left (brightness falls off to the right),
  smooth low-frequency plaster variation; white baseboard at y ≈ 1364–1390 and a wooden plank
  floor below.
- A **blank off-white poster** (`#efece6`) in perspective with corners at about **(930, 250),
  (1530, 290), (1522, 1172), (940, 1216)**, projected from a flat 1200 × 1800 sheet (2:3,
  matching the practice designs). The paper has two horizontal **fold creases** (dark crease,
  lit ridge) at thirds, a softer vertical fold, and a slightly shaded lifted bottom-right corner.
- A soft cast shadow of the poster on the wall (offset +16, +22, blurred), and two diagonal
  **window-bar shadows** crossing wall and poster: the details learners paint back on the
  Multiply layer. Fine grain (σ ≈ 2.4).

**`l14-mockup-tote-bag.jpg`** · 1600 × 2000 px.
- A natural canvas tote (`#e4d7bf`) with slightly bowed sides (top 330–1270, bottom
  300–1300, y 620–1790), a top hem with dashed stitching, two strap handles (back one darker),
  a soft floor shadow on a light gray backdrop.
- Fabric: a fine weave texture, gentle vertical folds, two soft vertical creases and a
  **diagonal crease** across the lower half, darker side edges. The front is blank: the
  curved, creased surface that needs Warp rather than a flat corner-pin.

**Swappable designs** · flat-color illustration posters for Northwind, no transparency:
- **`l14-art-a-sunrise-1200x1800.png`**: banded dawn sky, coral sun on the horizon, five
  wave bands, "NORTHWIND" in cream serif and "SUNRISE BLEND" in tracked caps.
- **`l14-art-b-geometric-1200x1800.png`**: dark teal field, mustard circle, teal quarter, coral
  triangle, cream bar; "SMALL / BATCH" in bold sans; "NO. 02".
- **`l14-art-c-typographic-1200x1800.png`**: coral field, "SLOW / ROAST / ED." in large serif
  (cream/navy/cream), a navy rule, "Tasted, not guessed.", tracked footer.
- **`l14-art-d-landscape-1800x1200.png`**: navy field, "COLD BREW / SEASON" and a subline on the
  left, pale ice-cube squares on the right. **Deliberately landscape**: Replace Contents
  into a 1200 × 1800 placeholder distorts or misplaces it (the lesson's size trap); the fix is
  to double-click the placeholder and paste it into the existing canvas.

**`l14-logo-v1.png`** and **`l14-logo-v2.png`** · both 1600 × 600 px RGBA (identical canvas, so a
linked file can be swapped without shifting).
- v1: navy (`#1d3557`) circle emblem (radius 230, ring 22 px) with a coral (`#e76f51`) rising
  sun over three navy waves; "NORTHWIND" in bold serif (128 px, navy) and "COASTAL COFFEE
  ROASTERS" in tracked bold caps (34 px, coral).
- v2 (the "rebrand"): teal (`#1f6f66`) and gold (`#d9a441`); the emblem becomes a coffee bean
  with steam; adds "EST. 2019 · PORTLAND". Clearly different at a glance.
- Use: copy v1 into the project folder as `logo.png`, Place Linked it; to prove the update,
  either edit `logo.png`'s single layer and File ▸ Save, or copy v2 over `logo.png` in the
  file manager (same name). Dark ink: on the dark background add a Color Overlay layer style
  to the linked Smart Object.

### L15 · Campaign from One Master

**`l15-key-art.png`** · 2400 × 2400 px RGBA. A coral sun disk (radius 780, lighter inner disk)
behind a cream ceramic cup with shaded body, handle and dark coffee with a crema ring, on a
saucer; three soft white steam ribbons rising from the cup. Transparent background so it
recomposes on any artboard. On the 3300 px poster keep it at or below 100 % (it is capped at
2400 px to keep the kit small; "design at the biggest size" means never enlarge detailed art).

**`l15-background-light.jpg`** and **`l15-background-dark.jpg`** · 1950 × 3000 px (the poster's
proportions). A coastal horizon at y = 1900: light = pale blue sky to peach at the horizon over
a blue sea; dark = night navy sky over a near-black sea; both with soft horizontal light
streaks on the water and fine grain. They are smooth gradients with no fine detail, so
scaling them up to the 3300 × 5100 poster is harmless (a Gradient Fill layer is an equally
good background). Swap light → dark with right-click ▸ Relink to File for the light/dark
variant.

**`l15-campaign-copy.txt`** · UTF-8 plain text. The four artboard sizes; the shared linked
files; the shared copy (Headline "Sunrise Blend", Subhead "Slow-roasted, small batch", Tagline
"Tasted, not guessed.", CTA "Order a sample box", Caption "northwindroasters.example") with
advice to drop words on small sizes; recomposition notes (stack / center / stack in the safe
zone / spread); the optional shared grade; Export As; and the one-edit proof.

**`l15-safe-zones-story.png`** · 1080 × 1920 px RGBA. Translucent red bands over the top 250 px
and bottom 340 px (typical story UI overlays) and a blue text-safe rectangle inset 64 px from
the sides. **`l15-safe-zones-banner.png`** · 1500 × 500 px RGBA, translucent red 60 px bands on
every edge and a blue text-safe rectangle. Both are labeled "rule of thumb": platforms change
their UI, so check the destination's current spec. Place on top as a temporary guide, delete
(or hide) before export.

**`instructor/l15-campaign-reference-INSTRUCTOR.png`** · 2200 × 900 px. The four artboards
composed from the same assets (light background, key art, logo v1, serif headline, sans
subhead, CTA) at reduced scale with their real sizes labeled: poster stacked, square
centered, story stacked with the logo inside the top safe line, banner spread horizontally.

© 2026 Ray de la Paz
