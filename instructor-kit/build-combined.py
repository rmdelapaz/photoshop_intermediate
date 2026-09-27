#!/usr/bin/env python3
"""
Assemble the three combined instructor-kit books from the per-module source docs.

Reads:  source/module-N/{facilitator-guide,participant-workbook,answer-key}.html
Writes: ./participant-workbook.html, ./facilitator-guide.html, ./answer-key.html
        (the canonical hand-out documents, each with a cover + TOC + one chapter
         per module, continuous pagination)

After editing a module's source doc, re-run this to regenerate the books, then
render PDFs (each book has a Print / Save as PDF button, or use headless Chrome).

Usage:  python3 build-combined.py   (run from the instructor-kit/ folder)
"""
import os

MODULES = [
    (1, "Advanced Selection & Masking", [("L01", "Luminosity Masks: Select by Tone"), ("L02", "Channel Masking & Blend-If"), ("L03", "Select & Mask Mastery: The Hard Cutout")]),
    (2, "Color & Tone, Deep", [("L04", "Color Management & Working Spaces"), ("L05", "Grading with Curves, Gradient Maps & LUTs"), ("L06", "Match, Split-Tone & Soft-Proof")]),
    (3, "High-End Retouching", [("L07", "Skin & Frequency Separation"), ("L08", "Dodge & Burn Sculpting"), ("L09", "Eyes, Teeth & Hair: Natural Finish")]),
    (4, "Commercial Compositing", [("L10", "Match Perspective, Scale & Lens"), ("L11", "Light, Shadows & Reflections"), ("L12", "Atmosphere & the Unifying Grade")]),
    (5, "Design Systems & Type", [("L13", "Type Systems, Styles & Grids"), ("L14", "Smart-Object Templates & Linked Assets"), ("L15", "Campaign from One Master")]),
    (6, "Generative + Automation, Advanced", [("L16", "Generative for Compositing"), ("L17", "Advanced Actions & Conditionals"), ("L18", "Data-Driven Graphics & Scripting")]),
    (7, "Multi-Shot Techniques", [("L19", "Panoramas, HDR & Focus Stacking"), ("L20", "Timeline Animation & Export")]),
    (8, "Capstone", [("L21", "The Brief & the Plan"), ("L22", "Studio Session: Build It"), ("L23", "Present & Case Study")]),
]

DOCS = {
    "participant-workbook": dict(
        base="participant-workbook.html", role="Participant Workbook",
        eyebrow="Photoshop Intermediate · Complete Course Workbook",
        sub="Your working notebook for the whole course — all eight modules. Read the key ideas, study the worked examples, do the exercises in the space provided, and check yourself with the quizzes.",
        chips=['<span class="chip"><b>8</b> modules · 23 lessons</span>', '<span class="chip">Write-in exercises &amp; self-checks</span>', '<span class="chip">Name: ____________________</span>'],
        toolbar=("Student workbook —", "write in it · bring it to every session")),
    "facilitator-guide": dict(
        base="facilitator-guide.html", role="Facilitator Guide",
        eyebrow="Photoshop Intermediate · Complete Facilitator Guide",
        sub="The full teaching manual for the eight-session course (one 3-hour session per module). Timing, live-demo scripts, the beginner mistakes to pre-empt, lab facilitation, and checks for understanding — for all eight modules.",
        chips=['<span class="chip"><b>8</b> modules · 23 lessons</span>', '<span class="chip">8 sessions × 3 h · 24 h with labs &amp; breaks</span>', '<span class="chip">Instructor copy · not for students</span>'],
        toolbar=("Instructor copy —", "contains answers &amp; timing · not for students")),
    "answer-key": dict(
        base="answer-key.html", role="Answer Key",
        eyebrow="Photoshop Intermediate · Complete Answer Key",
        sub="Every quiz answered and explained, plus reference notes for each lab — for all eight modules. Use for grading and reteaching. Confidential instructor material.",
        chips=['<span class="chip"><b>8</b> modules</span>', '<span class="chip">every quiz item + lab reference notes</span>', '<span class="chip">Confidential — do not distribute</span>'],
        toolbar=("Instructor copy —", "answers &amp; solutions · not for students")),
}

STYLE = """<style>
  .cover { border-bottom:3px solid var(--accent); padding-bottom:22px; margin-bottom:12px; }
  .cover .kit-eyebrow { color:var(--accent); }
  .cover h1 { font-size:clamp(2rem,5vw,2.7rem); font-weight:800; letter-spacing:-.02em; margin:10px 0 6px; }
  .cover .sub { font-size:1.05rem; color:var(--ink-2); max-width:64ch; }
  .toc { margin:26px 0 8px; }
  .toc h2 { font-size:.95rem; font-weight:700; letter-spacing:.05em; text-transform:uppercase; color:var(--ink-2); margin-bottom:10px; }
  .toc ol { list-style:none; margin:0; padding:0; }
  .toc .mod { font-family:"Archivo",sans-serif; font-weight:700; font-size:1.02rem; margin:12px 0 3px; color:var(--ink); }
  .toc .mod .mnum { font-family:"JetBrains Mono",monospace; font-size:.7rem; color:var(--accent); font-weight:600; margin-right:8px; }
  .toc .les { display:flex; gap:10px; padding:2px 0 2px 18px; font-size:.9rem; color:var(--ink-2); }
  .toc .les .lc { font-family:"JetBrains Mono",monospace; font-size:.72rem; color:var(--accent); }
  .modwrap { break-before:page; }
  .modwrap > .mast h1 { font-size:1.55rem; }
  @media print { .modwrap { break-before:page; } }
</style>"""


def esc(s):
    return s.replace("&", "&amp;")


def extract_body(path):
    """Inner content of .sheet minus the trailing .foot block."""
    html = open(path, encoding="utf-8").read()
    i = html.index('<div class="sheet">') + len('<div class="sheet">')
    j = html.rindex('<div class="foot">')
    return html[i:j].strip()


def build(key):
    d = DOCS[key]
    toc_rows = []
    for num, title, lessons in MODULES:
        toc_rows.append(f'<li class="mod"><span class="mnum">MOD {num}</span>{esc(title)}</li>')
        for lc, lt in lessons:
            toc_rows.append(f'<li class="les"><span class="lc">{lc}</span><span>{esc(lt)}</span></li>')
    toc = "\n        ".join(toc_rows)

    mods = []
    for num, _, _ in MODULES:
        body = extract_body(os.path.join("source", f"module-{num}", d["base"]))
        mods.append(f'<section class="modwrap">\n{body}\n</section>')
    mods = "\n\n".join(mods)

    out = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{d['role']} — Photoshop Intermediate</title>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700;800&family=Source+Sans+3:ital,wght@0,400;0,500;0,600;1,400&family=JetBrains+Mono:wght@500;600&display=swap">
<link rel="stylesheet" href="kit.css">
{STYLE}
</head>
<body>

<div class="toolbar">
  <span class="lbl">{d['toolbar'][0]}</span>
  <button type="button" onclick="window.print()">🖨 Print / Save as PDF</button>
  <span class="hint">{d['toolbar'][1]}</span>
</div>

<div class="sheet">

  <header class="cover">
    <div class="kit-eyebrow">{d['eyebrow']}</div>
    <h1>Photoshop Intermediate: From Practitioner to Pro</h1>
    <p class="sub">{d['sub']}</p>
    <div class="meta-row">{''.join(d['chips'])}</div>
  </header>

  <nav class="toc">
    <h2>Contents</h2>
    <ol>
        {toc}
    </ol>
  </nav>

{mods}

  <div class="foot">
    <div class="who"><span class="bio">Photoshop Intermediate: From Practitioner to Pro · {d['role']}</span></div>
    <div class="ver">Complete {d['role']} · all 8 modules · v1.0 · &copy; 2026 Ray de la Paz</div>
  </div>

</div>
</body>
</html>
"""
    open(d["base"], "w", encoding="utf-8").write(out)
    print(f"wrote {d['base']}  ({len(out)//1024} KB)")


if __name__ == "__main__":
    if not os.path.isdir("source"):
        raise SystemExit("Run this from the instructor-kit/ folder (source/ not found).")
    for k in DOCS:
        build(k)
    print("Done. Now render PDFs (open each and Print, or use headless Chrome).")
