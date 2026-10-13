import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # raíz del repo: streamlit solo agrega app/ al path

from app import theme

theme.coming_soon("Altitud", "HACK-015", "Efecto de la altitud por forma de lanzamiento.")
