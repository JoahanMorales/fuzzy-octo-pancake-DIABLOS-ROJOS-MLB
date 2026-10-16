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

# HACK-056: one-command pipeline (hours on the real data; pipeline-dry just lists the steps)
.PHONY: pipeline pipeline-dry
pipeline:
	$(PY) -m analysis.pipeline.run
pipeline-dry:
	$(PY) -m analysis.pipeline.run --dry-run
