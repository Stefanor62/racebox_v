from dataclasses import dataclass
from typing import List, Optional
import yaml  # Add this import

@dataclass
class MotionData:
    """Data class for motion-related measurements."""
    acc_x: float  # Acceleration in g
    acc_y: float
    acc_z: float
    rot_x: float  # Rotation in deg/s
    rot_y: float
    rot_z: float

@dataclass
class LocationData:
    """Data class for GPS-related measurements."""
    latitude: float
    longitude: float
    speed: float      # Speed in km/h
    satellites: int
    fix_status: str
    altitude_wgs: float  # Altitude in meters
    altitude_msl: float

@dataclass
class ParsedData:
    """Complete parsed data from a RaceBox packet."""
    motion: MotionData
    location: LocationData
    raw_data: bytes

class PacketParser:
    """
    Handles RaceBox packet assembly and parsing.
    Implements the UBX protocol for RaceBox devices.
    """
    def __init__(self, config_path=None):
        """Initialize parser with configuration."""
        if config_path:
            with open(config_path) as f:
                self.config = yaml.safe_load(f)
        
        self.buffer = bytearray()
        self.PACKET_START = bytes([0xB5, 0x62])  # UBX start sequence
        self.PACKET_SIZE = 80  # Standard RaceBox packet size

    def add_data(self, data: bytes) -> List[bytes]:
        """
        Add received data to buffer and extract complete packets.
        Returns a list of complete packets found in the data.
        """
        self.buffer.extend(data)
        packets = []
        
        while len(self.buffer) >= 2:
            # Look for packet start sequence
            if self.buffer[0:2] != self.PACKET_START:
                # Remove byte until we find start sequence or buffer is too small
                self.buffer = self.buffer[1:]
                continue
                
            # Check if we have a complete packet
            if len(self.buffer) >= self.PACKET_SIZE:
                # Extract packet
                packet = self.buffer[:self.PACKET_SIZE]
                packets.append(bytes(packet))
                self.buffer = self.buffer[self.PACKET_SIZE:]
            else:
                # Not enough data for complete packet
                break
                
        return packets

    def parse_motion_data(self, data: bytes) -> MotionData:
        """Parse motion-related data from packet."""
        try:
            acc_x = int.from_bytes(data[68:70], byteorder='little', signed=True) / 1000
            acc_y = int.from_bytes(data[70:72], byteorder='little', signed=True) / 1000
            acc_z = int.from_bytes(data[72:74], byteorder='little', signed=True) / 1000
            
            rot_x = int.from_bytes(data[74:76], byteorder='little', signed=True) / 100
            rot_y = int.from_bytes(data[76:78], byteorder='little', signed=True) / 100
            rot_z = int.from_bytes(data[78:80], byteorder='little', signed=True) / 100
            
            return MotionData(acc_x, acc_y, acc_z, rot_x, rot_y, rot_z)
        except Exception as e:
            raise ValueError(f"Error parsing motion data: {e}")

    def parse_location_data(self, data: bytes) -> LocationData:
        """Parse location-related data from packet."""
        try:
            lat = int.from_bytes(data[28:32], byteorder='little', signed=True) / 10000000
            lon = int.from_bytes(data[24:28], byteorder='little', signed=True) / 10000000
            speed = int.from_bytes(data[48:52], byteorder='little', signed=True) / 1000 * 3.6
            satellites = data[23]
            fix_status = "3D FIX" if data[20] == 3 else "NO FIX"
            alt_wgs = int.from_bytes(data[32:36], byteorder='little', signed=True) / 1000  # mm to m
            alt_msl = int.from_bytes(data[36:40], byteorder='little', signed=True) / 1000  # mm to m
            
            return LocationData(
                latitude=lat,
                longitude=lon,
                speed=speed,
                satellites=satellites,
                fix_status=fix_status,
                altitude_wgs=alt_wgs,
                altitude_msl=alt_msl
            )
        except Exception as e:
            raise ValueError(f"Error parsing location data: {e}")

    def parse_packet(self, packet: bytes) -> Optional[ParsedData]:
        """
        Parse a complete RaceBox packet.
        Returns ParsedData if successful, None if packet is invalid.
        """
        if len(packet) != self.PACKET_SIZE:
            return None
            
        if packet[0:2] != self.PACKET_START:
            return None
            
        try:
            motion_data = self.parse_motion_data(packet)
            location_data = self.parse_location_data(packet)
            
            return ParsedData(
                motion=motion_data,
                location=location_data,
                raw_data=packet
            )
        except Exception as e:
            print(f"Error parsing packet: {e}")
            return None