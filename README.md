# Walk Away: Pete Cipollone coxes the 1997 Head of the Charles

A TEI P5 digital edition of coxswain Pete Cipollone's in-boat recording from the US Rowing men's Championship Eight at the Head of the Charles Regatta, 19 October 1997. The crew started first and finished first in 13:58.9, a course record that stood until 2017.

**Live site:** see the GitHub Pages link in the repository's About panel.

## What's here

| Path | Contents |
|---|---|
| `data/cipollone-hocr-1997.xml` | Revised TEI edition (v2.0), the source of truth |
| `original/cipollone-1997-original.xml` | Original student encoding (v1.0), unchanged |
| `scripts/build.py` | Builds every HTML page from the TEI |
| `scripts/about.fragment.html` | Content of the About & recommendations page |
| `data/stats.json` | Figures computed from the TEI at build time |
| `index.html`, `crew-and-course.html`, `analysis.html`, `about.html` | Generated site |

## Rebuild

```
pip install lxml
python3 scripts/build.py
```

Edit the XML, rebuild, and commit. GitHub Pages serves the repository root. Both XML files validate against `tei_all` (TEI P5 4.10.2).

## Changes from v1.0

The full list, with planned next steps, is on the site's About & recommendations page. In short: corrected factual notes, a complete header, the spoken-text module (`u`, `shift`, `incident`), the crew and course in `particDesc` and `settingDesc`, a call-type taxonomy in place of free-text `@ana`, valid renditions, a linked glossary, removal of hotlinked images, a declared profanity policy, and data-driven analysis.

## Rights

The transcript and audio belong to [row2k.com](https://www.row2k.com/features/488/pete-cipollone-olympic-gold-medalist-coxing-the-1997-head-of-the-charles/) and are quoted here for non-commercial educational use. The encoding, annotations, glossary, diagrams and code are released under CC BY 4.0.
