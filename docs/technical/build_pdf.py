"""paper.md -> stuffplus2240.html -> stuffplus2240.pdf without pandoc/LaTeX (HACK-023).

    python docs/technical/build_pdf.py [--html-only]

Handles the Markdown subset paper.md uses: YAML title block, numbered headings ({-} = unnumbered), paragraphs,
bullet and numbered lists (one nesting level), pipe tables with a ": caption" line, figures with {width=..},
**bold**, *italic*, `code`, $inline$ and $$display$$ math (KaTeX), and [@key; @key] citations resolved from
references.bib into an author-year bibliography at ::: {#refs}. Prints with headless Edge or Chrome.
"""
from __future__ import annotations

import html
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC, BIB = HERE / "paper.md", HERE / "references.bib"
OUT_HTML, OUT_PDF = HERE / "stuffplus2240.html", HERE / "stuffplus2240.pdf"
KATEX = "https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9"
BROWSERS = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe", "msedge", "google-chrome", "chromium", "chrome"]

CSS = """
@page { size: Letter; margin: 1.9cm 2.0cm 1.8cm 2.0cm; }
:root { --rojo: #C8102E; --tinta: #111111; --gris: #555; }
body { font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif; font-size: 10pt; line-height: 1.38; color: var(--tinta); }
header.run { position: fixed; top: -1.25cm; left: 0; right: 0; font-size: 8pt; border-bottom: 1.2pt solid var(--rojo);
             display: flex; justify-content: space-between; padding-bottom: 2pt; }
header.run b { color: var(--rojo); }
h1.title { color: var(--rojo); font-size: 19pt; margin: 0 0 2pt 0; line-height: 1.15; }
p.subtitle { font-size: 11pt; margin: 0 0 2pt 0; color: var(--gris); }
p.meta { font-size: 9pt; margin: 0 0 10pt 0; color: var(--gris); border-bottom: 2pt solid var(--tinta); padding-bottom: 6pt; }
h1 { color: var(--rojo); font-size: 13.5pt; margin: 13pt 0 4pt 0; break-after: avoid; }
h2 { font-size: 11pt; margin: 9pt 0 3pt 0; break-after: avoid; }
p { margin: 3pt 0 5pt 0; text-align: justify; }
ul, ol { margin: 2pt 0 5pt 0; padding-left: 16pt; }
li { margin: 1pt 0; }
table { border-collapse: collapse; margin: 5pt auto 2pt auto; font-size: 8.6pt; break-inside: avoid; }
th { background: var(--tinta); color: #fff; font-weight: 600; padding: 2.5pt 6pt; text-align: left; }
td { border-bottom: 0.5pt solid #ccc; padding: 2pt 6pt; }
td.num, th.num { text-align: right; }
p.caption, figcaption { font-size: 8.4pt; color: var(--gris); text-align: center; margin: 2pt 0 8pt 0; }
figure { margin: 6pt 0; text-align: center; break-inside: avoid; }
figure img { max-width: 100%; }
code { font-family: Consolas, 'Courier New', monospace; font-size: 8.6pt; background: #f2f2f2; padding: 0 2pt; }
.katex-display { margin: 4pt 0; }
div.refs p { text-align: left; font-size: 8.6pt; margin: 2pt 0; padding-left: 14pt; text-indent: -14pt; }
"""


def parse_bib(text: str) -> dict[str, dict]:
    out = {}
    for m in re.finditer(r"@\w+\{([^,]+),(.*?)\n\}", text, re.S):
        fields = dict((k.lower(), v.strip()) for k, v in re.findall(r"(\w+)\s*=\s*\{(.*?)\}\s*,?\s*$", m.group(2), re.M))
        out[m.group(1).strip()] = fields
    return out


def _surname(author: str) -> str:
    names = [a.strip() for a in author.split(" and ")]
    first = names[0].split(",")[0].strip()
    return first if len(names) == 1 else (f"{first} y {names[1].split(',')[0].strip()}" if len(names) == 2
                                          else f"{first} et al.")


def cite_label(e: dict) -> str:
    who = _surname(e["author"]) if "author" in e else e.get("howpublished", e.get("title", "?"))
    return f"{who}, {e['year']}" if "year" in e else who


def bib_entry(key: str, e: dict) -> str:
    who = e.get("author", "").replace(" and ", "; ") or e.get("howpublished", "")
    parts = [f"{html.escape(who)} ({e['year']})." if "year" in e else f"{html.escape(who)}.",
             f"<i>{html.escape(e.get('title', key))}</i>."]
    for k in ("journal", "booktitle", "howpublished", "pages"):
        if k in e and not (k == "howpublished" and e.get("author") is None and who == e[k]):
            parts.append(html.escape(e[k]) + ".")
    if "url" in e:
        parts.append(f'<a href="{e["url"]}">{html.escape(e["url"])}</a>')
    return "<p>" + " ".join(parts) + "</p>"


class Inline:
    """Inline Markdown -> HTML; math is shielded first so * and _ inside formulas survive."""

    def __init__(self, bib: dict):
        self.bib, self.cited = bib, []

    def __call__(self, s: str) -> str:
        shield: list[str] = []

        def keep(text: str) -> str:
            shield.append(text)
            return f"\x00{len(shield) - 1}\x00"

        s = re.sub(r"\$\$.+?\$\$", lambda m: keep(m.group(0)), s)
        s = re.sub(r"(?<!\\)\$(?!\s)(.+?)(?<!\s)\$", lambda m: keep(m.group(0)), s)
        s = re.sub(r"`([^`]+)`", lambda m: keep(f"<code>{html.escape(m.group(1))}</code>"), s)
        s = re.sub(r"\[(@[^\]]+)\]", lambda m: keep(self._cite(m.group(1))), s)
        s = html.escape(s, quote=False)
        s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
        s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", s)
        return re.sub(r"\x00(\d+)\x00", lambda m: shield[int(m.group(1))], s)

    def _cite(self, body: str) -> str:
        labels = []
        for key in re.findall(r"@([\w:-]+)", body):
            if key not in self.bib:
                raise KeyError(f"citation @{key} not in references.bib")
            if key not in self.cited:
                self.cited.append(key)
            labels.append(f'<a href="#ref-{key}">{html.escape(cite_label(self.bib[key]))}</a>')
        return "(" + "; ".join(labels) + ")"


def _cells(row: str) -> list[str]:
    return [c.strip() for c in row.strip().strip("|").split("|")]


def convert(md: str, bib: dict) -> str:
    meta = {}
    if md.startswith("---"):
        head, md = md[3:].split("\n---", 1)
        meta = dict((k.strip(), v.strip().strip('"')) for k, v in
                    (line.split(":", 1) for line in head.strip().splitlines() if ":" in line))
    md = re.sub(r"<!--.*?-->", "", md, flags=re.S)
    inline = Inline(bib)
    lines, out, i, sec, sub = md.splitlines(), [], 0, 0, 0
    para: list[str] = []

    def flush():
        if para:
            out.append(f"<p>{inline(' '.join(para))}</p>")
            para.clear()

    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if not s:
            flush(); i += 1; continue
        if s.startswith("$$"):
            flush()
            block = [s]
            while not (len(block) > 1 and block[-1].endswith("$$")) and not (len(s) > 2 and s.endswith("$$") and len(block) == 1):
                i += 1
                block.append(lines[i].strip())
            out.append("<div>" + " ".join(block) + "</div>"); i += 1; continue
        if s.startswith("::: {#refs}"):
            flush()
            out.append('<div class="refs">' + "".join(
                f'<div id="ref-{k}">{bib_entry(k, bib[k])}</div>'
                for k in sorted(inline.cited, key=lambda k: cite_label(bib[k]))) + "</div>")
            while i < len(lines) and lines[i].strip() != ":::" or lines[i].strip().startswith("::: {"):
                i += 1
            i += 1; continue
        m = re.match(r"^(#{1,2})\s+(.*?)(\s*\{-\})?$", s)
        if m:
            flush()
            text, unnumbered = m.group(2), bool(m.group(3))
            if len(m.group(1)) == 1:
                if not unnumbered:
                    sec, sub = sec + 1, 0
                out.append(f"<h1>{'' if unnumbered else f'{sec} '}{inline(text)}</h1>")
            else:
                sub += 1
                out.append(f"<h2>{sec}.{sub} {inline(text)}</h2>")
            i += 1; continue
        m = re.match(r"^!\[(.*?)\]\((.*?)\)(\{width=(.*?)\})?$", s)
        if m:
            flush()
            width = m.group(4) or "80%"
            out.append(f'<figure><img src="{m.group(2)}" style="width:{width}"><figcaption>{inline(m.group(1))}'
                       "</figcaption></figure>")
            i += 1; continue
        if s.startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i].strip()); i += 1
            head, align, body = _cells(rows[0]), _cells(rows[1]), [_cells(r) for r in rows[2:]]
            right = [a.endswith(":") and not a.startswith(":") for a in align]
            t = ["<table><tr>" + "".join(f'<th class="{"num" if r else ""}">{inline(c)}</th>' for c, r in zip(head, right))
                 + "</tr>"]
            t += ["<tr>" + "".join(f'<td class="{"num" if r else ""}">{inline(c)}</td>' for c, r in zip(row, right))
                  + "</tr>" for row in body]
            out.append("".join(t) + "</table>")
            while i < len(lines) and not lines[i].strip():
                i += 1
            if i < len(lines) and lines[i].startswith(": "):
                out.append(f'<p class="caption">{inline(lines[i][2:])}</p>'); i += 1
            continue
        m = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", line)
        if m:
            flush()
            items, depth_tag = [], ("ol" if m.group(2)[0].isdigit() else "ul")
            while i < len(lines):
                mm = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", lines[i])
                if mm and len(mm.group(1)) == 0:
                    items.append([mm.group(3), []])
                elif mm and items:
                    items[-1][1].append((mm.group(2), mm.group(3)))
                elif lines[i].strip() and items and lines[i].startswith("  "):
                    if items[-1][1]:
                        k, txt = items[-1][1][-1]
                        items[-1][1][-1] = (k, txt + " " + lines[i].strip())
                    else:
                        items[-1][0] += " " + lines[i].strip()
                else:
                    break
                i += 1
            html_items = []
            for text, children in items:
                inner = ""
                if children:
                    tag = "ol" if children[0][0][0].isdigit() else "ul"
                    inner = f"<{tag}>" + "".join(f"<li>{inline(c)}</li>" for _, c in children) + f"</{tag}>"
                html_items.append(f"<li>{inline(text)}{inner}</li>")
            out.append(f"<{depth_tag}>" + "".join(html_items) + f"</{depth_tag}>")
            continue
        para.append(s)
        i += 1
    flush()
    title = (f'<h1 class="title">{inline(meta.get("title", ""))}</h1><p class="subtitle">{inline(meta.get("subtitle", ""))}'
             f'</p><p class="meta">{html.escape(meta.get("author", ""))} · {html.escape(meta.get("date", ""))}</p>')
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><title>{html.escape(meta.get('title', 'paper'))}</title>
<link rel="stylesheet" href="{KATEX}/katex.min.css">
<script defer src="{KATEX}/katex.min.js"></script>
<script defer src="{KATEX}/contrib/auto-render.min.js"
 onload="renderMathInElement(document.body,{{delimiters:[{{left:'$$',right:'$$',display:true}},{{left:'$',right:'$',display:false}}],throwOnError:false}});document.body.dataset.ready='1'"></script>
<style>{CSS}</style></head><body><header class="run"><b>Stuff+ 2240</b><span>ISAC Hackathon 2026 · Diablos Rojos</span></header>
{title}{''.join(out)}</body></html>"""


def browser() -> str:
    for b in BROWSERS:
        if Path(b).exists() or shutil.which(b):
            return b
    raise SystemExit("No Edge/Chrome found: open stuffplus2240.html in a browser and print to PDF.")


def main() -> None:
    page = convert(SRC.read_text(encoding="utf-8"), parse_bib(BIB.read_text(encoding="utf-8")))
    OUT_HTML.write_text(page, encoding="utf-8")
    print("HTML:", OUT_HTML)
    if "--html-only" in sys.argv:
        return
    subprocess.run([browser(), "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=20000",
                    "--run-all-compositor-stages-before-draw", f"--print-to-pdf={OUT_PDF}", OUT_HTML.as_uri()],
                   check=True, capture_output=True, timeout=180)
    print("PDF:", OUT_PDF, f"{OUT_PDF.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
