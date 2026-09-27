# Photoshop Intermediate: Instructor Kit ("Course-in-a-Box")

A ready-to-teach package that lets another instructor deliver the course
**Photoshop Intermediate: From Practitioner to Pro** without building it from scratch.
The live course site (<https://rays-photoshop-intermediate.netlify.app/>) is the
learner's textbook; this kit is everything the instructor needs around it. It is the
sequel to the intro course and its kit (**Photoshop: From First Win to Finished Work**,
<https://rays-photoshop-intro.netlify.app/>) and follows the same structure.

**Format:** 8 sessions × 3 hours (24 instructional hours), one module per session.
Every session ends with one finished professional deliverable. Run it weekly (8 weeks),
twice a week (4 weeks), or as an intensive (two sessions a day, with a gap before
Session 8 for the capstone build).

| Session | Module | Lessons | Tier | Deliverable |
|---------|--------|---------|------|-------------|
| S1 | 1 · Advanced Selection & Masking | L01–L03 (+ orientation & setup check) | Core Craft | A flowing-hair cutout that passes the saturated-background test |
| S2 | 2 · Color & Tone, Deep | L04–L06 | Core Craft | A graded, split-toned image delivered for screen and print |
| S3 | 3 · High-End Retouching | L07–L09 | Core Craft | A finished portrait that passes the flip-and-mirror test |
| S4 | 4 · Commercial Compositing | L10–L12 | Commercial Work | A composite key visual: placed, lit, shadowed, graded as one |
| S5 | 5 · Design Systems & Type | L13–L15 | Commercial Work | A four-size campaign from one master file |
| S6 | 6 · Generative + Automation, Advanced | L16–L18 | Commercial Work | A folder of data-driven cards from one template + a CSV |
| S7 | 7 · Multi-Shot Techniques | L19–L20 (+ capstone kickoff: L21) | Going Further | Panorama, HDR, focus stack, and a looping GIF/MP4 |
| S8 | 8 · Capstone | L21 review, L22–L23 | Going Further | A client-style project with a case study, presented |

Alongside the path runs **Recipes II** (`recipes.html` on the course site): 28
standalone how-to cards in six groups. Point learners to it for between-session
practice and after the course ends.

**Why this shape (and the timing trade-off):** each module already ends in a finished
piece, so one module fits one session. The lesson pages estimate 160–175 minutes per
module for a solo learner, and a 3-hour session leaves about 145–155 minutes after the
warm-up, break, and wrap-up. The room therefore runs every lesson's framing, live demo,
Guided Build, and self-check, and each lesson's **"Now You" solo variation starts in
class and finishes at home**. Each facilitator guide's agenda says what to protect (the
module deliverable) if you run long. Module 7 has only two lessons (about 105 minutes),
so Session 7 closes with a 42-minute **capstone kickoff** that runs L21 (The Brief &
the Plan) in class. The build (L22) happens as homework, and Session 8 is plan review,
a studio block, case-study assembly, presentations, and peer critique.

### Primary documents: the combined books (start here)

These are the **canonical** print/hand-out documents: the whole course in one file each,
with a cover, table of contents, and continuous pagination.

| File | Audience | Contents |
|------|----------|----------|
| `participant-workbook.{html,pdf}` | Learner | The complete workbook: all 8 modules as chapters |
| `facilitator-guide.{html,pdf}` | Instructor | The complete teaching manual: all 8 modules |
| `answer-key.{html,pdf}` | Instructor | Every quiz answered + lab reference notes, all modules (confidential) |

**Quiz items (self-checks) per module, all answered in the answer key:**
M1 18 · M2 18 · M3 18 · M4 18 · M5 18 · M6 18 · M7 12 · M8 18 = **138**.

The editable per-module docs live in `source/module-N/` (also usable for teaching a
single module standalone). **If you edit a module's doc, run `python3 build-combined.py`
to regenerate the three books, then re-render their PDFs.** Per-module PDFs are not
shipped; the combined PDFs replace them.

### Kit-wide documents (at this folder's root)

| File | Audience | Purpose |
|------|----------|---------|
| `setup-guide.html` | Learner | Pre-course "before you begin" handout: readiness check, update Photoshop, workspace, GPU and preferences, course folder, what images to bring to each session. Send it before Session 1 |
| `final-assessment.html` | Instructor | The four capstone project options from L21, a 12-row rubric quoting the L21/L22/L23 checklists (scored 1–3; pass = no row below 2 + deliverables exported at spec + a layered master), matching the Module 8 guide and answer key, peer-critique protocol, scoring sheet |
| `sell-sheet.html` | Prospective instructors | Marketing one-pager: what's inside, who it's for, license tiers |
| `README.md` · `LICENSE.md` | — | This overview and the tiered license template |

The 8-session **syllabus** lives in the course root, one level up, so it stays public:
`syllabus.html` (screen, light/dark), `syllabus-print.html` (print-first, with a
Print / Save as PDF button), and `Photoshop-Intermediate-Syllabus-8-sessions.pdf`.

**Still to do:** the `LICENSE.md` is a plain-language **template**; have it reviewed by
a lawyer before commercial distribution. Pricing in the sell sheet is a suggested
anchor within the license's ranges; adjust to your market.

---

## Folder layout

```
instructor-kit/
├─ participant-workbook.{html,pdf}   ← canonical hand-out books (all 8 modules)
├─ facilitator-guide.{html,pdf}
├─ answer-key.{html,pdf}
├─ setup-guide / final-assessment / sell-sheet  (.html + .pdf)
├─ slides/            one self-contained deck per module: module-N-<topic>.html (N = 1 … 8)
├─ labs/              module-1/ … module-8/  + build_practice_files.py (see labs/README.md)
│  ├─ module-N/practice/     generated practice files for that module's labs
│  └─ module-N/instructor/   instructor-only answer maps, references, fallbacks
├─ source/            module-1/ … module-8/  editable per-module docs (build the books)
├─ kit.css            single shared print-first stylesheet (Photoshop-blue accent)
├─ build-combined.py  regenerate the 3 books from source/
└─ README.md · LICENSE.md
```

Every document is print-ready (a **Print / Save as PDF** button + a tuned `@media print`
layout, US Letter). Slide decks are single-file and need no server (arrow keys / space
to advance).

The whole `instructor-kit/` folder is kept **off the live site**: the course root's
`_redirects` returns 404 for `/instructor-kit/*`. It lives in the repository only.

### How to teach from it
1. Send learners the **setup guide** a week before Session 1. It includes a readiness
   check (this course assumes intro-level skills) and lists which images to bring to
   which session, including a consented portrait for Session 3.
2. Skim the **facilitator guide** for the module and each lesson's timing.
3. Present from the module's deck in **`slides/`** (full-screen the browser), and demo
   live in Photoshop.
4. Learners follow the lesson's **Guided Build** on a practice file from
   `labs/module-N/practice/` or on their own image, and finish the session's
   deliverable against the lesson's **Project Completion Checklist**.
5. Learners work in the **participant workbook** (printed or on screen) and keep a
   **learning journal** (a prompt ends every lesson). The journal feeds the capstone
   case study.
6. Grade quizzes with the **answer key**, and the capstone with **final-assessment.html**.

Each module's facilitator guide opens with a minute-by-minute 0:00–3:00 agenda; the
public syllabus uses the same timings on a 9:00 clock.

**Session-specific checks:**
- **Session 1:** everyone notes their Color Settings but doesn't change them; Module 2
  sets color up properly.
- **Session 4:** turn on **Use Graphics Processor** on every machine; Perspective Warp is
  grayed out without it.
- **Session 5:** learners need Adobe Fonts access.
- **Session 6:** confirm every learner is signed in, online, and has generative credits.
  Reset rulers to **Pixels** after L17; the L18 script assumes pixels.
- **Session 7:** print the Module 8 workbook's L21 pages for the capstone kickoff.

### Requirements (for you and your learners)
- **Adobe Photoshop 2025 or newer**, desktop app, current release recommended.
- An **Adobe account** with a plan that includes Photoshop and Adobe Fonts.
- **Internet + generative credits** for Module 6 (Session 6).
- 16 GB of RAM strongly recommended (16-bit, many-layer files).
- Practice files from `labs/` plus learners' own images. **Never** hand out the course
  site's `images/` folder: those are Adobe Stock images licensed to the author for the
  website only, not for redistribution.

### Editing and building
The three books at the root are **generated** from `source/module-N/` by
`build-combined.py`. Don't hand-edit the combined `.html`: your changes will be
overwritten on the next build.

```bash
cd instructor-kit
python3 build-combined.py              # regenerate the 3 books from source/
python3 labs/build_practice_files.py   # regenerate labs/module-N/practice/ + instructor/
```

Then re-render the PDFs: open each document and use **Print / Save as PDF**
(Destination: Save as PDF, Paper: Letter, Margins: Default, Background graphics: on),
or use headless Chrome, for example:

```bash
google-chrome --headless --no-pdf-header-footer \
  --print-to-pdf=facilitator-guide.pdf facilitator-guide.html
```

Repeat for `participant-workbook`, `answer-key`, `setup-guide`, `final-assessment`,
and `sell-sheet`, and (from the course root) `syllabus-print.html`.

---

## License

See `LICENSE.md`. Short version: this kit is licensed to a **single instructor or
organization** to teach the course; it is **not** to be resold, and the facilitator
guide and answer keys are **not** for learner distribution. Tiers (Solo / Organization /
White-label, plus an optional updates add-on) are set at point of sale.

© 2026 Ray de la Paz. Photoshop Intermediate: From Practitioner to Pro. All rights reserved.
