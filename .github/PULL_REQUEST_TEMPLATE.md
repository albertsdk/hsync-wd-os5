## Description

Brief summary of the changes and why they are needed.

## Type of change

- [ ] Bug fix (non-breaking change)
- [ ] New feature (non-breaking change)
- [ ] Breaking change (package behaviour, web UI or release artifact)
- [ ] Documentation update
- [ ] Build / CI change

## Checklist

- [ ] Tests pass locally (`.venv/bin/python -m pytest -q`)
- [ ] Code is linted (`.venv/bin/python -m ruff check . && .venv/bin/python -m ruff format --check .`)
- [ ] Shell syntax is valid (`bash -n compile.sh`, `sh -n packaging/Apkg/*.sh`)
- [ ] Documentation is updated:
  - [ ] `docs/` (user-facing) for configuration, install or UI changes
  - [ ] `llm-wiki/` (internal) for architecture or contract changes
- [ ] `packaging/Apkg/web/i18n/*.json` updated for every language in `SUPPORTED`
- [ ] Client parity: the matching change landed (or is already present) in
      `hsync-client` / `hsync-common`
- [ ] `docs/configuration.md` ranges still match `config_set.php` (the
      `tests/test_docs_configuration.py` guard)

## Related issues

Closes # (issue number) or N/A.
