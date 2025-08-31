# reMarkable Mouse & Keyboard

Transform your reMarkable tablet into a virtual mouse and keyboard for your Linux desktop! This toolkit includes two tools:
- **reMarkable Mouse**: Creates a virtual mouse device that translates pen movements and touches into mouse events
- **reMarkable Keyboard**: Creates a virtual keyboard device for the reMarkable Type Folio keyboard

<img src="images/remarkable.png" alt="reMarkable Mouse" width="400"/>

## Features

### Mouse Features
- ✨ **Hover Detection**: Move the mouse cursor by hovering the pen above the tablet surface
- 🖱️ **Click Detection**: Click by touching the pen to the tablet surface  
- 🎯 **Pressure Sensitivity**: Responsive to pen pressure levels
- 📐 **Aspect Ratio Preservation**: Maintains proper scaling between tablet and screen
- 🎛️ **Configurable Sensitivity**: Adjustable mouse movement sensitivity
- � **Orientation Control**: Default flipped orientation for Type Folio compatibility, with CLI option to restore original
- �🔧 **Multiple reMarkable Models**: Supports reMarkable 2 (and probably 1)
- ⚡ **Low Latency**: Real-time pen tracking via SSH connection

### Keyboard Features
- ⌨️ **Full Keyboard Support**: Complete Type Folio keyboard functionality
- 🔧 **reMarkable 2 Only**: Requires Type Folio (reMarkable 2.0 only)
- ⚡ **Direct Key Mapping**: All keys mapped directly to Linux input events

## Requirements

### System Requirements
- **Linux** with **Wayland or X11** display server (tested under Ubuntu)
- **Ubuntu 18.04+** or equivalent Linux distribution
- **SSH access** to your reMarkable tablet
- **Root privileges** or proper udev rules for input device creation

### Dependencies
Install the required system package (pip version might not work):
```bash
sudo apt install python3-evdev
```

## Installation

### Option 1: Direct Download
```bash
# Download the scripts
wget https://raw.githubusercontent.com/valechelaru/remarkable-mouseNkeyboard/refs/heads/main/remarkable_mouse.py
wget https://raw.githubusercontent.com/valechelaru/remarkable-mouseNkeyboard/refs/heads/main/remarkable_keyboard.py
chmod +x remarkable_mouse.py remarkable_keyboard.py

# Run mouse
python3 remarkable_mouse.py

# Run keyboard (in separate terminal)
python3 remarkable_keyboard.py
```

### Option 2: Clone Repository
```bash
git clone https://github.com/valechelaru/remarkable-mouseNkeyboard.git
cd remarkable-mouseNkeyboard

# Run mouse
python3 remarkable_mouse.py

# Run keyboard (in separate terminal)
python3 remarkable_keyboard.py
```

## Setup

### 1. Enable SSH on reMarkable

On your reMarkable tablet (connect via USB or Wi-Fi):
1. Go to **Settings** → **Help** → **About**
2. Tap on **General Information** 
3. Tap on **Copyrights and Licenses**
5. Note the IP address shown (usually `10.11.99.1` when connected via USB)

## Usage

### Mouse Usage
```bash
# Basic usage
python3 remarkable_mouse.py

# With custom options
python3 remarkable_mouse.py --host root@192.168.1.100 --sensitivity 2.0 --verbose

# Restore original orientation (default is flipped for Type Folio)
python3 remarkable_mouse.py --flip
```

### Keyboard Usage
```bash
# Basic usage
python3 remarkable_keyboard.py

# With verbose output
python3 remarkable_keyboard.py --verbose --host root@192.168.1.100
```

### Command Line Options

#### Mouse Options
| Option | Description | Default |
|--------|-------------|---------|
| `--host` | reMarkable SSH host | `root@10.11.99.1` |
| `--remarkable-version` | reMarkable version (1 or 2) | `2` |
| `--sensitivity` | Mouse sensitivity multiplier | `1.0` |
| `--flip` | Restore original orientation | `False` (flipped by default) |
| `--no-uniform-scaling` | Disable uniform scaling | `False` |
| `--verbose` | Enable verbose output | `False` |

#### Keyboard Options
| Option | Description | Default |
|--------|-------------|---------|
| `--host` | reMarkable SSH host | `root@10.11.99.1` |
| `--verbose` | Enable verbose output | `False` |

## How It Works

### Mouse
1. **SSH Connection**: Connects to your reMarkable tablet via SSH
2. **Input Reading**: Reads pen input events from `/dev/input/event1` (rM2) or `/dev/input/event0` (rM1)
3. **Virtual Device**: Creates a virtual mouse/pen input device on your Linux system
4. **Event Translation**: Translates reMarkable coordinates to screen coordinates with flipped orientation for Type Folio compatibility
5. **Input Simulation**: Sends mouse movements, clicks, and hover events to your system

### Keyboard
1. **SSH Connection**: Connects to your reMarkable tablet via SSH
2. **Input Reading**: Reads keyboard events from `/dev/input/event3` (Type Folio)
3. **Virtual Device**: Creates a virtual keyboard input device on your Linux system
4. **Event Pass-through**: Directly forwards all keyboard events to your system

## Pen Behavior

- **Hovering**: Move pen above tablet surface → cursor moves without clicking
- **Touching**: Touch pen to tablet surface → left mouse button press
- **Pen Button**: Hold pen button while touching → right mouse button press
- **Dragging**: Keep pen pressed while moving → click and drag

## Security Notes

- SSH connection uses your system's SSH keys for authentication
- No data is stored or transmitted beyond the direct SSH connection
- The virtual input device is removed when the program exits

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Inspired by the [pipes and paper](https://gitlab.com/afandian/pipes-and-paper) implementation of https://gitlab.com/jwass1 and by the reMarkable community's reverse engineering efforts
- Built using the excellent `python3-evdev` library

## Known/Unknown Issues

- Tested and working on both Wayland and X11 under Ubuntu
- Zig zagging behaviour when fast movements are made
- Has not been tested on multiple monitors
- Has not been tested with a remarkable 1
- Has not been tested with reMarkable paper pro
- Some keys on the german type folio do not map correctly (ü, ß)

## Roadmap

- [x] X11 support (tested and working)
- [x] Wayland support (tested and working)
- [x] Keyboard support for Type Folio
- [ ] Fix key mapping issues (ü, ß)
- [ ] Smoothing of cursor movement (zig zagging)
- [ ] Gnome appindicator support
- [ ] GUI configuration tool
- [ ] Windows support
- [ ] macOS support
- [ ] pip package for easy installation
- [ ] reMarkable paper pro support (?)
