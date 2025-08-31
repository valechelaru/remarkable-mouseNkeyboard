#!/usr/bin/env python3
"""
reMarkable Mouse - Virtual Mouse from reMarkable Tablet

This program connects to a reMarkable tablet via SSH and creates a virtual mouse
input device on Linux desktops (Wayland/X11). It processes pen data from the reMarkable
and translates it into Linux mouse events with hover detection and pressure sensitivity.

Features:
- Hover detection (pen movement without touching surface)
- Click detection when pen touches the surface (pressure > 0)
- Pressure sensitivity support
- Configurable mouse sensitivity
- Support for reMarkable 1.0 and 2.0
- Proper aspect ratio scaling
- Works with Wayland and X11 desktop environments
- Default flipped orientation (180 degrees) with option to restore original

Requirements:
- Linux with Wayland or X11 display server (tested under Ubuntu)
- python3-evdev system package (install with: sudo apt install python3-evdev)
- SSH access to reMarkable tablet
- Root privileges to create input devices (or proper udev rules)

Usage:
    python3 remarkable_mouse.py [--host REMARKABLE_IP] [--remarkable-version VERSION] [--flip]
    
Note: Default orientation is now flipped 180 degrees. Use --flip/-f to restore original orientation.
"""

import asyncio
import argparse
import os
import signal
import struct
import subprocess
import sys
from typing import Optional, Tuple

# Import evdev with error handling
try:
    import evdev
    from evdev import UInput
    from evdev import ecodes
    from evdev import AbsInfo
except ImportError:
    print("ERROR: python3-evdev library is required. Install with:")
    print("sudo apt install python3-evdev")
    sys.exit(1)


class RemarkableMouse:
    def __init__(self, rm_host: str = "root@10.11.99.1", remarkable_version: int = 2, verbose: bool = False, flip_orientation: bool = False):
        self.rm_host = rm_host
        # reMarkable version: 1 for reMarkable 1.0, 2 for reMarkable 2.0, 3+ for future versions
        if remarkable_version not in [1, 2]:
            raise ValueError(f"Invalid reMarkable version: {remarkable_version}. Supported versions: 1, 2")
        self.remarkable_version = remarkable_version
        self.device_path: Optional[str] = None
        self.uinput: Optional[UInput] = None
        self.verbose = verbose
        self.flip_orientation = flip_orientation
        
        # Stylus state
        self.x = 0
        self.y = 0
        self.pressure = 0
        self.is_touching = False
        self.was_touching = False
        
        # Button state
        self.button_pressed = False
        self.was_button_pressed = False
        
        # Mouse state for relative movement
        self.last_x = 0
        self.last_y = 0
        self.mouse_button_pressed = False
        
        # Mouse sensitivity and scaling
        self.mouse_sensitivity = 1.0  # Adjustable sensitivity multiplier
        self.uniform_scaling = True   # Use uniform scaling for both axes
        
        # reMarkable tablet coordinate system dimensions (standard for both versions)
        self.rm_width = 15725  # reMarkable coordinate system width
        self.rm_height = 20967  # reMarkable coordinate system height
        
        # Screen dimensions (auto-detected using xrandr)
        self.screen_width = 1920
        self.screen_height = 1080
        
        self._running = False
        self._process: Optional[asyncio.subprocess.Process] = None


    def get_device_path(self) -> str:
        """Get the input device path based on reMarkable version."""
        if self.remarkable_version == 1:
            return "/dev/input/event0"
        elif self.remarkable_version == 2:
            return "/dev/input/event1"
        else:
            # Future versions can be added here (version 3, 4, etc.)
            raise NotImplementedError(f"Unsupported reMarkable version: {self.remarkable_version}. Currently supported: 1, 2")

    def detect_screen_resolution(self) -> Tuple[int, int]:
        """Auto-detect screen resolution using xrandr (works on X11 and Wayland)."""
        try:
            result = subprocess.run(
                ["xrandr", "--current"],
                capture_output=True,
                text=True
            )
            
            for line in result.stdout.split('\n'):
                if '*' in line and '+' in line:
                    # Parse line like "1920x1080     60.00*+  59.93"
                    resolution = line.split()[0]
                    width, height = map(int, resolution.split('x'))
                    if self.verbose:
                        print(f"Detected screen resolution: {width}x{height}")
                    return width, height
        except Exception as e:
            if self.verbose:
                print(f"Warning: Could not detect screen resolution: {e}")
        
        # Fallback to default
        if self.verbose:
            print(f"Using default resolution: {self.screen_width}x{self.screen_height}")
        return self.screen_width, self.screen_height

    def create_virtual_device(self):
        """Create a virtual mouse/stylus input device with pressure sensitivity and hover detection."""
        # Update screen dimensions
        self.screen_width, self.screen_height = self.detect_screen_resolution()
        
        # Define capabilities for a pressure-sensitive mouse/stylus device
        capabilities = {
            ecodes.EV_KEY: [
                ecodes.BTN_LEFT,        # Left mouse button
                ecodes.BTN_RIGHT,       # Right mouse button
                ecodes.BTN_MIDDLE,      # Middle mouse button
                ecodes.BTN_STYLUS,      # Stylus button for right-click
            ],
            ecodes.EV_REL: [
                ecodes.REL_X,           # Relative X movement
                ecodes.REL_Y,           # Relative Y movement
                ecodes.REL_WHEEL,       # Mouse wheel (we'll use this for pressure)
            ],
        }
        
        try:
            # Create a virtual mouse/stylus device
            self.uinput = UInput(
                capabilities,
                name='reMarkable Virtual Mouse',
                vendor=0x1234,  # Generic vendor ID
                product=0x5678,  # Generic product ID
                version=0x0001,
                bustype=ecodes.BUS_VIRTUAL
            )
            if self.verbose:
                print("Virtual mouse/stylus device created successfully")
                print(f"Device: {self.uinput.device.path}")
        except Exception as e:
            print(f"ERROR: Failed to create stylus device: {e}")
            print("Trying fallback configuration...")
            
            # Fallback: Try simpler mouse-like device
            try:
                fallback_capabilities = {
                    ecodes.EV_KEY: [ecodes.BTN_LEFT, ecodes.BTN_TOOL_PEN, ecodes.BTN_STYLUS],
                    ecodes.EV_ABS: [
                        (ecodes.ABS_X, AbsInfo(value=0, min=0, max=self.screen_width-1, fuzz=0, flat=0, resolution=0)),
                        (ecodes.ABS_Y, AbsInfo(value=0, min=0, max=self.screen_height-1, fuzz=0, flat=0, resolution=0)),
                    ],
                }
                
                self.uinput = UInput(
                    fallback_capabilities,
                    name='reMarkable Mouse',
                    bustype=ecodes.BUS_VIRTUAL
                )
                if self.verbose:
                    print("Fallback virtual device created successfully")
                    print(f"Device: {self.uinput.device.path}")
                    print("Note: Using simplified mouse mode (no pressure sensitivity)")
                
            except Exception as e2:
                print(f"ERROR: Failed to create fallback device: {e2}")
                print("Please check:")
                print("1. Running with sudo")
                print("2. /dev/uinput exists and is accessible")
                print("3. No conflicting input devices")
                sys.exit(1)

    def map_coordinates(self, rm_x: int, rm_y: int) -> Tuple[int, int]:
        """Map reMarkable coordinates to screen coordinates with proper aspect ratio."""
        # Apply orientation flipping - by default we flip (180 degree rotation)
        # When --flip is used, we restore the original orientation
        if not self.flip_orientation:  # Default behavior: flipped orientation
            # Flip coordinates (180 degree rotation around center)
            flipped_x = self.rm_width - rm_x
            flipped_y = self.rm_height - rm_y
        else:  # When --flip flag is used: original orientation
            flipped_x = rm_x
            flipped_y = rm_y
        
        # Calculate aspect ratios
        rm_aspect = self.rm_width / self.rm_height  # reMarkable aspect ratio
        screen_aspect = self.screen_width / self.screen_height  # Screen aspect ratio
        
        # Use uniform scaling to maintain aspect ratio
        # Scale based on the limiting dimension
        if rm_aspect > screen_aspect:
            # reMarkable is wider relative to height, scale by width
            scale = self.screen_width / self.rm_width
            screen_x = int(flipped_x * scale)
            screen_y = int(flipped_y * scale)
        else:
            # reMarkable is taller relative to width, scale by height  
            scale = self.screen_height / self.rm_height
            screen_x = int(flipped_x * scale)
            screen_y = int(flipped_y * scale)
        
        # Ensure coordinates are within bounds
        screen_x = max(0, min(screen_x, self.screen_width - 1))
        screen_y = max(0, min(screen_y, self.screen_height - 1))
        
        return screen_x, screen_y

    def calculate_relative_movement(self, current_x: int, current_y: int) -> Tuple[int, int]:
        """Calculate relative movement with floating-point accumulation for smooth fine motion."""
        # Apply coordinate flipping before calculating relative movement
        if not self.flip_orientation:  # Default behavior: flipped orientation
            flipped_current_x = self.rm_width - current_x
            flipped_current_y = self.rm_height - current_y
        else:  # When --flip flag is used: original orientation
            flipped_current_x = current_x
            flipped_current_y = current_y
        
        if not hasattr(self, 'last_x') or self.last_x == 0:
            self.last_x = flipped_current_x
            self.last_y = flipped_current_y
            self._rel_x_accum = 0.0
            self._rel_y_accum = 0.0
            return 0, 0

        # Calculate raw movement in reMarkable coordinates (after flipping)
        raw_rel_x = flipped_current_x - self.last_x
        raw_rel_y = flipped_current_y - self.last_y

        if self.uniform_scaling:
            scale_x = self.screen_width / self.rm_width
            scale_y = self.screen_height / self.rm_height
            scale = min(scale_x, scale_y) * self.mouse_sensitivity
            move_x = raw_rel_x * scale
            move_y = raw_rel_y * scale
        else:
            scale_x = (self.screen_width / self.rm_width) * self.mouse_sensitivity
            scale_y = (self.screen_height / self.rm_height) * self.mouse_sensitivity
            move_x = raw_rel_x * scale_x
            move_y = raw_rel_y * scale_y

        # Accumulate fractional movement
        if not hasattr(self, '_rel_x_accum'):
            self._rel_x_accum = 0.0
        if not hasattr(self, '_rel_y_accum'):
            self._rel_y_accum = 0.0
        self._rel_x_accum += move_x
        self._rel_y_accum += move_y

        rel_x = int(round(self._rel_x_accum))
        rel_y = int(round(self._rel_y_accum))

        # Remove the sent integer part, keep the fractional remainder
        self._rel_x_accum -= rel_x
        self._rel_y_accum -= rel_y

        # Update last position (using flipped coordinates)
        self.last_x = flipped_current_x
        self.last_y = flipped_current_y

        return rel_x, rel_y

    def process_stylus_event(self, x: int, y: int, pressure: int):
        """Process stylus event and send to virtual device."""
        if not self.uinput:
            return
            
        # Map coordinates
        screen_x, screen_y = self.map_coordinates(x, y)
        
        # Update stylus state
        self.x, self.y, self.pressure = x, y, pressure
        self.was_touching = self.is_touching
        self.is_touching = pressure > 0
        
        # Check if we have stylus capabilities or fallback to mouse mode
        device_name = getattr(self.uinput, 'name', 'Unknown')
        is_pen_mode = 'Pen' in device_name
        
        if is_pen_mode:
            # Full stylus mode with hover detection
            # Always send stylus tool presence (for hovering)
            self.uinput.write(ecodes.EV_KEY, ecodes.BTN_TOOL_PEN, 1)
            
            # Send absolute position
            self.uinput.write(ecodes.EV_ABS, ecodes.ABS_X, screen_x)
            self.uinput.write(ecodes.EV_ABS, ecodes.ABS_Y, screen_y)
            
            # Send pressure if available
            try:
                self.uinput.write(ecodes.EV_ABS, ecodes.ABS_PRESSURE, pressure)
            except:
                pass  # Pressure might not be available in fallback mode
            
            # Handle touch events (clicks only when touching surface)
            # Also send stylus button state for applications that can use it
            if self.button_pressed != self.was_button_pressed:
                self.uinput.write(ecodes.EV_KEY, ecodes.BTN_STYLUS, 1 if self.button_pressed else 0)
            
            if self.is_touching and not self.was_touching:
                # Pen just touched the surface - start click
                self.uinput.write(ecodes.EV_KEY, ecodes.BTN_TOUCH, 1)
                if self.verbose:
                    button_info = " (with button)" if self.button_pressed else ""
                    print(f"Stylus DOWN{button_info} at ({screen_x}, {screen_y}) pressure: {pressure}")
            elif not self.is_touching and self.was_touching:
                # Pen lifted from surface - end click
                self.uinput.write(ecodes.EV_KEY, ecodes.BTN_TOUCH, 0)
                if self.verbose:
                    print(f"Stylus UP at ({screen_x}, {screen_y})")
            elif self.is_touching:
                # Pen dragging on surface
                if self.verbose:
                    button_info = " (with button)" if self.button_pressed else ""
                    print(f"Stylus DRAG{button_info} at ({screen_x}, {screen_y}) pressure: {pressure}")
            else:
                # Pen hovering above surface
                if self.verbose:
                    button_info = " (with button)" if self.button_pressed else ""
                    print(f"Stylus HOVER{button_info} at ({screen_x}, {screen_y})")
        else:
            # Mouse mode with relative movement
            # Calculate relative movement with proper scaling
            rel_x, rel_y = self.calculate_relative_movement(x, y)
            
            # Send movement events whenever the stylus moves (hovering or touching)
            if rel_x != 0 or rel_y != 0:
                self.uinput.write(ecodes.EV_REL, ecodes.REL_X, rel_x)
                self.uinput.write(ecodes.EV_REL, ecodes.REL_Y, rel_y)
            
            # Handle mouse clicks (only when touching surface)
            # Determine which mouse button to use based on stylus button state
            mouse_button = ecodes.BTN_RIGHT if self.button_pressed else ecodes.BTN_LEFT
            button_name = "RIGHT" if self.button_pressed else "LEFT"
            
            if self.is_touching and not self.was_touching:
                # Start click
                self.uinput.write(ecodes.EV_KEY, mouse_button, 1)
                self.mouse_button_pressed = True
                if self.verbose:
                    print(f"Mouse {button_name} DOWN at ({screen_x}, {screen_y}) pressure: {pressure}")
            elif not self.is_touching and self.was_touching:
                # End click - use the button that was active when click started
                # For simplicity, release both buttons to handle button state changes during click
                if self.mouse_button_pressed:
                    self.uinput.write(ecodes.EV_KEY, ecodes.BTN_LEFT, 0)
                    self.uinput.write(ecodes.EV_KEY, ecodes.BTN_RIGHT, 0)
                    self.mouse_button_pressed = False
                if self.verbose:
                    print(f"Mouse UP at ({screen_x}, {screen_y})")
            elif self.is_touching:
                # Handle button state changes during drag
                if self.button_pressed != self.was_button_pressed and self.mouse_button_pressed:
                    # Button state changed while dragging - switch button type
                    # Release old button, press new button
                    old_button = ecodes.BTN_LEFT if self.button_pressed else ecodes.BTN_RIGHT
                    new_button = ecodes.BTN_RIGHT if self.button_pressed else ecodes.BTN_LEFT
                    self.uinput.write(ecodes.EV_KEY, old_button, 0)
                    self.uinput.write(ecodes.EV_KEY, new_button, 1)
                    if self.verbose:
                        new_button_name = "RIGHT" if self.button_pressed else "LEFT"
                        print(f"Switched to {new_button_name} button during drag")
                
                # Dragging with button held
                if self.verbose:
                    print(f"Mouse {button_name} DRAG at ({screen_x}, {screen_y}) pressure: {pressure}")
            else:
                # Hovering - cursor moves but no click
                if rel_x != 0 or rel_y != 0:
                    if self.verbose:
                        print(f"Mouse HOVER at ({screen_x}, {screen_y})")
                    
        # Synchronize the event
        self.uinput.syn()

    async def read_remarkable_data(self):
        """Read pen/stylus data from reMarkable tablet via SSH connection."""
        command = f"ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no {self.rm_host} cat {self.device_path}"
        
        if self.verbose:
            print(f"Connecting to reMarkable at {self.rm_host}...")
        
        try:
            self._process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            if self.verbose:
                print("Connected! Move your stylus on the reMarkable tablet.")
                print("Press Ctrl+C to stop.")
            
            # Read data in 16-byte chunks (reMarkable input event structure)
            while self._running and self._process.returncode is None:
                try:
                    data = await asyncio.wait_for(self._process.stdout.read(16), timeout=1.0)
                    
                    if len(data) != 16:
                        if len(data) == 0:
                            if self.verbose:
                                print("Connection closed by reMarkable")
                            break
                        continue
                    
                    # Parse reMarkable input event structure
                    # Based on Linux input_event structure
                    timestamp = data[0:8]  # struct timeval (8 bytes)
                    type_code = data[8:10]  # __u16 type (2 bytes)
                    code = data[10:12]     # __u16 code (2 bytes)
                    value = data[12:16]    # __s32 value (4 bytes)
                    
                    # Unpack the values
                    event_type = struct.unpack('<H', type_code)[0]
                    event_code = struct.unpack('<H', code)[0]
                    event_value = struct.unpack('<i', value)[0]
                    
                    # Process absolute position events (type 3)
                    if event_type == 3:  # EV_ABS
                        if event_code == 0:    # ABS_X
                            self.x = event_value
                            # Process stylus event on X coordinate update (for hovering)
                            self.process_stylus_event(self.x, self.y, self.pressure)
                        elif event_code == 1:  # ABS_Y
                            self.y = event_value
                            # Process stylus event on Y coordinate update (for hovering)
                            self.process_stylus_event(self.x, self.y, self.pressure)
                        elif event_code == 24: # ABS_PRESSURE
                            self.pressure = event_value
                            # Process stylus event on pressure update (for touching)
                            self.process_stylus_event(self.x, self.y, self.pressure)
                    
                    # Process key events (type 1) for button presses
                    elif event_type == 1:  # EV_KEY
                        if event_code == 331:  # BTN_STYLUS (stylus button)
                            self.was_button_pressed = self.button_pressed
                            self.button_pressed = event_value == 1
                            if self.verbose:
                                button_state = "PRESSED" if self.button_pressed else "RELEASED"
                                print(f"Stylus button {button_state}")
                            # Process stylus event on button state change
                            self.process_stylus_event(self.x, self.y, self.pressure)
                
                except asyncio.TimeoutError:
                    # Timeout is normal, just continue
                    continue
                except Exception as e:
                    if self.verbose:
                        print(f"Error reading data: {e}")
                    break
                    
        except Exception as e:
            print(f"ERROR: Failed to connect to reMarkable: {e}")
        finally:
            if self._process:
                self._process.kill()
                await self._process.wait()

    async def run(self):
        """Main run loop - connects to reMarkable and starts processing input events."""
        self._running = True
        
        try:
            # Setup device path based on reMarkable version
            self.device_path = self.get_device_path()
            
            # Create virtual input device
            self.create_virtual_device()
            
            # Start reading data
            await self.read_remarkable_data()
            
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources and close virtual input device."""
        self._running = False
        
        if self.uinput:
            # Send stylus tool away event (if in stylus mode)
            try:
                device_name = getattr(self.uinput, 'name', 'Unknown')
                if 'Pen' in device_name:
                    self.uinput.write(ecodes.EV_KEY, ecodes.BTN_TOOL_PEN, 0)
                    self.uinput.syn()
            except:
                pass  # Ignore errors during cleanup
            
            self.uinput.close()
            if self.verbose:
                print("Virtual device closed")


def signal_handler(signum, frame, mouse_instance):
    """Handle Ctrl+C gracefully."""
    print("\nReceived interrupt signal...")
    mouse_instance.cleanup()
    sys.exit(0)


async def main():
    parser = argparse.ArgumentParser(description='reMarkable Mouse - Virtual Mouse from reMarkable Tablet')
    parser.add_argument(
        '--host', 
        default='root@10.11.99.1',
        help='reMarkable SSH host (default: root@10.11.99.1)'
    )
    parser.add_argument(
        '--sensitivity', '-s',
        type=float,
        default=1.0,
        help='Mouse sensitivity multiplier (default: 1.0)'
    )
    parser.add_argument(
        '--no-uniform-scaling',
        action='store_true',
        help='Disable uniform scaling (may cause distortion but covers full screen)'
    )
    parser.add_argument(
        '--remarkable-version',
        type=int,
        choices=[1, 2],
        default=2,
        help='reMarkable version: 1 for reMarkable 1.0, 2 for reMarkable 2.0 (default: 2)'
    )
    parser.add_argument(
        '--flip', '-f',
        action='store_true',
        help='Flip orientation to original (default is now flipped 180 degrees)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    # Check if running as root
    if os.geteuid() != 0:
        print("WARNING: Not running as root. You may need sudo for virtual device creation.")
    
    # Create and run the virtual mouse/stylus
    mouse = RemarkableMouse(args.host, getattr(args, 'remarkable_version'), verbose=args.verbose, flip_orientation=args.flip)
    mouse.mouse_sensitivity = args.sensitivity
    mouse.uniform_scaling = not args.no_uniform_scaling
    
    if args.verbose:
        print(f"Mouse sensitivity: {mouse.mouse_sensitivity}")
        print(f"Uniform scaling: {mouse.uniform_scaling}")
        orientation = "original" if args.flip else "flipped (default)"
        print(f"Orientation: {orientation}")
    
    # Setup signal handler for graceful shutdown
    signal.signal(signal.SIGINT, lambda s, f: signal_handler(s, f, mouse))
    
    await mouse.run()


if __name__ == "__main__":
    print("reMarkable Mouse - Virtual Mouse from reMarkable Tablet")
    print("===================================================================")
    asyncio.run(main())
