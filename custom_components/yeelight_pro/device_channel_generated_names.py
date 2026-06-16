"""Generated channel-name detection for Yeelight Pro devices."""

from __future__ import annotations

CHANNEL_NUMERAL_LABELS = {
    1: ("一键", "1键"),
    2: ("二键", "2键"),
    3: ("三键", "3键"),
    4: ("四键", "4键"),
    5: ("五键", "5键"),
    6: ("六键", "6键"),
    7: ("七键", "7键"),
    8: ("八键", "8键"),
    9: ("九键", "9键"),
    10: ("十键", "10键"),
    11: ("十一键", "11键"),
    12: ("十二键", "12键"),
}


def looks_like_generated_channel_name(
    value: str,
    index: int | None,
    *,
    positional_context: bool = False,
) -> bool:
    """Return true for generated labels that should be replaced."""
    text = _normal_name(value)
    generated = {
        "button",
        "key",
        "relay_switch",
        "scene_button",
        "scene_control_button",
        "switch",
        "switch_control",
        "wireless_switch_channel",
        "开关",
        "按键",
        "情景按键",
        "无线开关通道",
    }
    if positional_context:
        generated.update({"wireless_switch_channel", "无线开关通道"})
    if index is not None:
        generated.update(_indexed_generated_names(index))
    return text in generated


def generated_channel_name_index(value: str) -> int | None:
    """Return channel index from generated labels such as 1/一键/按键1."""
    text = value.strip()
    if text.isdecimal() and int(text) > 0:
        return int(text)
    normalized = _normal_name(text)
    for index, labels in CHANNEL_NUMERAL_LABELS.items():
        generated = {
            f"按键{index}",
            f"按键_{index}",
            f"第{index}键",
            f"第_{index}_键",
            f"键{index}",
            f"键_{index}",
        }
        generated.update(_normal_name(label) for label in labels)
        if normalized in generated:
            return index
    return None


def _indexed_generated_names(index: int) -> set[str]:
    generated = {
        str(index),
        f"air_conditioner_{index}",
        f"按键{index}",
        f"按键_{index}",
        f"第{index}键",
        f"第_{index}_键",
        f"键{index}",
        f"键_{index}",
        f"button_{index}",
        f"channel_{index}",
        f"curtain_{index}",
        f"fan_{index}",
        f"human_sensor_{index}",
        f"key_{index}",
        f"knob_{index}",
        f"switch_{index}",
        f"relay_switch_{index}",
        f"relay_input_{index}",
        f"sensor_{index}",
        f"scene_button_{index}",
        f"scene_control_button_{index}",
        f"switch_control_{index}",
        f"wireless_switch_channel_{index}",
    }
    generated.update(_normal_name(label) for label in CHANNEL_NUMERAL_LABELS.get(index, ()))
    return generated


def _normal_name(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


__all__ = [
    "CHANNEL_NUMERAL_LABELS",
    "generated_channel_name_index",
    "looks_like_generated_channel_name",
]
