"""Yeelight Pro options flow."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .config_flow_device_picker import (
    DevicePickerChoice,
    async_load_device_choices,
    cloud_devices_schema,
    merge_options_device_picker,
    selected_device_ids_from_input,
    selected_device_ids_from_options,
)
from .config_flow_options import (
    device_filter_schema_fields,
    entry_options,
    menu_options,
    merge_device_import_filter,
    merge_options,
    merge_private_entry_data,
    options_confirm_schema,
    options_schema,
    options_support_device_filter,
    visible_entry_data_change_count,
    visible_option_change_count,
)
from .config_flow_helpers import flow_error_from_exception
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_CLOUD_DOMAIN,
    CONF_DEVICE_IMPORT_FILTER_INCLUDE_DEVICES,
    CONF_HOUSE_ID,
    CONF_OPEN_API_CLIENT_ID,
    CONF_PRIVATE_PUSH_PROXY,
    DOMAIN,
)
from .device_filter_options import (
    DIMENSION_NAMES,
    current_filter_selections,
    filter_dimension_choices,
)
from .entry_migration import normalize_entry_options
from .runtime_options import options_require_reload


class YeelightProOptionsFlow(config_entries.OptionsFlow):
    """Yeelight Pro 配置选项流程."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """初始化 options flow."""
        self._config_entry = config_entry
        self._pending_options: dict[str, Any] | None = None
        self._pending_entry_data: dict[str, Any] | None = None
        self._filter_selections: dict[str, list[str]] = {}
        self._filter_all_choices: dict[str, list[str]] = {}
        self._filter_loaded = False
        self._device_choices: tuple[DevicePickerChoice, ...] = ()

    # ── 入口菜单与通用设置 ──────────────────────────────────────

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """进入 Yeelight Pro 选项流程."""
        if not options_support_device_filter(self._config_entry):
            return await self.async_step_general(user_input)

        return self.async_show_menu(
            step_id="init",
            menu_options=menu_options(self._config_entry),
        )

    async def async_step_general(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """编辑 Yeelight Pro 通用运行时选项."""
        if user_input is not None:
            try:
                self._pending_options = merge_options(
                    entry_options(self._config_entry),
                    user_input,
                    self._config_entry,
                )
                self._pending_entry_data = merge_private_entry_data(
                    self._config_entry.data,
                    user_input,
                    self._config_entry,
                )
            except vol.Invalid:
                return self.async_show_form(
                    step_id="general",
                    data_schema=options_schema(
                        entry_options(self._config_entry),
                        self._config_entry,
                    ),
                    errors={CONF_PRIVATE_PUSH_PROXY: "invalid_url"},
                )
            if self._pending_options_require_reload():
                return await self.async_step_confirm_reload()
            return await self.async_step_confirm_runtime()

        return self.async_show_form(
            step_id="general",
            data_schema=options_schema(
                entry_options(self._config_entry),
                self._config_entry,
            ),
        )

    # ── 设备过滤线性向导 ────────────────────────────────────────

    async def async_step_filter_categories(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """品类选择页."""
        return await self._handle_filter_dimension("categories", user_input)

    async def async_step_filter_rooms(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """房间选择页."""
        return await self._handle_filter_dimension("rooms", user_input)

    async def async_step_filter_gateways(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """网关选择页."""
        return await self._handle_filter_dimension("gateways", user_input)

    async def async_step_filter_devices(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """设备选择页."""
        return await self._handle_filter_dimension("devices", user_input)

    async def async_step_cloud_devices(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Use the current cloud house device list to update import filtering."""
        errors: dict[str, str] = {}

        if user_input is not None:
            selected = selected_device_ids_from_input(user_input, self._device_choices)
            self._pending_options = merge_options_device_picker(
                entry_options(self._config_entry),
                selected,
                self._device_choices,
            )
            return await self.async_step_confirm_reload()

        try:
            self._device_choices = await async_load_device_choices(
                self.hass,
                domain=str(self._config_entry.data.get(CONF_CLOUD_DOMAIN, "")),
                access_token=str(self._config_entry.data.get(CONF_ACCESS_TOKEN, "")),
                house_id=_entry_house_id(self._config_entry.data),
                client_id=self._config_entry.data.get(CONF_OPEN_API_CLIENT_ID),
            )
        except Exception as err:
            errors["base"] = flow_error_from_exception("options cloud devices", err)
            self._device_choices = ()

        selected = selected_device_ids_from_options(entry_options(self._config_entry))
        selected = selected_device_ids_from_input(
            {CONF_DEVICE_IMPORT_FILTER_INCLUDE_DEVICES: selected},
            self._device_choices,
        )
        if not selected:
            selected = selected_device_ids_from_input(None, self._device_choices)

        return self.async_show_form(
            step_id="cloud_devices",
            data_schema=cloud_devices_schema(self._device_choices, selected),
            errors=errors,
        )

    async def _handle_filter_dimension(
        self,
        dimension: str,
        user_input: dict[str, Any] | None,
    ) -> FlowResult:
        """处理单个过滤维度，并线性进入下一页."""
        await self._ensure_filter_loaded()
        choices = filter_dimension_choices(self._coordinator_devices(), dimension)
        all_values = [value for value, _label in choices]

        if user_input is not None:
            form_key = f"filter_{dimension}"
            self._filter_selections[dimension] = _selected_values(
                user_input.get(form_key, []),
                all_values,
            )
            return await self._async_next_filter_step(dimension)

        return self.async_show_form(
            step_id=f"filter_{dimension}",
            data_schema=device_filter_schema_fields(
                choices,
                self._filter_selections.get(dimension, all_values),
                dimension=dimension,
            ),
        )

    async def _async_next_filter_step(self, dimension: str) -> FlowResult:
        """进入下一个过滤维度；最后一页后保存过滤配置."""
        try:
            index = DIMENSION_NAMES.index(dimension)
        except ValueError:
            index = len(DIMENSION_NAMES) - 1
        if index + 1 < len(DIMENSION_NAMES):
            return await self._handle_filter_dimension(
                DIMENSION_NAMES[index + 1],
                None,
            )
        return await self._finish_filter_wizard()

    async def _finish_filter_wizard(self) -> FlowResult:
        """完成过滤向导，将选择结果写入 pending_options."""
        self._pending_options = merge_device_import_filter(
            normalize_entry_options(entry_options(self._config_entry)),
            self._filter_selections,
            self._filter_all_choices,
        )
        return await self.async_step_confirm_reload()

    # ── 确认页 ──────────────────────────────────────────────────

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
            if self._pending_entry_data is not None:
                self.hass.config_entries.async_update_entry(
                    self._config_entry,
                    data=self._pending_entry_data,
                )
            return self.async_create_entry(title="", data=self._pending_options)

        current_options = normalize_entry_options(entry_options(self._config_entry))
        pending_options = normalize_entry_options(self._pending_options)
        current_data = self._config_entry.data
        return self.async_show_form(
            step_id=step_id,
            data_schema=options_confirm_schema(),
            description_placeholders={
                "changed_count": str(
                    visible_option_change_count(
                        current_options,
                        pending_options,
                        self._config_entry,
                    )
                    + visible_entry_data_change_count(
                        current_data,
                        self._pending_entry_data,
                        self._config_entry,
                    )
                ),
            },
        )

    # ── 内部工具 ────────────────────────────────────────────────

    def _pending_options_require_reload(self) -> bool:
        """Return whether the pending options require a config entry reload."""
        if self._pending_options is None:
            return False
        if self._pending_entry_data is not None:
            return True
        return options_require_reload(
            normalize_entry_options(entry_options(self._config_entry)),
            normalize_entry_options(self._pending_options),
        )

    async def _ensure_filter_loaded(self) -> None:
        """加载当前设备维度选项，并用“全选”补齐未配置维度."""
        if self._filter_loaded:
            return
        self._filter_loaded = True

        devices = self._coordinator_devices()
        self._filter_all_choices = {}
        for dimension in DIMENSION_NAMES:
            choices = filter_dimension_choices(devices, dimension)
            self._filter_all_choices[dimension] = [value for value, _label in choices]

        stored = current_filter_selections(
            entry_options(self._config_entry),
            self._filter_all_choices,
        )
        self._filter_selections = {}
        for dimension in DIMENSION_NAMES:
            all_values = self._filter_all_choices.get(dimension, [])
            self._filter_selections[dimension] = _selected_values(
                stored.get(dimension, all_values),
                all_values,
            )

    def _coordinator_devices(self) -> Mapping[str, Any]:
        """从 coordinator 获取当前设备数据."""
        domain_data = self.hass.data.get(DOMAIN, {})
        entry_data = domain_data.get(self._config_entry.entry_id, {})
        if not isinstance(entry_data, Mapping):
            return {}
        coordinator = entry_data.get("coordinator")
        if coordinator is None:
            return {}
        for attr in ("data", "devices"):
            value = getattr(coordinator, attr, None)
            if isinstance(value, Mapping):
                return value
        return {}


def _selected_values(value: Any, allowed_values: Sequence[str]) -> list[str]:
    """返回保持表单顺序且只包含当前可选项的选择值."""
    if isinstance(value, str):
        values: Sequence[Any] = [value]
    elif isinstance(value, Sequence):
        values = value
    else:
        values = []
    allowed = set(allowed_values)
    return [text for item in values if (text := str(item).strip()) in allowed]


def _entry_house_id(data: Mapping[str, Any]) -> int:
    """Return a numeric house id for the real-device picker."""
    value = data.get(CONF_HOUSE_ID)
    if value is None:
        raise ValueError("missing house id")
    return int(value)
