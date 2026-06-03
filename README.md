# Yeelight Pro

[English](README.md) | [中文](README_zh.md)

Yeelight Pro integration for Home Assistant. Supports both cloud and private deployment modes.

## Features

- ✅ Cloud and private deployment support
- ✅ Automatic device discovery and state synchronization
- ✅ Real-time event updates via SSE
- ✅ 14 entity platforms supported
- ✅ Complete device control capabilities

## Installation

### HACS Installation (Recommended)

1. Open HACS
2. Search for "Yeelight Pro"
3. Click Install
4. Restart Home Assistant

### Manual Installation

1. Download the latest release
2. Extract to `custom_components/yeelight_pro/`
3. Restart Home Assistant

## Configuration

### Cloud Mode

1. Go to Settings → Devices & Services → Add Integration
2. Search for "Yeelight Pro"
3. Select "Yeelight Pro Cloud"
4. Enter Access Token
5. Select House
6. Complete configuration

### Private Deployment Mode

1. Go to Settings → Devices & Services → Add Integration
2. Search for "Yeelight Pro"
3. Select "Private Deployment (Lucore)"
4. Enter server address (e.g., `192.168.1.100:8080`)
5. Enter Access Token
6. Enter House ID
7. Complete configuration

## Supported Device Types

| Device Type | Entity Platform | Features |
| --- | --- | --- |
| Light | light | Brightness, color temperature, RGB control |
| Switch | switch | On/Off control |
| Socket | switch | On/Off control |
| Fan | fan | Speed, oscillation control |
| Curtain | cover | Position control |
| Air Conditioner | climate | Temperature, mode control |
| Door Lock | lock | Lock/Unlock |
| Sensor | sensor | Temperature, humidity, illuminance |
| Motion Sensor | binary_sensor | Motion detection |
| Door/Window Sensor | binary_sensor | Contact status |
| Remote Control | event | Button events |
| Button | button | Button operations |
| Number | number | Number settings |
| Select | select | Option selection |
| Text | text | Text input |

## Services

### yeelight_pro.assign_areas

Batch assign areas to devices.

**Parameters**:

- `devices`: List of device IDs
- `area_id`: Area ID

### yeelight_pro.set_scene

Activate a scene.

**Parameters**:

- `scene_id`: Scene ID

## Advanced Configuration

### Custom Scan Interval

Default scan interval is 30 seconds. Can be modified in configuration options.

### Debug Logging

Add to `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.yeelight_pro: debug
```

## Troubleshooting

### Cannot Connect

1. Check network connection
2. Verify server address and port
3. Check if Access Token is valid

### Devices Not Showing

1. Check if devices are online
2. Check if devices are in the selected house
3. Check logs for detailed error information

### Control Failed

1. Check if devices are online
2. Check if you have permission to control the device
3. Check logs for detailed error information

## Support

- [GitHub Issues](https://github.com/Yeelight/ha_yeelight_pro/issues)
- [Documentation](https://github.com/Yeelight/ha_yeelight_pro)

## License

MIT License
