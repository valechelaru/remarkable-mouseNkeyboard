#!/usr/bin/env python3
"""
reMarkable Keyboard - Virtual Keyboard from reMarkable Tablet with Type Folio

This program connects to a reMarkable tablet via SSH and creates a virtual keyboard
input device on Linux desktops. It processes keyboard data from the reMarkable Type Folio
and translates it into Linux keyboard events.

Features:
- Full keyboard support for the reMarkable Type Folio
- Works with reMarkable 2.0 only (requires Type Folio)
- Works with Wayland and X11 desktop environments

Requirements:
- Linux with Wayland or X11 display server
- python3-evdev system package (install with: sudo apt install python3-evdev)
- SSH access to reMarkable tablet
- Root privileges to create input devices (or proper udev rules)

Usage:
    python3 remarkable_keyboard.py [--host REMARKABLE_IP]
"""

import asyncio
import argparse
import os
import signal
import struct
import sys
from typing import Optional

# Import evdev with error handling
try:
    import evdev
    from evdev import UInput
    from evdev import ecodes
except ImportError:
    print("ERROR: python3-evdev library is required. Install with:")
    print("sudo apt install python3-evdev")
    sys.exit(1)


class RemarkableKeyboard:
    def __init__(self, rm_host: str = "root@10.11.99.1", verbose: bool = False):
        self.rm_host = rm_host
        self.device_path = "/dev/input/event3"  # rM_Keyboard device
        self.uinput: Optional[UInput] = None
        self.verbose = verbose
        
        self._running = False
        self._process: Optional[asyncio.subprocess.Process] = None

    def create_virtual_device(self):
        """Create a virtual keyboard input device."""
        # Define capabilities for a keyboard device
        # We need to support all the keys that the reMarkable Type Folio can generate
        capabilities = {
            ecodes.EV_KEY: list(range(ecodes.KEY_ESC, ecodes.KEY_MAX + 1)),
        }
        
        try:
            # Create a virtual keyboard device
            self.uinput = UInput(
                capabilities,
                name='reMarkable Virtual Keyboard',
                vendor=0x1234,  # Generic vendor ID
                product=0x5678,  # Generic product ID
                version=0x0001,
                bustype=ecodes.BUS_VIRTUAL
            )
            if self.verbose:
                print("Virtual keyboard device created successfully")
                print(f"Device: {self.uinput.device.path}")
        except Exception as e:
            print(f"ERROR: Failed to create keyboard device: {e}")
            print("Please check:")
            print("1. Running with sudo")
            print("2. /dev/uinput exists and is accessible")
            print("3. No conflicting input devices")
            sys.exit(1)

    async def read_remarkable_data(self):
        """Read keyboard data from reMarkable tablet via SSH connection."""
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
                print("Connected! Use your Type Folio keyboard on the reMarkable tablet.")
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
                    
                    # Process key events (type 1) for keyboard presses
                    if event_type == 1:  # EV_KEY
                        # Direct pass-through of keyboard events
                        if self.verbose:
                            key_name = evdev.ecodes.KEY.get(event_code, f"Unknown({event_code})")
                            state = "PRESSED" if event_value == 1 else "RELEASED" if event_value == 0 else "REPEAT"
                            print(f"Key {key_name} {state}")
                        
                        # Forward the event to the virtual keyboard
                        self.uinput.write(ecodes.EV_KEY, event_code, event_value)
                        self.uinput.syn()
                
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
            self.uinput.close()
            if self.verbose:
                print("Virtual keyboard device closed")


def signal_handler(signum, frame, keyboard_instance):
    """Handle Ctrl+C gracefully."""
    print("\nReceived interrupt signal...")
    keyboard_instance.cleanup()
    sys.exit(0)


async def main():
    parser = argparse.ArgumentParser(description='reMarkable Keyboard - Virtual Keyboard from reMarkable Tablet')
    parser.add_argument(
        '--host', 
        default='root@10.11.99.1',
        help='reMarkable SSH host (default: root@10.11.99.1)'
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
    
    # Create and run the virtual keyboard
    keyboard = RemarkableKeyboard(args.host, verbose=args.verbose)
    
    # Setup signal handler for graceful shutdown
    signal.signal(signal.SIGINT, lambda s, f: signal_handler(s, f, keyboard))
    
    await keyboard.run()


if __name__ == "__main__":
    print("reMarkable Keyboard - Virtual Keyboard from reMarkable Tablet")
    print("===================================================================")
    asyncio.run(main())
