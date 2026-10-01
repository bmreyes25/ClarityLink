import unittest

from tools.elf_va_map import ELFAddressMap, ELFMapError


class ELFAddressMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mapper = ELFAddressMap("extracted/system/system/bin/jmcs")

    def test_known_file_offset_to_va_first_load(self):
        self.assertEqual(self.mapper.file_offset_to_va(0x28557E), 0x28557E)

    def test_known_va_to_file_offset_second_load(self):
        self.assertEqual(self.mapper.va_to_file_offset(0x342858), 0x341858)

    def test_read_known_second_load_data(self):
        self.assertEqual(self.mapper.read_va(0x342858, 4), b"\x00\x00\x00\x00")

    def test_load_segment_file_end_is_inclusive_for_zero_length(self):
        seg = self.mapper.load_segments[0]
        self.assertEqual(self.mapper.file_offset_to_va(seg.file_offset + seg.file_size, 0),
                         seg.virtual_address + seg.file_size)

    def test_file_offset_outside_load_is_rejected(self):
        with self.assertRaises(ELFMapError):
            self.mapper.file_offset_to_va(0x400000)

    def test_bss_va_is_not_file_backed(self):
        with self.assertRaises(ELFMapError):
            self.mapper.va_to_file_offset(0x360000)

    def test_thumb_bit_is_normalized_only_when_requested(self):
        self.assertEqual(self.mapper.va_to_file_offset(0x28EBC5, thumb=True), 0x28EBC4)
        self.assertEqual(self.mapper.va_to_file_offset(0x28EBC5), 0x28EBC5)

    def test_crossing_segment_file_boundary_is_rejected(self):
        seg = self.mapper.load_segments[0]
        with self.assertRaises(ELFMapError):
            self.mapper.file_offset_to_va(seg.file_offset + seg.file_size - 1, 2)


if __name__ == "__main__":
    unittest.main()
