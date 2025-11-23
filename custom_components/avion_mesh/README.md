# Avi-on Mesh Mesh - Home Assistant Custom Integration

A direct Home Assistant integration for Avi-on mesh lighting systems that bypasses MQTT and connects directly to your lights.

## Features

- 🔌 Mesh connection to Avi-on mesh network (no MQTT broker required)
- 💡 Full control of dimmable lights with brightness adjustment
- 🌡️ Color temperature support for compatible devices
- 🏠 Seamless Home Assistant integration
- ⚡ Rapid dimming detection (double-tap dimming)
- 📱 Control via Home Assistant UI, automations, and scripts

## Installation

### 1. Install via HACS

1. Open Home Assistant
2. Go to **Settings** → **Devices & Services** → **Custom repositories**
3. Add this repository: `https://github.com/oyvindkinsey/avionmqtt`
4. Search for "Avi-on Mesh Mesh" in HACS and install it
5. Restart Home Assistant

### 2. Configuration

#### Option A: UI Configuration (Recommended)

1. Go to **Settings** → **Devices & Services** → **Create Automation**
2. Select "Avi-on Mesh Mesh"
3. Enter your Avi-on account credentials (email and password)
4. Specify the path to your settings YAML file (e.g., `/config/avion_settings.yaml`)
5. Click "Create"

#### Option B: YAML Configuration

Add the following to your `configuration.yaml`:

```yaml
avion_direct:
  username: your-email@example.com
  password: your-password
  settings_yaml: /config/avion_settings.yaml
```

### 3. Settings YAML File

Create a `avion_settings.yaml` file with your mesh configuration:

```yaml
# Example avion_settings.yaml
devices:
  import: true
  exclude: []
  exclude_in_group: true

groups:
  import: true
  exclude: []

all:
  name: All Lights

capabilities_overrides:
  dimming: []
  color_temp: []
```

## Configuration Options

### Settings YAML

- **devices.import**: Enable/disable importing individual devices
- **devices.exclude**: List of device PIDs to exclude
- **devices.exclude_in_group**: Hide devices that are members of groups
- **groups.import**: Enable/disable importing groups
- **groups.exclude**: List of group PIDs to exclude
- **all.name**: Name for the "All Lights" group
- **capabilities_overrides**: Override device capabilities (dimming, color_temp)

## Supported Devices

The integration automatically detects and supports:

- Lamp Dimmer (90)
- Recessed Downlight (RL) (93)
- Light Adapter (94)
- Smart Dimmer (97)
- Smart Bulb A19 (134)
- Surface Downlight (137)
- MicroEdge (162)
- Smart Switch (167)

## Features

### Light Control

- Turn lights on/off
- Adjust brightness (for dimmable devices)
- Adjust color temperature (for compatible devices)

### Rapid Dimming Detection

When you press a dimmer button twice rapidly (within 750ms):

- **Incrementing**: Sends full brightness (255)
- **Decrementing**: Sends minimum brightness (5)

## Troubleshooting

### Integration won't initialize

- Verify your Avi-on credentials are correct
- Check that the settings YAML file path is accessible
- Look for errors in the Home Assistant logs

### Lights not appearing

- Ensure `import: true` is set for devices/groups in settings YAML
- Verify the devices are properly paired to your mesh network
- Check the device exclusion list

### Commands not working

- Verify the BLE mesh is reachable (lights are in range)
- Check Home Assistant logs for connection errors
- Try restarting the integration

## Logs

Enable debug logging for troubleshooting:

```yaml
logger:
  logs:
    custom_components.avion_direct: debug
    avionmqtt: debug
```

## License

See LICENSE in the main repository.
