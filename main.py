import asyncio
import keyboard
from pathlib import Path
import yaml
import sys

from src.handlers.gps_BLT_handler import BLTHandler
from src.handlers.gps_PACKET_parser import PacketParser, ParsedData

class RaceboxApp:
    def __init__(self):
        """Initialize the RaceBox application."""
        # Load configuration
        self.config_path = Path(__file__).parent / 'src' / 'config' / 'config.yaml'
        with open(self.config_path) as f:
            self.config = yaml.safe_load(f)

        # Initialize components
        self.parser = PacketParser(self.config_path)
        self.display_data = False
        self.last_update = 0

    def handle_parsed_data(self, parsed_data: ParsedData):
        """Display parsed data in a formatted way."""
        if self.config['display']['clear_screen']:
            print("\033[H\033[J")  # Clear screen

        # Display motion data
        print("\nMotion Data:")
        print(f"Acceleration (g):")
        print(f"  X: {parsed_data.motion.acc_x:7.3f} | "
              f"Y: {parsed_data.motion.acc_y:7.3f} | "
              f"Z: {parsed_data.motion.acc_z:7.3f}")
        print(f"Rotation (deg/s):")
        print(f"  X: {parsed_data.motion.rot_x:7.2f} | "
              f"Y: {parsed_data.motion.rot_y:7.2f} | "
              f"Z: {parsed_data.motion.rot_z:7.2f}")

        # Display GPS data
        print(f"\nGPS Data ({parsed_data.location.fix_status}, "
              f"Satellites: {parsed_data.location.satellites}):")
        print(f"Position: {parsed_data.location.latitude:10.6f}°, "
              f"{parsed_data.location.longitude:10.6f}°")
        print(f"Speed: {parsed_data.location.speed:6.1f} km/h")
        print(f"Altitude (MSL): {parsed_data.location.altitude_msl:6.1f} m")

        # Display controls if enabled
        if self.config['display']['show_controls']:
            print("\nControls:")
            print("q - Toggle data display")
            print("Ctrl+C - Exit program")

    def handle_bluetooth_data(self, data: bytes):
        """Handle incoming Bluetooth data."""
        # Process packets
        complete_packets = self.parser.add_data(data)
        
        # Parse and display each complete packet
        for packet in complete_packets:
            if self.display_data:
                parsed_data = self.parser.parse_packet(packet)
                if parsed_data:
                    self.handle_parsed_data(parsed_data)

    async def keyboard_monitor(self):
        """Monitor keyboard for control commands."""
        while True:
            if keyboard.is_pressed('q'):
                self.display_data = not self.display_data
                if self.display_data:
                    print("\nStarting data display...")
                else:
                    print("\nPausing data display...")
                await asyncio.sleep(0.5)  # Debounce
            await asyncio.sleep(0.1)

    async def run(self):
        """Main application loop."""
        try:
            print("Starting RaceBox Debug Tool...")
            print("Initializing Bluetooth connection...")

            # Initialize BLT handler with our data callback
            blt_handler = BLTHandler(
                config_path=self.config_path,
                data_callback=self.handle_bluetooth_data
            )

            # Start keyboard monitoring
            keyboard_task = asyncio.create_task(self.keyboard_monitor())

            try:
                # Start BLT handler
                await blt_handler.connect_and_run()
            except Exception as e:
                print(f"Error in BLT handler: {e}")
            finally:
                # Clean up keyboard task
                if not keyboard_task.done():
                    keyboard_task.cancel()
                    try:
                        await keyboard_task
                    except asyncio.CancelledError:
                        pass

        except Exception as e:
            print(f"Application error: {e}")
        finally:
            # Cleanup
            keyboard.unhook_all()

async def main():
    """Entry point of the application."""
    app = RaceboxApp()
    try:
        await app.run()
    except KeyboardInterrupt:
        print("\nApplication stopped by user.")
    except Exception as e:
        print(f"\nUnexpected error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nApplication terminated by user.")