#!/usr/bin/env python3
"""Audit Yeelight Pro private-house device projection coverage.

The script is read-only. It loads one installed Home Assistant config entry,
reads Open API list/property/schema endpoints, and compares projected entity
candidates with the local HA entity registry.
"""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Mapping, Sequence
import json
from pathlib import Path
import sys
from typing import Any

import aiohttp

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from custom_components.yeelight_pro.const import (  # noqa: E402
    CONF_ACCESS_TOKEN,
    CONF_HOUSE_ID,
    CONF_OPEN_API_CLIENT_ID,
    CONF_PRIVATE_DOMAIN,
)
from custom_components.yeelight_pro.core.client import YeelightProClient  # noqa: E402
from custom_components.yeelight_pro.core.device_payload import (  # noqa: E402
    DevicePayloadBuilder,
)
from custom_components.yeelight_pro.core.auxiliary_data import (  # noqa: E402
    AuxiliaryData,
    async_fetch_auxiliary_data,
)
from custom_components.yeelight_pro.core.property_hydration import (  # noqa: E402
    async_hydrate_device_properties,
)
from custom_components.yeelight_pro.core.property_hydration_summary import (  # noqa: E402
    PropertyHydrationDiagnostics,
)
from custom_components.yeelight_pro.core.schema_cache import (  # noqa: E402
    product_ids_from_items,
)
from custom_components.yeelight_pro.deployment_urls import (  # noqa: E402
    deployment_iot_base_url,
)
from custom_components.yeelight_pro.entry_migration import (  # noqa: E402
    normalize_entry_data,
)
from custom_components.yeelight_pro.identity import (  # noqa: E402
    apply_identity_scope_to_device_maps,
)
from scripts.private_house_audit.io_helpers import (  # noqa: E402
    entity_registry_by_unique_id,
    installed_runtime_status,
    load_target_entry,
    print_summary,
    safe_list,
    safe_mapping,
)
from scripts.private_house_audit.report import build_report  # noqa: E402
from scripts.private_house_audit.projection import (  # noqa: E402
    projected_property_keys as _projected_property_keys,
    unprojected_property_samples as _unprojected_property_samples,
)
from scripts.private_house_audit.schema_cache import (  # noqa: E402
    cached_product_schemas,
    merge_product_schemas,
)

DEFAULT_ENTRY_TITLE = (
    "Yeelight Pro Private (http://api-dev.yeedev.com · IoT 全量样板家庭)"
)
DEFAULT_CONFIG_DIR = Path(
    "/Users/yeelight/Desktop/workspace/ai/lucore/config/homeassistant-verify"
)


class _AuditCoordinator:
    """Minimal coordinator view needed by identity helpers."""

    def __init__(self, *, entry_data: Mapping[str, Any], house_id: int) -> None:
        self.entry_data = dict(entry_data)
        self.house_id = house_id


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(
        description="Audit Yeelight Pro private-house entity coverage from local HA."
    )
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=DEFAULT_CONFIG_DIR,
        help="Home Assistant config directory containing .storage.",
    )
    parser.add_argument(
        "--entry-id",
        default="",
        help="Config entry id to audit. Defaults to title lookup.",
    )
    parser.add_argument(
        "--entry-title",
        default=DEFAULT_ENTRY_TITLE,
        help="Config entry title to audit when --entry-id is not provided.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path to write the JSON report.",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=30,
        help="Maximum per-device problem rows to include in stdout summary.",
    )
    return parser


async def async_main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint."""
    args = build_parser().parse_args(argv)
    config_dir = args.config_dir
    entry = load_target_entry(
        config_dir,
        entry_id=args.entry_id,
        entry_title=args.entry_title,
    )
    data = normalize_entry_data(entry.get("data") or {})
    house_id = int(data[CONF_HOUSE_ID])
    endpoint_errors: dict[str, str] = {}
    async with aiohttp.ClientSession() as session:
        client = YeelightProClient(
            domain=deployment_iot_base_url(data[CONF_PRIVATE_DOMAIN]),
            access_token=str(data[CONF_ACCESS_TOKEN]),
            client_id=str(data.get(CONF_OPEN_API_CLIENT_ID) or ""),
            session=session,
        )
        devices = await client.get_devices(house_id)
        gateways = await safe_list(
            "gateways",
            client.get_gateways(house_id),
            endpoint_errors,
        )
        product_schemas = merge_product_schemas(
            cached_product_schemas(config_dir),
            await safe_mapping(
                "product_schemas",
                client.get_product_schemas(product_ids_from_items([*devices, *gateways])),
                endpoint_errors,
            ),
        )
        hydration = PropertyHydrationDiagnostics()
        hydrated_devices = await async_hydrate_device_properties(
            client,
            house_id=house_id,
            devices=devices,
            product_schemas=product_schemas,
            diagnostics=hydration,
        )
        auxiliary = await async_fetch_auxiliary_data(
            client,
            house_id,
            AuxiliaryData(
                areas=[],
                rooms=[],
                groups=[],
                houses=[],
                scenes=[],
            ),
        )

    builder = DevicePayloadBuilder()
    runtime_data, gateway_data = builder.build_runtime_payloads(
        devices=hydrated_devices,
        gateways=gateways,
        product_schemas=product_schemas,
        apply_runtime_overrides=lambda payload: payload,
        rooms=auxiliary.rooms,
        areas=auxiliary.areas,
    )
    apply_identity_scope_to_device_maps(
        entry_data=data,
        house_id=house_id,
        devices=runtime_data,
        gateways=gateway_data,
    )

    registry_entries = entity_registry_by_unique_id(config_dir, entry["entry_id"])
    install_runtime = installed_runtime_status(config_dir)
    report = build_report(
        entry=entry,
        entry_data=data,
        runtime_data=runtime_data,
        registry_entries=registry_entries,
        hydration=hydration.as_dict(),
        endpoint_errors=endpoint_errors,
        install_runtime=install_runtime,
        areas=auxiliary.areas,
        rooms=auxiliary.rooms,
        groups=auxiliary.groups,
        houses=auxiliary.houses,
        scenes=auxiliary.scenes,
        analytics_enabled=True,
    )
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    print_summary(report, top=max(0, int(args.top)))
    return 1 if report["summary"]["devices_with_missing_entities"] else 0


def main(argv: Sequence[str] | None = None) -> int:
    """Synchronous CLI wrapper."""
    return asyncio.run(async_main(argv))


if __name__ == "__main__":
    raise SystemExit(main())
