#!/usr/bin/env bash
# Compila docs/technical/paper.md -> stuffplus2240.tex -> stuffplus2240.pdf (pandoc + Tectonic, XeTeX).
# Requiere pandoc >= 3 y tectonic (scoop install pandoc tectonic; brew install pandoc tectonic). Tectonic baja los
# paquetes de TeX Live que usa diablos.tex la primera vez. Sin LaTeX: python build_pdf.py (HTML + Edge).
set -euo pipefail
cd "$(dirname "$0")"
command -v pandoc >/dev/null || { echo "pandoc no está instalado" >&2; exit 1; }
command -v tectonic >/dev/null || { echo "tectonic no está instalado" >&2; exit 1; }
python check_numbers.py
python figures.py
(cd figures && for f in *.tex; do tectonic -X compile "$f" 2>&1 | grep -E "^error" || true; done)
pandoc paper.md \
  --from markdown+tex_math_dollars+yaml_metadata_block \
  --lua-filter figures.lua --citeproc --bibliography references.bib \
  --standalone --to latex \
  -M subtitle= \
  -V documentclass=article -V papersize=letter -V fontsize=10pt -V lang=es \
  -V babel-otherlangs=english -V babeloptions=es-noshorthands,es-nodecimaldot \
  -V geometry:top=2.3cm,bottom=2.1cm,left=2.2cm,right=2.2cm,headsep=0.5cm \
  -V colorlinks=true -V linkcolor=diablos -V urlcolor=diablos -V citecolor=tinta -V linestretch=1.06 \
  -H diablos.tex \
  --number-sections \
  -o stuffplus2240.tex
sed -i 's/\\begin{CSLReferences}{1}{1}/\\begin{CSLReferences}{1}{0}/' stuffplus2240.tex  # bibliografía sin hueco entre entradas
tectonic -X compile --keep-logs stuffplus2240.tex 2>&1 | grep -vE "accessing absolute path|^note: (downloading|Running|Skipped)" || true
test -s stuffplus2240.pdf
rm -f stuffplus2240.log
echo "OK: $(pwd)/stuffplus2240.pdf"
