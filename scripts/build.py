#!/usr/bin/env python3
"""Build the static GitHub Pages site from the TEI edition.

Usage:  python3 scripts/build.py            (run from the repository root)
Reads   data/cipollone-hocr-1997.xml
Writes  index.html, crew-and-course.html, analysis.html, about.html
"""
import html, json, re, sys
from collections import Counter, OrderedDict
from pathlib import Path
from lxml import etree

ROOT = Path(__file__).resolve().parent.parent
TEI_FILE = ROOT / "data" / "cipollone-hocr-1997.xml"
NS = {"t": "http://www.tei-c.org/ns/1.0"}
T = "{http://www.tei-c.org/ns/1.0}"
XMLID = "{http://www.w3.org/XML/1998/namespace}id"

doc = etree.parse(str(TEI_FILE))
root = doc.getroot()
esc = html.escape

def local(el):
    return etree.QName(el).localname

def text_of(el):
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip()

# ---------- lookups from the header and back matter ----------
gloss = {}
for lab in root.iterfind(".//t:back//t:list[@type='gloss']/t:label", NS):
    item = lab.getnext()
    item_txt = "".join(t for t in item.xpath("text()|*[local-name()!='note']//text()"))
    gloss[lab.get(XMLID)] = (text_of(lab), re.sub(r"\s+", " ", item_txt).strip())

people = OrderedDict()
for p in root.iterfind(".//t:particDesc/t:listPerson[@type='crew']/t:person", NS):
    names = p.findall("t:persName", NS)
    people[p.get(XMLID)] = {
        "name": text_of(names[0]),
        "nick": next((text_of(n) for n in names if n.get("type") == "nickname"), ""),
        "role": p.get("role"),
        "aff": text_of(p.find("t:affiliation", NS)),
        "note": text_of(p.find("t:note", NS)) if p.find("t:note", NS) is not None else "",
    }
orgs = {o.get(XMLID): text_of(o.find("t:orgName", NS)) for o in root.iterfind(".//t:listOrg/t:org", NS)}
places = OrderedDict((p.get(XMLID), text_of(p.find("t:placeName", NS))) for p in root.iterfind(".//t:listPlace/t:place", NS))
cats = OrderedDict()
for c in root.iterfind(".//t:taxonomy/t:category", NS):
    cats[c.get(XMLID)] = text_of(c.find("t:catDesc", NS))
CAT_SHORT = {"ct-rhythm": "Rhythm", "ct-technique": "Technique", "ct-rate": "Stroke rate",
             "ct-steering": "Steering", "ct-position": "Race position",
             "ct-motivation": "Personal / motivational", "ct-info": "Information"}

SHIFT_LABEL = {
    ("voice", "whisper"): "whispers", ("voice", "growl"): "growling, two octaves lower",
    ("voice", "normal"): None, ("loud", "p"): "quietly", ("loud", "f"): "much louder",
    ("tempo", "urgent"): "urgently", ("tempo", "calm"): "calmly",
    ("tempo", "enunciated"): "enunciating clearly", ("tempo", "conversational"): "almost conversationally",
    ("tempo", "cool"): "coolly", ("pitch", "low"): "lower", ("tension", "intense"): "intensely",
    ("tension", "frenzied"): "almost crazed",
}

# ---------- TEI -> HTML rendering ----------
notes_counter = [0]

def ref_id(v):
    return (v or "").lstrip("#")

def render_inline(el, pending_notes):
    """Render an element's children (with text and tails) to an HTML string."""
    out = [esc(el.text or "")]
    for ch in el:
        out.append(render_el(ch, pending_notes))
        out.append(esc(ch.tail or ""))
    return "".join(out)

def render_el(el, pending_notes):
    if not isinstance(el.tag, str):
        return ""
    n = local(el)
    if n == "shift":
        lab = SHIFT_LABEL.get((el.get("feature"), el.get("new")), el.get("new"))
        return f'<span class="shift">{esc(lab)}</span>' if lab else ""
    if n == "term":
        gid = ref_id(el.get("ref"))
        head, body = gloss.get(gid, ("", ""))
        return (f'<span class="term" tabindex="0" data-term="{esc(head)}" data-gloss="{esc(body)}">'
                f'{render_inline(el, pending_notes)}</span>')
    if n == "persName":
        pid = ref_id(el.get("ref"))
        p = people.get(pid, {})
        return (f'<a class="person" data-person="{pid}" href="crew-and-course.html#{pid}" '
                f'data-term="{esc(p.get("name",""))}" data-gloss="{esc(p.get("note",""))}">'
                f'{render_inline(el, pending_notes)}</a>')
    if n == "orgName":
        return f'<span class="org">{render_inline(el, pending_notes)}</span>'
    if n == "placeName":
        return f'<a class="place" href="crew-and-course.html#course">{render_inline(el, pending_notes)}</a>'
    if n == "measure":
        if el.get("type") == "strokeRate":
            return (f'<span class="rate" title="Stroke rate: {esc(el.get("quantity"))} strokes per minute">'
                    f'{render_inline(el, pending_notes)}</span>')
        return f'<span class="measure">{render_inline(el, pending_notes)}</span>'
    if n == "seg":
        cls = []
        if el.get("type") == "expletive": cls.append("expl")
        if el.get("rendition") == "#shout": cls.append("shout")
        return f'<span class="{" ".join(cls)}">{render_inline(el, pending_notes)}</span>'
    if n == "gap":
        return f'<span class="gap">[{esc(text_of(el))}]</span>'
    if n == "note":
        notes_counter[0] += 1
        k = notes_counter[0]
        pending_notes.append((k, el))
        return f'<button class="nref" aria-controls="n{k}" aria-label="Note {k}">{k}</button>'
    return render_inline(el, pending_notes)

def render_note(k, el):
    typ = el.get("type", "editorial")
    tag = {"editorial": "Note", "query": "Editorial query", "correction": "Correction", "context": "Context"}.get(typ, "Note")
    inner_notes = []
    body = render_inline(el, inner_notes)
    extra = "".join(render_note(kk, ee) for kk, ee in inner_notes)
    return f'<div class="note {esc(typ)}" id="n{k}"><span class="tag">{tag}</span>{body}</div>{extra}'

def render_div(div):
    parts = []
    head = div.find("t:head", NS)
    n_u = len(div.findall("t:u", NS))
    parts.append(f'<section id="{div.get(XMLID)}"><h2>{esc(text_of(head))} <small>{n_u} utterances</small></h2>')
    for ch in div:
        if not isinstance(ch.tag, str): continue
        n = local(ch)
        pend = []
        if n == "u":
            who = ref_id(ch.get("who"))
            ana = " ".join(ref_id(a) for a in (ch.get("ana") or "").split())
            persons = " ".join(sorted({ref_id(p.get("ref")) for p in ch.iterfind(".//t:persName", NS)}))
            parts.append(f'<p class="u" data-who="{who}" data-ana="{ana}" data-persons="{persons}">{render_inline(ch, pend)}</p>')
        elif n == "incident":
            parts.append(f'<p class="incident">{render_inline(ch.find("t:desc", NS), pend)}</p>')
        elif n == "note":
            parts.append(f'<div class="context">{render_inline(ch, pend)}</div>')
        parts.extend(render_note(k, e) for k, e in pend)
    parts.append("</section>")
    return "\n".join(parts)

body_divs = root.findall(".//t:body/t:div", NS)
transcript_html = "\n".join(render_div(d) for d in body_divs)

# ---------- analysis data ----------
utts = root.findall(".//t:body//t:u[@who='#cipollone']", NS)
cat_counts = Counter()
for u in utts:
    for a in (u.get("ana") or "").split():
        cat_counts[ref_id(a)] += 1
mentions = Counter()
for p in root.iterfind(".//t:body//t:u/t:persName", NS):
    mentions[ref_id(p.get("ref"))] += 1
rates = []
for i, u in enumerate(root.findall(".//t:body//t:u", NS)):
    for m in u.iterfind(".//t:measure[@type='strokeRate']", NS):
        sec = u.getparent().get("type")
        rates.append({"i": i + 1, "rate": float(m.get("quantity")), "text": text_of(u), "section": sec})
def norm(s):
    s = s.lower()
    s = re.sub(r"[^a-z' ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()
phr = Counter()
for u in utts:
    t = norm("".join(x for x in u.xpath(".//text()[not(ancestor::t:note)]", namespaces=NS)))
    for key in ["push send", "legs send", "push chaa", "legs chaa", "that's it", "walk away",
                "on the rudder", "attack", "catches in", "drive", "do not sit", "go"]:
        phr[key] += len(re.findall(r"\b" + re.escape(key).replace("chaa", "cha+") + r"\b", t))
words = sum(len(norm("".join(u.xpath(".//text()[not(ancestor::t:note)]", namespaces=NS))).split()) for u in utts)
expl = len(root.findall(".//t:body//t:seg[@type='expletive']", NS))
whispers = len(root.findall(".//t:body//t:shift[@new='whisper']", NS))
stats = {"utterances": len(utts), "words": words, "expletives": expl, "whispers": whispers,
         "rateCalls": len(rates), "namedCalls": sum(mentions.values())}

# ---------- SVG charts (single series, so one hue and no legend) ----------
MARK = "#0e7c86"

def hbar_svg(rows, title, unit):
    W, rowh, lab = 640, 30, 190
    H = rowh * len(rows) + 30
    mx = max(v for _, v, _ in rows) or 1
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{esc(title)}">']
    for gx in range(0, int(mx) + 1, max(1, round(mx / 5))):
        x = lab + (W - lab - 50) * gx / mx
        s.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="0" y2="{H-24}" stroke="#e6eaee"/>'
                 f'<text x="{x:.1f}" y="{H-8}" font-size="11" fill="#6b7684" text-anchor="middle">{gx}</text>')
    for i, (name, v, tip) in enumerate(rows):
        y = i * rowh + 6
        w = max(8, (W - lab - 50) * v / mx) if v else 0
        s.append(f'<text x="{lab-10}" y="{y+13}" font-size="14" fill="#1c2430" text-anchor="end">{esc(name)}</text>')
        s.append(f'<g class="bar" data-tip="{esc(tip)}"><rect x="{lab}" y="{y-3}" width="{W-lab}" height="{rowh-2}" fill="transparent"/>'
                 + (f'<path d="M{lab},{y} h{w-4:.1f} a4,4 0 0 1 4,4 v10 a4,4 0 0 1 -4,4 h-{w-4:.1f} z" fill="{MARK}"/>' if v else '') + '</g>')
        s.append(f'<text x="{lab+w+6:.1f}" y="{y+13}" font-size="12" fill="#4a5566">{v:g}</text>')
    s.append("</svg>")
    return "".join(s)

def rate_svg(rates):
    W, H, l, r, t, b = 640, 260, 44, 16, 16, 34
    n = len(root.findall(".//t:body//t:u", NS))
    lo, hi = 33, 40
    X = lambda i: l + (W - l - r) * (i - 1) / (n - 1)
    Y = lambda v: t + (H - t - b) * (hi - v) / (hi - lo)
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Stroke rate called over the course of the recording">']
    for v in range(lo, hi + 1):
        s.append(f'<line x1="{l}" x2="{W-r}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="#e6eaee"/>'
                 f'<text x="{l-8}" y="{Y(v)+4:.1f}" font-size="11" fill="#6b7684" text-anchor="end">{v}</text>')
    # section bands
    idx = 0
    for d in body_divs:
        k = len(d.findall("t:u", NS))
        if idx > 0:
            s.append(f'<line x1="{X(idx+1):.1f}" x2="{X(idx+1):.1f}" y1="{t}" y2="{H-b}" stroke="#c3cbd3" stroke-dasharray="3 3"/>')
        lbx = X(idx+1)+4 if d.get("type") != "finish" else W - r
        s.append(f'<text x="{lbx:.1f}" y="{H-12}" font-size="11" fill="#6b7684" text-anchor="{'end' if d.get('type')=='finish' else 'start'}">{ {"warmup":"Warm-up","race":"Race","finish":"Finish"}.get(d.get("type"),"") }</text>')
        idx += k
    pts = " ".join(f"{X(p['i']):.1f},{Y(p['rate']):.1f}" for p in rates)
    s.append(f'<polyline points="{pts}" fill="none" stroke="{MARK}" stroke-width="2" stroke-linejoin="round"/>')
    for p in rates:
        tip = f"Utterance {p['i']}: {p['rate']:g} spm. “{p['text'][:70]}”"
        s.append(f'<g class="dot" data-tip="{esc(tip)}"><circle cx="{X(p["i"]):.1f}" cy="{Y(p["rate"]):.1f}" r="12" fill="transparent"/>'
                 f'<circle cx="{X(p["i"]):.1f}" cy="{Y(p["rate"]):.1f}" r="5" fill="{MARK}" stroke="#fff" stroke-width="2"/></g>')
    s.append(f'<text x="{l}" y="{t-4}" font-size="11" fill="#6b7684">strokes per minute</text></svg>')
    return "".join(s)

cat_rows = [(CAT_SHORT[c], cat_counts.get(c, 0), f"{CAT_SHORT[c]}: {cat_counts.get(c,0)} utterances. {cats[c]}")
            for c in sorted(cats, key=lambda c: -cat_counts.get(c, 0)) if cat_counts.get(c, 0)]
rower_rows = [(f'{people[p]["name"]}', mentions.get(p, 0), f'{people[p]["name"]}: named {mentions.get(p,0)} times')
              for p in sorted([p for p in people if people[p]["role"] == "rower"], key=lambda p: -mentions.get(p, 0))]
phr_rows = [(k.replace("chaa", "chaa").capitalize(), v, f"“{k}”: {v} times") for k, v in phr.most_common() if v]

def table(rows, h1, h2):
    tr = "".join(f"<tr><td>{esc(a)}</td><td class='num'>{b:g}</td></tr>" for a, b, _ in rows)
    return f'<details class="tbl"><summary>Show as table</summary><table><thead><tr><th>{h1}</th><th class="num">{h2}</th></tr></thead><tbody>{tr}</tbody></table></details>'

# ---------- page shell ----------
NAV = [("index.html", "Edition"), ("crew-and-course.html", "Crew & course"),
       ("analysis.html", "Analysis"), ("about.html", "About & recommendations"),
       ("data/cipollone-hocr-1997.xml", "TEI XML")]

def page(fname, title, content, hero=""):
    nav = "".join(f'<a href="{h}"{" aria-current=page" if h == fname else ""}>{l}</a>' for h, l in NAV)
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · Cipollone, HOCR 1997</title>
<meta name="description" content="A TEI digital edition of coxswain Pete Cipollone's recording from the record-breaking US Rowing men's eight at the 1997 Head of the Charles.">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 16 16%22%3E%3Crect width=%2216%22 height=%2216%22 rx=%223%22 fill=%22%230e7c86%22/%3E%3Cpath d=%22M2 9h12%22 stroke=%22%23ff6b4a%22 stroke-width=%223%22/%3E%3C/svg%3E"><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400;1,500&family=IBM+Plex+Mono:wght@500;700&display=swap"><link rel="stylesheet" href="assets/style.css"></head>
<body class="notes">
<a class="skip" href="#main">Skip to content</a>
<header class="mast"><div class="mast-inner"><a class="brand" href="index.html">Walk Away<small>HOCR 1997 · Coxswain recording</small></a><nav class="main" aria-label="Main">{nav}</nav></div></header>
{hero}
<main id="main">{content}</main>
<footer>Transcript text © row2k.com, quoted for educational use, with <a href="https://www.row2k.com/features/488/pete-cipollone-olympic-gold-medalist-coxing-the-1997-head-of-the-charles/">audio at row2k</a>. Encoding, notes and site released under CC BY 4.0. Built from <a href="data/cipollone-hocr-1997.xml">TEI P5</a> with <code>scripts/build.py</code>.</footer>
<div id="tip" role="tooltip"></div>
<script src="assets/site.js"></script>
</body></html>"""

# ----- index / edition -----
hero = f"""<section class="hero"><div class="hero-inner">
<div class="eyebrow">Head of the Charles Regatta · 19 October 1997 · Championship Eights</div>
<h1>“Walk away”: fourteen minutes in the coxswain's seat</h1>
<p class="lede">Pete Cipollone's in-boat recording of the US Rowing eight, which started first, finished first, and set a course record that stood for twenty years. Every call is encoded in TEI. Hover over the underlined terms for rowing jargon and over the names to identify the rowers.</p>
<div class="facts"><div><b>13:58.9</b><span>Official time, course record</span></div><div><b>4.8 km</b><span>Three miles upstream</span></div><div><b>{stats['utterances']}</b><span>Encoded calls</span></div><div><b>{stats['namedCalls']}</b><span>Calls naming a rower</span></div></div>
</div></section>"""

cat_opts = "".join(f'<option value="{c}">{esc(CAT_SHORT[c])} ({cat_counts.get(c,0)})</option>' for c in cats)
per_opts = "".join(f'<option value="{p}">{esc(people[p]["name"])}{" (“"+esc(people[p]["nick"])+"”)" if people[p]["nick"] else ""}</option>'
                   for p in people if people[p]["role"] == "rower")
edition = f"""<div class="edition">
<article class="transcript" id="transcript">
{transcript_html}
</article>
<aside class="controls" aria-label="Reading controls">
<h2>Reading controls</h2>
<label><input type="checkbox" id="t-notes" checked> Show editorial notes</label>
<label><input type="checkbox" id="t-mask"> Mask profanity</label>
<hr>
<label for="f-cat" style="display:block">Highlight a type of call</label>
<select id="f-cat"><option value="">All calls</option>{cat_opts}</select>
<label for="f-per" style="display:block;margin-top:.7rem">Highlight calls to a rower</label>
<select id="f-per"><option value="">Everyone</option>{per_opts}</select>
<p class="count" id="hl-count" aria-live="polite"></p>
<hr>
<div class="legend-key">
<span><span class="shift">whispers</span> change of voice</span>
<span><span class="rate">36</span> stroke rate (spm)</span>
<span><span class="term">term</span> glossary term</span>
<span><span class="incident" style="margin:0">event</span></span>
</div>
</aside>
</div>"""
(ROOT / "index.html").write_text(page("index.html", "Edition", edition, hero))

# ----- crew & course -----
RIG = {1: "Starboard", 2: "Port", 3: "Starboard", 4: "Port", 5: "Starboard", 6: "Port", 7: "Starboard", 8: "Port"}
rowers = [p for p in people if people[p]["role"] == "rower"]
crew_rows = ""
for i, pid in enumerate(rowers, 1):
    p = people[pid]
    seat = "Bow (1)" if i == 1 else ("Stroke (8)" if i == 8 else str(i))
    crew_rows += (f'<tr id="{pid}"><td>{seat}</td><td><b>{esc(p["name"])}</b>{"<br><span class=muted>“"+esc(p["nick"])+"”</span>" if p["nick"] else ""}</td>'
                  f'<td>{esc(p["aff"])}</td><td>{RIG[i]}</td><td class="num">{mentions.get(pid,0)}</td></tr>')
cox = people["cipollone"]
crew_rows += f'<tr id="cipollone"><td>Coxswain</td><td><b>{esc(cox["name"])}</b></td><td>{esc(cox["aff"])}</td><td>Stern</td><td class="num">n/a</td></tr>'

# boat diagram: bow at right, stern (cox) at left, direction of travel → right
bx = []
W = 900
bx.append(f'<svg viewBox="0 0 {W} 170" role="img" aria-label="Seating diagram of the eight, coxswain at the stern, bow on the right">')
bx.append('<path d="M40,85 C120,52 760,52 880,85 C760,118 120,118 40,85 Z" fill="#eef6f6" stroke="#0a4f56" stroke-width="2"/>')
bx.append('<text x="880" y="40" text-anchor="end" font-size="12" fill="#6b7684">BOW →</text><text x="40" y="40" font-size="12" fill="#6b7684">STERN</text>')
bx.append('<circle cx="95" cy="85" r="13" fill="#e8553a"/><text x="95" y="89" text-anchor="middle" font-size="11" fill="#fff" font-weight="700">C</text>')
for i, pid in enumerate(reversed(rowers)):
    seat = 8 - i
    x = 160 + i * 88
    side = RIG[seat]
    oy = 30 if side == "Port" else 140
    bx.append(f'<line x1="{x}" y1="85" x2="{x-18}" y2="{oy}" stroke="#0e7c86" stroke-width="3" stroke-linecap="round"/>')
    bx.append(f'<a href="#{pid}"><circle cx="{x}" cy="85" r="15" fill="#0a4f56"/><text x="{x}" y="89" text-anchor="middle" font-size="12" fill="#fff" font-weight="700">{seat}</text></a>')
    bx.append(f'<text x="{x+12}" y="{oy+ (4 if side=="Port" else 4)}" font-size="11.5" fill="#1c2430">{esc(people[pid]["name"].split()[-1])}</text>')
bx.append('<text x="470" y="18" text-anchor="middle" font-size="11" fill="#6b7684">PORT (coxswain\'s left)</text><text x="470" y="166" text-anchor="middle" font-size="11" fill="#6b7684">STARBOARD (coxswain\'s right)</text></svg>')

# course schematic
landmarks = list(places.items())
events = {"bu-bridge": "Calls echo under the bridge. “We got flat water.”",
          "river-st": "“Here's the first bridge, in the wind.” The one-minute commitment.",
          "western-ave": "Crowds cheer. “They're cheering for you.” Taunting Richter about Princeton.",
          "weeks": "Ahead: “The next turn will be to port, and it's the big dog.” (location not certain)",
          "start": "“Ready all, row!” US Rowing starts first.",
          "finish": "“12:40 down, I think you can break the record!” Official time 13:58.9."}
cs = [f'<svg viewBox="0 0 900 300" role="img" aria-label="Schematic of the Head of the Charles course with bridges in order">']
cs.append('<path d="M40,240 C180,250 200,120 320,140 S520,250 600,170 S760,60 860,80" fill="none" stroke="#cfe9ea" stroke-width="26" stroke-linecap="round"/>')
cs.append('<path d="M40,240 C180,250 200,120 320,140 S520,250 600,170 S760,60 860,80" fill="none" stroke="#0e7c86" stroke-width="2" stroke-dasharray="6 6"/>')
pos = [(40,240),(170,226),(285,140),(420,180),(560,196),(660,128),(770,74),(860,80)]
for (pid, name), (x, y) in zip(landmarks, pos):
    has = pid in events
    cs.append(f'<g class="dot" data-tip="{esc(name + (": " + events[pid] if has else ""))}"><circle cx="{x}" cy="{y}" r="14" fill="transparent"/>'
              f'<circle cx="{x}" cy="{y}" r="{7 if has else 5}" fill="{"#e8553a" if has else "#0a4f56"}" stroke="#fff" stroke-width="2"/></g>')
    ty = y - 18 if y > 120 else y + 28
    cs.append(f'<text x="{x}" y="{ty}" text-anchor="middle" font-size="12" fill="#1c2430">{esc(name.split(",")[0].replace(" Bridge","").replace("Memorial ",""))}</text>')
cs.append('<text x="40" y="290" font-size="11" fill="#6b7684">Schematic only, not to scale. Red marks are places the recording refers to. Hover for the calls.</text></svg>')

course_list = "".join(f"<li><b>{esc(n)}</b>{' · ' + esc(events[p]) if p in events else ''}</li>" for p, n in landmarks)
crew = f"""<div class="prose"><h2 style="margin-top:0">The boat</h2>
<p>row2k lists the crew from bow to stern. The entry was not the 1997 World Champion eight, but a boat drawn from members of the 1997 US Team. Cipollone uses surnames, nicknames ("Philthy", "Giboon") and seat numbers ("Seven, six and five, go!"), so the names in the transcript link here.</p></div>
<div class="card chart">{''.join(bx)}<p class="muted" style="font:13px var(--sans)">The rigging is assumed to be the standard US layout, with the stroke on port. The call "Richter … you drive the starboard side" is consistent with it.</p></div>
<h3>Crew list</h3>
<div class="card" style="overflow:auto"><table><thead><tr><th>Seat</th><th>Name</th><th>College</th><th>Side</th><th class="num">Named in calls</th></tr></thead><tbody>{crew_rows}</tbody></table></div>
<h2 id="course">The course</h2>
<div class="prose"><p>The Head of the Charles is a three-mile (4.8 km) head race rowed upstream on the Charles River between Boston and Cambridge. Crews start one at a time at intervals and race the clock. Winning depends as much on steering the long bends and the narrow bridge arches as on speed.</p></div>
<div class="card chart">{''.join(cs)}</div>
<ol class="prose" style="font-family:var(--sans);font-size:15px">{course_list}</ol>
<p class="muted prose" style="font:13px var(--sans)">The excerpt names only the BU Bridge and the Western Avenue Bridge. The "first bridge" is identified as River Street from the order of the course, and this identification is marked as an editorial inference in the TEI.</p>"""
(ROOT / "crew-and-course.html").write_text(page("crew-and-course.html", "Crew & course", crew))

# ----- analysis -----
ana = f"""<div class="prose"><h2 style="margin-top:0">Reading the calls as data</h2>
<p>Every number on this page is computed from the TEI markup at build time, so it updates when the encoding changes. The figures show how a world-class coxswain spreads his attention. Short rhythm phrases dominate the word counts, and among the coded calls, personal calls to named rowers outnumber steering, stroke-rate, technique and race information.</p></div>
<div class="facts" style="color:var(--ink);margin:1.5rem 0 2rem">
<div><b>{stats['utterances']}</b><span style="color:var(--ink-3)">Calls by the cox</span></div>
<div><b>{stats['words']}</b><span style="color:var(--ink-3)">Words spoken</span></div>
<div><b>{stats['rateCalls']}</b><span style="color:var(--ink-3)">Stroke-rate calls</span></div>
<div><b>{stats['whispers']}</b><span style="color:var(--ink-3)">Whispered calls</span></div>
<div><b>{stats['expletives']}</b><span style="color:var(--ink-3)">Expletives</span></div></div>
<div class="grid2">
<div class="card chart"><h3>Stroke rate called through the race</h3>{rate_svg(rates)}
<p class="muted" style="font:13px var(--sans)">After a 39 start sprint the rate settles to 36, then falls to 34.5 by the River Street commitment and holds near 35. A head race is paced over fourteen minutes, not sprinted.</p>
{table([(f"Utterance {r['i']}", r['rate'], '') for r in rates], 'Position', 'spm')}</div>
<div class="card chart"><h3>Calls by type</h3>{hbar_svg(cat_rows, 'Calls by type', 'utterances')}
<p class="muted" style="font:13px var(--sans)">Only coded calls are counted. Pure rhythm calls ("Push, send") are left uncoded in this version (see recommendation 15 on the About page).</p>
{table(cat_rows, 'Call type', 'Utterances')}</div>
<div class="card chart"><h3>Who gets called out by name</h3>{hbar_svg(rower_rows, 'Mentions per rower', 'mentions')}
<p class="muted" style="font:13px var(--sans)">Holbrook (seat 2) is never named in this excerpt. Callahan, who was told it was his "seat race", is named at the start and again near the end.</p>
{table(rower_rows, 'Rower', 'Times named')}</div>
<div class="card chart"><h3>The cox's vocabulary</h3>{hbar_svg(phr_rows, 'Most frequent call phrases', 'times')}
<p class="muted" style="font:13px var(--sans)">Phrase counts across all calls by the cox. Short, repeated call-and-response phrases carry the rhythm of the boat.</p>
{table(phr_rows, 'Phrase', 'Times')}</div>
</div>"""
(ROOT / "analysis.html").write_text(page("analysis.html", "Analysis", ana))

# ----- about & recommendations (content kept in a separate fragment for easy editing) -----
about_frag = (ROOT / "scripts" / "about.fragment.html").read_text()
(ROOT / "about.html").write_text(page("about.html", "About & recommendations", about_frag))

(ROOT / "data" / "stats.json").write_text(json.dumps({"stats": stats, "callTypes": cat_counts, "mentions": mentions, "strokeRates": rates}, indent=2))
print("built:", stats)
