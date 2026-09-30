"""Standard-library smoke suite; run with python3 tests/hook/smoke_self_locator.py."""
import hashlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "claritylink-hook"))
from self_locator import (DladdrResult, LocationError, Mapping, TargetDescriptor,
                          Verdict, classify_load_seam, locate_load_bias,
                          locate_via_dladdr, parse_maps_bounded, validate_target)


class LocatorSmoke(unittest.TestCase):
    def setUp(self):
        self.mapping = Mapping(0x50000000, 0x50003000, "r-xp", 0, "/system/bin/jmcs")

    def test_maps_and_bias_offset_and_duplicates(self):
        maps = parse_maps_bounded(b"50000000-50003000 r-xp 00000000 00:00 0 /system/bin/jmcs\n"
                                  b"50004000-50005000 rw-p 00004000 00:00 0 /system/bin/jmcs\n")
        self.assertEqual(locate_load_bias(maps, module_path="/system/bin/jmcs",
                                          executable_segment_offset=0, executable_segment_vaddr=0), 0x50000000)
        self.assertEqual(locate_load_bias((self.mapping, self.mapping), module_path="/system/bin/jmcs",
                                          executable_segment_offset=0, executable_segment_vaddr=0), 0x50000000)
        with self.assertRaises(LocationError):
            parse_maps_bounded(b"bad line\n")
        with self.assertRaises(LocationError):
            parse_maps_bounded(b"1-2 r-xp 0 0 0 /a", max_bytes=2)

    def test_dladdr_model_checks_null_wrong_module_wrong_base_and_pointer(self):
        self.assertEqual(locate_via_dladdr(result=DladdrResult("/system/bin/jmcs", 0x50000000),
                                           expected_path="/system/bin/jmcs", pointer=0x50000100,
                                           module_mappings=(self.mapping,)), 0x50000000)
        for result, pointer in ((None, 0x50000100), (DladdrResult("/wrong", 0x50000000), 0x50000100),
                                (DladdrResult("/system/bin/jmcs", 0x60000000), 0x50000100),
                                (DladdrResult("/system/bin/jmcs", 0x50000000), 0x60000000)):
            with self.assertRaises(LocationError):
                locate_via_dladdr(result=result, expected_path="/system/bin/jmcs", pointer=pointer,
                                  module_mappings=(self.mapping,))

    def test_target_and_load_seams_fail_closed(self):
        content = b"fixture"
        digest = hashlib.sha256(content).hexdigest()
        descriptor = TargetDescriptor("/system/bin/jmcs", digest, 0x100, b"\x00\xbf", "thumb", 2)
        kwargs = dict(actual_sha256=digest, descriptor=descriptor, load_bias=0x40000000,
                      memory_window=b"\x00\xbf", mapping_permissions="r-xp")
        self.assertEqual(validate_target(**kwargs).verdict, Verdict.VALID_TARGET)
        self.assertEqual(validate_target(**{**kwargs, "actual_sha256": "0"*64}).verdict, Verdict.WRONG_BINARY)
        self.assertEqual(classify_load_seam(mechanism="ld_preload", proven_existing=False,
                                            persistent_change_required=False), "FAIL_CLOSED_UNPROVEN")
        self.assertEqual(classify_load_seam(mechanism="ld_preload", proven_existing=True,
                                            persistent_change_required=True), "PERSISTENT_CHANGE_REQUIRED")
        self.assertEqual(classify_load_seam(mechanism="mystery", proven_existing=True,
                                            persistent_change_required=False), "UNSUPPORTED_CANDIDATE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
