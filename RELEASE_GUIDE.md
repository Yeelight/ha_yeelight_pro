# Yeelight Pro Release Guide

This repository is not yet published from the current workspace. Treat the steps below as the release checklist.

## Required Checks

Run from `extensions/ha_yeelight_pro`:

```bash
python3 -m compileall -q custom_components/yeelight_pro scripts hacs_publish.py
ruff check custom_components/yeelight_pro scripts hacs_publish.py
mypy --ignore-missing-imports --explicit-package-bases custom_components/yeelight_pro scripts hacs_publish.py
pytest -q
python3 validate_hacs.py
python3 scripts/check_release_zip.py
python3 scripts/sync_local_ha_runtime.py
python3 scripts/verify_local_ha.py
```

Optional external checks before public release:

```bash
hassfest
hacs validate
```

GitHub workflow entrypoints:

- `.github/workflows/test.yaml`: runs `pytest -q`.
- `.github/workflows/validate.yaml`: runs hassfest, HACS validation, compile, lint, type-check, tests, local preflight, and release package shape checks.
- `.github/workflows/release.yaml`: runs the full local release gate with `python hacs_publish.py --check`, then creates and uploads `yeelight_pro.zip`.

## Release Package

The HACS release zip must contain:

```text
custom_components/yeelight_pro/manifest.json
custom_components/yeelight_pro/__init__.py
custom_components/yeelight_pro/config_flow.py
custom_components/yeelight_pro/translations/en.json
custom_components/yeelight_pro/translations/zh-Hans.json
```

It must not contain:

```text
__pycache__/
*.pyc
.pytest_cache/
.coverage
htmlcov/
custom_components/yeelight_pro/tests/
```

Use `python3 scripts/check_release_zip.py --write dist/yeelight_pro.zip` to create and verify the package. Use `python3 scripts/sync_local_ha_runtime.py` before `python3 scripts/verify_local_ha.py` so the local Home Assistant install receives runtime files without tests or generated artifacts.

## Publication Status

- HACS publication: pending
- Home Assistant brands/community publication: pending
- GitHub release: create only after checks pass and docs are reviewed

## Before Publishing

- Verify the version in `custom_components/yeelight_pro/manifest.json`.
- Verify `hacs.json` points to the same release zip filename.
- Confirm no real token, password, house ID, or raw device payload is committed.
- Confirm README and changelog only describe implemented and tested behavior.
- Confirm `custom_components/yeelight_pro/text.py` remains absent unless a real writable TextEntity API and tests are added in a future release.

## Verification Policy

Release-facing documents must not freeze historical test counts, coverage percentages, mypy source counts, or release zip file counts. Re-run the required checks and use the current command output for release review.

```text
python3 -m compileall -q custom_components/yeelight_pro scripts hacs_publish.py
pytest -q
ruff check custom_components/yeelight_pro scripts hacs_publish.py
mypy --ignore-missing-imports --explicit-package-bases custom_components/yeelight_pro scripts hacs_publish.py
python3 validate_hacs.py
python3 scripts/check_release_zip.py
python3 scripts/sync_local_ha_runtime.py
python3 scripts/verify_local_ha.py
```
