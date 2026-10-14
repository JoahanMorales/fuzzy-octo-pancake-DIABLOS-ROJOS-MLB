"""Build editable PPTX + PDF from tracked aggregates; no private data access."""
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
RED, INK, GRAY, LIGHT, WHITE = '#D71920', '#202124', '#585B60', '#ECEDEF', '#FFFFFF'
W, H = 720, 405
for name, file in [('Arial', 'Arial.ttf'), ('ArialBold', 'Arial Bold.ttf')]:
    pdfmetrics.registerFont(TTFont(name, '/System/Library/Fonts/Supplemental/' + file))

sources, evidence = {}, []


def row(path, **where):
    p = ROOT / path
    sources[path] = hashlib.sha256(p.read_bytes()).hexdigest()
    rows = list(csv.DictReader(p.open()))
    found = [r for r in rows if all(r[k] == str(v) for k, v in where.items())]
    if len(found) != 1:
        raise ValueError(f'Expected one source row: {path}, {where}, found {len(found)}')
    return found[0]


def number(slide, path, where, column, digits=2, factor=1):
    r = row(path, **where)
    v = float(r[column])
    display = str((Decimal(r[column]) * Decimal(str(factor))).quantize(Decimal('1').scaleb(-digits), rounding=ROUND_HALF_UP))
    evidence.append(dict(slide=slide, source=path, row=where, column=column,
                         value=v, factor=factor, display=display))
    return display


class Page:
    """Shared explicit line positions for native PowerPoint shapes and PDF."""
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

    def text(self, text, x, y, width=640, size=18, color=INK, bold=False, leading=None):
        font = 'ArialBold' if bold else 'Arial'
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
                p.font.name = 'Arial'; p.font.size = Pt(size); p.font.bold = bold
                p.font.color.rgb = RGBColor.from_string(color[1:])
            if self.pdf is not None:
                self.pdf.setFillColor(color); self.pdf.setFont(font, size)
                self.pdf.drawString(x, self.height-yy-size*.82, line)
        return y+len(lines)*leading


def header(p, title, index, source, dark=False):
    p.rect(0, 0, W, H, INK if dark else WHITE)
    p.rect(40, 23, 42, 4, RED)
    p.text('STUFF+ 2240   /   DIABLOS ROJOS', 95, 18, 570, 10, LIGHT if dark else GRAY)
    p.text(title, 40, 53, 640, 28, WHITE if dark else INK, True, 32)
    p.text(source, 40, 356, 640, 8.5, LIGHT if dark else GRAY, leading=11)
    p.text(f'{index:02d}', 650, 381, 30, 10, LIGHT if dark else GRAY)


def bar(p, label, value, text, y, max_value, color=RED):
    p.text(label, 40, y, 150, 17)
    p.rect(215, y+2, abs(value)/max_value*335, 18, color)
    p.text(text, 572, y-1, 108, 18, bold=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True); ONE.mkdir(parents=True, exist_ok=True)
    prs = Presentation(); prs.slide_width = Pt(W); prs.slide_height = Pt(H)
    pdf = Canvas(str(OUT/'stuffplus2240.pdf'), pagesize=(W,H))
    pdf.setTitle('Stuff+ 2240 · Diablos Rojos · evidencia exploratoria')
    titles, footers, notes = [], [], []
    def slide(title, footer, note, dark=False):
        s = prs.slides.add_slide(prs.slide_layouts[6])
        s.notes_slide.notes_text_frame.text = note + '\nFuentes: ' + footer
        p = Page(s, pdf); header(p, title, len(prs.slides), footer, dark)
        titles.append(title); footers.append(footer); notes.append(note)
        return p
    def end(): pdf.showPage()

    p = slide('El mismo arsenal cambia\nen el aire de CDMX',
              'Fuente: reports/altitude_delta/delta_by_shape.csv. Estimaciones exploratorias.',
              '45 s. Problema: un buen arsenal a nivel del mar puede cambiar en casa. Proponemos comparar la misma forma de lanzamiento bajo dos ambientes. Abrir con una decisión del coach, sin prometer superioridad predictiva.', True)
    p.text('Comparación física y estadística para discutir\nel uso del arsenal y la evaluación de lanzadores.',40,162,640,22,WHITE)
    p.text('Documento para entrevista. Datos oficiales agregados.\nStaff, prospectos y validación inductiva siguen pendientes.',40,263,640,17,LIGHT)
    end()

    density = 'reports/physics/rho_by_bucket.csv'
    p = slide('El aire estimado cambia entre ambientes', density + ' · media por bucket; parques anónimos.',
              '55 s. Mostrar densidad relativa estimada. Son grupos de altitud y la identidad exacta del Harp Helú aún no está verificada. Los valores no prueban por sí solos una relación causal.')
    for y, name, label in [(150,'No Altitude','Nivel del mar'),(208,'Medium Altitude','Altitud media'),(266,'Extreme Altitude','Altitud extrema')]:
        v=number(2,density,{'bucket':name},'mean',3)
        bar(p,label,float(v),v,y,1.1)
    p.text('Densidad relativa: menor valor significa aire menos denso.',40,319,640,14,GRAY)
    end()

    shape = 'reports/altitude_delta/delta_by_shape.csv'
    observed = 'reports/physics/delta_extreme_vs_no.csv'
    obs = number(3,observed,{'pitch_family':'Four-Seam','outcome':'ivb'},'delta')
    cf = number(3,shape,{'shape':'4S'},'delta_ivb_in')
    p = slide('La recta pierde movimiento vertical', observed + ' · Four-Seam/ivb; ' + shape + ' · 4S.',
              '55 s. Separar observación y contrafactual: el primer valor compara Extreme menos No dentro de lanzador; el segundo mueve la misma forma 4S a aire de Harp Helú frente a nivel del mar. La concordancia describe un mecanismo, no identifica causalidad.')
    p.text(obs+'"',40,153,280,55,RED,True)
    p.text('Contraste observado\nExtreme menos No',40,227,285,19)
    p.text(cf+'"',380,153,300,55,RED,True)
    p.text('Cambio físico modelado\nCDMX menos nivel del mar',380,227,300,19)
    p.text('IVB: movimiento vertical inducido. Comparaciones exploratorias.',40,319,640,14,GRAY)
    end()

    stuff = 'reports/stuff_model/metrics.csv'; pitching = 'reports/pitching_model/metrics.csv'
    b=number(4,stuff,{'model':'baseline','baseline_name':'mean xRV by count'},'rmse',5)
    s=number(4,stuff,{'model':'stuff_v1','baseline_name':'mean xRV by count'},'rmse',5)
    q=number(4,pitching,{'model':'pitching_combined','target':'rv_x'},'rmse',5)
    skill=number(4,pitching,{'model':'pitching_combined','target':'rv_x'},'skill_vs_baseline',2,100)
    p = slide('Pitching+ mejora el error. Stuff+ queda cerca', stuff + '; ' + pitching + ' · rv_x, baseline por conteo.',
              '75 s. RMSE menor es mejor. La mejora de Pitching+ no se atribuye a Stuff+ puro. La preparación global es transductiva: faltan holdouts inductivos reales por lanzador, temporada y parque. No usar benchmark/demo como calidad real.')
    for y,label,v,color in [(144,'Baseline',b,GRAY),(191,'Stuff+',s,RED),(238,'Pitching+',q,INK)]:
        bar(p,label,float(v),v,y,.22,color)
    p.text('Pitching+: '+skill+'% menos RMSE frente al baseline por conteo.',40,294,640,17,bold=True)
    p.text('Preparación global. La validación inductiva sigue pendiente.',40,325,640,14,GRAY)
    end()

    p = slide('Las pérdidas dependen de la forma del pitch', shape + ' · delta_stuff; misma forma, CDMX menos nivel del mar.',
              '65 s. Barras muestran magnitud de pérdida: ninguna forma del cuadro gana en términos absolutos. Sweeper pierde menos que riding 4S. Es una hipótesis operativa para discutir, condicionada al modelo y a la física.')
    for y,label,key in [(144,'Sweeper','sweeper'),(191,'Slider','slider'),(238,'4S','4S'),(285,'Riding 4S','riding 4S')]:
        v=number(5,shape,{'shape':key},'delta_stuff')
        bar(p,label,float(v),v,y,18)
    p.text('Longitud = pérdida; etiquetas = ΔStuff+. Ninguna forma gana en absoluto.',40,329,640,14,GRAY)
    end()

    top='reports/pitcher_sensitivity/top15.csv'; bottom='reports/pitcher_sensitivity/bottom15.csv'
    a={'pitcher_anon_id':'pitcher_01003','year':'2025'}; z={'pitcher_anon_id':'pitcher_00529','year':'2025'}
    av=number(6,top,a,'altitude_proof_index'); zv=number(6,bottom,z,'altitude_proof_index')
    ad=number(6,top,a,'delta_eb'); zd=number(6,bottom,z,'delta_eb')
    p=slide('La resistencia varía entre arsenales', top + '; ' + bottom + ' · temporada 2025; estimaciones EB.',
            '65 s. Comparar la misma temporada. Índice centrado en 100: resistencia relativa a la liga, no percentil. Ambos pierden puntos absolutos. Los intervalos condicionan física, modelo, prior, baseline y uso. No miden certeza de rango ni garantizan desempeño futuro.')
    p.text('pitcher_01003 · 2025',40,146,300,20,bold=True)
    p.text(av,40,181,300,48,RED,True)
    p.text('Índice de resistencia\nΔStuff+ ajustado: '+ad,40,244,300,18)
    p.text('pitcher_00529 · 2025',380,146,300,20,bold=True)
    p.text(zv,380,181,300,48,RED,True)
    p.text('Índice de resistencia\nΔStuff+ ajustado: '+zd,380,244,300,18)
    p.text('Ranking exploratorio. Identidades anónimas. EB reduce ruido de muestras.',40,319,640,14,GRAY)
    end()

    park='reports/park_id/franchise_rho.csv'
    x=number(7,park,{'franchise':'5'},'rho_mean',3); y=number(7,park,{'franchise':'11'},'rho_mean',3)
    p=slide('El staff requiere confirmar la sede', park + '; reports/park_id/harp_helu.md · identidad provisional.',
            '55 s. Las franquicias 5 y 11 son candidatos por densidad, no identificación verificada de Diablos. La auditoría de uso en casa frente a gira está pendiente. No nombrar una rotación, un bullpen o pitches para cortar sin el vínculo oficial y HACK-032.')
    p.text('Franquicia 5: '+x+'\nFranquicia 11: '+y,40,146,300,24,bold=True)
    p.text('Candidatos por densidad.\nLa identidad del Harp Helú\nsigue sin verificarse.',40,238,300,18)
    p.text('Antes de recomendar uso',380,146,300,22,RED,True)
    p.text('Confirmar equipo y estadio.\nVincular arsenal por temporada.\nRevisar el split casa y gira\ny su cobertura.',380,192,300,19)
    end()

    p=slide('El prospecto comienza con un perfil físico', 'Contrato: docs/CONTRACT.md; stuffplus/schema.py. Flujo propuesto, sin evaluación real de prospectos.',
            '50 s. Solicitar velocidad, giro, eje de giro, punto de liberación y extensión del arsenal. El motor compara movimiento y calidad en dos ambientes. La salida del evaluador de prospectos y sus comparables aún debe integrarse y verificarse. No emitir Firmar o Evitar con evidencia incompleta.')
    p.text('Entrada',40,146,280,22,RED,True)
    p.text('Velocidad y giro\nEje de giro\nPunto de liberación\nExtensión y uso del arsenal',40,190,280,20)
    p.text('Discusión con scouting',380,146,300,22,RED,True)
    p.text('Cambio de movimiento\nCalidad en ambos ambientes\nCobertura e incertidumbre\nNecesidades de desarrollo',380,190,300,20)
    p.text('Evaluador y comparables pendientes. Este flujo no constituye un dictamen.',40,329,640,14,GRAY)
    end()

    value='reports/business_value/runs_per_win.csv'
    league=number(9,value,{'entorno':'liga'},'carreras_por_victoria'); extreme=number(9,value,{'entorno':'Extreme Altitude'},'carreras_por_victoria')
    p=slide('El entorno cambia el valor de una carrera', value + ' · aproximación pitagórica; no proyección de ahorro del staff.',
            '65 s. Carreras por victoria como conversión descriptiva: liga y bucket Extreme. El bucket no certifica identidad del estadio. Las conversiones de puntos Stuff+ a carreras dependen de la desviación del xRV predicho y calibración final. Las tablas por calidad del modelo son escenarios, no ahorros observados.')
    p.text(league,40,146,300,53,RED,True)
    p.text('Carreras por victoria\nLiga',40,218,300,20)
    p.text(extreme,380,146,300,53,RED,True)
    p.text('Carreras por victoria\nAltitud extrema',380,218,300,20)
    p.text('El ahorro proyectado exige calibrar la escala del modelo final.',40,304,640,18,bold=True)
    p.text('Las tablas de conversión Stuff+ actuales describen escenarios.',40,334,640,14,GRAY)
    end()

    p=slide('La demo compara y explica el arsenal', 'Respaldo: reports/altitude_delta/ y reports/pitcher_sensitivity/. Integración de dashboard pendiente.',
            '70 s. Abrir comparación por forma, mostrar la pérdida del arsenal y discutir el pitch que más contribuye. Si dashboard no está integrado o falla, usar las tablas y estas láminas. Terminar con el siguiente paso: validar, confirmar el staff y contrastar recomendaciones con el coach. No afirmar demo en vivo verificada.', True)
    p.text('Comparar movimiento entre ambientes.\nRevisar qué pitch impulsa la pérdida.\nMostrar cobertura y límites del resultado.',40,157,640,24,WHITE,leading=34)
    p.text('Respaldo offline: agregados y PDF de esta presentación.\nLa recomendación final requiere validar y confirmar el staff.',40,294,640,17,LIGHT)
    end()
    pdf.save(); prs.save(OUT/'stuffplus2240.pptx')

    # One-page executive brief; designed independently for printing.
    c=Canvas(str(ONE/'resumen_ejecutivo.pdf'),pagesize=(595,842))
    c.setTitle('Stuff+ 2240 · resumen ejecutivo para el GM')
    p=Page(pdf=c,width=595,height=842)
    p.rect(38,32,42,5,RED)
    p.text('STUFF+ 2240 / DIABLOS ROJOS',94,28,463,11,GRAY)
    p.text('El arsenal cambia con el aire',38,67,519,28,bold=True)
    p.text('Resumen ejecutivo para discusión con el GM y el coach',38,111,519,13,GRAY)
    p.text('Hallazgos disponibles',38,158,519,18,RED,True)
    p.text(f'La recta Four-Seam pierde {abs(float(obs)):.2f} pulgadas de IVB en el contraste observado entre altitud extrema y nivel del mar. El modelo físico estima {abs(float(cf)):.2f} pulgadas para la forma 4S al cambiar de ambiente.',38,193,519,14,leading=19)
    p.text(f'Pitching+ reduce el RMSE {skill}% frente al baseline por conteo. Stuff+ queda cerca del baseline. La preparación global impide presentar estos resultados como validación inductiva final.',38,278,519,14,leading=19)
    p.text('Sweeper pierde menos Stuff+ que riding 4S en el modelo. Los rankings de lanzadores son exploratorios y usan identidades anónimas. Ninguna de estas comparaciones garantiza desempeño futuro.',38,363,519,14,leading=19)
    p.text('Decisión propuesta',38,451,519,18,RED,True)
    p.text('Usar la comparación por ambiente para priorizar una revisión de arsenal con scouting y coaching. Confirmar primero la identidad del staff y la sede, validar fuera de muestra y contrastar los cambios físicos con evidencia propia.',38,486,519,14,leading=19)
    p.text('Valor y límites',38,573,519,18,RED,True)
    p.text(f'La aproximación de carreras por victoria es {league} en liga y {extreme} en altitud extrema. El ahorro del staff aún no está cuantificado. Las conversiones de Stuff+ a carreras actuales son escenarios.',38,608,519,14,leading=19)
    p.text('Fuentes y trazabilidad',38,705,519,12,bold=True)
    p.text('physics/delta_extreme_vs_no.csv; altitude_delta/delta_by_shape.csv;\nstuff_model/metrics.csv; pitching_model/metrics.csv;\nbusiness_value/runs_per_win.csv. Todos bajo reports/.\nDetalle de filas, columnas y hashes: demo/deck/sources.json.',38,733,519,10,GRAY,leading=14)
    c.showPage(); c.save()

    (OUT/'sources.json').write_text(json.dumps({'demo_data':False,'exploratory':True,
        'source_sha256':sources,'evidence':evidence},ensure_ascii=False,indent=2)+'\n')
    timing=[45,55,55,75,65,65,55,50,65,70]
    rows=['# Presentación ejecutiva · HACK-036','',
          '10 diapositivas para una entrevista de 10 minutos. Identidad tipográfica Diablos con rojo #D71920, gris carbón y Arial, consistente con los reportes existentes. No sustituye ni cambia el diseño de la aplicación.','',
          '**Estado:** evidencia oficial agregada, exploratoria. PPTX editable y PDF disponibles. Staff, evaluador de prospectos, dashboard integrado y validación inductiva final pendientes. La presentación lo dice explícitamente.','',
          '| Lámina | Idea principal | Tiempo | Fuente de cifras |','|---|---|---:|---|']
    for i,(t,f,sec) in enumerate(zip(titles,footers,timing),1):
        rows.append(f'| {i} | {t.replace(chr(10)," ")} | {sec} s | {f} |')
    rows += ['', '## Archivos y reconstrucción','',
             '`stuffplus2240.pptx`: editable. `stuffplus2240.pdf`: versión de presentación. `../one-pager/resumen_ejecutivo.pdf`: una página para el GM.', '',
             '`sources.json` conserva archivo, fila, columna, factor de formato y SHA-256 por cifra. El guion oral y los límites están en las notas de cada diapositiva. Todos los datos provienen de CSV agregados versionados. No se leen datos privados.', '',
             'Reconstruir con Python 3.12 y `python-pptx`, `reportlab`, `pandas`, `pymupdf`: `python demo/deck/build.py`. Para PDF se usan Arial y Arial Bold de macOS. LibreOffice sirve para exportar el PPTX real a PDF y comparar visualmente. `python demo/deck/verify.py` valida fuentes, cifras y artefactos.','',
             '## Revisión antes de entrevista','',
             'Confirmar el staff y el estadio con el equipo, integrar salidas de HACK-032/021 y refrescar HACK-014 con holdouts inductivos reales. Sustituir los estados pendientes solo con resultados verificables. No citar `reports/benchmark/demo` como evidencia real.','',
             'En la demo integrada mostrar movimiento por ambiente, pérdida del arsenal y cobertura. Si no está integrada, presentar el PDF y abrir los CSV agregados. El respaldo actual no depende de servicios ni incluye una grabación plan B.','',
             '## Verificación','',
             'Verify del backlog: `test -s demo/deck/README.md`. Verificación de artefactos y trazabilidad: `python demo/deck/verify.py`. La evidencia real de ejecución y QA visual se documenta en `verification.md`.']
    (OUT/'README.md').write_text('\n'.join(rows)+'\n')
    (ONE/'README.md').write_text('# Resumen ejecutivo\n\n`resumen_ejecutivo.pdf`: una página en español para el GM. Fuentes y límites completos en `../deck/README.md` y `../deck/sources.json`. Reconstrucción: `python demo/deck/build.py`.\n')
    print('Built 10-slide PPTX + presentation PDF + one-page executive PDF with '+str(len(evidence))+' source bindings.')


if __name__=='__main__': main()
