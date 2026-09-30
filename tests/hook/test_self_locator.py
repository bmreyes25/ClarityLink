import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "claritylink-hook"))
import pytest
from self_locator import (LocationError, Mapping, TargetDescriptor, Verdict,
                          locate_load_bias, parse_maps_bounded, validate_target)


def test_parse_maps_supports_path_spaces_and_bounds():
    parsed = parse_maps_bounded(b"40001000-40002000 r-xp 00000000 00:00 0 /system/bin/jmcs\n")
    assert parsed[0].pathname == "/system/bin/jmcs"
    with pytest.raises(LocationError):
        parse_maps_bounded(b"broken\n")
    with pytest.raises(LocationError):
        parse_maps_bounded(b"\n".join([b"1000-2000 r-xp 0 00:00 0 /x"] * 3), max_entries=2)


def test_bias_offset_matching_and_duplicate_mapping_handling():
    maps = (Mapping(0x50001000, 0x50003000, "r-xp", 0, "/system/bin/jmcs"),
            Mapping(0x50001000, 0x50003000, "r-xp", 0, "/system/bin/jmcs"))
    assert locate_load_bias(maps, module_path="/system/bin/jmcs", executable_segment_offset=0x100,
                            executable_segment_vaddr=0x100, page_size=4096) == 0x50001000
    with pytest.raises(LocationError):
        locate_load_bias(maps, module_path="/wrong", executable_segment_offset=0,
                         executable_segment_vaddr=0)


@pytest.mark.parametrize("offset,vaddr,bias", [(0, 0x1000, 0x70000000), (0x1000, 0x2000, 0x71000000)])
def test_nonzero_bias_for_et_exec_or_pie_segment_model(offset, vaddr, bias):
    maps = (Mapping(bias + (vaddr & -4096), bias + (vaddr & -4096) + 0x3000,
                    "r-xp", offset & -4096, "/module"),)
    assert locate_load_bias(maps, module_path="/module", executable_segment_offset=offset,
                            executable_segment_vaddr=vaddr) == bias


def test_validator_fail_closed_on_hash_bytes_permissions_mode_and_overflow():
    expected = b"\x00\xbf\x00\xbf"
    desc = TargetDescriptor("/module", hashlib.sha256(b"fixture").hexdigest(), 0x100,
                            expected, "thumb", 4)
    args = dict(actual_sha256=desc.module_sha256, descriptor=desc, load_bias=0x40000000,
                memory_window=expected, mapping_permissions="r-xp")
    assert validate_target(**args).verdict is Verdict.VALID_TARGET
    assert validate_target(**{**args, "actual_sha256": "0" * 64}).verdict is Verdict.WRONG_BINARY
    assert validate_target(**{**args, "memory_window": b"bad!"}).verdict is Verdict.WRONG_PROLOGUE
    assert validate_target(**{**args, "mapping_permissions": "rw-p"}).verdict is Verdict.WRONG_MAPPING
    assert validate_target(**{**args, "descriptor": TargetDescriptor("/m", desc.module_sha256, 0, expected, "aarch64", 4)}).verdict is Verdict.UNSUPPORTED_MODE
    assert validate_target(**{**args, "load_bias": 0xffffffff}).verdict is Verdict.WRONG_MAPPING
