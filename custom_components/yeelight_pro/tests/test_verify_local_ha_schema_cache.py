"""Local HA product schema cache verification tests."""

from __future__ import annotations

from pathlib import Path

from scripts.verify_local_ha import VerificationReport, verify_product_schema_cache

from .storage_verifier_helpers import write_storage as _write_storage


def test_product_schema_cache_rejects_sensitive_markers(tmp_path: Path) -> None:
    """Product schema cache must not contain account or topology markers."""
    _write_storage(
        tmp_path,
        "yeelight_pro.product_schemas",
        {"schemas": {"1": {"accessToken": "secret"}}},
    )
    report = VerificationReport()

    verify_product_schema_cache(tmp_path, report)

    assert not report.ok
    assert any("accessToken" in failure for failure in report.failures)


def test_product_schema_cache_rejects_raw_device_payloads(tmp_path: Path) -> None:
    """Product schema cache must not persist raw house/device topology payloads."""
    _write_storage(
        tmp_path,
        "yeelight_pro.product_schemas",
        {
            "schemas": {},
            "devices": [{"device_id": "raw-device"}],
        },
    )
    report = VerificationReport()

    verify_product_schema_cache(tmp_path, report)

    assert not report.ok
    assert any("unexpected top-level fields" in failure for failure in report.failures)


def test_product_schema_cache_allows_schema_text_that_mentions_device(
    tmp_path: Path,
) -> None:
    """Ordinary product schema text should not be treated as raw device leakage."""
    _write_storage(
        tmp_path,
        "yeelight_pro.product_schemas",
        {
            "schemas": {
                "1": {
                    "description": "Device supports wall switch mode.",
                    "properties": [{"name": "power", "type": "bool"}],
                }
            }
        },
    )
    report = VerificationReport()

    verify_product_schema_cache(tmp_path, report)

    assert report.ok
    assert any(
        "product schema cache contains no sensitive markers" in fact
        for fact in report.facts
    )
    assert any("product schema cache schema count: 1" in fact for fact in report.facts)
    assert report.metrics["product_schema_cache"] == {"schema_count": 1}


def test_product_schema_cache_rejects_non_object_schema_values(
    tmp_path: Path,
) -> None:
    """Product schema cache entries must stay object-shaped for runtime loading."""
    _write_storage(
        tmp_path,
        "yeelight_pro.product_schemas",
        {"schemas": {"1": ["not", "a", "schema"]}},
    )
    report = VerificationReport()

    verify_product_schema_cache(tmp_path, report)

    assert not report.ok
    assert any("schema values are not objects" in failure for failure in report.failures)


def test_product_schema_cache_missing_storage_is_pending_fact(tmp_path: Path) -> None:
    """没有触发真实 schema 拉取前，缓存文件缺失不是发布阻断问题."""
    report = VerificationReport()

    verify_product_schema_cache(tmp_path, report)

    assert report.ok
    assert not report.warnings
    assert any("product schema cache storage not present yet" in fact for fact in report.facts)
