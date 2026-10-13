#!/usr/bin/env bash
# Compila docs/technical/paper.md -> docs/technical/paper.pdf (pandoc + XeLaTeX).
# Requiere: pandoc >= 2.11 y una distribución LaTeX (xelatex) con los paquetes xcolor, sectsty, fancyhdr, hyperref.
set -euo pipefail
cd "$(dirname "$0")"
command -v pandoc >/dev/null || { echo "pandoc no está instalado" >&2; exit 1; }
pandoc paper.md \
  --from markdown+tex_math_dollars+yaml_metadata_block \
  --citeproc --bibliography references.bib \
  --pdf-engine=xelatex \
  -V geometry:margin=2.2cm -V fontsize=10pt -V lang=es -V colorlinks=true \
  -H diablos.tex \
  --number-sections \
  -o paper.pdf
echo "OK: $(pwd)/paper.pdf"
