[繁體中文](README.zh-Hant.md) | **English**

# IR Honeycomb Blind

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue.svg)](https://www.home-assistant.io/)

A Home Assistant custom integration for controlling **Top-Down Bottom-Up (TDBU) Honeycomb Blinds** via any Home Assistant IR remote entity. Tested with Broadlink.

## Overview

### What is a TDBU Honeycomb Blind?

A TDBU honeycomb blind has two independently movable rails:
- **Top rail**: moves down from the top to provide shade
- **Bottom rail**: moves up from the bottom to open the blind

The fabric between the two rails can be flexibly positioned to cover any portion of the window.

### Control Modes

This integration offers two cover control modes (configurable in settings):

#### Mode 1: Separate Controls

| Entity | Type | Function | Description |
|--------|------|----------|-------------|
| `cover.xxx_position` | Cover | Bottom rail position | 0 (fully closed) ~ 100 (fully open) |
| `cover.xxx_ratio` | Cover | Top rail coverage ratio | 0 (no coverage) ~ 100 (full coverage) |

#### Mode 2: Combined Cover with Tilt (Default)

| Entity | Type | Function | Description |
|--------|------|----------|-------------|
| `cover.xxx_blind` | Cover | Unified control | Position = bottom rail, Tilt = top rail ratio |

This mode is ideal for platforms like HomeKit that support Window Covering + Tilt, allowing both rails to be controlled from a single entity.

#### Shared Entities

| Entity | Type | Function | Description |
|--------|------|----------|-------------|
| `button.xxx_calibrate` | Button | Calibration | Press to run calibration |
| `binary_sensor.xxx_moving` | Binary Sensor | Moving status | Whether the blind is currently moving |
| `sensor.xxx_moving_rail` | Sensor | Moving rail | Which rail is moving (top / bottom / none) |
| `sensor.xxx_time_remaining` | Sensor | Time remaining | Estimated remaining movement time |
| `sensor.xxx_last_calibration` | Sensor | Last calibration | Timestamp of the last calibration |

**Position Model:**
- `POS` = bottom rail height position
- `R` = top rail coverage ratio (from the top)
- Top rail position = `100 - (100 - POS) * R / 100`

**Examples:**
| R | POS | Effect |
|---|-----|--------|
| 0 | 0 | Fully open (initial state after calibration) |
| 100 | 0 | Fully covered |
| 50 | 50 | Bottom half open, top half 50% covered |

## Features

- **UI Configuration**: Set up entirely through the Home Assistant UI, no YAML editing required
- **Flexible Control Modes**: Choose between separate (Position + Ratio) or combined (Position + Tilt) mode
- **HomeKit Support**: Combined mode supports Window Covering + Tilt for seamless HomeKit control
- **Real-time Position Updates**: Shows estimated position in real-time during movement (toggleable)
- **Smart Collision Avoidance**: Automatically detects and clears the path before moving to prevent rail collisions
- **Debounce**: Rapid slider adjustments are coalesced into a single command
- **Interruption Estimation**: When movement is interrupted, the current position is estimated from elapsed time
- **Linked Adjustment**: After moving the bottom rail, the top rail is automatically adjusted to maintain the ratio
- **Multi-blind Support**: Each blind operates independently and can be controlled simultaneously
- **Shared Remote**: Multiple blinds can share a single IR remote; IR commands are automatically queued
- **State Persistence**: Position state is restored after Home Assistant restarts
- **One-tap Calibration**: Each blind has a calibration button to reset position tracking
- **Live Settings Reload**: Configuration changes take effect immediately without restart
- **Multilingual**: Supports English and Traditional Chinese

## Requirements

- **Home Assistant** 2024.1.0 or later
- **IR Remote Integration**: Any integration that provides a `remote` entity (e.g., Broadlink, Tuya, Xiaomi, SwitchBot, SmartIR)
- **IR Codes**: Learned IR codes for the 5 blind remote buttons (format depends on your remote integration)

### RF Support (433 / 315 MHz)

If you use a **Broadlink RM Pro / RM4 Pro** series, this integration also supports **RF (433 / 315 MHz) controlled blinds** with no additional configuration. The `remote.send_command` service automatically determines whether to transmit via IR or RF based on the learned code content — simply fill in the learned RF codes in the same `b64:` format.

### How to Obtain IR / RF Codes

#### IR Codes

1. Go to **Developer Tools > Services** in Home Assistant
2. Call the `remote.learn_command` service, targeting your Broadlink device
3. Follow the prompts and press the remote button
4. After learning, the IR code will be stored in the Broadlink integration
5. You can also use third-party tools (e.g., Broadlink Manager) to export Base64 IR codes

#### RF Codes (RM Pro / RM4 Pro only)

1. Go to **Developer Tools > Services** in Home Assistant
2. Call the `remote.learn_command` service with `command_type: rf`
3. **Frequency scan**: Hold down the remote button until the device beeps (scanning for RF frequency)
4. **Code learning**: Press the remote button briefly to learn the specific code
5. The learned RF code will be in the same `b64:` format and can be used directly

**Buttons to learn:**
- T-UP: Top rail up
- T-DN: Top rail down
- B-UP: Bottom rail up
- B-DN: Bottom rail down
- STOP: Stop

## Installation

### Option 1: Via HACS (Recommended)

1. Make sure [HACS](https://hacs.xyz/) is installed
2. Click the three-dot menu in the top right corner of HACS
3. Select **Custom repositories**
4. Enter this repository URL and select category **Integration**
5. Click **Add**
6. Search for **IR Honeycomb Blind** in the HACS integrations page and install
7. Restart Home Assistant

### Option 2: Manual Installation

1. Download the latest release from this repository
2. Copy the `custom_components/ir_honeycomb_blind` folder to your Home Assistant `custom_components` directory
   ```
   <config_dir>/
   └── custom_components/
       └── ir_honeycomb_blind/
           ├── __init__.py
           ├── manifest.json
           ├── config_flow.py
           ├── cover.py
           ├── sensor.py
           ├── binary_sensor.py
           ├── button.py
           ├── coordinator.py
           ├── const.py
           ├── strings.json
           ├── services.yaml
           ├── hacs.json
           └── translations/
               ├── en.json
               └── zh-Hant.json
   ```
3. Restart Home Assistant

## Configuration

1. Go to **Settings > Devices & Services > Add Integration**
2. Search for **IR Honeycomb Blind**
3. Fill in the configuration form:

| Field | Description |
|-------|-------------|
| Blind Name | A unique name for this blind |
| Remote Entity | Select the remote entity to use |
| IR Codes (T-UP/T-DN/B-UP/B-DN/STOP) | Paste IR codes (Broadlink uses `b64:` format) |
| Full Open Time | Seconds for the blind to go from fully closed to fully open |
| Full Close Time | Seconds for the blind to go from fully open to fully closed |
| IR Repeat Count | Number of times to repeat each IR command (recommended: 3) |
| IR Repeat Delay | Delay between repeated commands in seconds (recommended: 0.3) |
| Debounce Delay | Time to wait for user input to stabilize (recommended: 1.0) |
| Real-time Position Update | Show estimated position in real-time during movement |
| Separate Position/Ratio Covers | Create separate Position and Ratio cover entities |
| Combined Cover with Tilt | Create a single cover entity using Position + Tilt |

4. Click **Submit** to finish

## Calibration

### Option 1: Calibration Button (Recommended)

Each blind automatically gets a **Calibrate button** (`button.xxx_calibrate`):

1. Find the calibration button on the Home Assistant dashboard or device page
2. Press the button to run calibration
3. After calibration, position resets to: POS=0, R=0 (fully open)

### Option 2: Service Call

Call `ir_honeycomb_blind.calibrate` via **Developer Tools > Services**:

**Parameters:**
- `entry_id` (optional): The config entry ID of the blind to calibrate. Leave empty to calibrate all blinds.

### When to Calibrate

- After first installation
- When position tracking becomes inaccurate
- After manually using the physical remote

## Troubleshooting

### IR commands not working
- Verify the remote device is properly configured and online
- Confirm IR codes are in the correct format for your remote integration
- Try increasing the IR repeat count
- Ensure there are no obstacles between the IR transmitter and the blind

### Position is inaccurate
- Re-measure the full open/close times and ensure the values are accurate
- Press the calibration button to reset position
- Avoid using the physical remote (it causes tracking drift)

### Multiple blinds interfering with each other
- Ensure each blind uses different IR codes
- If sharing the same IR remote, IR commands are automatically queued; please be patient

## License

MIT License
