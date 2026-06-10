"""Yeelight Pro options flow."""

from __future__ import annotations

from typing import Any

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_ACCESS_TOKEN
from .config_flow_helpers import (
    device_picker_context,
    entry_options,
    flow_error_from_exception,
    merge_options,
    merge_options_device_picker,
    options_confirm_schema,
    options_device_picker_requested,
    options_schema,
    selected_device_ids_from_options,
    visible_option_change_count,
)
from .config_flow_device_picker import (
    DevicePickerChoice,
    async_load_device_choices,
    cloud_devices_schema,
    selected_device_ids_from_input,
)
from .entry_migration import normalize_entry_options
from .runtime_options import options_require_reload


class YeelightProOptionsFlow(config_entries.OptionsFlow):
    """Yeelight Pro 配置选项流程."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """初始化 options flow."""
        self._config_entry = config_entry
        self._pending_options: dict[str, Any] | None = None
        self._device_choices: tuple[DevicePickerChoice, ...] = ()
        self._selected_device_ids: list[str] = []

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """编辑 Yeelight Pro 运行时选项."""
        if user_input is not None:
            if options_device_picker_requested(user_input):
                return await self.async_step_cloud_devices()
            self._pending_options = merge_options(
                entry_options(self._config_entry),
                user_input,
            )
            if self._pending_options_require_reload():
                return await self.async_step_confirm_reload()
            return await self.async_step_confirm_runtime()

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema(
                entry_options(self._config_entry),
                self._config_entry,
            ),
        )

    async def async_step_cloud_devices(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """通过真实云端设备 picker 调整导入范围."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._selected_device_ids = selected_device_ids_from_input(
                user_input,
                self._device_choices,
            )
            self._pending_options = merge_options_device_picker(
                entry_options(self._config_entry),
                self._selected_device_ids,
                self._device_choices,
            )
            return await self.async_step_confirm_reload()

        try:
            domain, house_id, client_id = device_picker_context(self._config_entry)
            self._device_choices = await async_load_device_choices(
                self.hass,
                domain=domain,
                access_token=str(self._config_entry.data.get(CONF_ACCESS_TOKEN, "")),
                house_id=house_id,
                client_id=client_id,
            )
        except Exception as err:
            errors["base"] = flow_error_from_exception("options cloud devices", err)
            self._device_choices = ()

        self._selected_device_ids = selected_device_ids_from_options(
            entry_options(self._config_entry),
            self._device_choices,
        )
        return self.async_show_form(
            step_id="cloud_devices",
            data_schema=cloud_devices_schema(
                self._device_choices,
                self._selected_device_ids,
            ),
            errors=errors,
        )

    async def async_step_confirm_runtime(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """确认无需 reload 的 options 变更."""
        return await self._async_step_confirm_options(
            step_id="confirm_runtime",
            user_input=user_input,
        )

    async def async_step_confirm_reload(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """确认需要 reload 的 options 变更."""
        return await self._async_step_confirm_options(
            step_id="confirm_reload",
            user_input=user_input,
        )

    async def _async_step_confirm_options(
        self,
        *,
        step_id: str,
        user_input: dict[str, Any] | None,
    ) -> FlowResult:
        """显示确认页，确认后保存待提交 options."""
        if self._pending_options is None:
            return await self.async_step_init()

        pending_requires_reload = self._pending_options_require_reload()
        if step_id == "confirm_runtime" and pending_requires_reload:
            return await self.async_step_confirm_reload()
        if step_id == "confirm_reload" and not pending_requires_reload:
            return await self.async_step_confirm_runtime()

        if user_input is not None:
            return self.async_create_entry(title="", data=self._pending_options)

        current_options = normalize_entry_options(entry_options(self._config_entry))
        pending_options = normalize_entry_options(self._pending_options)
        return self.async_show_form(
            step_id=step_id,
            data_schema=options_confirm_schema(),
            description_placeholders={
                "changed_count": str(
                    visible_option_change_count(
                        current_options,
                        pending_options,
                    )
                ),
            },
        )

    def _pending_options_require_reload(self) -> bool:
        """Return whether the pending options require a config entry reload."""
        if self._pending_options is None:
            return False
        return options_require_reload(
            normalize_entry_options(entry_options(self._config_entry)),
            normalize_entry_options(self._pending_options),
        )
