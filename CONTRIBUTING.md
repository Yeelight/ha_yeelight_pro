# Contributing

## Ground Rules

- Do not commit Yeelight tokens, Home Assistant credentials, house IDs, IPs tied to a user, or raw device payloads.
- Use sanitized fixtures for device samples.
- Keep Yeelight IoT categories separate from Home Assistant entity platforms in docs and tests.
- Treat `vacuum` as experimental unless real Yeelight payloads prove the mapping.
- Do not document local gateway discovery, multi-account-in-one-entry UX, or full rules/spec filters as implemented until code and tests exist.

## Test Commands

Run from this directory:

```bash
python3 -m compileall -q custom_components/yeelight_pro
pytest -q
python3 validate_hacs.py
python3 scripts/check_release_zip.py
```

## Device Sample Format

When adding a fixture, include only the minimum sanitized data:

```json
{
  "category": "light",
  "component_id": "main_light",
  "properties": {
    "p": true,
    "l": 80,
    "ct": 4000
  },
  "expected_platforms": ["light"]
}
```

Do not include:

- Full tokens
- Real user IDs or usernames
- Real house IDs
- Raw cloud response bodies with personal data

## Pull Request Checklist

- [ ] `pytest -q` passes.
- [ ] New behavior has regression tests.
- [ ] Release-facing docs match implemented behavior.
- [ ] `custom_components/yeelight_pro/manifest.json`, release notes, and `CHANGELOG.md` describe the same release version when preparing a public release.
- [ ] Public support or bug reports use the GitHub issue templates and contain only sanitized diagnostics/logs.
- [ ] New options have translations in `strings.json`, `translations/en.json`, and `translations/zh-Hans.json`.
- [ ] Generated files are excluded from the release package.
