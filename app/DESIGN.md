# Diseño del dashboard · Stuff+ 2240

**Estado: PROVISIONAL — pendiente del bloqueo de diseño (`/uak-design-lock`, decide luis).** Solo se implementó la dirección del brief; las otras dos están descritas, no construidas.

## Dirección implementada (A · "Transmisión Diablos")
Fondo negro, paneles grafito, rojo Diablos como único acento, números enormes en condensada (Barlow Condensed), títulos en mayúsculas con filete rojo. Estilo broadcast tipo Statcast.

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

## Alternativas para el bloqueo (sin construir)
- **B · Laboratorio claro:** fondo hueso, rojo y negro como tinta, tipografía de reporte técnico; mejor para imprimir y para jurado académico.
- **C · Tablero de cabina:** negro profundo con medidores grandes y acento ámbar sobre rojo; máxima legibilidad a distancia.
