# reMarkable Mouse


Transform your reMarkable tablet into a virtual mouse for your Linux desktop! This tool creates a virtual input device that translates pen movements and touches from your reMarkable tablet into mouse events on your computer.

<img src="images/remarkable.png" alt="reMarkable Mouse" width="400"/>

## Features

- ✨ **Hover Detection**: Move the mouse cursor by hovering the pen above the tablet surface
- 🖱️ **Click Detection**: Click by touching the pen to the tablet surface  
- 🎯 **Pressure Sensitivity**: Responsive to pen pressure levels
- 📐 **Aspect Ratio Preservation**: Maintains proper scaling between tablet and screen
- 🎛️ **Configurable Sensitivity**: Adjustable mouse movement sensitivity
- 🔧 **Multiple reMarkable Models**: Supports reMarkable 2 (and probably 1)
- ⚡ **Low Latency**: Real-time pen tracking via SSH connection

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
# Download the script
wget https://raw.githubusercontent.com/valechelaru/remarkable-mouse/refs/heads/main/remarkable_mouse.py
chmod +x remarkable_mouse.py

# Run
python3 remarkable_mouse.py
```

### Option 2: Clone Repository
```bash
git clone https://github.com/valechelaru/remarkable-mouse.git
cd remarkable-mouse
python3 remarkable_mouse.py
```

## Setup

### 1. Enable SSH on reMarkable

On your reMarkable tablet (connect via USB or Wi-Fi):
1. Go to **Settings** → **Help** → **About**
2. Tap on **General Information** 
3. Tap on **Copyrights and Licenses**
5. Note the IP address shown (usually `10.11.99.1` when connected via USB)

## Usage

### Basic Usage
```bash
python3 remarkable_mouse.py
```

### With Custom Options
```bash
# Specify reMarkable IP address
python3 remarkable_mouse.py --host root@192.168.1.100

# Set reMarkable version (1 or 2)
python3 remarkable_mouse.py --remarkable-version 1

# Adjust mouse sensitivity
python3 remarkable_mouse.py --sensitivity 2.0

# Enable verbose output for debugging
python3 remarkable_mouse.py --verbose

# Disable uniform scaling (may cause distortion)
python3 remarkable_mouse.py --no-uniform-scaling
```

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--host` | reMarkable SSH host | `root@10.11.99.1` |
| `--remarkable-version` | reMarkable version (1 or 2) | `2` |
| `--sensitivity` | Mouse sensitivity multiplier | `1.0` |
| `--no-uniform-scaling` | Disable uniform scaling | `False` |
| `--verbose` | Enable verbose output | `False` |

## How It Works

1. **SSH Connection**: Connects to your reMarkable tablet via SSH
2. **Input Reading**: Reads pen input events from `/dev/input/event1` (rM2) or `/dev/input/event0` (rM1)
3. **Virtual Device**: Creates a virtual mouse/pen input device on your Linux system
4. **Event Translation**: Translates reMarkable coordinates to screen coordinates
5. **Input Simulation**: Sends mouse movements, clicks, and hover events to your system

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

## Roadmap

- [x] X11 support (tested and working)
- [x] Wayland support (tested and working)
- [ ] Smoothing of cursor movement (zig zagging)
- [ ] Gnome appindicator support
- [ ] GUI configuration tool
- [ ] Windows support
- [ ] macOS support
- [ ] pip package for easy installation
- [ ] reMarkable paper pro support (?)
