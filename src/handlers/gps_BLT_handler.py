import asyncio
from bleak import BleakScanner, BleakClient
from pathlib import Path
import yaml

class BLTHandler:
    """
    Handles Bluetooth Low Energy (BLE) communication with RaceBox devices.
    Responsible for device scanning, connection management, and data reception.
    """
    def __init__(self, config_path: Path = None, data_callback=None):
        # Load configuration
        if config_path is None:
            config_path = Path(__file__).parents[1] / 'config' / 'config.yaml'
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        
        # Initialize variables
        self.device_info = None
        self.client = None
        self.data_callback = data_callback
        self._is_connected = False

    async def find_device(self):
        """Scans for RaceBox devices and returns the first one found."""
        print("Scanning for RaceBox devices...")
        while True:
            devices = await BleakScanner.discover()
            for device in devices:
                if device.name and device.name.startswith(tuple(self.config['device']['name_prefixes'])):
                    print("\nRaceBox device found!")
                    print(f"Name: {device.name}")
                    print(f"Address: {device.address}")
                    if hasattr(device, 'advertisement_data'):
                        rssi = device.advertisement_data.rssi
                        print(f"Signal Strength: {rssi} dBm")
                    self.device_info = device
                    return device.address
            print(".", end="", flush=True)
            await asyncio.sleep(self.config['bluetooth']['scan_interval'])

    async def _configure_connection(self, client):
        """Configures BLE connection parameters for optimal performance."""
        try:
            # Check if MTU methods are available
            if hasattr(client, 'get_mtu') and hasattr(client, 'request_mtu'):
                mtu = await client.get_mtu()
                print(f"Current MTU: {mtu}")
                
                try:
                    desired_mtu = self.config['bluetooth']['desired_mtu']
                    await client.request_mtu(desired_mtu)
                    new_mtu = await client.get_mtu()
                    print(f"Negotiated MTU: {new_mtu}")
                except NotImplementedError:
                    print("MTU negotiation not supported on this platform")
                except Exception as e:
                    print(f"MTU negotiation failed, using default MTU: {e}")
            else:
                print("MTU configuration not supported on this platform")
                print("Using default MTU size")
                    
        except Exception as e:
            print(f"Note: Using default BLE parameters ({e})")

    def _notification_handler(self, sender, data):
        """Handles incoming BLE notifications."""
        if self.data_callback:
            self.data_callback(data)

    async def connect_and_run(self):
        """
        Main connection method. Handles device connection, configuration,
        and maintains the connection with retry logic.
        """
        retry_count = 0
        
        while retry_count < self.config['device']['max_retry_attempts']:
            try:
                # Find device if not already connected
                if not self._is_connected:
                    device_address = await self.find_device()
                    if not device_address:
                        return False

                print("\nConnecting to device...")
                async with BleakClient(device_address, 
                                     timeout=self.config['bluetooth']['connection_timeout']) as client:
                    # Configure connection
                    await self._configure_connection(client)
                    self._is_connected = True
                    print("Connected successfully!")
                    
                    # Start notification handler
                    await client.start_notify(
                        self.config['bluetooth']['tx_char_uuid'],
                        self._notification_handler
                    )
                    
                    # Keep connection alive
                    try:
                        while True:
                            await asyncio.sleep(0.1)
                    except asyncio.CancelledError:
                        print("\nConnection cancelled...")
                        raise
                    finally:
                        # Clean up notifications
                        await client.stop_notify(self.config['bluetooth']['tx_char_uuid'])
                        self._is_connected = False

            except asyncio.CancelledError:
                print("\nStopping BLE handler gracefully...")
                break
            except Exception as e:
                print(f"Connection error: {e}")
                self._is_connected = False
                retry_count += 1
                if retry_count < self.config['device']['max_retry_attempts']:
                    retry_delay = self.config['device']['retry_delay']
                    print(f"Retrying in {retry_delay} seconds... "
                          f"(Attempt {retry_count + 1}/{self.config['device']['max_retry_attempts']})")
                    await asyncio.sleep(retry_delay)
                else:
                    print("Max retry attempts reached. Exiting...")
                    break

        return self._is_connected

    def is_connected(self):
        """Returns current connection status."""
        return self._is_connected

    @property
    def device_name(self):
        """Returns connected device name if available."""
        return self.device_info.name if self.device_info else None