# Windows: run from Git Bash. PY can point at the shared venv of the main checkout.
PY ?= python

.PHONY: install test app synthetic
install:
	$(PY) -m pip install -r requirements.txt
test:
	$(PY) -m pytest -q --tb=short
app:
	$(PY) -m streamlit run app/Home.py
synthetic:
	$(PY) -m tests.fixtures.synthetic data/sample/synthetic_pitches.parquet
