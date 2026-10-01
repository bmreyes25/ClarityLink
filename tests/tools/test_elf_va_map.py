import unittest
import struct
import tempfile

from tools.elf_va_map import ELFAddressMap, ELFMapError


class ELFAddressMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.synthetic_file = tempfile.NamedTemporaryFile()
        cls.synthetic_file.write(cls.synthetic_elf())
        cls.synthetic_file.flush()
        cls.mapper = ELFAddressMap(cls.synthetic_file.name)
        cls.addClassCleanup(cls.synthetic_file.close)

    @staticmethod
    def synthetic_elf():
        """Tiny synthetic ELF32 with two PT_LOAD ranges; contains no Honda bytes."""
        data = bytearray(range(0xE0))
        ident = b"\x7fELF" + bytes((1, 1, 1, 0)) + bytes(8)
        struct.pack_into("<16sHHIIIIIHHHHHH", data, 0, ident, 3, 40, 1, 0, 52, 0, 0,
                         52, 32, 2, 0, 0, 0)
        struct.pack_into("<IIIIIIII", data, 52, 1, 0, 0, 0, 0x20, 0x30, 5, 0x1000)
        struct.pack_into("<IIIIIIII", data, 84, 1, 0xC0, 0x10C0, 0x10C0, 0x20, 0x40, 5, 0x1000)
        return bytes(data)

    def test_known_file_offset_to_va_first_load(self):
        self.assertEqual(self.mapper.file_offset_to_va(0x10), 0x10)

    def test_known_va_to_file_offset_second_load(self):
        self.assertEqual(self.mapper.va_to_file_offset(0x10C8), 0xC8)

    def test_read_known_second_load_data(self):
        self.assertEqual(self.mapper.read_va(0x10C8, 4), b"\xC8\xC9\xCA\xCB")

    def test_load_segment_file_end_is_inclusive_for_zero_length(self):
        seg = self.mapper.load_segments[0]
        self.assertEqual(self.mapper.file_offset_to_va(seg.file_offset + seg.file_size, 0),
                         seg.virtual_address + seg.file_size)

    def test_file_offset_outside_load_is_rejected(self):
        with self.assertRaises(ELFMapError):
            self.mapper.file_offset_to_va(0x400000)

    def test_bss_va_is_not_file_backed(self):
        with self.assertRaises(ELFMapError):
            self.mapper.va_to_file_offset(0x10E0)

    def test_thumb_bit_is_normalized_only_when_requested(self):
        self.assertEqual(self.mapper.va_to_file_offset(0x10D1, thumb=True), 0xD0)
        self.assertEqual(self.mapper.va_to_file_offset(0x10D1), 0xD1)

    def test_crossing_segment_file_boundary_is_rejected(self):
        seg = self.mapper.load_segments[0]
        with self.assertRaises(ELFMapError):
            self.mapper.file_offset_to_va(seg.file_offset + seg.file_size - 1, 2)


if __name__ == "__main__":
    unittest.main()
