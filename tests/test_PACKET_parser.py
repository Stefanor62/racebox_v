import sys
from pathlib import Path
import unittest

# Add the project root directory to Python path
project_root = Path(__file__).parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.handlers.gps_PACKET_parser import PacketParser

class TestPacketParser(unittest.TestCase):
    def setUp(self):
        """Set up test cases."""
        self.config_path = project_root / 'src' / 'config' / 'config.yaml'
        self.parser = PacketParser(self.config_path)
        
        # Example packet from RaceBox documentation
        self.example_packet = bytes.fromhex(
            "B5 62 FF 01 50 00 A0 E7 0C 07 E6 07 01 0A 08 33"
            "08 37 19 00 00 00 2A AD 4D 0E 03 01 EA 0B C6 93"
            "E1 0D 3B 37 6F 19 61 8C 09 00 0F 01 09 00 9C 03"
            "00 00 2C 07 00 00 23 00 00 00 00 00 00 00 D0 00"
            "00 00 88 A9 DD 00 2C 01 00 59 FD FF 71 00 CE 03"
            "2F FF 56 00 FC FF 06 DB"
        )

    def test_packet_start_detection(self):
        """Test that parser correctly identifies packet start sequence."""
        self.assertEqual(self.example_packet[0:2], bytes([0xB5, 0x62]))
        
    def test_packet_assembly(self):
        """Test packet assembly from split data."""
        # Split packet into two parts
        part1 = self.example_packet[:40]
        part2 = self.example_packet[40:]
        
        # Add first part
        packets = self.parser.add_data(part1)
        self.assertEqual(len(packets), 0)  # Should not have complete packet yet
        
        # Add second part
        packets = self.parser.add_data(part2)
        self.assertEqual(len(packets), 1)  # Should now have one complete packet
        self.assertEqual(packets[0], self.example_packet)

    def test_motion_data_parsing(self):
        """Test parsing of motion data from packet."""
        motion_data = self.parser.parse_motion_data(self.example_packet)
        
        # Test values from documentation example
        self.assertAlmostEqual(motion_data.acc_x, -0.003, places=3)
        self.assertAlmostEqual(motion_data.acc_y, 0.113, places=3)
        self.assertAlmostEqual(motion_data.acc_z, 0.974, places=3)
        self.assertAlmostEqual(motion_data.rot_x, -2.09, places=2)
        self.assertAlmostEqual(motion_data.rot_y, 0.86, places=2)
        self.assertAlmostEqual(motion_data.rot_z, -0.04, places=2)

    def test_location_data_parsing(self):
        """Test parsing of location data from packet."""
        location_data = self.parser.parse_location_data(self.example_packet)
        
        # Test values from documentation example
        self.assertAlmostEqual(location_data.latitude, 42.6719035, places=7)
        self.assertAlmostEqual(location_data.longitude, 23.2887238, places=7)
        self.assertAlmostEqual(location_data.speed, 0.126, places=3)
        self.assertEqual(location_data.satellites, 11)
        self.assertEqual(location_data.fix_status, "3D FIX")
        self.assertAlmostEqual(location_data.altitude_wgs, 625.761, places=3)
        self.assertAlmostEqual(location_data.altitude_msl, 590.095, places=3)

    def test_invalid_data_handling(self):
        """Test parser's handling of invalid data."""
        # Test with invalid start sequence
        invalid_packet = bytearray(self.example_packet)
        invalid_packet[0:2] = [0x00, 0x00]
        result = self.parser.parse_packet(bytes(invalid_packet))
        self.assertIsNone(result)
        
        # Test with packet too short
        short_packet = self.example_packet[:40]
        result = self.parser.parse_packet(short_packet)
        self.assertIsNone(result)

    def test_complete_packet_parsing(self):
        """Test complete packet parsing."""
        parsed_data = self.parser.parse_packet(self.example_packet)
        self.assertIsNotNone(parsed_data)
        self.assertEqual(parsed_data.raw_data, self.example_packet)
        
        # Test that both motion and location data are present
        self.assertIsNotNone(parsed_data.motion)
        self.assertIsNotNone(parsed_data.location)

if __name__ == '__main__':
    unittest.main()