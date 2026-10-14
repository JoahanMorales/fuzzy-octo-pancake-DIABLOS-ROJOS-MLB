# Diseño del dashboard · Stuff+ 2240

**Estado: BLOQUEADO — Dirección A · Transmisión Diablos.** Luis la eligió el 2026-10-13. Tema, paleta y tipografía no cambian sin una decisión humana nueva.

## Dirección A · Transmisión Diablos
Fondo negro, paneles grafito, rojo Diablos como único acento, números enormes en condensada (Barlow Condensed), títulos en mayúsculas con filete rojo. Estilo broadcast tipo Statcast. Es la dirección del brief y la que está construida.

| Token | Valor | Uso |
|---|---|---|
| `bg` | `#0B0B0D` | fondo |
| `panel` / `line` | `#16161A` / `#2A2A31` | tarjetas, rejillas |
| `red` / `red_soft` | `#D71920` / `#FF4B52` | acento, flechas, foco |
| `text` / `muted` | `#F4F4F5` / `#A1A1AA` | texto |

Todos viven en `app/theme.py` (`TOKENS`) y `.streamlit/config.toml`; ningún color suelto en las páginas.

## Reglas
- UI en español. Cada número lleva fuente (tooltip `title` o pie de gráfica).
- Datos simulados muestran la insignia **DATOS DE DEMOSTRACIÓN** (`demo_badge`); el modelo real, **MODELO REAL**.
- El simulador cabe en 1280×720 sin scroll (barra lateral colapsada por defecto).
- `prefers-reduced-motion` desactiva animaciones; foco visible con contorno rojo claro.
- Dos sabores siempre rotulados: *Stuff+ en Harp Helú* (ambiente) y *a nivel del mar* (neutral).

## Nunca
- Un color, radio o sombra fuera de `TOKENS` en `app/theme.py`.
- Un número en pantalla sin fuente (tooltip `title` o pie de gráfica).
- Un rediseño global (tema, paleta o tipografía) sin decisión humana.

## Direcciones no elegidas
- **B · Laboratorio claro:** fondo hueso, rojo y negro como tinta, tipografía de reporte técnico.
- **C · Tablero de cabina:** negro profundo, medidores grandes, acento ámbar sobre rojo.
