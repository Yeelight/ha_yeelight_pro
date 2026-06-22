# Automation Examples

更新时间：2026-06-22

## 说明

以下示例用于说明 `ha_yeelight_pro` 实体在 Home Assistant 自动化中的典型用法。示例里的 entity id 是占位符，实际使用时请替换为用户环境中的实体。

## 灯光：人体传感器触发开灯

```yaml
alias: Yeelight Pro motion turns on hallway light
mode: restart
trigger:
  - platform: state
    entity_id: binary_sensor.yeelight_pro_hallway_motion
    to: "on"
action:
  - service: light.turn_on
    target:
      entity_id: light.yeelight_pro_hallway
    data:
      brightness_pct: 60
```

## 灯光：无人在场后延时关灯

```yaml
alias: Yeelight Pro hallway light off after no motion
mode: restart
trigger:
  - platform: state
    entity_id: binary_sensor.yeelight_pro_hallway_motion
    to: "off"
    for: "00:05:00"
action:
  - service: light.turn_off
    target:
      entity_id: light.yeelight_pro_hallway
```

## 窗帘：日落后关闭

```yaml
alias: Yeelight Pro curtain closes after sunset
trigger:
  - platform: sun
    event: sunset
action:
  - service: cover.close_cover
    target:
      entity_id: cover.yeelight_pro_living_room_curtain
```

## 情景面板：事件触发场景

```yaml
alias: Yeelight Pro scene panel event
trigger:
  - platform: event
    event_type: yeelight_pro_device_event
    event_data:
      event_type: click
action:
  - service: button.press
    target:
      entity_id: button.yeelight_pro_evening_scene
```

## 温控：温度过高时切换模式

```yaml
alias: Yeelight Pro climate cooling assist
trigger:
  - platform: numeric_state
    entity_id: sensor.yeelight_pro_room_temperature
    above: 28
action:
  - service: climate.set_hvac_mode
    target:
      entity_id: climate.yeelight_pro_room
    data:
      hvac_mode: cool
```

## 手动刷新：维护自动化

```yaml
alias: Yeelight Pro nightly refresh
trigger:
  - platform: time
    at: "03:30:00"
action:
  - service: yeelight_pro.refresh
```

## 注意事项

- `yeelight_pro_device_event` 事件 payload 只暴露脱敏后的 `source_device_id`、`component_id`、`event_type` 和 `event_attributes`。
- 自动化不应依赖 token、house id、device id、MAC、IP 或原始 payload。
- 如果实体来自 HACS/custom 集成，未来迁移到 Core 后应确认 entity id 是否保持稳定。
