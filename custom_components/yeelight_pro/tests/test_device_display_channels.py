"""Device channel display helper tests."""

from __future__ import annotations

from custom_components.yeelight_pro.device_display import (
    channel_name_label,
    switch_channel_count_hint,
)


def test_channel_name_label_humanizes_indexed_switch_channels() -> None:
    """多键开关通道名应使用友好中文名称."""
    assert channel_name_label(index=1) == "按键 1"
    assert channel_name_label(index=2) == "按键 2"
    assert channel_name_label(index=7) == "按键 7"
    assert channel_name_label(index=8) == "按键 8"
    assert channel_name_label(index=12) == "按键 12"


def test_channel_name_label_uses_positional_names_for_known_switches() -> None:
    """官方产品证据证明双键/三键时，应显示左中右而不是 1/2/3."""
    assert channel_name_label(
        index=1,
        device_payload={"pid": 854018, "name": "厨房开关"},
    ) == "左键"
    assert channel_name_label(
        index=2,
        device_payload={"pid": 854018, "name": "厨房开关"},
    ) == "右键"
    assert channel_name_label(
        index=2,
        device_payload={"pid": 854019, "name": "玄关开关"},
    ) == "中键"
    assert channel_name_label(
        index=3,
        device_payload={"pid": 854019, "name": "玄关开关"},
    ) == "右键"


def test_channel_name_label_preserves_real_component_name() -> None:
    """官方组件名如左键/右键应优先于索引 fallback."""
    assert channel_name_label(index=1, component={"name": "左键"}) == "左键"
    assert channel_name_label(index=2, component={"name": "switch_2"}) == "按键 2"
    assert channel_name_label(index=3, component={"name": "3"}) == "按键 3"
    assert channel_name_label(index=4, component={"name": "按键4"}) == "按键 4"
    assert channel_name_label(index=1, component={"name": "一键"}) == "按键 1"
    assert channel_name_label(index=2, component={"name": "二键"}) == "按键 2"


def test_channel_name_label_humanizes_generated_names_without_component_index() -> None:
    """上游只给 name/desc=1/2/3 时，也不能直接在 HA 显示裸数字."""
    assert channel_name_label(
        index=None,
        component={"component_id": "switch_control", "name": "1"},
    ) == "按键 1"
    assert channel_name_label(
        index=None,
        component={"component_id": "switch_control", "desc": "二键"},
    ) == "按键 2"
    assert channel_name_label(
        index=None,
        component={"component_id": "switch_control", "name": "三键"},
        device_payload={"pid": 854019, "name": "玄关开关"},
    ) == "右键"


def test_channel_name_label_humanizes_generated_component_ids() -> None:
    """button/key/scene_button 等组件 ID 不应直接显示成 1/2/3."""
    assert channel_name_label(index=None, component={"component_id": "button_1"}) == "按键 1"
    assert channel_name_label(index=None, component={"component_id": "key_2"}) == "按键 2"
    assert (
        channel_name_label(index=None, component={"component_id": "scene_button_3"})
        == "按键 3"
    )
    assert channel_name_label(
        index=None,
        component={"component_id": "scene_control_button_2"},
        device_payload={"pid": 8390657, "name": "玄关情景面板"},
    ) == "中键"


def test_channel_name_label_humanizes_indexed_component_suffixes() -> None:
    """switch_1/curtain_1 等带索引组件 ID 不应直接暴露到实体名称."""
    for component_id in (
        "air_conditioner_1",
        "curtain_1",
        "human_sensor_1",
        "sensor_1",
        "switch_1",
    ):
        assert channel_name_label(
            index=None,
            component={"component_id": component_id},
            device_payload={"pid": 854018, "name": "厨房开关"},
        ) == "左键"


def test_channel_name_label_replaces_generated_chinese_names_for_known_switches() -> None:
    """云端一键/二键/三键这类生成名应按官方能力证据换成方位名."""
    assert channel_name_label(
        index=1,
        component={"name": "一键"},
        device_payload={"pid": 854018, "name": "厨房开关"},
    ) == "左键"
    assert channel_name_label(
        index=2,
        component={"desc": "二键"},
        device_payload={"pid": 854018, "name": "厨房开关"},
    ) == "右键"
    assert channel_name_label(
        index=3,
        component={"name": "三键"},
        device_payload={"pid": 854019, "name": "玄关开关"},
    ) == "右键"
    assert channel_name_label(
        index=1,
        component={"name": "无线开关通道"},
        device_payload={"pid": 854018, "name": "厨房开关"},
    ) == "左键"
    assert channel_name_label(
        index=2,
        component={"desc": "无线开关通道"},
        device_payload={"pid": 854018, "name": "厨房开关"},
    ) == "右键"


def test_channel_name_label_does_not_infer_positions_from_raw_params_only() -> None:
    """裸运行时 N-p 只证明实体存在，不证明它们有物理左中右语义."""
    payload = {
        "name": "墙壁开关1",
        "params": {"1-p": True, "2-p": False, "3-p": True},
    }

    assert switch_channel_count_hint(payload) is None
    assert channel_name_label(
        index=1,
        component={"name": "一键"},
        device_payload=payload,
    ) == "按键 1"
    assert channel_name_label(
        index=2,
        component={"name": "二键"},
        device_payload=payload,
    ) == "按键 2"
    assert channel_name_label(
        index=3,
        component={"name": "三键"},
        device_payload=payload,
    ) == "按键 3"


def test_channel_name_label_infers_positions_from_openapi_subdevices() -> None:
    """OpenAPI 子设备已证明多按键时，不应再显示 1/2/3 或泛化按键名."""
    payload = {
        "name": "按键",
        "subDeviceList": [
            {"index": 1, "name": "scene control button", "category": "scene_panel"},
            {"index": 2, "name": "scene control button", "category": "scene_panel"},
            {"index": 3, "name": "scene control button", "category": "scene_panel"},
        ],
    }

    assert switch_channel_count_hint(payload) == 3
    assert channel_name_label(index=1, component={"name": "1"}, device_payload=payload) == "左键"
    assert channel_name_label(index=2, component={"name": "2"}, device_payload=payload) == "中键"
    assert channel_name_label(index=3, component={"name": "3"}, device_payload=payload) == "右键"


def test_channel_name_label_uses_openapi_wireless_switch_channel_evidence() -> None:
    """OpenAPI 无 pid 但子设备声明无线开关通道时，应显示按键语义."""
    payload = {
        "name": "四键",
        "category": "relay_switch",
        "subDeviceList": [
            {"index": index, "name": "wireless switch channel", "category": "relay_switch"}
            for index in range(1, 5)
        ],
    }

    assert switch_channel_count_hint(payload) == 4
    assert channel_name_label(
        index=1,
        component={"name": "wireless switch channel", "category": "relay_switch"},
        device_payload=payload,
    ) == "按键 1"
    assert channel_name_label(
        index=4,
        component={"name": "wireless switch channel", "category": "relay_switch"},
        device_payload=payload,
    ) == "按键 4"


def test_channel_name_label_does_not_position_generic_relays() -> None:
    """纯多路继电器没有物理左右语义时，按输出组件显示回路语义."""
    payload = {
        "name": "多路继电器",
        "category": "relay_switch",
        "params": {"1-p": True, "2-sp": False},
    }

    assert switch_channel_count_hint(payload) is None
    assert channel_name_label(index=1, device_payload=payload) == "回路 1"
    assert channel_name_label(index=2, device_payload=payload) == "回路 2"


def test_channel_name_label_preserves_key_labels_for_event_input_components() -> None:
    """情景面板和旋钮属于输入组件，fallback 仍显示按键语义."""
    assert channel_name_label(
        index=1,
        component={"component_id": "scene_button_1", "category": "scene_panel"},
    ) == "按键 1"
    assert channel_name_label(
        index=2,
        component={"component_id": "knob_2", "category": "knob_switch"},
    ) == "按键 2"


def test_channel_name_label_uses_explicit_io_type_semantics() -> None:
    """组件 io_type 明确输入/输出时，优先于大类 fallback 显示键或路."""
    assert channel_name_label(
        index=1,
        component={
            "component_id": "relay_input_1",
            "category": "relay_switch",
            "io_type": "input",
        },
    ) == "按键 1"
    assert channel_name_label(
        index=2,
        component={"component_id": "channel_2", "io": "output"},
    ) == "回路 2"


def test_channel_name_label_replaces_generated_light_and_switch_component_names() -> None:
    """运行时 schema 只给泛化组件名时，应回退到可区分的通道名."""
    assert channel_name_label(
        index=1,
        component={"component_id": "light_1", "name": "switch light", "io": "output"},
    ) == "回路 1"
    assert channel_name_label(
        index=2,
        component={"component_id": "switch_2", "name": "开关组件", "category": "switch"},
    ) == "回路 2"


def test_product_catalog_channel_count_overrides_stale_runtime_channels() -> None:
    """官方产品构成明确双键时，运行时残留第三路不能阻止 stale 清理."""
    payload = {
        "pid": 854018,
        "name": "厨房开关",
        "params": {"1-p": True, "2-p": False, "3-p": True},
    }

    assert switch_channel_count_hint(payload) == 2
    assert channel_name_label(index=1, device_payload=payload) == "左键"
    assert channel_name_label(index=2, device_payload=payload) == "右键"


def test_switch_channel_count_hint_uses_official_product_evidence_not_user_name() -> None:
    """通道路数只能来自产品构成、官方型号或结构化运行时能力证据."""
    assert switch_channel_count_hint({"pid": 854018, "name": "厨房双键开关"}) == 2
    assert switch_channel_count_hint({
        "name": "厨房双键开关",
        "params": {"1-p": True, "2-p": False, "3-p": True},
    }) is None
    assert switch_channel_count_hint({"pid": 854019}) == 3
    assert switch_channel_count_hint({"productName": "三键智能开关"}) is None
    assert switch_channel_count_hint({"pid": 8390656, "name": "走廊面板"}) == 8
    assert switch_channel_count_hint({"model": "公开测试情景开关"}) is None
    assert switch_channel_count_hint({"pid": 1509378, "name": "走廊面板"}) == 4
    assert switch_channel_count_hint({"name": "普通继电器"}) is None
