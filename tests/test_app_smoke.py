from pathlib import Path

import pytest

st_testing = pytest.importorskip("streamlit.testing.v1")
ROOT = Path(__file__).resolve().parents[1]
PAGES = ["app/Home.py"] + sorted(str(p.relative_to(ROOT)) for p in (ROOT / "app/pages").glob("[1-8]_*.py"))


@pytest.mark.parametrize("path", PAGES)
def test_page_renders_without_exception(path):
    at = st_testing.AppTest.from_file(str(ROOT / path), default_timeout=30).run()
    assert not at.exception, [e.value for e in at.exception]


def test_simulator_computes_and_flags_demo():
    at = st_testing.AppTest.from_file(str(ROOT / "app/pages/1_Simulador.py"), default_timeout=30).run()
    assert at.info  # estado vacío antes de calcular
    at.button[0].click().run()
    assert not at.exception
    assert any("DEMOSTRACIÓN" in m.value or "MODELO REAL" in m.value for m in at.markdown)
    assert any("ΔStuff+ CDMX" in m.value for m in at.markdown)
