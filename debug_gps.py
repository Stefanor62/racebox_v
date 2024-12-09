import asyncio
from bleak import BleakScanner, BleakClient
import keyboard
import time
import yaml
from pathlib import Path

class RaceboxScanner:
    def __init__(self):
        # Load configuration
        config_path = Path(__file__).parent / 'config.yaml'
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        
        # Initialize variables
        self.client = None
        self.data_buffer = bytearray()
        self.device_info = None
        self.display_data = False
        self.sampling_frequency = self.config['device']['sampling_rate']
        self.last_update = 0
        
    async def find_racebox(self):
        print("Scanning for RaceBox devices...")
        while True:
            devices = await BleakScanner.discover()
            for device in devices:
                if device.name and device.name.startswith(("RaceBox Mini ", "RaceBox Mini S ", "RaceBox Micro ")):
                    print("\nRaceBox device found!")
                    print(f"Name: {device.name}")
                    print(f"Address: {device.address}")
                    if hasattr(device, 'advertisement_data'):
                        rssi = device.advertisement_data.rssi
                        print(f"Signal Strength: {rssi} dBm")
                    self.device_info = device
                    return device.address
            print(".", end="", flush=True)
            await asyncio.sleep(1)

    def handle_data(self, sender, data):
        current_time = time.time()
        interval = 1.0 / self.sampling_frequency
        
        if current_time - self.last_update >= interval:
            self.data_buffer.extend(data)
            if len(self.data_buffer) >= 80:  # Complete RaceBox packet
                if self.display_data:  # Only display if 'q' was pressed
                    self.parse_and_print_data(self.data_buffer[:80])
                self.data_buffer = self.data_buffer[80:]
                self.last_update = current_time

    def parse_and_print_data(self, data):
        try:
            if len(data) < 80:
                return
            
            if self.config['display']['clear_screen']:
                print("\033[H\033[J")  # Clear screen
            
            # Device info header
            if self.device_info:
                print(f"Connected to: {self.device_info.name}")
                print(f"Sampling Frequency: {self.sampling_frequency} Hz")
                print("-" * 50)

            # Parse motion data
            acc_x = int.from_bytes(data[68:70], byteorder='little', signed=True) / 1000
            acc_y = int.from_bytes(data[70:72], byteorder='little', signed=True) / 1000
            acc_z = int.from_bytes(data[72:74], byteorder='little', signed=True) / 1000
            
            # Parse rotation data
            rot_x = int.from_bytes(data[74:76], byteorder='little', signed=True) / 100
            rot_y = int.from_bytes(data[76:78], byteorder='little', signed=True) / 100
            rot_z = int.from_bytes(data[78:80], byteorder='little', signed=True) / 100

            # Parse location data
            lat = int.from_bytes(data[28:32], byteorder='little', signed=True) / 10000000
            lon = int.from_bytes(data[24:28], byteorder='little', signed=True) / 10000000
            
            # Parse speed and satellites
            speed = int.from_bytes(data[48:52], byteorder='little', signed=True) / 1000 * 3.6
            satellites = data[23]
            fix_status = "3D FIX" if data[20] == 3 else "NO FIX"

            # Print formatted data
            print("\nMotion Data:")
            print(f"Acceleration (g):")
            print(f"  X: {acc_x:7.3f} | Y: {acc_y:7.3f} | Z: {acc_z:7.3f}")
            print(f"Rotation (deg/s):")
            print(f"  X: {rot_x:7.2f} | Y: {rot_y:7.2f} | Z: {rot_z:7.2f}")
            
            print(f"\nGPS Data ({fix_status}, Satellites: {satellites}):")
            print(f"Position: {lat:10.6f}°, {lon:10.6f}°")
            print(f"Speed: {speed:6.1f} km/h")

            print("\nControls:")
            print("q - Toggle data display")
            print("Ctrl+C - Exit program")

        except Exception as e:
            print(f"Error parsing data: {e}")

    async def keyboard_monitor(self):
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
        while True:  # Keep trying to connect
            try:
                # Find and connect to device
                device_address = await self.find_racebox()
                if not device_address:
                    return

                print("\nConnecting to device...")
                for attempt in range(self.config['device']['max_connection_attempts']):
                    try:
                        async with BleakClient(device_address, timeout=self.config['device']['connection_timeout']) as client:
                            print("Connected successfully!")
                            print(f"Sampling Rate: {self.sampling_frequency} Hz")
                            print("\nPress 'q' to start/stop data display")
                            
                            # Start notification handler
                            await client.start_notify(
                                self.config['bluetooth']['tx_char_uuid'], 
                                self.handle_data
                            )
                            
                            # Start keyboard monitor
                            keyboard_task = asyncio.create_task(self.keyboard_monitor())
                            
                            while True:
                                await asyncio.sleep(0.1)

                    except Exception as e:
                        print(f"Connection attempt {attempt + 1} failed: {str(e)}")
                        if attempt + 1 < self.config['device']['max_connection_attempts']:
                            print(f"Retrying in {self.config['device']['retry_delay']} seconds...")
                            await asyncio.sleep(self.config['device']['retry_delay'])
                        else:
                            print("Maximum connection attempts reached.")
                            print("Tips:")
                            print("1. Make sure the device is powered on and in range")
                            print("2. Try restarting the device")
                            print("3. On Windows, try turning Bluetooth off and on again")
                            print("4. Check if device is connected to another application")
                            print("\nPress Ctrl+C to exit or wait to retry scanning...")
                            await asyncio.sleep(5)
                            break  # Break the retry loop and go back to scanning

            except asyncio.CancelledError:
                print("\nStopping...")
                break
            except Exception as e:
                print(f"Error: {str(e)}")
                print("Restarting scan in 5 seconds...")
                await asyncio.sleep(5)

        print("Scanner stopped.")

async def main():
    scanner = RaceboxScanner()
    try:
        await scanner.run()
    except KeyboardInterrupt:
        print("\nStopping scanner...")

if __name__ == "__main__":
    asyncio.run(main())