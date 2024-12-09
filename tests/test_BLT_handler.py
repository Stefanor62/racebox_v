import asyncio
from pathlib import Path
import sys

# Add the project root directory to Python path
project_root = str(Path(__file__).parents[1])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.handlers.gps_BLT_handler import BLTHandler

def data_callback(data):
    """Simple callback to print received data."""
    print(f"Received data length: {len(data)}")
    print(f"Raw data: {data.hex()}")

async def test_connection():
    """Test BLE connection and data reception."""
    handler = BLTHandler(data_callback=data_callback)
    try:
        await handler.connect_and_run()
    except KeyboardInterrupt:
        print("\nTest stopped by user")

if __name__ == "__main__":
    print("Starting BLT Handler test...")
    print("Press Ctrl+C to stop")
    asyncio.run(test_connection())