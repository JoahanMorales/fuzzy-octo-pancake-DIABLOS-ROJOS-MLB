# Shared-file owners

One writer per shared file. Others ask the owner with `uak msg ID --kind request`. Patterns are relative, with no spaces; directories end in `/`.
An owner is not a prerequisite for everyone: consumers work on published contracts and mocks. To transfer ownership, open a PR to main.

| Pattern | Owner task |
|---|---|
| requirements.txt | HACK-001 |
| pyproject.toml | HACK-001 |
| stuffplus/__init__.py | HACK-001 |
| stuffplus/config.py | HACK-001 |
| stuffplus/io.py | HACK-001 |
| tests/conftest.py | HACK-001 |
| README.md | HACK-001 |
| .uak/PROJECT.md | HACK-001 |
| .github/workflows/ | HACK-073 |
| stuffplus/schema.py | HACK-002 |
| stuffplus/targets.py | HACK-030 |
| stuffplus/splits.py | HACK-002 |
| stuffplus/api.py | HACK-002 |
| docs/CONTRACT.md | HACK-002 |
| stuffplus/physics/constants.py | HACK-004 |
| stuffplus/models/common.py | HACK-031 |
| stuffplus/bundle.py | HACK-031 |
| stuffplus/features/identity.py | HACK-029 |
| app/Home.py | HACK-007 |
| app/theme.py | HACK-007 |
| .streamlit/ | HACK-007 |
| web/package.json | HACK-045 |
| web/package-lock.json | HACK-045 |
| web/vite.config.ts | HACK-037 |
| web/tsconfig.json | HACK-037 |
| web/src/routes.tsx | HACK-067 |
| web/src/styles/tokens.css | HACK-039 |
| web/src/contract/ | HACK-066 |
| .gitignore | HACK-057 |
