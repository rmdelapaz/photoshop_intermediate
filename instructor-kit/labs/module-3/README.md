# Module 3 Labs: High-End Retouching (Session 3)

Module 3 runs on **one portrait** that moves through the professional pipeline,
saved as a new layered file at each stage:

- **L07 (Lesson 3.1)** frequency separation → `skin-retouched.psd`
- **L08 (Lesson 3.2)** dodge & burn on a 50% gray Soft Light layer → `portrait-sculpted.psd`
- **L09 (Lesson 3.3)** eyes, teeth & hair finish → the **Module 3 deliverable**
  (saved as `portrait-finished.psd`, a new name so `portrait-sculpted.psd` stays
  as a checkpoint)

**Demo on the practice faces, never on a learner's face.** The practice
portraits are illustrated faces with flaws placed on purpose (blotchy tone,
blemishes, flat light, dull eyes, yellowed teeth, flyaways), so every demo works
and nobody's appearance is discussed in front of the room.

```
practice/                              generated synthetic files (see specs below)
  l07-portrait-retouch.jpg             main portrait: pores + blotchy tone + blemishes + all later flaws
  l07-beauty-closeup.jpg               same face, tight beauty crop: big pores, needs a bigger radius
  l07-candid-distance.jpg              same face at arm's length outdoors: tiny pores, small radius
  l08-portrait-clean-flat.jpg          catch-up start for L08: skin already cleaned, light still flat
  l08-apple-flat.jpg                   flatly lit apple for the "sculpt something that isn't a face" variation
  l09-portrait-sculpted.jpg            catch-up start for L09: cleaned + sculpted, dull eyes, yellow teeth, flyaways
instructor/                            instructor only: do NOT hand out
  l07-flaw-map-INSTRUCTOR.png          every blemish, tone patch, flyaway, and permanent feature marked
  l08-light-map-INSTRUCTOR.png         where this face wants dodging and burning (light from the viewer's left)
```

**Licensing note.** Do **not** use or hand out anything from the course's
`images/` folder. Those are licensed Adobe Stock images and are not
redistributable. Every file here is synthetic and can be shared with enrolled
learners (except the two `instructor/` maps, which are answer keys).

**Catch-up files.** `l08-portrait-clean-flat.jpg` and `l09-portrait-sculpted.jpg`
are the same face at the start of Lessons 3.2 and 3.3. Hand them to anyone
whose previous file isn't ready, so nobody falls behind on the save chain.

**Bit depth.** Every practice file opens as **8 Bits/Channel** (they're
JPEGs). The lesson recommends 16-bit and gives a different Apply Image recipe
for it. To practice the 16-bit recipe, choose **Image ▸ Mode ▸ 16 Bits/Channel**
right after opening; to practice the 8-bit recipe, leave the file as it is.
Either way, check the title bar before opening Apply Image.

## Lab flow

**L07, Retouch the Skin (Lesson 3.1).** Own consented portrait (after global
corrections) or `l07-portrait-retouch.jpg` → duplicate the layer twice →
lower copy `Low`, upper copy `High` → hide High → **Filter ▸ Blur ▸ Gaussian
Blur** on Low until the pores vanish but the features stay (about 5–6 px on the
practice file; note it) → show High → **Image ▸ Apply Image**, Layer Low,
Channel RGB; 16-bit: Add, Invert ticked, Scale 2, Offset 0; 8-bit: Subtract,
Scale 2, Offset 128 → High to **Linear Light** → checkpoint: identical to the
original → even tone on Low (big soft Healing Brush, Sample: Current Layer, or a
low-opacity Mixer Brush with Sample All Layers off) → heal blemishes on High
(Healing Brush or Clone, Sample: Current Layer) → group both, opacity 70–85% →
check pores at 100% → Save As `skin-retouched.psd`.
*Now You (starts in class, finishes at home):* find the radius on
`l07-beauty-closeup.jpg` and `l07-candid-distance.jpg` (or two of the
learner's own portraits at different distances); over-smooth one face and
rescue it; compare with a plain soft brush and no separation; optionally record
the setup as an Action.

**L08, Sculpt the Face (Lesson 3.2).** `skin-retouched.psd` (or
`l08-portrait-clean-flat.jpg`) → select the top of the stack so the new layer
lands **above** the L07 group, not inside it → **Layer ▸ New ▸ Layer**, Mode
Soft Light, tick **Fill with Soft-Light-neutral color (50% gray)** → soft round
brush, Hardness 0, Flow 5–10%, Opacity 100% → burn (black) the eye sockets,
sides of the nose, under the cheekbones, under the jaw → dodge (white) the
cheekbone tops, nose bridge and tip, forehead center, brow bone → temporary
Black & White adjustment layer to check form, then delete it → lower the gray
layer's opacity until it's felt, not seen → Save As `portrait-sculpted.psd`.
*Now You:* three lighting moods on one face, or sculpt `l08-apple-flat.jpg`;
over-dodge and rescue; coarse and fine gray layers.

**L09, Finish the Portrait (Lesson 3.3, Module 3 deliverable).**
`portrait-sculpted.psd` (or `l09-portrait-sculpted.jpg`) → Curves layer, lift
midtones, invert the mask (Ctrl/⌘+I), paint the iris and whites → optional:
merged copy (Ctrl+Alt+Shift+E / ⌘+Option+Shift+E), **Filter ▸ Other ▸ High Pass**
about 1–3 px, blend Overlay or Soft Light, Alt/Option-click Add Layer Mask,
paint the iris only; never paint out the catchlight → Hue/Saturation layer:
Yellows, drop saturation; then Master, raise lightness slightly; invert the
mask, paint the teeth, feather the gum line → empty layer on top, Clone/Heal
with Sample: All Layers, remove flyaways with short strokes along the hair, fill
the thin gap, leave a few strays → **View ▸ Flip Horizontal** and toggle all
Module 3 work in pairs → save the finished layered file under a new name.
*Now You (homework):* three portraits back to back, timed; an over-finished
version beside the restrained one; magazine vs LinkedIn amounts; save the three
finishing layers as a template group.

Do not hand out the answer key or the instructor maps before the labs.

## What learners bring to Session 3

Ask each learner to bring **one portrait**, ideally two, as large original files
(straight from the camera or phone, not a messaging-app copy):

- **Who:** a self-portrait is ideal. Anyone else must have agreed to being
  photographed, **edited, and shown to the class**. Avoid photos of children.
- **What makes a good practice portrait:** the face fills a good part of the
  frame; at least ~2000 px on the long side; sharp focus on the eyes; fairly
  flat or soft light (so there's form to add in L08); a smile that shows teeth
  and some loose hair help L09.
- **For the L07 Now You:** two different distances, a close beauty shot and a
  candid at arm's length, show how the radius follows pore size. The practice
  pair covers this for anyone who brings only one.
- **Avoid:** photos already run through a beauty filter or "portrait smoothing"
  mode (there's no texture left to protect), heavy stylized filters, and group
  shots where the face is tiny.
- **Free-license option:** portraits from free-license sources (for example
  Pexels or Unsplash) are fine for practice. Check the current license on the
  download page first, and remind learners that retouching a real person's face
  carries the same respect rules: practice only, no misleading or unflattering
  edits, and don't publish edited faces of strangers.
- Learners who would rather not use a real face can do the whole module on the
  practice portraits. That's a complete, valid path.

**Ethics, briefly (from Lesson 3.3's FAQ).** Technique is neutral; context sets
the line. Evening skin and brightening eyes for a headshot is normal; reshaping
a body for an ad aimed at teenagers is a different conversation. Keep the
person recognizably themselves, and be honest with clients about what was
changed. In critique, talk about the edit, never the person's looks.

## Practice file specs

Generated by `labs/build_practice_files.py` (module 3 part: `labs/_parts/m3.py`,
functions `m3_*`, helpers `_m3_*`). Python 3 + Pillow + NumPy, fixed seed per
file (deterministic). All JPEGs: sRGB, 8 bits/channel, quality 90, no chroma
subsampling. Total for the module ≈ 6 MB.

### The shared face (`_m3_face`)
One illustrated head-and-shoulders portrait, drawn through a scale/offset
transform so the same face can be rendered close, standard, or far. Design
frame 2000 × 2500 px; face centered at (1000, 1230), about 1040 × 1360 px, with a
tapered chin; long dark-brown hair with a side part, drawn as hundreds of
individual strands; blue-gray top. Soft **window light from the viewer's left**
(background, hair, and skin brighter on the left; catchlights upper-left; nose
shadow on the viewer's right) but deliberately **flat** modeling on the face.

- **Skin texture (high frequency):** built at final pixel size from three
  layers of detail: fine grain, larger mottling, and individual pore pits with a
  lit rim, denser on the nose and cheeks. Pore size is a parameter in pixels:
  2.2 px (standard), 4.6 px (close-up), 1.1 px (candid). Clearly visible at 100%.
- **Tone patches (low frequency, map letters A–I):** soft Gaussian color shifts
  inside the skin only: redness on the nose (A), both cheeks (B, C), and chin
  (E); an uneven warm forehead patch (D); a muddy shadow under each eye (F, G);
  a sallow patch at the viewer's-left temple (H); a purplish patch on the
  viewer's-right jaw (I).
- **Blemishes (high frequency, map numbers 1–10):** ten raised red spots, radius
  6–11 px, with a small highlight and shadow; two carry a pale head. Placed
  across the forehead, cheeks, jaw, and chin, clear of the freckles.
- **Permanent features (keep):** about 36 freckles across the nose and upper
  cheeks, a mole beside the mouth on the viewer's left, two soft laugh lines.
- **Eyes:** dull, slightly gray whites (about RGB 206, 198, 188) with faint pink
  veins at the corners; brown irises with radial striations and a darker limbal
  ring (so High Pass sharpening has detail to find); a white catchlight
  upper-left in each pupil; lid line, lashes, lower lid, crease.
- **Mouth:** slightly parted lips showing a band of **yellowed teeth** (about
  RGB 226, 204, 152) with tooth separations and a pink gum line just above them.
- **Hair flaws (L09):** 17 flyaways leaving the hair outline against the
  background (11 around the top, 3 on each side), 2 stray hairs lying over the
  temples, and a thin gap in the hair mass on the viewer's right where the
  background shows through.

### `l07-portrait-retouch.jpg` (L07 main, and the start of the whole chain)
2000 × 2500. The shared face with **everything**: full tone patches, all ten
blemishes, pores at 2.2 px, dull eyes, yellow teeth, flyaways and gap. A
Gaussian Blur of about 5–6 px on Low removes the pores while keeping the
features; the tone patches stay on Low, the blemishes' texture goes to High.

### `l07-beauty-closeup.jpg` (L07 Now You)
2000 × 2500. The same face drawn 2.1× larger and cropped from mid-forehead to chin.
Pores at 4.6 px: the radius where they vanish is about 10–12 px. Everything
else (tone patches, blemishes, eyes, teeth) is present at the larger scale.

### `l07-candid-distance.jpg` (L07 Now You)
2400 × 1600 landscape. The same person at half scale right of center in the
frame, against a soft, out-of-focus outdoor background (sky, foliage, path).
Pores at 1.1 px: the radius is about 2–3 px. Shows that a candid needs a far
smaller radius and a lighter touch.

### `l08-portrait-clean-flat.jpg` (L08 catch-up)
2000 × 2500. The shared face as if Lesson 3.1 were done: no blemishes, tone
patches at about a fifth of full strength (as if the group opacity let a little
through), pores intact, lighting still flat. Eyes, teeth, and hair flaws still
present (they belong to L09).

### `l08-apple-flat.jpg` (L08 Now You)
1600 × 1600. A red apple on a warm-gray seamless backdrop, lit almost flat:
only a slight edge falloff, faint vertical color streaks and pale lenticel
dots, a stem in a soft dimple, a leaf, and a soft cast shadow to the right (the
light comes from the left). Dodge a highlight on the upper left and burn the
right side and base to make it round.

### `l09-portrait-sculpted.jpg` (L09 catch-up)
2000 × 2500. The L08 catch-up face with dodge and burn already applied:
forehead, nose bridge, cheekbone tops (left more than right), brow bones, and
chin lifted by a few percent; temples, eye sockets, sides of the nose, under the
cheekbones, jaw sides, and under the chin deepened, the viewer's right more
than the left. The finishing flaws are all present: dull whites, yellow teeth,
flyaways, strays, gap.

### `instructor/l07-flaw-map-INSTRUCTOR.png` (instructor only)
The main portrait at 1000 × 1250 with overlays: red numbered circles 1–10 on
the blemishes (heal on High), orange dashed circles A–I on the tone patches
(even on Low), blue circles on every flyaway and stray plus the gap (L09),
purple rings on the eyes and teeth (L09), and green marks on the permanent
features (dashed freckle region, mole, laugh lines). Legend across the top.

### `instructor/l08-light-map-INSTRUCTOR.png` (instructor only)
The L08 catch-up face at 1000 × 1250 with soft white zones where it wants
dodging and teal zones where it wants burning, stronger on the side away from
the light, plus a "window light" arrow from the viewer's left and a legend.
Show it on your own screen to a stuck learner, not on the projector.
