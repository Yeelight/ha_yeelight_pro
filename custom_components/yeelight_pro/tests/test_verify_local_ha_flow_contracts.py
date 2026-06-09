"""Local HA config/options flow contract verification tests."""

from __future__ import annotations

from pathlib import Path

from scripts.verify_local_ha import VerificationReport, verify_flow_contracts


def test_verify_flow_contracts_accepts_current_runtime_options_boundary(
    tmp_path: Path,
) -> None:
    """flow verifier 应接受当前 options merge/reload/确认页边界."""
    _write_flow_files(tmp_path)
    report = VerificationReport()

    verify_flow_contracts(tmp_path, report)

    assert report.ok
    assert any("flow contracts" in fact for fact in report.facts)
    flow_contracts = report.metrics["flow_contracts"]
    assert isinstance(flow_contracts, dict)
    assert flow_contracts["options_factory"] is True


def test_verify_flow_contracts_rejects_options_flow_without_reload_check(
    tmp_path: Path,
) -> None:
    """options flow 缺少 options_require_reload 时应阻断本地 HA 验证."""
    _write_flow_files(tmp_path, include_reload_check=False)
    report = VerificationReport()

    verify_flow_contracts(tmp_path, report)

    assert not report.ok
    assert any("options_require_reload" in failure for failure in report.failures)


def test_verify_flow_contracts_rejects_config_flow_without_options_factory(
    tmp_path: Path,
) -> None:
    """config flow 不返回 YeelightProOptionsFlow 时应阻断 release 契约."""
    _write_flow_files(tmp_path, include_options_factory=False)
    report = VerificationReport()

    verify_flow_contracts(tmp_path, report)

    assert not report.ok
    assert any("does not return YeelightProOptionsFlow" in failure for failure in report.failures)


def _write_flow_files(
    root: Path,
    *,
    include_reload_check: bool = True,
    include_options_factory: bool = True,
) -> None:
    """Write focused flow source fixtures."""
    reload_call = (
        "        return options_require_reload(\n"
        "            normalize_entry_options(entry_options(self._config_entry)),\n"
        "            normalize_entry_options(self._pending_options),\n"
        "        )"
        if include_reload_check
        else "        return False"
    )
    root.mkdir(parents=True, exist_ok=True)
    (root / "options_flow.py").write_text(
        "\n".join([
            "class YeelightProOptionsFlow:",
            "    def async_show_form(self, **kwargs): pass",
            "    def async_create_entry(self, **kwargs): pass",
            "    async def async_step_init(self, user_input=None):",
            "        self._pending_options = merge_options(entry_options(self._config_entry), user_input)",
            "        if self._pending_options_require_reload():",
            "            return await self.async_step_confirm_reload()",
            "        return await self.async_step_confirm_runtime()",
            "    async def async_step_confirm_runtime(self, user_input=None):",
            "        return await self._async_step_confirm_options(step_id='confirm_runtime', user_input=user_input)",
            "    async def async_step_confirm_reload(self, user_input=None):",
            "        return await self._async_step_confirm_options(step_id='confirm_reload', user_input=user_input)",
            "    async def _async_step_confirm_options(self, *, step_id, user_input):",
            "        if user_input is not None:",
            "            return self.async_create_entry(title='', data=self._pending_options)",
            "        current_options = normalize_entry_options(entry_options(self._config_entry))",
            "        pending_options = normalize_entry_options(self._pending_options)",
            "        return self.async_show_form(",
            "            step_id=step_id,",
            "            data_schema=options_confirm_schema(),",
            "            description_placeholders={",
            "                'changed_count': str(visible_option_change_count(current_options, pending_options)),",
            "            },",
            "        )",
            "    def _pending_options_require_reload(self):",
            reload_call,
            "    def init_form(self):",
            "        return self.async_show_form(step_id='init', data_schema=options_schema({}))",
        ]),
        encoding="utf-8",
    )
    factory = (
        "        return YeelightProOptionsFlow(config_entry)"
        if include_options_factory
        else "        return object()"
    )
    (root / "config_flow.py").write_text(
        "\n".join([
            "class YeelightProConfigFlow:",
            "    def async_get_options_flow(config_entry):",
            factory,
        ]),
        encoding="utf-8",
    )
