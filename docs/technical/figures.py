"""Figures of the technical paper as pgfplots, from the reports/ aggregates (HACK-085).

    python docs/technical/figures.py      # writes figures/*.tex; build.sh compiles them with Tectonic

Each figure is a standalone LaTeX file with the paper's fonts and colours (diablos.tex), so text in the figure
matches the body. figures.lua swaps the PNG of paper.md for the compiled PDF when it exists; the HTML build
(build_pdf.py) keeps the PNG.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "figures"

SHAPE_ES = {
    "12-6 CB": "Curva 12-6", "sweeper": "Sweeper", "splitter": "Splitter", "slider": "Slider",
    "gyro slider": "Slider giroscópico", "4S": "Recta (4S)", "running 2S": "Sinker corredora (2S)",
    "sinking 2S": "Sinker hundida (2S)", "cutter": "Cutter", "changeup": "Cambio", "11-5 CB": "Curva 11-5",
    "power CH": "Cambio de poder", "riding 4S": "Recta de ride",
}
COLOR = {"gana relativo": "tinta", "pierde relativo": "diablos", "neutral": "gris"}

PREAMBLE = r"""\documentclass[border=4pt]{standalone}
\usepackage{libertinus}
\usepackage[scale=0.92,lining,tabular]{FiraSans}
\usepackage{xcolor}
\definecolor{diablos}{HTML}{C8102E}
\definecolor{tinta}{HTML}{111111}
\definecolor{gris}{HTML}{8A8A8A}
\definecolor{linea}{HTML}{E3E3E3}
\usepackage{pgfplots}
\pgfplotsset{compat=1.18}
\begin{document}
\sffamily
"""


def num(x: float, d: int = 1) -> str:
    return f"{x:.{d}f}".replace("-", "−")


def forest_by_shape() -> str:
    d = pd.read_csv(ROOT / "reports/altitude_delta/delta_by_shape.csv")
    d = d.sort_values("delta_stuff", ascending=False).reset_index(drop=True)
    league = float((d["delta_stuff"] - d["relative_to_league"]).mean())
    n = len(d)
    labels = ",".join("{" + f"{SHAPE_ES.get(s, s)} \\textcolor{{gris}}{{\\scriptsize {p:,}}}" + "}"
                      for s, p in zip(d["shape"], d["pitches"]))
    rows = []
    for i, r in d.iterrows():
        c = COLOR.get(r["verdict"], "gris")
        rows.append(
            f"\\draw[{c}, line width=1.1pt] (axis cs:{r.delta_lo:.4f},{i}) -- (axis cs:{r.delta_hi:.4f},{i});\n"
            f"\\fill[{c}, draw=white, line width=0.8pt] (axis cs:{r.delta_stuff:.4f},{i}) circle[radius=3.2pt];\n"
            f"\\node[anchor=west, font=\\scriptsize\\bfseries, text={c}, fill=white, inner sep=1.5pt] at (axis cs:{r.delta_hi:.4f},{i}) "
            f"{{\\,{num(r.delta_stuff)}}};"
        )
    return PREAMBLE + rf"""\begin{{tikzpicture}}
\begin{{axis}}[
  width=13.2cm, height=8.6cm, scale only axis=false,
  xmin=-20, xmax=-6, ymin=-0.7, ymax={n - 0.3}, y dir=reverse,
  ytick={{0,...,{n - 1}}}, yticklabels={{{labels}}},
  yticklabel style={{font=\small, text=tinta}}, xticklabel style={{font=\small, text=tinta}},
  xtick={{-20,-18,...,-6}}, xticklabels={{−20,−18,−16,−14,−12,−10,−8,−6}},
  xmajorgrids, grid style={{linea}}, axis line style={{draw=none}}, tick style={{draw=none}},
  xlabel={{ΔStuff+ en el aire del Harp Helú contra nivel del mar (IC 95 \% por pitcher)}},
  xlabel style={{font=\small, text=tinta}}, clip=false,
]
\draw[tinta, dashed, line width=0.7pt] (axis cs:{league:.4f},-0.7) -- (axis cs:{league:.4f},{n - 0.3});
\node[anchor=south, font=\scriptsize\bfseries, text=tinta] at (axis cs:{league:.4f},-0.7) {{Promedio de la liga {num(league)}}};
{chr(10).join(rows)}
\end{{axis}}
\node[anchor=north west, font=\scriptsize, text=tinta] at (current bounding box.south west) {{%
\textcolor{{tinta}}{{\large$\bullet$}} pierde menos que la liga\quad
\textcolor{{diablos}}{{\large$\bullet$}} pierde más\quad
\textcolor{{gris}}{{\large$\bullet$}} igual que la liga\quad
\textcolor{{gris}}{{número junto al nombre = lanzamientos}}}};
\end{{tikzpicture}}
\end{{document}}
"""


def main() -> None:
    OUT.mkdir(exist_ok=True)
    (OUT / "forest_by_shape.tex").write_text(forest_by_shape(), encoding="utf-8", newline="\n")
    print(f"OK: {OUT / 'forest_by_shape.tex'}")


if __name__ == "__main__":
    main()
