"""Dynamic entity filter release preflight checks for Yeelight Pro."""

from __future__ import annotations

from pathlib import Path

from scripts.hacs_preflight_data import DYNAMIC_ENTITY_FILTER_CONTRACT_TOKENS


def check_dynamic_entity_filter_contracts(component_root: Path) -> list[str]:
    """Ensure non-destructive runtime device filtering remains tested."""
    errors: list[str] = []
    for relative_path, required_tokens in DYNAMIC_ENTITY_FILTER_CONTRACT_TOKENS.items():
        path = component_root / relative_path
        if not path.exists():
            errors.append(f"dynamic entity filter contract requires {relative_path}")
            continue
        content = path.read_text(encoding="utf-8")
        for token, reason in required_tokens.items():
            if token not in content:
                errors.append(f"{relative_path} missing {reason}: {token}")
    return errors
