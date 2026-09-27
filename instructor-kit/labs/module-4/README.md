# Module 4 Labs — Commercial Compositing (Session 4)

Module 4 builds **one layered file across three lessons**. L10 names it
`m4-key-visual.psd`. Learners place an element with the
right horizon, scale and perspective (L10 / Lesson 4.1), relight it and anchor it with
contact and cast shadows, plus a reflection on glossy ground (L11 / 4.2), then build depth
with contrast and haze and lay one unifying grade over everything (L12 / 4.3). The
exported key visual is the Module 4 deliverable.

```
labs/module-4/
├─ README.md                              this file
├─ practice/                              hand out to learners
│  ├─ l10-plaza-background.jpg            main scene: horizon y=700, one vanishing point, sun right
│  ├─ l10-figure-cutout.png               RGBA person, far too large, lit from the LEFT, cool
│  ├─ l10-product-box-cutout.png          RGBA carton shot from a high angle (needs Perspective Warp)
│  ├─ l10-horizon-practice-sheet.jpg      five "find the horizon" drills + a panel for own photo
│  ├─ l11-light-reference-hard-sun.jpg    read-the-light reference: hard sun, crisp shadows left
│  ├─ l11-light-reference-overcast.jpg    same objects, soft overcast light, no direction
│  ├─ l11-glossy-floor-scene.jpg          polished showroom floor with reflections to match
│  ├─ l12-far-clocktower-cutout.png       RGBA far element, too crisp and saturated on purpose
│  └─ l12-depth-bands-flat.jpg            five depth bands with NO atmospheric perspective
└─ instructor/                            keep on the instructor machine only
   ├─ l10-plaza-answer-overlay.jpg        horizon, VP, shadow direction, ghost figures at 8/16/32 m
   ├─ l10-horizon-practice-answers.jpg    the drill sheet with lines extended and horizons drawn
   └─ l12-key-visual-reference.jpg        a finished key visual built from the practice files
```

Regenerate everything with `python3 labs/build_practice_files.py --module 4` (from
`instructor-kit/`). Output is deterministic.

> **Image licensing.** Do **not** use or hand out anything from the course site's
> `images/` folder. Those photos are Adobe Stock licensed to the author for the website
> only. Labs use only the synthetic files below or the learner's own photos.

---

## What each lab uses

| Lab | Default files | Solo variation / stretch files |
|---|---|---|
| **L10** Place One Element (4.1) | `l10-plaza-background.jpg` + `l10-figure-cutout.png`; `l10-product-box-cutout.png` for the Perspective Warp step | Three distances (figure); "deliberately break it" (the high-angle box is the "shot from a ladder" element); `l10-horizon-practice-sheet.jpg` |
| **L11** Light & Anchor (4.2) | learner's L10 file (`m4-key-visual.psd`) | `l11-light-reference-hard-sun.jpg` vs `l11-light-reference-overcast.jpg` (same object in both lights); `l11-glossy-floor-scene.jpg` for the reflection step and colored rim light (magenta neon) |
| **L12** Depth & Grade (4.3) | learner's L11 file + `l12-far-clocktower-cutout.png` placed on the plaza's hills | `l12-depth-bands-flat.jpg` ("prove the depth with contrast and haze alone"); grade one composite three ways |

---

## Bring your own photos (recommended)

Ask learners, in the Session 3 wrap-up or the pre-session email, to bring:

1. **A background with clear perspective and visible shadows**: a street, a corridor, a room,
   a tiled floor, a table shot from standing height. Converging edges make the horizon
   findable; visible shadows tell them where the light is. People already in the shot are a
   bonus: they confirm the horizon at eye height.
2. **A cleanly cut-out element** from their Module 1 masking work, saved as a layered PSD
   (subject on a masked layer) or a transparent PNG. Full-length (feet or base visible) is
   essential: the ground-contact rule and both shadows need the base. A product with flat
   faces (a box, a book, a sign) is the best Perspective Warp practice.
3. *(Optional)* **A glossy surface photo** (wet street, marble or polished floor, polished
   tabletop, still water) for the reflection step.
4. *(Optional)* **A deep scene** with clear near, mid and far elements for L12.

Ideally the element and background were shot on similar focal lengths and similar camera
heights. The lesson is explicit that Warp fixes geometry, not optics; a telephoto headshot
will not sit convincingly on a wide-angle street.

Learners may also use free-license photos from sites such as **Pexels** or **Unsplash**,
after checking the current license terms on the photo's page. Never pull images from a web
search. **People in photos:** if a learner composites a real, recognizable person, they
should have that person's permission, and they should never composite someone into a
scene in a way that misrepresents them (a fake "they were there" image). Keep
portfolio composites obviously commercial or fictional.

Struggling learners should stay on the synthetic plaza: its geometry is exact, so their
placement can be checked in seconds.

---

## Instructor-only files

- **`l10-plaza-answer-overlay.jpg`**: the plaza with the horizon (red, y = 700), the vanishing
  point (1260, 700), extended edges (cyan), shadow direction (yellow), and ghost outlines of
  the practice figure placed correctly at 8, 16 and 32 m (301, 151 and 75 px tall). Use it
  to check placements, to rescue a learner who is lost at the end of L10 (they copy the
  8 m placement), and as the "same person walking away" answer. Fine to project during the
  break, after the L10 build.
- **`l10-horizon-practice-answers.jpg`**: the drill sheet with every horizon and vanishing
  point marked. Show it after learners have tried the sheet, not before.
- **`l12-key-visual-reference.jpg`**: a finished key visual built from these files the way
  the lessons describe (figure placed on the horizon and relit warm from the right, contact
  and cast shadows, clock tower hazed into the hills, one cool-shadow/warm-highlight grade,
  vignette, grain). Show it at the start of L12 as "where we are heading." It is a target,
  not a template: do not hand it out.

---

## Practice file specs (for the generator script)

All files are sRGB (embedded profile), 72 ppi. JPGs quality 86–90. RGBA PNGs have a fully
transparent background with anti-aliased alpha edges. The plaza and the light references
are rendered with a real **level pinhole camera** (no tilt), so verticals stay vertical and
all receding horizontal edges meet on one horizon. World units are metres; X right, Y up,
Z away from the camera.

### L10 · Match Perspective, Scale & Lens

**`l10-plaza-background.jpg`** · 2400 × 1600 px
- **Camera:** focal length 1400 px (a wide-ish lens, about 81° horizontal field of view),
  1.6 m above the ground, level. **Horizon at y = 700**; **vanishing point at (1260, 700)**.
- **Ground:** 1 m sandstone tiles with dark grout lines on a true perspective grid (tile
  colour varies ±5 % per tile); grout fades with distance so it doesn't alias. A strip of
  asphalt where a cross street closes the plaza at 88–92 m.
- **Left:** a 14 m, four-storey sandstone facade on the plane X = −7 m, lit by the sun:
  window rows every 2.9 m of height and every 3 m along the street, a red awning band and
  dark shopfronts on the ground floor, a light cornice. All window rows converge on the
  vanishing point.
- **Right:** a 0.6 m planter wall at X = 5 m (its face is in shade), a line of lamp posts
  (4.2 m) every 8 m at X = 4.55 m, then a lawn with eight trees and distant hills.
- **Closing the street:** a row of lower buildings across the far end at Z = 92 m.
- **People already in the shot:** three stylized figures, 1.72 m tall, at (X −2.8, Z 7.5)
  red jacket, (2.3, 13) blue coat, (−0.7, 26) green top. Because the camera is 1.6 m high,
  **the horizon crosses every one of them at the eyes**. Rule of thumb for this file: a
  1.72 m person with feet at image row *y* is **1.075 × (y − 700) px** tall.
- **Light:** late-afternoon sun, **high on the right** (elevation ≈ 50°), slightly in front
  of the scene. Every shadow falls **to the left** (and slightly away), crisp at the
  contact point and softening toward the tip (penumbra grows with distance), tinted cool.
  Each person has a small dark contact shadow at the feet.
- **Atmosphere:** mild exponential distance haze (≈ 25 % at the far end), paler blue-gray
  hills. Gentle warm cast, light lens falloff, fine mono noise.
- Purpose: the Module 4 key-visual background for all three lessons.

**`l10-figure-cutout.png`** · 678 × 1596 px, **RGBA**
- The same stylized person geometry as the plaza's figures, drawn at 820 px per metre
  (figure 1,422 px tall, feet at the bottom center), in a cream sweater and navy trousers.
- **Deliberate mismatches:** far too large for the plaza (it lands at roughly 10–20 % once
  scaled by the horizon rule), **lit from the left**, cool studio color cast. It needs
  scale (L10), relighting from the right plus warming (L11), and grading (L12).
- No shadow or fringe: this is the "clean cutout from your Module 1 work."

**`l10-product-box-cutout.png`** · 1400 × 1400 px, **RGBA**
- A teal product carton (0.42 × 0.52 × 0.30 m) with a cream label band, orange stripe and
  logo disc, rendered in 3D from a **high camera angle (looking down 30°) and rotated 34°**,
  so its top face is prominent and its edges run to vanishing points that do not exist in
  the plaza. Lit from the upper left.
- Purpose: the Perspective Warp step (Layout: one quad on each visible face; Warp: pins to
  the plaza's vanishing lines) and the "element with an obviously different horizon,
  like a shot taken from a ladder" solo variation.

**`l10-horizon-practice-sheet.jpg`** · 2200 × 1560 px
- Six panels (700 × 460): 1 corridor (one-point, VP off center); 2 road across fields;
  3 box on a table (two-point, both VPs off the panel); 4 building corner (two-point, low
  horizon); 5 railway with sleepers; 6 blank "your own photo" panel with instructions.
- Only the part of each receding edge **away** from its vanishing point is drawn, so
  learners must extend the lines themselves. All horizons are horizontal (level cameras).

**`instructor/l10-horizon-practice-answers.jpg`**: the same sheet with extensions (cyan),
vanishing points (red circles) and horizons (red lines) drawn.

**`instructor/l10-plaza-answer-overlay.jpg`**: see "Instructor-only files" above.

### L11 · Light, Shadows & Reflections

**`l11-light-reference-hard-sun.jpg`** · 2400 × 1600 px
- Level camera 1.2 m high, horizon at y = 520. Warm concrete ground, pale-blue sky, a hazy
  tree line on the horizon.
- Four objects: a red cube (0.55 m), a blue sphere (r 0.3 m), a yellow cylinder, a thin
  pole (1.7 m). Sun high right: right faces lit, crisp cast shadows falling **left**, dark
  and sharp at the base and softer at the tip, tinted cool; tight contact shadows.
- Purpose: practise reading direction, hardness and color; the hard-sun half of the
  "same object, two lights" solo variation.

**`l11-light-reference-overcast.jpg`** · 2400 × 1600 px
- Same camera and objects under flat gray-blue overcast: no cast shadows, only soft,
  broad occlusion pools under each object plus a slightly firmer contact shadow; flatter
  shading, lower contrast, cooler color.
- Purpose: the soft-light half of the variation ("feel how completely the shadow's edge
  and depth have to change").

**`l11-glossy-floor-scene.jpg`** · 2400 × 1600 px
- Level camera 1.5 m high, horizon y = 640, vanishing point (1200, 640). A dark showroom:
  polished black stone floor in 1.2 m tiles (seams converge on the VP), tall daylight
  windows on the left wall (the key light) throwing soft light patches on the floor, a
  dark right wall, and a **magenta neon strip** on the back wall.
- The floor mirrors the back wall and neon (fading with distance). Two existing objects,
  a white pedestal with a blue vase and a red sphere with a magenta rim from the neon,
  each have a **vertically flipped reflection that starts exactly at the base, fades, and
  blurs more with distance**, plus a tight contact shadow. That is the target for the
  learner's own reflection.
- Purpose: L11 Step 4 (reflection) with the product box or figure; the colored rim-light
  variation.

### L12 · Atmosphere & the Unifying Grade

**`l12-far-clocktower-cutout.png`** · 520 × 1500 px, **RGBA**
- A terracotta clock tower with white bands, a clock face and a teal spire, drawn
  **crisp, saturated and high-contrast**, hard-lit from the right.
- Purpose: the far element. Placed on the plaza's distant hills at roughly 200–250 px tall
  it looks pasted forward until a clipped Curves lowers its contrast and lifts its blacks
  and haze pushes it back.

**`l12-depth-bands-flat.jpg`** · 2400 × 1600 px
- Sky, far mountains, hills, a tree line and foreground rocky ground, each a textured band
  with **the same contrast and saturation** (no atmospheric perspective at all), so the
  depth reads only from overlap.
- Purpose: the "build a deep scene and prove the depth using contrast and haze alone,
  before any grade" variation, and a neutral canvas for "grade one composite three ways."

**`instructor/l12-key-visual-reference.jpg`**: see "Instructor-only files" above.

---

## Lab summaries

**L10 · Place One Element (4.1).** New empty layer; Line (or Pen) tool along two receding
edges, extended to their vanishing point; rulers (Ctrl/⌘+R) and a horizontal guide through
it. Place the element; set the ground-contact point; Free Transform (Ctrl/⌘+T) from the
feet until the horizon crosses it at the same body height as the scene's people (no Shift:
proportional is the default now). Boxes/signs: Convert to Smart Object, Edit ▸ Perspective
Warp (Layout quads, then Warp pins toward the VP); people: a touch of Distort. Step back
and check the lens feel. **Save the layered PSD.**
**Done when** the horizon is shared, the feet are on the ground, the size fits the distance,
and planes run to the vanishing point.

**L11 · Light & Anchor (4.2).** Read direction, hardness, color. Clipped 50% gray Soft Light
D&B layer (Lesson 3.2) to brighten the side facing the light; clipped Color Balance or
Photo Filter for the light's color. Contact shadow: new Multiply layer under the element,
small soft black brush at low flow, tight. Cast shadow: Ctrl/⌘-click the mask (or layer)
thumbnail, new layer below, Edit ▸ Fill very dark, deselect, Multiply; Distort/Skew away
from the light; Blur Gallery ▸ Tilt-Shift or Field Blur (or a blurred duplicate + gradient
mask); gradient mask to fade; tint cool outdoors. Glossy ground: duplicate, Flip Vertical,
align bases, 25–40 % opacity, blur increasing downward, mask a fade. **Save.**
**Done when** the element agrees with the scene's light and visibly touches the ground.

**L12 · Depth & Grade (4.3).** Clipped Curves on far elements (lower contrast, lift blacks,
a touch of sky color; if the far elements are part of the background plate, use a masked,
unclipped Curves). Haze layer (Normal) above the far elements, below the subject and its
shadows, very low flow. One grade at the top: Color Lookup or a Curves + Color Balance
group; pull the opacity back. Vignette, glow, grain. Save the master; flatten a copy,
convert to sRGB, export.
**Done when** far elements recede, one grade unifies the frame, and the key visual is exported.

**If time / homework:** three distances down the plaza; deliberately wrong horizon, then fix;
product on a phone-shot table; Filter ▸ Vanishing Point; same object in hard sun and
overcast; reflection on the glossy floor; colored rim light; grade one composite three ways;
the flat depth-bands scene; save the grade as a LUT and reuse it.

© 2026 Ray de la Paz
