"""Build the editable PPTX + presentation PDF + one-page PDF from tracked aggregates (HACK-036, v2 in HACK-059).

    python demo/deck/build.py

Every number on a slide is read from a CSV under reports/ (file, row, column and SHA-256 go to sources.json);
the two derived numbers (league average and bias reduction) record their inputs and formula, and verify.py
recomputes them. The PDF uses the font bundled in demo/deck/fonts (DejaVu Sans), so it builds the same on Windows,
macOS and Linux. No private data is read.
"""
from __future__ import annotations
import csv
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
from pathlib import Path

from pptx import Presentation
from pptx.util import Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR
from pptx.oxml.ns import qn
from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'demo/deck'
ONE = ROOT / 'demo/one-pager'
FONTS = OUT / 'fonts'
ASSETS = OUT / 'assets'
RED, INK, GRAY, LIGHT, WHITE = '#D71920', '#202124', '#585B60', '#ECEDEF', '#FFFFFF'
W, H = 720, 405
PPTX_FONT = 'Arial'  # what PowerPoint shows when editing; the PDF embeds the bundled font
for name, file in [('Deck', 'DejaVuSans.ttf'), ('DeckBold', 'DejaVuSans-Bold.ttf')]:
    pdfmetrics.registerFont(TTFont(name, str(FONTS / file)))

sources, evidence, derived = {}, [], []


def row(path, **where):
    p = ROOT / path
    # LF line endings, as git stores the file: a Windows checkout has CRLF, so the hash must not depend on the OS
    sources[path] = hashlib.sha256(p.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
    rows = list(csv.DictReader(p.open(encoding='utf-8')))
    found = [r for r in rows if all(r[k] == str(v) for k, v in where.items())]
    if len(found) != 1:
        raise ValueError(f'Expected one source row: {path}, {where}, found {len(found)}')
    return found[0]


def fmt(value: Decimal, digits: int) -> str:
    s = str(value.quantize(Decimal('1').scaleb(-digits), rounding=ROUND_HALF_UP))
    return s.replace('-', '−')


def val(display: str) -> float:
    return float(display.replace("−", "-"))


def number(slide, path, where, column, digits=2, factor=1):
    r = row(path, **where)
    display = fmt(Decimal(r[column]) * Decimal(str(factor)), digits)
    evidence.append(dict(slide=slide, source=path, row=where, column=column,
                         value=float(r[column]), factor=factor, digits=digits, display=display))
    return display


def derive(slide, formula, inputs, digits):
    """formula 'a-b' or '1-a/b' (as a percentage) on CSV inputs [(path, where, column), ...]."""
    vals = [Decimal(row(p, **w)[c]) for p, w, c in inputs]
    if formula == 'a-b':
        v = vals[0] - vals[1]
    elif formula == '1-a/b':
        v = (1 - vals[0] / vals[1]) * 100
    else:
        raise ValueError(formula)
    display = fmt(v, digits)
    derived.append(dict(slide=slide, formula=formula, digits=digits, display=display,
                        inputs=[dict(source=p, row=w, column=c) for p, w, c in inputs]))
    return display


class Page:
    """Shared explicit positions for native PowerPoint shapes and the PDF."""
    def __init__(self, ppt=None, pdf=None, width=W, height=H):
        self.ppt, self.pdf, self.width, self.height = ppt, pdf, width, height

    def rect(self, x, y, w, h, color):
        assert x >= 0 and y >= 0 and x+w <= self.width+.1 and y+h <= self.height+.1
        if self.ppt is not None:
            shape = self.ppt.shapes.add_shape(MSO_SHAPE.RECTANGLE, Pt(x), Pt(y), Pt(w), Pt(h))
            shape.fill.solid(); shape.fill.fore_color.rgb = RGBColor.from_string(color[1:])
            shape.line.fill.background()
            style = shape._element.find(qn("p:style"))
            if style is not None: shape._element.remove(style)
        if self.pdf is not None:
            self.pdf.setFillColor(color); self.pdf.rect(x, self.height-y-h, w, h, stroke=0, fill=1)

    def image(self, path, x, y, w, h):
        assert x >= 0 and y >= 0 and x+w <= self.width+.1 and y+h <= self.height+.1
        if self.ppt is not None:
            self.ppt.shapes.add_picture(str(path), Pt(x), Pt(y), Pt(w), Pt(h))
        if self.pdf is not None:
            self.pdf.drawImage(str(path), x, self.height-y-h, w, h)

    def text(self, text, x, y, width=640, size=18, color=INK, bold=False, leading=None):
        font = 'DeckBold' if bold else 'Deck'
        leading = leading or size*1.24
        lines = []
        for paragraph in str(text).split('\n'):
            line = ''
            for word in paragraph.split():
                candidate = (line+' '+word).strip()
                if pdfmetrics.stringWidth(candidate, font, size) > width and line:
                    lines.append(line); line = word
                else: line = candidate
            lines.append(line)
        for i, line in enumerate(lines):
            yy = y+i*leading
            assert yy+size <= self.height-8, (line, yy, self.height)
            assert pdfmetrics.stringWidth(line, font, size) <= width+.1, line
            if self.ppt is not None:
                shape = self.ppt.shapes.add_textbox(Pt(x), Pt(yy-2), Pt(width), Pt(leading+5))
                tf = shape.text_frame
                tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
                tf.word_wrap = False; tf.vertical_anchor = MSO_ANCHOR.TOP
                p = tf.paragraphs[0]; p.text = line
                p.font.name = PPTX_FONT; p.font.size = Pt(size); p.font.bold = bold
                p.font.color.rgb = RGBColor.from_string(color[1:])
            if self.pdf is not None:
                self.pdf.setFillColor(color); self.pdf.setFont(font, size)
                self.pdf.drawString(x, self.height-yy-size*.82, line)
        return y+len(lines)*leading


def header(p, title, index, source, dark=False):
    p.rect(0, 0, W, H, INK if dark else WHITE)
    p.rect(40, 23, 42, 4, RED)
    p.text('STUFF+ 2240   /   DIABLOS ROJOS', 95, 18, 570, 10, LIGHT if dark else GRAY)
    p.text(title, 40, 53, 640, 26, WHITE if dark else INK, True, 31)
    p.text(source, 40, 356, 600, 8, LIGHT if dark else GRAY, leading=10.5)
    p.text(f'{index:02d}', 650, 381, 30, 10, LIGHT if dark else GRAY)


def bar(p, label, value, text, y, max_value, color=RED, label_w=165):
    p.text(label, 40, y, label_w, 15)
    p.rect(215, y+2, abs(value)/max_value*335, 18, color)
    p.text(text, 562, y-1, 118, 17, bold=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True); ONE.mkdir(parents=True, exist_ok=True)
    prs = Presentation(); prs.slide_width = Pt(W); prs.slide_height = Pt(H)
    pdf = Canvas(str(OUT/'deck.pdf'), pagesize=(W, H))
    pdf.setTitle('Stuff+ 2240 · Diablos Rojos · deck v2')
    titles, footers = [], []

    def slide(title, footer, note, dark=False):
        s = prs.slides.add_slide(prs.slide_layouts[6])
        s.notes_slide.notes_text_frame.text = note + '\nFuentes: ' + footer
        p = Page(s, pdf); header(p, title, len(prs.slides), footer, dark)
        titles.append(title); footers.append(footer)
        return p

    def end(): pdf.showPage()

    shape = 'reports/altitude_delta/delta_by_shape.csv'
    league = derive(1, 'a-b', [(shape, {'shape': 'sweeper'}, 'delta_stuff'),
                               (shape, {'shape': 'sweeper'}, 'relative_to_league')], 1)

    # 1 · the headline
    p = slide(f'El mismo arsenal pierde {league.replace("−", "")} puntos\nde Stuff+ en el aire de CDMX',
              shape + ' · promedio de la liga = ΔStuff+ de una forma − su diferencia contra la liga.',
              '45 s. Problema: un buen arsenal a nivel del mar vale menos en casa. Comparamos el mismo lanzamiento en dos aires con Stuff+ v2 en producción. Abrir con la decisión del coach: qué reclutar y cómo usarlo en casa.', True)
    p.text(f'ΔStuff+ de la liga en el aire del Harp Helú: {league}.\nEl modelo mide el aire de cada juego y lo extrapola a un aire que no vio.', 40, 150, 640, 18, WHITE, leading=26)
    p.text('Datos oficiales agregados. Identificación inferida: la sede del staff\nsigue sin confirmarse.', 40, 263, 640, 16, LIGHT)
    end()

    # 2 · the air
    density = 'reports/physics/rho_by_bucket.csv'
    p = slide('El aire estimado cambia entre ambientes', density + ' · media por bucket; parques anónimos.',
              '55 s. Densidad relativa estimada con el arrastre de las rectas. Son grupos de altitud; la identidad exacta del Harp Helú no está verificada.')
    for y, name, label in [(150, 'No Altitude', 'Nivel del mar'), (208, 'Medium Altitude', 'Altitud media'), (266, 'Extreme Altitude', 'Altitud extrema')]:
        v = number(2, density, {'bucket': name}, 'mean', 3)
        bar(p, label, val(v), v, y, 1.1)
    p.text('Densidad relativa: menor valor significa aire menos denso.', 40, 319, 640, 14, GRAY)
    end()

    # 3 · the physics
    observed = 'reports/physics/delta_extreme_vs_no.csv'
    elastic = 'reports/physics_v2/magnus_elasticity.csv'
    obs = number(3, observed, {'pitch_family': 'Four-Seam', 'outcome': 'ivb'}, 'delta')
    cf = number(3, shape, {'shape': '4S'}, 'delta_ivb_in')
    el = number(3, elastic, {'pitch_family': 'Four-Seam'}, 'elasticity')
    p = slide('La recta pierde subida: el Magnus cae\nmás rápido que el aire', observed + '; ' + shape + ' · 4S; ' + elastic + '.',
              '55 s. Observado dentro del mismo lanzador contra el cambio del modelo para la forma 4S. La elasticidad dice cuánto cae la fuerza de Magnus con la densidad: la física de libro dice 1, medimos más.')
    p.text(obs+'"', 40, 145, 200, 44, RED, True)
    p.text('Observado\naltitud extrema − sin altitud', 40, 203, 210, 15)
    p.text(cf+'"', 262, 145, 200, 44, RED, True)
    p.text('Modelo, forma 4S\nCDMX − nivel del mar', 262, 203, 200, 15)
    p.text(el, 484, 145, 196, 44, RED, True)
    p.text('Elasticidad del Magnus\nde la recta (libro: 1)', 484, 203, 196, 15)
    p.text('IVB: movimiento vertical inducido, pulgadas. El simulador usa la elasticidad medida.', 40, 312, 640, 13, GRAY)
    end()

    # 4 · validation against the rubric's null
    hold = 'reports/validation/headline.csv'
    skill = 'reports/stuff_v2/skill.csv'
    level = 'reports/stuff_v2/pitcher_level.csv'
    pk = number(4, hold, {'split': 'pitcher_kfold', 'model': 'Pitching+'}, 'skill', 2, 100)
    v2 = number(4, skill, {'model': 'Stuff+ v2', 'split': 'pitcher_kfold'}, 'skill_vs_baseline', 2, 100)
    r50 = number(4, level, {'model': 'Stuff+ v2 (familia)'}, 'first50_r', 3)
    r50obs = number(4, level, {'model': 'Stuff+ v2 (familia)'}, 'observed_first50_r', 3)
    p = slide('Le ganamos al modelo nulo de la rúbrica', hold + '; ' + skill + '; ' + level + '.',
              '75 s. Skill: fracción del RMSE que el modelo le quita al nulo por conteo, por pitcher. Stuff+ v2 deja que el conteo valore los resultados y ya le gana al nulo. A nivel pitcher, 50 lanzamientos de Stuff+ dicen más del resto de la temporada que los resultados del propio pitcher.')
    bar(p, 'Pitching+', val(pk), pk+' %', 144, 5)
    bar(p, 'Stuff+ v2', val(v2), '+'+v2+' %', 191, 5)
    p.text('% de RMSE que baja frente al nulo por conteo, validación por pitcher.', 40, 226, 640, 13, GRAY)
    p.text(r50, 40, 248, 300, 32, RED, True)
    p.text('r de Stuff+ v2 con 50 lanzamientos contra\nel resto de la temporada', 40, 288, 320, 12)
    p.text(r50obs, 380, 248, 300, 32, GRAY, True)
    p.text('r de los resultados del propio pitcher\ncon los mismos 50 lanzamientos', 380, 288, 300, 12)
    end()

    # 5 · physics fixes the altitude bias
    bias = 'reports/stuff_v2/altitude_bias.csv'
    b0 = number(5, bias, {'model': 'baseline (conteo)'}, 'bias_obs_minus_pred', 4)
    b1 = number(5, bias, {'model': 'Stuff+ v1'}, 'bias_obs_minus_pred', 4)
    b2 = number(5, bias, {'model': 'Stuff+ v2'}, 'bias_obs_minus_pred', 4)
    cut = derive(5, '1-a/b', [(bias, {'model': 'Stuff+ v2'}, 'bias_obs_minus_pred'),
                              (bias, {'model': 'baseline (conteo)'}, 'bias_obs_minus_pred')], 0)
    p = slide('La física corrige el sesgo de altitud', bias + ' · entrenado sin altitud extrema, evaluado en ella.',
              '55 s. Se entrena sin un solo juego de altitud extrema y se predice esa altitud. El sesgo es carreras observadas menos predichas por lanzamiento: positivo = el modelo subestima el daño. Con la densidad del aire, Stuff+ v2 casi lo elimina.')
    bar(p, 'Nulo (conteo)', val(b0), '+'+b0, 144, 0.012, GRAY)
    bar(p, 'Stuff+ v1', val(b1), '+'+b1, 191, 0.012)
    bar(p, 'Stuff+ v2', val(b2), '+'+b2, 238, 0.012)
    p.text(f'Stuff+ v2 recorta el sesgo {cut} % frente al nulo.', 40, 290, 640, 17, bold=True)
    p.text('Carreras por lanzamiento que el modelo subestima en un aire que no vio.', 40, 319, 640, 13, GRAY)
    end()

    # 6 · shapes
    p = slide('Las pérdidas dependen de la forma del pitch', shape + ' · delta_stuff; misma forma, CDMX menos nivel del mar.',
              '65 s. Ninguna forma gana en términos absolutos. La curva 12-6 y el sweeper pierden menos que la liga; la recta de mucho ride pierde más. Hipótesis operativa para reclutar: no pagar por ride de recta.')
    for y, label, key in [(140, 'Curva 12-6', '12-6 CB'), (180, 'Sweeper', 'sweeper'), (220, 'Recta 4S', '4S'), (260, 'Recta de ride', 'riding 4S')]:
        v = number(6, shape, {'shape': key}, 'delta_stuff', 1)
        bar(p, label, val(v), v, y, 19)
    p.text('Longitud = pérdida de Stuff+. Ninguna forma gana en absoluto.', 40, 319, 640, 14, GRAY)
    end()

    # 7 · staff
    saved = 'reports/staff_audit/runs_saved.csv'

    def saved_num(franchise, component, column, digits=1):
        return number(7, saved, {'franchise': franchise, 'component': component}, column, digits)
    r5 = saved_num('5', 'total', 'runs_per_season'); w5 = saved_num('5', 'total', 'wins_per_season', 2)
    r11 = saved_num('11', 'total', 'runs_per_season'); w11 = saved_num('11', 'total', 'wins_per_season', 2)
    m5 = saved_num('5', 'mezcla de lanzamientos en casa', 'runs_per_season')
    a5 = saved_num('5', 'asignación de aperturas en casa', 'runs_per_season')
    m11 = saved_num('11', 'mezcla de lanzamientos en casa', 'runs_per_season')
    a11 = saved_num('11', 'asignación de aperturas en casa', 'runs_per_season')
    p = slide('Dos sedes candidatas, dos cuentas de carreras', saved + ' · franquicias 5 y 11, por separado.',
              '55 s. Identificación inferida: son las dos franquicias de aire más ligero, no un staff confirmado de Diablos. Carreras del modelo: mezcla de lanzamientos en casa más reasignación de aperturas. No sumar 5 y 11.')
    p.text('Franquicia 5', 40, 136, 300, 17, RED, True)
    p.text(r5+' carreras', 40, 162, 300, 30, RED, True)
    p.text(w5+' victorias por temporada', 40, 200, 300, 15)
    p.text('Mezcla '+m5+' · aperturas '+a5, 40, 226, 300, 14, GRAY)
    p.text('Franquicia 11', 380, 136, 300, 17, RED, True)
    p.text(r11+' carreras', 380, 162, 300, 30, RED, True)
    p.text(w11+' victorias por temporada', 380, 200, 300, 15)
    p.text('Mezcla '+m11+' · aperturas '+a11, 380, 226, 300, 14, GRAY)
    p.text('Identificación inferida. No se suman.\nLa sede sigue sin confirmarse.', 40, 290, 640, 15)
    end()

    # 8 · the product
    p = slide('El producto: dos aires, un lanzamiento', 'Capturas del simulador 3D y del explicador de física (Playwright, web/e2e/screenshots, HACK-051).',
              '50 s. Simulador 3D: el mismo release a nivel del mar y en el aire del Harp Helú, con el motor de vuelo que usa la elasticidad medida. El explicador de física deja mover la densidad y ver la subida perdida. Las cifras de la app salen de los mismos agregados.')
    p.image(ASSETS/'simulador_transmision.jpg', 40, 98, 308, 178)
    p.image(ASSETS/'fisica.jpg', 372, 98, 308, 198)
    p.text('Simulador 3D: dos aires, mismo release.', 40, 284, 308, 12, GRAY)
    p.text('Física: arrastre y Magnus contra la densidad.', 372, 302, 308, 12, GRAY)
    end()

    # 9 · value
    value = 'reports/business_value/runs_per_win.csv'
    gm = 'reports/business_value/gm_example.csv'
    rpw_l = number(9, value, {'entorno': 'liga'}, 'carreras_por_victoria', 1)
    rpw_x = number(9, value, {'entorno': 'Extreme Altitude'}, 'carreras_por_victoria', 1)
    wins = number(9, gm, {'escala': 'Stuff+', 'entorno': 'Harp Helú (bucket Extreme)'}, 'victorias', 2)
    runs = number(9, gm, {'escala': 'Stuff+', 'entorno': 'Harp Helú (bucket Extreme)'}, 'carreras', 1)
    p = slide('El entorno cambia el valor de una carrera', value + '; ' + gm + ' · puntos de Stuff+ v2 fuera de pliegue.',
              '65 s. En altura se anota más, así que cada carrera ahorrada vale menos victorias. +10 puntos de Stuff+ sostenidos en 2,500 lanzamientos es un escenario de orden de magnitud, no el ahorro del staff de la lámina 7.')
    p.text(rpw_l, 40, 138, 200, 42, RED, True)
    p.text('Carreras por victoria\nliga', 40, 190, 200, 15)
    p.text(rpw_x, 250, 138, 200, 42, RED, True)
    p.text('Carreras por victoria\naltitud extrema', 250, 190, 210, 15)
    p.text(wins, 490, 138, 190, 42, RED, True)
    p.text('Victorias en el Harp Helú\npor +10 de Stuff+', 490, 190, 190, 15)
    p.text(f'+10 puntos en 2,500 lanzamientos = {runs} carreras (escenario).', 40, 286, 640, 15, bold=True)
    p.text('El ahorro del staff está en la lámina 7, por franquicia.', 40, 318, 640, 13, GRAY)
    end()

    # 10 · demo
    p = slide('La demo compara el mismo arsenal', 'Producto web en el repo. Respaldo: este PDF y los CSV agregados de reports/.',
              '70 s. Abrir el simulador con una forma y dos densidades, pasar al explicador de física y a la página de altitud. Si la red falla, quedarse en este PDF. Cerrar: las franquicias 5 y 11 no se suman y la sede no está confirmada.', True)
    p.image(ASSETS/'simulador_receptor.jpg', 380, 96, 300, 173)
    p.text('Simulador: la misma forma,\ndos aires.\nFísica: la densidad en vivo.\nAltitud: los 20 parques\npor densidad.', 40, 104, 320, 19, WHITE, leading=27)
    p.text('Respaldo offline: este PDF y los CSV agregados.\nLa sede del staff sigue sin confirmarse.', 40, 290, 640, 15, LIGHT)
    end()
    pdf.save(); prs.save(OUT/'deck.pptx')

    # One-page executive brief, designed for printing.
    c = Canvas(str(ONE/'one-pager.pdf'), pagesize=(595, 842))
    c.setTitle('Stuff+ 2240 · resumen ejecutivo v2')
    p = Page(pdf=c, width=595, height=842)
    p.rect(38, 32, 42, 5, RED)
    p.text('STUFF+ 2240 / DIABLOS ROJOS', 94, 28, 463, 11, GRAY)
    p.text('El arsenal pierde valor en CDMX', 38, 67, 519, 24, bold=True)
    p.text('Resumen ejecutivo v2 para el GM y el cuerpo técnico', 38, 106, 519, 13, GRAY)
    p.text('Hallazgos', 38, 150, 519, 17, RED, True)
    y = p.text(f'El mismo lanzamiento pierde {league.replace("−", "")} puntos de Stuff+ en promedio en el aire del Harp Helú. La recta de mucho ride es la que más pierde; la curva 12-6 y el sweeper, las que mejor aguantan. La fuerza de Magnus de la recta cae con la densidad elevada a {el}, más que la física de libro.', 38, 180, 519, 13, leading=18)
    y = p.text(f'Stuff+ v2 le gana al modelo nulo de la rúbrica (+{v2} % de RMSE por pitcher; Pitching+ {pk} %). Con 50 lanzamientos predice el resto de la temporada con r = {r50}, contra {r50obs} de los propios resultados del pitcher.', 38, y+8, 519, 13, leading=18)
    y = p.text(f'Entrenado sin altitud extrema, Stuff+ v2 recorta {cut} % el daño que el nulo subestima allí: la física extrapola a un aire que no vio.', 38, y+8, 519, 13, leading=18)
    p.text('Decisión propuesta', 38, y+22, 519, 17, RED, True)
    y = p.text('No pagar por ride de recta; preferir secundarios que aguantan el aire (curva 12-6, sweeper). En casa, mover uso hacia el lanzamiento que mejor resiste y dar las aperturas de casa al abridor más resistente. Confirmar antes con el club cuál franquicia es la sede.', 38, y+52, 519, 13, leading=18)
    p.text('Valor', 38, y+14, 519, 17, RED, True)
    y = p.text(f'Franquicia 5: {r5} carreras ({w5} victorias) por temporada. Franquicia 11: {r11} carreras ({w11} victorias). Identificación inferida: no se suman. Una carrera vale {rpw_l} por victoria en la liga y {rpw_x} en altitud extrema; +10 de Stuff+ en 2,500 lanzamientos son {wins} victorias en el Harp Helú.', 38, y+44, 519, 13, leading=18)
    p.text('Fuentes y trazabilidad', 38, 728, 519, 12, bold=True)
    p.text('altitude_delta/delta_by_shape.csv; physics_v2/magnus_elasticity.csv; stuff_v2/skill.csv,\npitcher_level.csv y altitude_bias.csv; validation/headline.csv; staff_audit/runs_saved.csv;\nbusiness_value/runs_per_win.csv y gm_example.csv. Todos bajo reports/. Filas, columnas\ny hashes: demo/deck/sources.json.', 38, 750, 519, 9.5, GRAY, leading=13)
    c.showPage(); c.save()

    (OUT/'sources.json').write_text(json.dumps({'demo_data': False, 'exploratory': True, 'model': 'Stuff+ v2 (HACK-057)',
        'source_sha256': sources, 'evidence': evidence, 'derived': derived}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    timing = [45, 55, 55, 75, 55, 65, 55, 50, 65, 70]
    rows = ['# Presentación ejecutiva v2 · HACK-036, HACK-059', '',
            '10 diapositivas para una entrevista de 10 minutos, con Stuff+ v2 en producción (HACK-057). Rojo #D71920, gris carbón; el PDF usa DejaVu Sans incluida en `fonts/` (licencia en `fonts/LICENSE_DEJAVU`), así que se construye igual en Windows, macOS y Linux. El PPTX editable usa Arial.', '',
            '**Estado:** evidencia oficial agregada. Las franquicias 5 y 11 no se suman: identificación inferida y sede sin confirmar.', '',
            '| Lámina | Idea principal | Tiempo | Fuente de cifras |', '|---|---|---:|---|']
    for i, (t, f, sec) in enumerate(zip(titles, footers, timing), 1):
        rows.append(f'| {i} | {t.replace(chr(10), " ")} | {sec} s | {f} |')
    rows += ['', '## Archivos y reconstrucción', '',
             '`deck.pptx`: editable. `deck.pdf`: versión de presentación. `../one-pager/one-pager.pdf`: una página para el GM. `assets/`: capturas del producto tomadas por las pruebas e2e de HACK-051 (`web/e2e/screenshots/`).', '',
             '`sources.json` guarda archivo, fila, columna, formato y SHA-256 de cada cifra, y para las dos cifras derivadas (promedio de la liga y recorte del sesgo) sus entradas y la fórmula. Las notas de cada diapositiva llevan el guion oral.', '',
             'Reconstruir con Python 3.12 y `demo/deck/requirements.txt`: `python demo/deck/build.py`. Validar: `python demo/deck/verify.py`.', '',
             '## Revisión antes de entrevista', '',
             'Confirmar con el club cuál de las franquicias 5 y 11 es la sede. La conversión a victorias usa los puntos de Stuff+ v2 fuera de pliegue (`reports/business_value/stuff_scale_calibration.csv`, HACK-078).', '',
             '## Verificación', '',
             'Verify del backlog: `test -s demo/deck/deck.pdf && test -s demo/one-pager/one-pager.pdf`. Trazabilidad: `python demo/deck/verify.py`.']
    (OUT/'README.md').write_text('\n'.join(rows)+'\n', encoding='utf-8')
    (ONE/'README.md').write_text('# Resumen ejecutivo v2\n\n`one-pager.pdf`: una página en español para el GM, con Stuff+ v2. Fuentes en `../deck/README.md` y `../deck/sources.json`. Reconstrucción: `python demo/deck/build.py`.\n', encoding='utf-8')
    print(f'Built 10-slide PPTX + presentation PDF + one-page PDF with {len(evidence)} source bindings and {len(derived)} derived values.')


if __name__ == '__main__': main()
