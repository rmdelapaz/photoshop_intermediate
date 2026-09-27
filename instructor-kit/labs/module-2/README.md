# Module 2 Labs: Color & Tone, Deep (Session 2)

Module 2 runs on **one graded file** that grows across the session:
`grade-working.psd` (built in L05, Lesson 2.2) becomes `finish-working.psd`
(L06, Lesson 2.3), which is split-toned, soft-proofed and delivered twice. L04
(Lesson 2.1) sets up the pipeline everything else sits on. The practice files
below give every learner a file with a known, teachable property (a gradient
that bands, a wide-gamut file, a cast to neutralize, colors that die on paper)
and a fallback if their own photo goes missing.

```
practice/                            generated synthetic files (see specs below)
  l04-smooth-sky-16bit.tif           16-bit, Adobe-RGB-tagged dusk gradient: the banding proof
  l04-histogram-a.jpg … -e.jpg       five histogram drills (one is a trap: fine as it is)
  l04-lagoon-adobergb.jpg            saturated scene tagged with an Adobe RGB (1998)-compatible profile
  l04-lagoon-untagged.jpg            the same pixel values with NO profile: Assign vs Convert demo
  l05-portrait-studio.jpg            studio portrait, mild yellow cast + underexposed: the grading file
  l05-pier-dusk.jpg                  flat pier at sunset: the "different photo" for the LUT transfer
  l05-grade-test-chart.png           gray ramp, steps, hue x lightness field, memory colors
  l06-companion-portrait.jpg         same sitter, cool cast, flatter: the companion to match
  l06-set-a-daylight.jpg             still life, neutral reference
  l06-set-b-tungsten.jpg             same set, warm and dark
  l06-set-c-shade.jpg                same set, blue and flat
  l06-neon-proof.jpg                 neon on brick: lights up the Gamut Warning
instructor/                          instructor-only (do not hand out)
  l04-histogram-answers.txt          answers + example edit plans for the five drills
  l05-teal-gold-fallback.cube        a ready-made 17-point LUT for anyone whose export fails
```

**Licensing note.** Do **not** use or hand out anything from the course's
`images/` folder. Those are licensed Adobe Stock images and are not
redistributable. Every file here is synthetic (generated from code by
`labs/build_practice_files.py`) and can be shared freely with enrolled learners.

## Before class: what Photoshop will ask

This module deliberately turns on the profile warnings (Color Settings ▸
Profile Mismatches: **Ask When Opening**). Expect dialogs, and teach learners to
read them:

- **Opening `l04-lagoon-adobergb.jpg` or `l04-smooth-sky-16bit.tif`** may show
  *Embedded Profile Mismatch*: the embedded profile is named
  **"Adobe RGB (1998) compatible"**. It was built by the generator with the
  published Adobe RGB (1998) primaries, D65 white and 563/256 gamma (Pillow
  cannot write Adobe's own file), so Photoshop may treat it as a different
  profile from the Adobe RGB (1998) working space even though the colors are
  the same. Answer: **Use the embedded profile (instead of the working space).**
- **Opening an sRGB practice JPEG** with an Adobe RGB working space shows the
  same dialog. Same answer.
- **Opening `l04-lagoon-untagged.jpg`** shows *Missing Profile* only if the
  learner also ticked Missing Profiles: Ask When Opening. Choose **Leave as is
  (don't color manage)** first so they see the dull version, then fix it with
  **Edit ▸ Assign Profile ▸ Adobe RGB (1998)**. If a learner's machine has no
  dialog, the file simply opens in the working space; Assign still works.
- If you would rather the lagoon open with Adobe's own profile: open it,
  **Edit ▸ Assign Profile ▸ Adobe RGB (1998)** (appearance does not change,
  because the values are identical), and File ▸ Save As a copy.

## Lab flow

**L04, Set Up & Diagnose (24 min build + Now You).** Edit ▸ Color Settings
(Adobe RGB (1998) or sRGB, CMYK press profile or default, Preserve Embedded
Profiles, mismatch warnings on). Open `l04-smooth-sky-16bit.tif` and confirm
RGB/16. Window ▸ Histogram on `l04-histogram-a.jpg` (demo) and the learner's
own image: write a one-sentence diagnosis. Banding proof on the sky TIFF:
Image ▸ Duplicate, set the copy to Image ▸ Mode ▸ 8 Bits/Channel, the same
aggressive Curves on both (drag both ends of the curve far inward, then a strong
brighten), compare at 100% on the upper sky. Export: save the layered master
as `color-master.psd`, Image ▸ Duplicate (Duplicate Merged Layers Only), Edit ▸
Convert to Profile ▸ sRGB, 8 Bits/Channel, export.
*Now You (start in class, finish at home):* read histograms a–e cold, check with
the instructor; export `l04-lagoon-adobergb.jpg` twice (Converted to sRGB, and
with the profile stripped: File ▸ Export ▸ Export As with Convert to sRGB and
Embed Color Profile both unticked), view both in a browser; save a wide-gamut
16-bit File ▸ New preset.

**L05, Grade & Bottle It (30 min build + Now You).** Open
`l05-portrait-studio.jpg` (or own portrait), Image ▸ Mode ▸ 16 Bits/Channel,
neutralize with a Curves layer's gray eyedropper on the middle GRAY CARD patch
(or Camera Raw Filter) and lift exposure, Save As `grade-working.psd`. RGB
S-curve → new Curves, Blue channel split (shadow end up, highlight end down;
optional Green up / Red down in the shadows) → Gradient Map teal→gold, Color or
Soft Light, ~20–30% → mask the grade off the face or the highlights. Save,
Shift-click the masks off, hide non-grade layers, File ▸ Export ▸ Color Lookup
Tables → `.cube`, masks back on, save. Open `l05-pier-dusk.jpg`, Color Lookup ▸
Load 3D LUT… ▸ the new .cube. Demo aid: `l05-grade-test-chart.png` shows exactly
what a Gradient Map or LUT does to every tone and hue.
*If a learner's LUT export fails:* give them
`instructor/l05-teal-gold-fallback.cube` for the transfer test and fix the
export at the break (usual cause: the document isn't a Background layer plus
adjustment layers).
*Now You (start in class, finish at home):* three LUTs (warm summer, cold
thriller, faded matte) on one photo; reverse-engineer a film still; one LUT
across five photos.

**L06, Split-Tone & Proof (34 min build, the Module 2 deliverable).** Open
`grade-working.psd`, Save As `finish-working.psd`. Color Balance: Shadows toward
cyan/blue, Highlights toward red/yellow, Midtones near neutral. Open
`l06-companion-portrait.jpg` (or own second photo); Color Sampler on the gray
card's middle patch in each file (and a second point on the lit cheek), Window ▸
Info; Curves on the companion: RGB first, then each channel until the values
meet. View ▸ Proof Setup ▸ Custom (printer profile or U.S. Web Coated (SWOP) v2,
Relative Colorimetric or Perceptual, Black Point Compensation, Simulate Paper
Color), Ctrl/⌘ + Y, Gamut Warning Ctrl/⌘ + Shift + Y, masked Hue/Saturation
until clear (use `l06-neon-proof.jpg` if the portrait shows no warnings).
Deliver: save master; merged duplicate → Convert to sRGB, 8-bit, JPG; merged
duplicate → Convert to the printer/CMYK profile (or tagged RGB if the printer
asks) → PDF or TIFF.
*Now You (homework):* match `l06-set-b-tungsten.jpg` and `l06-set-c-shade.jpg`
to `l06-set-a-daylight.jpg` (or three own photos); split-tone one image cool/warm
and green/magenta; soft-proof a vivid image; optionally save the split-tone as a
LUT.

Do not hand out the answer key or the `instructor/` folder before the lab.

## Practice file specs (for the generator script)

Generated by the Module 2 part of `labs/build_practice_files.py` (source:
`labs/_parts/m2.py`), Python 3 + Pillow + NumPy, fixed seeds, idempotent.
JPEGs at quality 88–92 with no chroma subsampling; all 8-bit files sRGB-tagged
unless stated. Total ≈ 5 MB.

### Special formats
- **Adobe RGB (1998)-compatible ICC profile.** Pillow's ImageCms can only create
  sRGB/Lab/XYZ, so the generator writes a minimal ICC v2.1 display profile by
  hand: `desc` "Adobe RGB (1998) compatible", `wtpt` D65, `rXYZ/gXYZ/bXYZ` =
  the Adobe RGB primaries (0.64,0.33), (0.21,0.71), (0.15,0.06) adapted to D50
  with Bradford, and one shared `curv` TRC of gamma 563/256 (2.19921875). The
  creation date is pinned so rebuilds are byte-identical. Verified with
  LittleCMS: mid-gray maps to mid-gray, pure Adobe-RGB green clips in sRGB.
- **16-bit TIFF.** Pillow cannot save 16-bit RGB, so the generator writes a
  baseline little-endian TIFF itself: 16/16/16 bits, RGB, planar contiguous,
  Deflate (ZIP) compression with horizontal predictor, 32-row strips, 300 ppi,
  ICC profile in tag 34675. Photoshop opens it as RGB/16.
- **.cube LUT.** Plain-text 3D LUT, `LUT_3D_SIZE 17`, red index fastest.

### `l04-smooth-sky-16bit.tif`: the banding proof (L04 Step 3, and Step 1/4)
- **Size:** 2400 × 1600, 16 bits/channel, Adobe RGB (1998)-compatible, ~0.7 MB.
- **Content:** a narrow-range dusk gradient, slate blue at the top to pale peach
  near the horizon, plus a broad soft sun glow at lower right; a near-black hill
  silhouette with an anti-aliased ridge across the bottom quarter. **No noise at
  all**, so nothing dithers the gradient.
- **Why it works:** across the upper ~700 px of sky each channel changes by only
  about 15–50 levels (8-bit), so every level is a stripe 15–50 px tall. Any Curves
  move that stretches those tones 4× or more turns the 8-bit copy into clear
  bands, while the 16-bit file (thousands of steps) stays smooth.
  If Photoshop dithers on the 8-bit conversion, the bands have slightly noisy
  edges but are still obvious at 100%.

### `l04-histogram-a.jpg` … `l04-histogram-e.jpg`: diagnosis drills (L04 Step 2, Now You)
- **Size:** 1200 × 800 each. One farm scene (sky with clouds, hills, dark
  conifers, red barn with a black door, white fence) rendered five ways:
  - **a** flat: `v = 72 + 0.42v` (narrow middle histogram);
  - **b** a *snow* version of the scene, correctly exposed (high-key: piled right,
    not clipped), the trap;
  - **c** underexposed: `v × 0.40`;
  - **d** overexposed: `v × 1.45 + 30`, clipped (spike at the right wall, sky and
    fence gone);
  - **e** crushed: `(v − 70) × 1.35`, clipped (spike at the left wall).
- Letters are deliberately not in problem order. Answers and example edit plans
  in `instructor/l04-histogram-answers.txt`.

### `l04-lagoon-adobergb.jpg` / `l04-lagoon-untagged.jpg`: containers (L04 demo + Now You)
- **Size:** 2000 × 1333. Identical pixel values; the first embeds the Adobe RGB
  (1998)-compatible profile, the second has no profile at all.
- **Content (authored directly in Adobe RGB values):** a blue sky with clouds, a
  band of very saturated turquoise shallows, a palm with saturated green fronds,
  a red/green/cyan parrot on a branch, sand, and a labelled swatch strip (gray,
  skin, green, cyan, red, blue). The turquoise, the fronds and the green/cyan
  swatches lie outside sRGB.
- **What learners see:** tagged and color-managed, the scene is vivid;
  untagged (read as sRGB/working space) or exported with the profile stripped,
  the same numbers look duller, most in the water and greens. The gray swatch
  hardly changes. Assign Adobe RGB (1998) to the untagged file and it snaps to
  match: the honest use of Assign.

### `l05-portrait-studio.jpg`: the grading file (L05, carried into L06)
- **Size:** 1600 × 2000 portrait. An illustrated studio head-and-shoulders
  (adapted from the intro kit's portrait): gray seamless backdrop with a hot spot
  behind the head, dark hair with sheen strands, charcoal jacket, a near-white
  shirt V, key light from camera left (lit cheek and forehead highlights, darker
  shadow side and a soft shadow under the jaw) so shadows and highlights are
  distinct zones for split-toning. A three-patch **GRAY CARD** (black / 18% gray /
  white) at lower right.
- **Flaw:** mild yellow cast (R ×1.03 +6, G +3, B ×0.86) and about ⅔ stop under
  (×0.80). Learners neutralize with the gray card before grading.

### `l05-pier-dusk.jpg`: LUT transfer target (L05 Step 4)
- **Size:** 2400 × 1600. Sunset sky (slate blue to peach), low sun on the horizon
  with a glitter path, rippled sea, a wooden pier converging toward the sun with
  posts, a lamp post with a soft glow. Rendered flat and neutral ("straight out
  of camera": `22 + 0.84v`), so a teal-and-gold LUT reads clearly.

### `l05-grade-test-chart.png`: what a remap does (L05 demo)
- **Size:** 2000 × 1300, 8-bit sRGB PNG, mid-gray background. A smooth 0–255
  gray ramp; 11 framed gray steps (0–100% in 10% steps); a hue × lightness field
  (full hue sweep left to right, light at the top to dark at the bottom, 75%
  saturation); eight memory-color patches (dark skin, light skin, sky, foliage,
  teal, gold, neutral 8, neutral 3.5) with labels.
- **Use:** a Gradient Map turns the ramp into the gradient exactly; a LUT shows
  its shadow and highlight colors on the ramp and where it breaks skin on the
  patches.

### `l06-companion-portrait.jpg`: the image to match (L06 Step 2)
- **Size:** 1440 × 1800. The same sitter, tighter crop, gray card at lower left.
  "Window light": cool cast (R ×0.86, G ×0.93, B ×1.06 +14) and flatter, lifted
  tones (`38 + 0.80v`). Its gray card middle patch reads about R 119 / G 127 /
  B 148 before correction; the L05 file's reads about R 103 / G 97 / B 81 before
  correction, so learners see opposite casts in the Info panel.

### `l06-set-a-daylight.jpg`, `-b-tungsten.jpg`, `-c-shade.jpg`: a set to match (L06 Now You)
- **Size:** 1800 × 1200 each. A still life: pale wall, wooden board, folded
  off-white linen, blue mug with a handle, lemon, a gray card (no label) at lower
  right. **a** neutral daylight (the reference); **b** tungsten: R ×1.08 +10,
  G ×0.94, B ×0.66, overall ×0.78 (warm, dark); **c** open shade: R ×0.88, G ×0.97,
  B ×1.10 +12, then `52 + 0.72v` (blue, lifted, flat).

### `l06-neon-proof.jpg`: soft-proof and Gamut Warning (L06 demo, Step 3)
- **Size:** 2000 × 1334. Brick wall and wet pavement at night. Neon in sRGB's
  most saturated corners: a magenta "OPEN" (255,0,190), an electric-blue arrow
  (20,70,255), an acid-green arc (40,255,60), an orange-red vertical tube
  (255,70,0), each with a glow halo and a reflection in the pavement. Printable
  areas alongside: brick, a wooden door, a muted "JAZZ · FRI" poster.
- **What learners see:** with proof on (SWOP v2 or similar), the neon grays out
  under Gamut Warning; brick, door and poster stay clear. A masked Hue/Saturation
  on the neon clears it.

### `instructor/l04-histogram-answers.txt` and `instructor/l05-teal-gold-fallback.cube`
- The answers file lists each drill's problem, what its histogram shows, and an
  example one-sentence plan.
- The fallback LUT: `LUT_3D_SIZE 17`, a monotonic S-curve (`x − 0.08 sin 2πx`) plus
  teal in the shadows and warm gold in the highlights, weighted by luminance.
  Load via Color Lookup ▸ Load 3D LUT….

## Learners' own photos (bring to Session 2)

Ask each learner to bring the **largest original files** they have (straight
from the camera or phone, not a messaging-app copy; RAW is welcome):

- **A favorite photo to grade**, ideally a **portrait**, because L06 split-tones
  the same file and judges the result on skin.
- **A second photo that should belong to the same set** (same person or place,
  different light) for the L06 match.
- **One deliberately vivid image** (neon, a saturated sunset, a bright product)
  for the soft-proof.
- Optional: five varied images for the histogram drill, and five photos for the
  one-LUT-across-five test.

**Consent.** Portraits of other people should be of people who have agreed to
their photo being edited in class and shown on the projector. Learners without a
suitable portrait can use `l05-portrait-studio.jpg`, or free-license images (for
example from Pexels or Unsplash); tell them to check the current license on the
download page before using or sharing an edited version.

**Printing (optional).** If a learner has access to a printer or lab, ask them to
find out which profile it wants (or whether it wants tagged RGB) before the
session; it makes the soft-proof real. Otherwise U.S. Web Coated (SWOP) v2 is the
stand-in.
