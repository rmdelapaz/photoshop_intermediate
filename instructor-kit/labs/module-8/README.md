# Module 8 Labs: Capstone (Session 8, with the L21 kickoff in Session 7)

The capstone is one self-directed professional project built mostly from **the
learner's own photos and assets**. L21 (Lesson 8.1, The Brief & the Plan) is taught
in the Session 7 capstone kickoff; learners finish the plan and build most of the
piece (L22, Lesson 8.2) as homework, arriving at Session 8 with Pass 1 and Pass 2
done. Session 8 is for finishing, case-study assembly, presentations, and critique
(L23, Lesson 8.3). There are no step-by-step solution files: every capstone is
different. Judge briefs, files, and case studies with the reference notes in the
Module 8 answer key and the 12-row rubric in `final-assessment.html`.

The course's `images/` folder is Adobe Stock licensed to the author and is **not**
redistributable. Never copy it into a lab. Everything below is synthetic, generated
by `labs/build_practice_files.py --module 8` (source: `labs/_parts/m8.py`).

```
practice/
  l21-vague-brief.txt             L21 warm-up: sticky-note brief to pin to specs
  l21-brief-template.txt          L21: one-page, six-part brief + plan + milestones
  l21-backup-briefs.txt           Two ready-made briefs (key art, product campaign)
  l21-backup-keyart-plate.jpg     Backup brief A: road at dusk (the background plate)
  l21-backup-keyart-figure.jpg    Backup brief A: figure on gray, wind-blown hair
  l21-backup-product.jpg          Backup brief B: the can to cut out
  l21-backup-product-surface.jpg  Backup brief B: counter + wall, window light
  l21-backup-brand-logo.png       Backup brief B: the (fictional) logo, transparent
  l23-case-study-outline.txt      L23: page order, five beats, export menus
  l23-mockup-wall.jpg             L23: framed print, 2:3 portrait opening
  l23-mockup-phone.jpg            L23: phone on a desk, 4:5 feed post
  l23-mockup-sleeve.jpg           L23: square record sleeve on a shelf
instructor/
  l21-vague-brief-fixed.txt       One good answer to the warm-up (instructor only)
```

---

## Lab pointers

**L21 · The Brief & the Plan (Session 7 kickoff, ~45 min; reviewed 15 min in Session 8)**
- Warm-up (6 min, pairs): open `l21-vague-brief.txt`; pin each sticky note to a spec,
  a named constraint, or a reference image, and rewrite it as the six parts. Compare
  with `instructor/l21-vague-brief-fixed.txt` (accept any version where every line is
  checkable).
- Step 1, write the brief (15 min in class): `l21-brief-template.txt` or the
  workbook page. Success criteria as a checklist someone else could grade.
- Steps 2–3 (started in class, finished at home): a moodboard of 6–12 annotated
  references (a contact-sheet PSD or a simple grid), then the staged plan with module
  skills, assets to source (licenses checked), two or three milestones, a finish
  date, and cuttable stretch goals.
- Session 8 review: partners try to grade the current file against each other's
  success criteria; anything they cannot check gets rewritten.

**L22 · Studio Session: Build It (home + 70 min studio)**
- The learner's own file, built in passes: block-in, refine, polish, each across the
  frame; a version (`capstone_v01`, `v02`…) and a screenshot at the end of each pass.
- Fresh-eyes checks: View ▸ Flip Horizontal (older versions: Image ▸ Image Rotation ▸
  Flip Canvas Horizontal, then flip back), zoom to fit and squint, a temporary Black &
  White adjustment layer at the top of the stack, walk away.
- The finish gate: tick every success criterion on the artwork; save the layered
  master; export the deliverables at spec; `firstname-hero.jpg` (sRGB) to the shared
  folder.
- Learners who arrive behind use a backup brief (see specs below).

**L23 · Present & Case Study (25 min assembly + 50 min presentations; layout at home)**
- Step 1: place the hero into a mockup (Module 5.2 recipe: rectangle over the gray
  area → Convert to Smart Object → double-click the thumbnail, place the art, save
  and close; shadows on Multiply and highlights on Screen above it, clipped; Layer ▸
  Smart Objects ▸ Replace Contents to swap). Export `firstname-context.jpg` and
  `firstname-before-after.jpg` to the shared folder.
- Step 2: the five beats and a 30-second spoken version (`l23-case-study-outline.txt`
  or the workbook).
- Steps 3–4 (homework, within a week): lay out top to bottom in the Module 5 type
  system; export web images (File ▸ Export ▸ Export As) and a PDF (File ▸ Save a Copy ▸
  Photoshop PDF, or File ▸ Export ▸ Artboards to PDF); disclose generative assistance;
  publish.

---

## What learners should bring (their own photos and files)

Tell learners at the Session 7 kickoff, by project:
- **All projects (Session 8):** the layered master and every incremental version; the
  brief and moodboard; the end-of-pass screenshots and a true "before"; fonts they
  are licensed to use (Adobe Fonts via their plan, or system fonts).
- **Key art poster:** a hero subject photo with clear edges, a background plate shot
  at a similar light direction and eye level, the title and credit text.
- **Product campaign:** a product photographed on a plain background, a surface or
  setting photo, the brand's colors and logo file, and the list of sizes.
- **Editorial portrait:** a well-lit portrait of someone who has **agreed** to have
  it retouched and shown in class; the headline and body text for the layout.
- **Your own:** whatever the brief's deliverables need.

No suitable photos? Stock is fine **after** checking each image's license and credit
terms (the L21 plan step asks for this). Mockup PSDs from design sites are fine only
if their license allows it; otherwise use the three mockups here.

**Consent and honesty.** Portraits need the subject's consent to be retouched and
shown. Before/after and progress shots must be real. Any Generative Fill or Expand is
disclosed in the case study's process section; Content Credentials can be attached
on export. Generative steps need internet, an Adobe sign-in, and credits: finish them
at home before Session 8.

---

## Practice file specs (for the generator script)

All JPEGs: RGB, sRGB ICC profile embedded, 72 ppi metadata, quality 90 unless
stated. "Noise" means per-pixel Gaussian noise (sigma given; "mono" = the same value
on R, G, B) added after drawing and clipped to 0–255. Every file is deterministic
(seeded from its filename). Whole module: 13 files, about 4.1 MB.

**`l21-vague-brief.txt`** (practice): the warm-up. Eight sticky-note phrases from a
fictional cafe owner ("Something for the new cold brew, for online," "Make it pop,"
"Modern vibe, but not cold," "Clean but bold," "Young people should like it," "Our
colors, I guess?," "Soon-ish," "You'll know it when you see it"), then the six parts
to rewrite them into, the stranger test, and the mantra.

**`l21-vague-brief-fixed.txt`** (instructor): one good answer. Each part filled in
for the fictional Halden Cold Brew launch, with a parenthetical after each part
naming which sticky note it pinned (e.g. "Soon-ish" → "Friday, 5 p.m."). Its sizes,
colors, and success criteria match Brief B below.

**`l21-brief-template.txt`** (practice): a one-page plain-text form. Six numbered
parts with the lesson's definitions as prompts; deliverable lines (size, ppi, color,
format) plus the layered master; five checkbox success criteria; 12 reference slots
with "→ what I take from it"; the plan table (the lesson's Figure 3 stages with their
module skills and an assets column); a license-checked box; three milestones and a
finish date; two stretch-goal lines.

**`l21-backup-briefs.txt`** (practice): two complete six-part briefs for learners
with no project, each listing its assets. **A · "The Salt Road"** key art poster
(fictional film; 24 × 36 in at 300 ppi or a smaller 2400 × 3600 px build, a print PDF,
a 1080 × 1620 px screen JPG; six success criteria on scale, light from the left,
contact + cast shadows, haze, a thumbnail-readable title, one unifying grade).
**B · "Halden Cold Brew"** product campaign (fictional brand; web hero 3000 × 2000,
feed 1080 × 1350, story 1080 × 1920, artboards; brand green `#1F4D3F` and cream
`#F3E9DC`; five success criteria on the cutout, light direction, contact shadow,
thumbnail-readable name, all sizes from one master). A closing note: no synthetic
portrait here; reuse the Module 3 practice portrait (`labs/module-3/practice/`) or,
better, a consenting subject's portrait.

**`l23-case-study-outline.txt`** (practice): the lesson's page order (hero → brief →
approach → process → details → result → reflection) with one-line definitions, the
five beats with write-in lines, the outcome-first example, the honesty rules
(real before; disclose generative assistance), the export menus, and a line for the
30-second spoken version.

**`l21-backup-keyart-plate.jpg`**: 2000 × 3000, portrait (ready for a 2:3 poster).
A straight road across a salt flat at dusk, for matching scale, perspective, light,
and atmosphere (Module 4).
- Horizon at y 1900; vanishing point x 1120. Sky gradient `#101a3a` → `#2c3a6e`
  (45%) → `#b7616a` (78%) → `#ee9a5e` → `#f7c27a` at the horizon.
- **Low sun on the left** at (430, 1830), radius 46, `#fff1cf`, inside a warm glow
  (`#ffd79a`, elliptical falloff 900 × 520 px).
- Two ridges of distant hills just above the horizon (`#9b6f7e` far, `#6d4f66` near),
  then a haze band on the horizon (`#f0b98a`, Gaussian falloff sigma ≈ 140 px, 35%)
  so distance reads lighter.
- Salt flat: `#e8c9a6` at the horizon to `#7f7f93` at the bottom, with faint
  crust texture and 60 pale streaks that grow toward the viewer.
- Asphalt road: a trapezoid from the vanishing point to x 420–1780 at the bottom,
  `#5a5058` → `#2c2a33`, with 14 perspective-spaced dashes (`#e9d9a8`).
- **Six telephone poles** on the left verge, shrinking toward the horizon (1465 px
  tall at the front down to about 170 px): scale cues for placing the figure. Each is
  lit on its left edge (`#b86a4e`) and casts a **long soft shadow to the right**.
- A gentle vignette. Noise sigma 3, mono.

**`l21-backup-keyart-figure.jpg`**: 1600 × 2400, portrait, quality 92. A full-length
stylized figure to cut out (Module 1) and composite onto the plate.
- Seamless gray studio background `#a3a8ae` → `#8e949a` → `#7b8187` with a soft
  vignette; contact shadow under the boots and a soft cast shadow falling right.
- Figure centered on x 800, boots at y ≈ 2250: long coat `#3b4a52` with a hem blown
  to the right, sleeves, trousers `#2c2c33`, boots `#1e1a18`, a red scarf `#9b3b2c`
  trailing right, skin `#c99b7c`, hair `#2b1d16`.
- **Key light from the left** (matches the plate's sun): each shape brighter on its
  left side (×1.22 falling to ×0.72) plus a warm rim (`#f3c89a`) on left edges.
- **520 fine hair strands** (1–1.8 px, partly transparent, `#3a2a20`) streaming right
  from the head against the gray: the Select & Mask test.
- Noise sigma 2.5.

**`l21-backup-product.jpg`**: 2000 × 2000, square, quality 92. A drinks can on
seamless gray to cut out and relight (Modules 1, 4).
- Background `#d6d9dc` → `#c4c8cc` → `#b9bdc1`, slightly darker to the right.
- Can: x 720–1280, y 470–1600, brushed-metal body (`#b9bec4`) with **cylindrical
  shading lit from the left** (highlight at 24% of the width, a thin rim on the right).
  A curved label band y 690–1400 in brand green `#1f4d3f` with a cream stripe, the
  cream "HALDEN / COLD BREW" wordmark squeezed toward the edges like a cylinder, a
  lid ellipse with a darker recess and a pull tab.
- Cast shadow to the right and a tight contact shadow under the base (learners may
  replace both). Noise sigma 2.5, mono.

**`l21-backup-product-surface.jpg`**: 3000 × 2000, landscape. The setting for the
hero.
- Wall (y 0–1160) `#e6dccd` → `#d6c8b4` with a **window-light patch on the left**
  (a skewed four-pane rectangle of `#fff4df` at 32% with soft mullion shadows).
- Counter (y 1160–2000): warm concrete `#b8ab9c` → `#8e8273` with fine speckle, a
  soft light pool near x 900, a darker occlusion line at the wall, and a front edge
  band (y 1930–2000).
- Light falloff left → right (×1.06 to ×0.84). Noise sigma 3, mono.

**`l21-backup-brand-logo.png`**: 1400 × 480, RGBA, transparent background. The
fictional Halden wordmark in `#1f4d3f`: a ring (radius 150) around a coffee bean,
"HALDEN" bold at about 165 px, "COLD BREW CO." beneath. For placing, recoloring, and
Smart-Object templating (Module 5).

**`l23-mockup-wall.jpg`**: 3000 × 2000. A framed print on a gallery wall for
presenting a poster in context.
- Wall y 0–1700 (`#e9e4dc` → `#d6cfc3`) with a soft light pool; wood floor below with
  a baseboard line; a low bench on the right for scale.
- Frame x 1000–2000, y 160–1560 (`#262626`), white mat, **opening x 1100–1900,
  y 260–1460 (800 × 1200, 2:3 portrait)** filled with flat `#9a9a9a`. Soft drop
  shadow below-right of the frame. Noise sigma 2, mono.

**`l23-mockup-phone.jpg`**: 2400 × 1600. A phone lying on a wooden desk, showing a
social feed, for campaign and social deliverables.
- Desk: vertical wood grain `#8b6446` → `#6f4f37`; a notebook corner lower right.
- Phone 600 × 1220 (black body, rounded screen, a feed header with avatar and name
  bars), **rotated 9° clockwise**, centered near (1050, 800), with a soft shadow.
- **Post area: 552 × 690 px (4:5) in flat `#9a9a9a`** (before rotation), with icon
  and caption bars below. Learners rotate (Free Transform) or Warp their Smart Object
  to fit.

**`l23-mockup-sleeve.jpg`**: 2400 × 1600. A square record sleeve on a shelf for
album-cover or square pieces.
- Painted wall `#3e4a57` → `#56626e` with a soft light pool; wooden shelf lip at
  y 1340; dark shelf face below.
- **Sleeve x 560–1500, y 400–1340 (940 × 940)**: a thin paper edge (`#d8d6d0`) around a
  flat `#9a9a9a` front; soft shadow on the wall.
- A black record with grooves and an orange-red label peeking out on the right,
  behind the sleeve.

---

## Running the capstone

1. **Session 7 kickoff (~45 min):** the L21 lesson plan in the Module 8 facilitator
   guide. Learners leave with a brief started, a project chosen, and a moodboard file.
2. **Between sessions:** finish the plan; build Pass 1 and Pass 2; start Pass 3;
   screenshot every pass. Optional midweek email of the objective and success criteria.
3. **Session 8:** plan review (15) → studio (70) → break (12) → case-study assembly (25)
   → presentations + peer critique (50, about 4 min each for ~12) → course close (8).
4. **Within a week:** the case study laid out, exported, and published. Score with
   `final-assessment.html`: pass = no row below 2, plus the deliverables exported at
   spec and a saved layered master.
