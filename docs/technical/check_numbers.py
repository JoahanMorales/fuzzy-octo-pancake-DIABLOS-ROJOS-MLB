"""Every number next to a cited reports/ file must appear in that file (HACK-058).

    python docs/technical/check_numbers.py [paper.md]

A *block* of paper.md is a paragraph, one list item, or a table together with its ": caption" line. When a block
cites files under `reports/` (in backticks; a directory means every text file inside it, `{a,b}` expands), every
number written in the block must match a number in one of those files at the precision it is written with:
3.88 % matches 0.03884 or 3.884; -4.6 matches -4.63; 7.24×10^-4 matches 0.0007237; 1,134 matches 1134. Signs are
ignored (prose says "pierde 9.6" for a delta of -9.6). Blocks that cite no report file are not checked.

Not numbers of the evidence, so skipped: task ids (HACK-052), section refs (§5), the seasons 2024-2026, the
confidence level "95 %", the stadium altitude 2,240 m, footnote and list markers, and anything inside a code span
other than the cited paths. Exits 1 and lists every miss.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TEXT_SUFFIXES = {".csv", ".md", ".json", ".txt"}

CITE = re.compile(r"`(reports/[^`\s]+)`")
SCI = re.compile(r"(\d+(?:\.\d+)?)\s*(?:\\times|×|x)\s*10\^\{?([−-]?\d+)\}?")
NUM = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)(\s*%)?(?![\w])")
FILE_NUM = re.compile(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")
SKIP = [
    re.compile(r"HACK-\d+"),
    re.compile(r"§\s*\d+(?:\.\d+)*"),
    re.compile(r"\b20(?:24|25|26)(?:\s*[–-]\s*(?:20)?(?:24|25|26))?\b"),
    re.compile(r"(?:IC|intervalos?|bandas?)\s+(?:al\s+)?(?:95|90)\s*%"),
    re.compile(r"(?:95|90)\s*%\s*(?:de\s+)?(?:IC|confianza|cobertura nominal)"),
    re.compile(r"2,?240\s*m"),
    re.compile(r"\[@[^\]]*\]"),
    re.compile(r"\{width=[^}]*\}"),
    re.compile(r"!\[[^\]]*\]\([^)]*\)"),
    re.compile(r"\$\^\\dagger\$"),
]


def expand(path: str) -> list[Path]:
    m = re.search(r"\{([^}]*)\}", path)
    if m:
        out = []
        for alt in m.group(1).split(","):
            out += expand(path[: m.start()] + alt.strip() + path[m.end():])
        return out
    p = ROOT / path.rstrip("/")
    if p.is_dir():
        return sorted(f for f in p.rglob("*") if f.suffix in TEXT_SUFFIXES)
    return [p]


_cache: dict[Path, list[float]] = {}


def file_numbers(p: Path) -> list[float]:
    if p not in _cache:
        text = p.read_text(encoding="utf-8", errors="replace").replace("−", "-")
        if p.suffix != ".csv":  # thousands separators in prose and markdown tables, never in a CSV row
            text = re.sub(r"(?<![\d.])(\d{1,3}(?:,\d{3})+)(?![\d,])", lambda m: m.group(1).replace(",", ""), text)
        _cache[p] = [abs(float(x)) for x in FILE_NUM.findall(text)]
    return _cache[p]


def blocks(md: str) -> list[tuple[int, str]]:
    """(first line number, text) for paragraphs, list items and table+caption."""
    md = re.sub(r"<!--.*?-->", lambda m: "\n" * m.group(0).count("\n"), md, flags=re.S)
    lines = md.splitlines()
    if lines and lines[0].strip() == "---":
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
        lines = [""] * (end + 1) + lines[end + 1:]
    out: list[tuple[int, list[str]]] = []
    cur: list[str] = []
    start = 0
    is_table = False

    def flush():
        nonlocal cur
        if cur:
            out.append((start, cur))
        cur = []

    for i, line in enumerate(lines, 1):
        s = line.strip()
        if not s:
            if not is_table:
                flush()
            continue
        if s.startswith(":") and not s.startswith(":::") and is_table:
            cur.append(s)
            is_table = False
            flush()
            continue
        if is_table and not s.startswith("|"):
            is_table = False
            flush()
        new_item = bool(re.match(r"([-*]|\d+\.)\s", s)) and not line.startswith("  ")
        if new_item or s.startswith("#") or (s.startswith("|") and not is_table):
            flush()
        if not cur:
            start = i
            is_table = s.startswith("|")
        cur.append(s)
        if s.startswith("#"):
            flush()
    flush()
    return [(n, "\n".join(b)) for n, b in out]


def numbers(text: str) -> list[tuple[str, float, float]]:
    """(as written, value, tolerance) for every number in the text outside skipped spans and code."""
    text = re.sub(r"`[^`]*`", " ", text).replace("−", "-")
    for pat in SKIP:
        text = pat.sub(" ", text)
    found = []
    for m in SCI.finditer(text):
        mant, exp = m.group(1), int(m.group(2).replace("−", "-"))
        d = len(mant.split(".")[1]) if "." in mant else 0
        found.append((m.group(0), float(mant) * 10 ** exp, 0.5 * 10 ** (exp - d) + 1e-12))
    text = SCI.sub(" ", text)
    for m in NUM.finditer(text):
        raw, pct = m.group(1), m.group(2)
        clean = raw.replace(",", "")
        d = len(clean.split(".")[1]) if "." in clean else 0
        val, tol = float(clean), 0.5 * 10 ** -d + 1e-12
        found.append((raw + (pct or ""), val, tol))
        if pct:
            found.append(("", val / 100, tol / 100))  # the fraction form, checked as an alternative
    return found


def check(md_path: Path) -> list[str]:
    misses = []
    for line, block in blocks(md_path.read_text(encoding="utf-8")):
        cited = [p for c in CITE.findall(block) for p in expand(c)]
        if not cited:
            continue
        missing = [p for p in cited if not p.exists()]
        for p in missing:
            misses.append(f"{md_path.name}:{line}: cited file not found: {p.relative_to(ROOT)}")
        pool = [x for p in cited if p.exists() for x in file_numbers(p)]
        nums = numbers(block)
        i = 0
        while i < len(nums):
            raw, val, tol = nums[i]
            alt = nums[i + 1] if i + 1 < len(nums) and nums[i + 1][0] == "" else None
            ok = any(abs(abs(val) - x) <= tol for x in pool)
            if not ok and alt:
                ok = any(abs(abs(alt[1]) - x) <= alt[2] for x in pool)
            if not ok:
                names = ", ".join(sorted({str(p.relative_to(ROOT)) for p in cited}))
                misses.append(f"{md_path.name}:{line}: {raw} not in {names}")
            i += 2 if alt else 1
    return misses


def main(argv: list[str]) -> int:
    paper = Path(argv[1]) if len(argv) > 1 else HERE / "paper.md"
    misses = check(paper)
    for m in misses:
        print(m)
    blocks_checked = sum(1 for _, b in blocks(paper.read_text(encoding="utf-8")) if CITE.search(b))
    if misses:
        print(f"NUMBERS_FAIL: {len(misses)} miss(es) in {blocks_checked} cited blocks")
        return 1
    print(f"NUMBERS_OK: {blocks_checked} cited blocks, every number found in its reports/ file")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
