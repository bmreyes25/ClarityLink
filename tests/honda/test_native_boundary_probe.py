import argparse
import hashlib
from pathlib import Path
import struct

import pytest
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_PROT_READ, UC_PROT_WRITE, UC_PROT_EXEC
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_SP

from tools.honda_native_boundary_probe import (
    IMPORT_BASE,
    LOAD_BASE,
    ProbeObservation,
    ProbeResult,
    _load_image,
    _execute_bounded,
    _parse_words,
    _page_permissions,
    _range_in_executable_load_segment,
    _relocation_value,
    _parse_dynamic_entries,
    _validate_load_segments,
    _validate_emulator_permissions,
    _read_elf,
    _validate_elf_format,
    _symbol,
    _symbol_details,
    _validate_dynamic_relocations,
    run_registration_probe,
)


def _synthetic_arm_shared_object(path: Path, *, thumb_function: bool = True,
                                plt_executable: bool = True,
                                plt_section_flags: int = 6,
                                defined_import: bool = False,
                                plt_size_override: int | None = None,
                                relative_target: int = 0x2020,
                                relative_symbol_index: int = 0,
                                jump_symbol_index: int = 4,
                                pt_dynamic_offset_delta: int = 0,
                                rel_dyn_section_offset_delta: int = 0,
                                initial_callback_table: tuple[int, ...] = (0, 0, 0, 0, 0, 0),
                                initial_registration_flag: int = 0,
                                registration_flag_address: int = 0x2018) -> str:
    """Write a minimal synthetic ET_DYN with a Thumb caller and local PLT."""
    code = bytearray.fromhex(
        "10b504460a4b984720460a490a68002a0cd14ff4903206230468146004300432013bf9d10122"
        "0a60002010bd162010bd0130010018200100"
    )
    plt_code = bytes.fromhex("014b1b68184700bf1c200100")
    plt_size = len(plt_code) if plt_size_override is None else plt_size_override
    if plt_size < len(plt_code):
        raise ValueError("synthetic PLT size cannot be smaller than its stub")
    plt = plt_code + bytes(plt_size - len(plt_code))
    if len(initial_callback_table) != 6:
        raise ValueError("initial callback table must contain six words")
    data = (struct.pack("<6I", *initial_callback_table)
            + struct.pack("<I", initial_registration_flag) + bytes(4) + struct.pack("<I", 0x10))
    shstr = b"\0.text\0.data\0.plt\0.shstrtab\0.dynstr\0.dynsym\0.rel.dyn\0.rel.plt\0"
    section_names = (".text", ".data", ".plt", ".shstrtab", ".dynstr", ".dynsym",
                     ".rel.dyn", ".rel.plt")
    shstr_offsets = {name: shstr.index(name.encode()) for name in section_names}
    dynstr = b"\0register_cb\0callback_table\0registration_flag\0external_probe\0"
    dynstr_offsets = {name: dynstr.index(name.encode()) for name in (
        "register_cb", "callback_table", "registration_flag", "external_probe",
    )}
    dynsym = b"\0" * 16
    function_value = 0x1001 if thumb_function else 0x1000
    dynsym += struct.pack("<IIIBBH", dynstr_offsets["register_cb"], function_value, 48, 0x12, 0, 1)
    dynsym += struct.pack("<IIIBBH", dynstr_offsets["callback_table"], 0x2000, 24, 0x11, 0, 2)
    dynsym += struct.pack("<IIIBBH", dynstr_offsets["registration_flag"],
                          registration_flag_address, 4, 0x11, 0, 2)
    import_shndx = 1 if defined_import else 0
    dynsym += struct.pack("<IIIBBH", dynstr_offsets["external_probe"], 0, 0, 0x12, 0,
                          import_shndx)
    relative_relocation = struct.pack("<II", relative_target, (relative_symbol_index << 8) | 23)
    jump_slot_relocation = struct.pack("<II", 0x201C, (jump_symbol_index << 8) | 22)

    text_offset, data_offset, plt_offset = 0x1000, 0x2000, 0x3000
    metadata_offset = 0x4000
    metadata = bytearray(relative_relocation + jump_slot_relocation)
    dynsym_relative = len(metadata)
    metadata.extend(dynsym)
    dynstr_relative = len(metadata)
    metadata.extend(dynstr)
    dynamic_relative = (len(metadata) + 3) & ~3
    metadata.extend(bytes(dynamic_relative - len(metadata)))
    dynamic_tags = (
        (17, metadata_offset), (18, len(relative_relocation)), (19, 8),
        (23, metadata_offset + len(relative_relocation)), (2, len(jump_slot_relocation)),
        (20, 17), (6, metadata_offset + dynsym_relative), (11, 16), (0, 0),
    )
    dynamic = b"".join(struct.pack("<II", *item) for item in dynamic_tags)
    metadata.extend(dynamic)
    rel_dyn_offset = metadata_offset
    rel_plt_offset = metadata_offset + len(relative_relocation)
    dynsym_offset = metadata_offset + dynsym_relative
    dynstr_offset = metadata_offset + dynstr_relative
    dynamic_offset = metadata_offset + dynamic_relative
    shstr_offset = metadata_offset + len(metadata)
    shoff = (shstr_offset + len(shstr) + 3) & ~3
    shnum, shentsize = 9, 40

    ident = b"\x7fELF" + bytes((1, 1, 1, 0, 0)) + bytes(7)
    header = struct.pack(
        "<16sHHIIIIIHHHHHH", ident, 3, 40, 1, function_value, 52, shoff,
        0x05000000, 52, 32, 5, shentsize, shnum, 4,
    )
    phdrs = struct.pack("<IIIIIIII", 1, text_offset, 0x1000, 0x1000,
                        len(code), len(code), 5, 0x1000)
    phdrs += struct.pack("<IIIIIIII", 1, data_offset, 0x2000, 0x2000,
                         len(data), len(data), 6, 0x1000)
    phdrs += struct.pack("<IIIIIIII", 1, plt_offset, 0x3000, 0x3000,
                         len(plt), len(plt), 5 if plt_executable else 6, 0x1000)
    phdrs += struct.pack("<IIIIIIII", 1, metadata_offset, metadata_offset, metadata_offset,
                         len(metadata), len(metadata), 4, 0x1000)
    phdrs += struct.pack("<IIIIIIII", 2, dynamic_offset + pt_dynamic_offset_delta,
                         metadata_offset + dynamic_relative,
                         metadata_offset + dynamic_relative, len(dynamic), len(dynamic), 4, 4)

    def section(name, kind, flags, address, offset, size, link=0, info=0, align=1, entsize=0):
        return struct.pack("<IIIIIIIIII", shstr_offsets[name] if name else 0,
                           kind, flags, address, offset, size, link, info, align, entsize)

    sections = [bytes(40)]
    sections.append(section(".text", 1, 6, 0x1000, text_offset, len(code), align=2))
    sections.append(section(".data", 1, 3, 0x2000, data_offset, len(data), align=4))
    sections.append(section(".plt", 1, plt_section_flags, 0x3000, plt_offset, len(plt), align=4))
    sections.append(section(".shstrtab", 3, 0, 0, shstr_offset, len(shstr)))
    sections.append(section(".dynstr", 3, 2, dynstr_offset, dynstr_offset, len(dynstr)))
    sections.append(section(".dynsym", 11, 2, dynsym_offset, dynsym_offset, len(dynsym),
                            link=5, info=1, align=4, entsize=16))
    sections.append(section(".rel.dyn", 9, 2, rel_dyn_offset,
                            rel_dyn_offset + rel_dyn_section_offset_delta, len(relative_relocation),
                            link=6, info=2, align=4, entsize=8))
    sections.append(section(".rel.plt", 9, 2, rel_plt_offset, rel_plt_offset, len(jump_slot_relocation),
                            link=6, info=2, align=4, entsize=8))

    output = bytearray(shoff + shnum * shentsize)
    output[:len(header)] = header
    output[52:52 + len(phdrs)] = phdrs
    output[text_offset:text_offset + len(code)] = code
    output[data_offset:data_offset + len(data)] = data
    output[plt_offset:plt_offset + len(plt)] = plt
    output[metadata_offset:metadata_offset + len(metadata)] = metadata
    output[shstr_offset:shstr_offset + len(shstr)] = shstr
    for index, data_bytes in enumerate(sections):
        start = shoff + index * shentsize
        output[start:start + shentsize] = data_bytes
    path.write_bytes(output)
    return hashlib.sha256(output).hexdigest()


def test_callback_word_parser_requires_six_values():
    assert _parse_words("1,2,3,4,5,6") == (1, 2, 3, 4, 5, 6)
    with pytest.raises(argparse.ArgumentTypeError, match="exactly six"):
        _parse_words("1,2,3,4,5")


def test_callback_word_parser_rejects_non_integer():
    with pytest.raises(argparse.ArgumentTypeError, match="comma-separated"):
        _parse_words("1,2,3,4,5,nope")


def test_artifact_fingerprint_mismatch_fails_before_elf_parsing(tmp_path: Path):
    artifact = tmp_path / "sample.elf"
    artifact.write_bytes(b"synthetic test bytes")
    with pytest.raises(ValueError, match="SHA-256"):
        _read_elf(artifact, "0" * 64)


def test_synthetic_arm_elf_loader_applies_relative_relocation(tmp_path: Path):
    artifact = tmp_path / "synthetic.so"
    digest = _synthetic_arm_shared_object(artifact)
    elf, _raw, relocation_tables, dynamic_symbols = _read_elf(artifact, digest)
    emulator = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    _load_image(emulator, elf, relocation_tables, dynamic_symbols)
    relocated = struct.unpack("<I", emulator.mem_read(LOAD_BASE + 0x2020, 4))[0]
    assert relocated == LOAD_BASE + 0x10
    jump_slot = struct.unpack("<I", emulator.mem_read(LOAD_BASE + 0x201C, 4))[0]
    assert jump_slot == IMPORT_BASE | 1


def test_dynamic_tag_parser_requires_in_bounds_terminator_and_complete_entry():
    assert _parse_dynamic_entries(struct.pack("<II", 6, 0x4000) + bytes(8)) == ((6, 0x4000),)
    with pytest.raises(ValueError, match="DT_NULL terminator"):
        _parse_dynamic_entries(struct.pack("<II", 6, 0x4000))
    with pytest.raises(ValueError, match="not aligned"):
        _parse_dynamic_entries(bytes(9))


def test_dynamic_segment_cannot_consume_tags_past_its_file_backed_size():
    class DynamicSegment:
        def __getitem__(self, key):
            return {"p_type": "PT_DYNAMIC", "p_vaddr": 0x4000, "p_offset": 0x4000,
                    "p_filesz": 8, "p_memsz": 8}[key]

        def data(self):
            return struct.pack("<II", 6, 0x4000)  # no DT_NULL within p_filesz

        def iter_tags(self):
            raise AssertionError("bounded parser must not use unbounded iter_tags")

    class Elf:
        def iter_segments(self):
            return iter((DynamicSegment(), _FileBackedLoadSegment()))

        def iter_sections(self):
            return iter(())

    with pytest.raises(ValueError, match="in-bounds DT_NULL"):
        _validate_dynamic_relocations(Elf(), type("RelSection", (), {}), 0x10000)


def test_load_segment_validator_rejects_overlapping_memory_ranges():
    class Segment:
        def __init__(self, address, file_offset):
            self.values = {"p_type": "PT_LOAD", "p_vaddr": address, "p_offset": file_offset,
                           "p_filesz": 0x100, "p_memsz": 0x200}

        def __getitem__(self, key):
            return self.values[key]

    class Elf:
        def iter_segments(self):
            return iter((Segment(0x1000, 0), Segment(0x1100, 0x100)))

    with pytest.raises(ValueError, match="overlapping PT_LOAD"):
        _validate_load_segments(Elf(), 0x1000)


def test_registration_probe_rejects_arm_mode_symbol(tmp_path: Path):
    artifact = tmp_path / "arm-mode.so"
    digest = _synthetic_arm_shared_object(artifact, thumb_function=False)
    callbacks = (1, 2, 3, 4, 5, 6)
    other_callbacks = (7, 8, 9, 10, 11, 12)
    with pytest.raises(ValueError, match="Thumb"):
        run_registration_probe(
            artifact, digest, "register_cb", "callback_table", "registration_flag",
            callbacks, other_callbacks, 0, 22,
        )


def test_registration_probe_rejects_plt_outside_executable_load_segment(tmp_path: Path):
    artifact = tmp_path / "non-executable-plt.so"
    digest = _synthetic_arm_shared_object(artifact, plt_executable=False)
    callbacks = (1, 2, 3, 4, 5, 6)
    other_callbacks = (7, 8, 9, 10, 11, 12)
    with pytest.raises(ValueError, match="PLT range is outside executable"):
        run_registration_probe(
            artifact, digest, "register_cb", "callback_table", "registration_flag",
            callbacks, other_callbacks, 0, 22,
        )


def test_registration_probe_rejects_defined_symbol_jump_slot(tmp_path: Path):
    artifact = tmp_path / "defined-import.so"
    digest = _synthetic_arm_shared_object(artifact, defined_import=True)
    callbacks = (1, 2, 3, 4, 5, 6)
    other_callbacks = (7, 8, 9, 10, 11, 12)
    with pytest.raises(ValueError, match="defined-symbol PLT calls"):
        run_registration_probe(
            artifact, digest, "register_cb", "callback_table", "registration_flag",
            callbacks, other_callbacks, 0, 22,
        )


def test_registration_probe_rejects_oversized_plt_allowlist(tmp_path: Path):
    artifact = tmp_path / "oversized-plt.so"
    digest = _synthetic_arm_shared_object(artifact, plt_size_override=64)
    callbacks = (1, 2, 3, 4, 5, 6)
    other_callbacks = (7, 8, 9, 10, 11, 12)
    with pytest.raises(ValueError, match="PLT section exceeds the bounded size"):
        run_registration_probe(
            artifact, digest, "register_cb", "callback_table", "registration_flag",
            callbacks, other_callbacks, 0, 22,
        )


@pytest.mark.parametrize(
    ("fixture_options", "message"),
    [
        ({"relative_target": 0x4000}, "overlaps dynamic relocation or symbol metadata"),
        ({"relative_target": 0x3000}, "outside writable loadable data"),
        ({"relative_symbol_index": 1}, "must use the null symbol"),
        ({"jump_symbol_index": 5}, "symbol index exceeds DT_SYMTAB"),
        ({"pt_dynamic_offset_delta": 1}, "PT_DYNAMIC is outside consistent"),
        ({"rel_dyn_section_offset_delta": 1}, "section offset disagrees"),
    ],
)
def test_registration_probe_rejects_invalid_relocation_observations(
    tmp_path: Path, fixture_options, message: str,
):
    artifact = tmp_path / "invalid-relocation.so"
    digest = _synthetic_arm_shared_object(artifact, **fixture_options)
    callbacks = (1, 2, 3, 4, 5, 6)
    other_callbacks = (7, 8, 9, 10, 11, 12)
    with pytest.raises(ValueError, match=message):
        run_registration_probe(
            artifact, digest, "register_cb", "callback_table", "registration_flag",
            callbacks, other_callbacks, 0, 22,
        )


def test_synthetic_arm_elf_registration_pipeline_records_observations(tmp_path: Path):
    artifact = tmp_path / "synthetic.so"
    digest = _synthetic_arm_shared_object(artifact)
    first = (0x101, 0x102, 0x103, 0x104, 0x105, 0x106)
    second = (0x201, 0x202, 0x203, 0x204, 0x205, 0x206)
    result = run_registration_probe(
        artifact, digest, "register_cb", "callback_table", "registration_flag",
        first, second, 0, 22, repetitions=2,
    )
    assert result.matches_expectation
    assert result.emulator_instances == 2
    assert result.first_return == 0
    assert result.second_return == 22
    assert result.first_table == struct.pack("<6I", *first)
    assert result.second_table == result.first_table
    assert result.registration_flag == 1


@pytest.mark.parametrize(
    ("fixture_options", "message"),
    [
        ({"initial_callback_table": (0x101, 0x102, 0x103, 0x104, 0x105, 0x106)},
         "initial callback registration state"),
        ({"initial_registration_flag": 1}, "initial callback registration state"),
    ],
)
def test_probe_rejects_prepopulated_registration_state(tmp_path: Path, fixture_options, message):
    artifact = tmp_path / "prepopulated.so"
    digest = _synthetic_arm_shared_object(artifact, **fixture_options)
    callbacks = (0x101, 0x102, 0x103, 0x104, 0x105, 0x106)
    other = (0x201, 0x202, 0x203, 0x204, 0x205, 0x206)
    with pytest.raises(ValueError, match=message):
        run_registration_probe(
            artifact, digest, "register_cb", "callback_table", "registration_flag",
            callbacks, other, 0, 22,
        )


def test_probe_rejects_expected_returns_outside_unsigned_32_bit_range(tmp_path: Path):
    artifact = tmp_path / "invalid-return.so"
    digest = _synthetic_arm_shared_object(artifact)
    callbacks = (1, 2, 3, 4, 5, 6)
    other = (7, 8, 9, 10, 11, 12)
    with pytest.raises(ValueError, match="unsigned 32-bit"):
        run_registration_probe(
            artifact, digest, "register_cb", "callback_table", "registration_flag",
            callbacks, other, -1, 22,
        )


def test_probe_rejects_non_allocated_or_non_executable_plt_section(tmp_path: Path):
    artifact = tmp_path / "non-executable-plt.so"
    digest = _synthetic_arm_shared_object(artifact, plt_section_flags=2)
    callbacks = (1, 2, 3, 4, 5, 6)
    other = (7, 8, 9, 10, 11, 12)
    with pytest.raises(ValueError, match="allocated and executable"):
        run_registration_probe(
            artifact, digest, "register_cb", "callback_table", "registration_flag",
            callbacks, other, 0, 22,
        )


def test_probe_rejects_overlapping_callback_table_and_flag_symbols(tmp_path: Path):
    artifact = tmp_path / "overlapping-objects.so"
    digest = _synthetic_arm_shared_object(artifact, registration_flag_address=0x2014)
    callbacks = (1, 2, 3, 4, 5, 6)
    other = (7, 8, 9, 10, 11, 12)
    with pytest.raises(ValueError, match="ranges overlap"):
        run_registration_probe(
            artifact, digest, "register_cb", "callback_table", "registration_flag",
            callbacks, other, 0, 22,
        )


def test_synthetic_arm_elf_returns_observations_when_expectations_mismatch(tmp_path: Path):
    artifact = tmp_path / "synthetic.so"
    digest = _synthetic_arm_shared_object(artifact)
    first = (0x101, 0x102, 0x103, 0x104, 0x105, 0x106)
    second = (0x201, 0x202, 0x203, 0x204, 0x205, 0x206)
    result = run_registration_probe(
        artifact, digest, "register_cb", "callback_table", "registration_flag",
        first, second, 0, 0, repetitions=1,
    )
    observation = result.observations[0]
    assert not result.matches_expectation
    assert observation.first_return == 0
    assert observation.second_return == 22
    assert observation.expected_returns_match is False
    assert observation.second_table_preserved


def test_probe_result_selects_first_mismatch_across_emulator_instances():
    first = ProbeObservation(0, 22, b"first", b"first", 1, True, True, True, True)
    mismatch = ProbeObservation(0, 7, b"first", b"changed", 1, False, True, False, True)
    result = ProbeResult((mismatch, first))
    assert result.emulator_instances == 2
    assert result.matching_instances == 1
    assert not result.matches_expectation
    assert result.second_return == 7
    assert result.second_table == b"changed"


def test_oversized_artifact_is_rejected_by_bounded_read(tmp_path: Path, monkeypatch):
    artifact = tmp_path / "large.elf"
    artifact.write_bytes(b"12345")
    monkeypatch.setattr("tools.honda_native_boundary_probe.MAX_ARTIFACT_BYTES", 4)
    with pytest.raises(ValueError, match="inspection limit"):
        _read_elf(artifact, "0" * 64)


class _Symbol:
    def __init__(self, name, value, size, section=".text", symbol_type="STT_FUNC"):
        self.name = name
        self.values = {
            "st_value": value,
            "st_size": size,
            "st_shndx": section,
        }
        self.info = {"type": symbol_type}

    def __getitem__(self, key):
        if key == "st_info":
            return self.info
        return self.values[key]


class _Section:
    name = ".symtab"

    def __init__(self, symbols):
        self.symbols = symbols

    def iter_symbols(self):
        return iter(self.symbols)


class _Elf:
    def __init__(self, symbols):
        self.sections = [_Section(symbols)]

    def iter_sections(self):
        return iter(self.sections)


def test_symbol_resolution_requires_one_defined_symbol():
    with pytest.raises(ValueError, match="exactly one"):
        _symbol(_Elf([_Symbol("target", 0x1000, 8), _Symbol("target", 0x2000, 8)]), "target")


def test_symbol_resolution_enforces_function_size_bound():
    with pytest.raises(ValueError, match="excessive"):
        _symbol(_Elf([_Symbol("target", 0x1000, 4097)]), "target", maximum_size=4096)


def test_relative_rel_uses_the_implicit_addend():
    assert _relocation_value(23, load_base=LOAD_BASE, implicit_addend=0x234) == LOAD_BASE + 0x234


def test_jump_slot_resolves_to_the_local_import_stub():
    assert _relocation_value(22, load_base=LOAD_BASE) == IMPORT_BASE | 1


def test_segment_layout_rejects_writable_executable_pages():
    class Segment:
        def __init__(self, vaddr, memsz, flags):
            self.values = {"p_vaddr": vaddr, "p_memsz": memsz, "p_filesz": memsz,
                           "p_flags": flags}

        def __getitem__(self, key):
            return self.values[key]

    with pytest.raises(ValueError, match="writable executable"):
        _page_permissions([Segment(0, 0x800, 5), Segment(0x800, 0x800, 6)])


def test_emulator_stub_and_stack_permissions_are_enforced():
    regions = [
        (0x700000, 0x71FFFF, 3),  # RW stack
        (0x800000, 0x800FFF, 5),  # RX import stub
        (0x810000, 0x810FFF, 5),  # RX return stub
    ]
    _validate_emulator_permissions(
        regions, stack=0x700000, import_stub=0x800000, return_stub=0x810000,
        read=1, write=2, execute=4,
    )
    with pytest.raises(RuntimeError, match="non-executable"):
        _validate_emulator_permissions(
            [(0x700000, 0x71FFFF, 7), *regions[1:]], stack=0x700000,
            import_stub=0x800000, return_stub=0x810000, read=1, write=2, execute=4,
        )


def _tiny_thumb_emulator(code: bytes, lr: int = 0x20001):
    emulator = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    emulator.mem_map(0x10000, 0x1000, UC_PROT_READ | UC_PROT_WRITE)
    emulator.mem_map(0x20000, 0x1000, UC_PROT_READ | UC_PROT_WRITE)
    emulator.mem_map(0x30000, 0x1000, UC_PROT_READ | UC_PROT_WRITE)
    emulator.mem_map(0x50000, 0x1000, UC_PROT_READ | UC_PROT_WRITE)
    emulator.mem_write(0x10000, code)
    emulator.mem_write(0x30000, b"\x00\x20\x70\x47")
    emulator.mem_protect(0x10000, 0x1000, UC_PROT_READ | UC_PROT_EXEC)
    emulator.mem_protect(0x20000, 0x1000, UC_PROT_READ | UC_PROT_EXEC)
    emulator.mem_protect(0x30000, 0x1000, UC_PROT_READ | UC_PROT_EXEC)
    emulator.reg_write(UC_ARM_REG_LR, lr)
    emulator.reg_write(UC_ARM_REG_SP, 0x50800)
    return emulator


def test_bounded_executor_runs_synthetic_thumb_function_to_return_sentinel():
    # movs r0, #7; bx lr
    emulator = _tiny_thumb_emulator(b"\x07\x20\x70\x47")
    steps, result = _execute_bounded(
        emulator, entry=0x10000,
        allowed_ranges=((0x10000, 0x10004),), sentinel=0x20000,
        import_stub=0x30000, instruction_limit=8, return_register=UC_ARM_REG_R0,
    )
    assert steps == 3
    assert result == 7


def test_bounded_executor_allows_both_instructions_of_zero_return_import_stub():
    # push {lr}; ldr r3, [pc, #8]; blx r3; movs r0, #9; pop {pc}; nop; .word 0x30001
    code = b"\x00\xb5\x02\x4b\x98\x47\x09\x20\x00\xbd\x00\xbf\x01\x00\x03\x00"
    emulator = _tiny_thumb_emulator(code)
    steps, result = _execute_bounded(
        emulator, entry=0x10000,
        allowed_ranges=((0x10000, 0x1000A),), sentinel=0x20000,
        import_stub=0x30000, instruction_limit=12, return_register=UC_ARM_REG_R0,
    )
    assert steps == 8
    assert result == 9


def test_bounded_executor_rejects_execution_outside_allowlist():
    emulator = _tiny_thumb_emulator(b"\x70\x47", lr=0x40001)
    emulator.mem_map(0x40000, 0x1000, UC_PROT_READ | UC_PROT_EXEC)
    with pytest.raises(RuntimeError, match="escaped"):
        _execute_bounded(
            emulator, entry=0x10000,
            allowed_ranges=((0x10000, 0x10002),), sentinel=0x20000,
            import_stub=0x30000, instruction_limit=8, return_register=UC_ARM_REG_R0,
        )


def test_bounded_executor_stops_before_escaped_instruction_side_effect():
    emulator = _tiny_thumb_emulator(b"\x00\x47")
    emulator.mem_map(0x40000, 0x1000, UC_PROT_READ | UC_PROT_WRITE)
    emulator.mem_write(0x40000, b"\x11\x60")  # Thumb str r1,[r2]
    emulator.mem_protect(0x40000, 0x1000, UC_PROT_READ | UC_PROT_EXEC)
    emulator.mem_write(0x50000, struct.pack("<I", 0xDEADBEEF))
    emulator.reg_write(UC_ARM_REG_R0, 0x40000)
    emulator.reg_write(UC_ARM_REG_R1, 0x12345678)
    emulator.reg_write(UC_ARM_REG_R2, 0x50000)
    with pytest.raises(RuntimeError, match="escaped"):
        _execute_bounded(
            emulator, entry=0x10000, allowed_ranges=((0x10000, 0x10002),),
            sentinel=0x20000, import_stub=0x30000, instruction_limit=8,
            return_register=UC_ARM_REG_R0,
        )
    assert struct.unpack("<I", emulator.mem_read(0x50000, 4))[0] == 0xDEADBEEF


def test_bounded_executor_rejects_wide_thumb_instruction_crossing_range_end():
    emulator = _tiny_thumb_emulator(bytes.fromhex("00f000f8"))
    with pytest.raises(RuntimeError, match="escaped"):
        _execute_bounded(
            emulator, entry=0x10000, allowed_ranges=((0x10000, 0x10002),),
            sentinel=0x20000, import_stub=0x30000, instruction_limit=8,
            return_register=UC_ARM_REG_R0,
        )


def test_bounded_executor_rejects_arm_state_branch_inside_allowed_address_range():
    emulator = _tiny_thumb_emulator(b"\x00\x47")  # bx r0
    emulator.mem_map(0x40000, 0x1000, UC_PROT_READ | UC_PROT_WRITE)
    emulator.mem_write(0x40000, b"\x1e\xff\x2f\xe1")  # ARM bx lr
    emulator.mem_protect(0x40000, 0x1000, UC_PROT_READ | UC_PROT_EXEC)
    emulator.reg_write(UC_ARM_REG_R0, 0x40000)
    with pytest.raises(RuntimeError, match="escaped"):
        _execute_bounded(
            emulator, entry=0x10000,
            allowed_ranges=((0x10000, 0x10002), (0x40000, 0x40004)),
            sentinel=0x20000, import_stub=0x30000, instruction_limit=8,
            return_register=UC_ARM_REG_R0,
        )


def test_bounded_executor_allows_arm_state_only_inside_explicit_plt_range():
    emulator = _tiny_thumb_emulator(b"\x00\x47")  # bx r0, interworking to ARM
    emulator.mem_map(0x40000, 0x1000, UC_PROT_READ | UC_PROT_WRITE)
    emulator.mem_write(0x40000, b"\x1e\xff\x2f\xe1")  # ARM bx lr
    emulator.mem_protect(0x40000, 0x1000, UC_PROT_READ | UC_PROT_EXEC)
    emulator.reg_write(UC_ARM_REG_R0, 0x40000)
    emulator.reg_write(UC_ARM_REG_LR, 0x20001)
    steps, _result = _execute_bounded(
        emulator, entry=0x10000, allowed_ranges=((0x10000, 0x10002),),
        arm_ranges=((0x40000, 0x40004),), sentinel=0x20000,
        import_stub=0x30000, instruction_limit=8, return_register=UC_ARM_REG_R0,
    )
    assert steps == 3


def test_bounded_executor_runs_arm_plt_stub_through_local_import_and_back():
    emulator = _tiny_thumb_emulator(b"\x00\x47")  # Thumb bx r0 into ARM PLT
    emulator.mem_map(0x40000, 0x1000, UC_PROT_READ | UC_PROT_WRITE)
    # ARM PLT tail branch: ldr pc,[pc,#-4]; .word import_stub|1
    emulator.mem_write(0x40000, struct.pack("<II", 0xE51FF004, 0x30001))
    emulator.mem_protect(0x40000, 0x1000, UC_PROT_READ | UC_PROT_EXEC)
    emulator.reg_write(UC_ARM_REG_R0, 0x40000)
    steps, result = _execute_bounded(
        emulator, entry=0x10000, allowed_ranges=((0x10000, 0x10002), (0x40000, 0x40008)),
        arm_ranges=((0x40000, 0x40008),), sentinel=0x20000,
        import_stub=0x30000, instruction_limit=12, return_register=UC_ARM_REG_R0,
    )
    assert steps == 5
    assert result == 0


def test_bounded_executor_rejects_mid_stub_entry():
    emulator = _tiny_thumb_emulator(b"\x00\xbf")
    with pytest.raises(RuntimeError, match="escaped"):
        _execute_bounded(
            emulator, entry=0x30002,
            allowed_ranges=((0x10000, 0x10002),), sentinel=0x20000,
            import_stub=0x30000, instruction_limit=8,
            return_register=UC_ARM_REG_R0,
        )


def test_bounded_executor_stops_infinite_loop_at_per_call_budget():
    # b .
    emulator = _tiny_thumb_emulator(b"\xfe\xe7")
    with pytest.raises(RuntimeError, match="instruction budget"):
        _execute_bounded(
            emulator, entry=0x10000,
            allowed_ranges=((0x10000, 0x10002),), sentinel=0x20000,
            import_stub=0x30000, instruction_limit=8, return_register=UC_ARM_REG_R0,
        )


def test_emulator_permissions_are_read_from_real_unicorn_mappings():
    emulator = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    emulator.mem_map(0x700000, 0x20000, UC_PROT_READ | UC_PROT_WRITE)
    for address in (0x800000, 0x810000):
        emulator.mem_map(address, 0x1000, UC_PROT_READ | UC_PROT_WRITE)
        emulator.mem_write(address, b"\x70\x47")
        emulator.mem_protect(address, 0x1000, UC_PROT_READ | UC_PROT_EXEC)
    _validate_emulator_permissions(
        emulator.mem_regions(), stack=0x700000, import_stub=0x800000,
        return_stub=0x810000, read=UC_PROT_READ, write=UC_PROT_WRITE,
        execute=UC_PROT_EXEC,
    )


def test_elf_validator_rejects_non_arm32_and_non_shared_objects():
    class Format:
        elfclass = 64
        little_endian = True

        def __getitem__(self, key):
            return {"e_machine": "EM_X86_64", "e_type": "ET_EXEC"}[key]

    with pytest.raises(ValueError, match="ELF32 ARM"):
        _validate_elf_format(Format())

    class ArmExecutable:
        elfclass = 32
        little_endian = True

        def __getitem__(self, key):
            return {"e_machine": "EM_ARM", "e_type": "ET_EXEC"}[key]

    with pytest.raises(ValueError, match="ET_DYN"):
        _validate_elf_format(ArmExecutable())


class _FileBackedLoadSegment:
    def __init__(self, size=0x1000):
        self.size = size

    def __getitem__(self, key):
        return {"p_type": "PT_LOAD", "p_vaddr": 0x4000, "p_offset": 0x4000,
                "p_filesz": self.size, "p_memsz": self.size}[key]



def _packed_dynamic_segment(segment):
    names = {
        "DT_PLTRELSZ": 2, "DT_SYMTAB": 6, "DT_RELA": 7, "DT_RELASZ": 8,
        "DT_RELAENT": 9, "DT_SYMENT": 11, "DT_REL": 17, "DT_RELSZ": 18,
        "DT_RELENT": 19, "DT_PLTREL": 20, "DT_TEXTREL": 22, "DT_JMPREL": 23,
        "DT_FLAGS": 30, "DT_RELR": 36, "DT_RELRSZ": 35, "DT_RELRENT": 37,
    }
    entries = []
    for tag in segment.iter_tags():
        entry = tag.entry
        raw_tag = entry.d_tag
        numeric_tag = names.get(raw_tag, raw_tag) if isinstance(raw_tag, str) else raw_tag
        value = getattr(entry, "d_ptr", getattr(entry, "d_val", 0))
        entries.append(struct.pack("<II", numeric_tag, value))
    entries.append(bytes(8))
    return b"".join(entries)

def _dynamic_segment_value(key):
    return {"p_type": "PT_DYNAMIC", "p_vaddr": 0x4000, "p_offset": 0x4000,
            "p_filesz": 0x100, "p_memsz": 0x100}[key]


def test_dynamic_relocations_without_section_tables_fail_closed():
    from types import SimpleNamespace

    class DynamicSegment:
        def __getitem__(self, key):
            return _dynamic_segment_value(key)

        def data(self):
            return _packed_dynamic_segment(self)

        def iter_tags(self):
            return iter((
                SimpleNamespace(entry=SimpleNamespace(d_tag="DT_REL", d_ptr=0x4000)),
                SimpleNamespace(entry=SimpleNamespace(d_tag="DT_RELSZ", d_val=8)),
                SimpleNamespace(entry=SimpleNamespace(d_tag="DT_RELENT", d_val=8)),
            ))

    class ElfWithStrippedRelocations:
        def iter_segments(self):
            return iter((DynamicSegment(), _FileBackedLoadSegment()))

        def iter_sections(self):
            return iter(())

    with pytest.raises(ValueError, match="lacks an exact matching section"):
        _validate_dynamic_relocations(ElfWithStrippedRelocations(), type("RelSection", (), {}), 0x10000)


def test_dynamic_relocation_requires_matching_section_not_unrelated_section():
    from types import SimpleNamespace

    class DynamicSegment:
        def __getitem__(self, key):
            return _dynamic_segment_value(key)

        def data(self):
            return _packed_dynamic_segment(self)

        def iter_tags(self):
            return iter((
                SimpleNamespace(entry=SimpleNamespace(d_tag="DT_REL", d_ptr=0x4000)),
                SimpleNamespace(entry=SimpleNamespace(d_tag="DT_RELSZ", d_val=8)),
                SimpleNamespace(entry=SimpleNamespace(d_tag="DT_RELENT", d_val=8)),
            ))

    class RelocationSection:
        def __init__(self, address, *, section_type="SHT_REL", size=8, entry_size=8,
                     offset=None):
            self.values = {"sh_type": section_type, "sh_addr": address,
                           "sh_size": size, "sh_entsize": entry_size, "sh_flags": 2,
                           "sh_offset": address if offset is None else offset}

        def __getitem__(self, key):
            return self.values[key]

    class Elf:
        def __init__(self, address):
            self.address = address

        def iter_segments(self):
            return iter((DynamicSegment(), _FileBackedLoadSegment()))

        def iter_sections(self):
            return iter((RelocationSection(self.address),))

    with pytest.raises(ValueError, match="lacks an exact matching section"):
        _validate_dynamic_relocations(Elf(0x5000), RelocationSection, 0x10000)
    _validate_dynamic_relocations(Elf(0x4000), RelocationSection, 0x10000)


def test_dynamic_rela_table_requires_exact_allocated_rela_section():
    from types import SimpleNamespace

    class DynamicSegment:
        def __getitem__(self, key):
            return _dynamic_segment_value(key)

        def data(self):
            return _packed_dynamic_segment(self)

        def iter_tags(self):
            return iter((
                SimpleNamespace(entry=SimpleNamespace(d_tag="DT_RELA", d_ptr=0x4000)),
                SimpleNamespace(entry=SimpleNamespace(d_tag="DT_RELASZ", d_val=12)),
                SimpleNamespace(entry=SimpleNamespace(d_tag="DT_RELAENT", d_val=12)),
            ))

    class RelaSection:
        def __getitem__(self, key):
            return {"sh_type": "SHT_RELA", "sh_addr": 0x4000,
                    "sh_size": 12, "sh_entsize": 12, "sh_flags": 2,
                    "sh_offset": 0x4000}[key]

    class Elf:
        def iter_segments(self):
            return iter((DynamicSegment(), _FileBackedLoadSegment()))

        def iter_sections(self):
            return iter((RelaSection(),))

    tables, symbols = _validate_dynamic_relocations(Elf(), RelaSection, 0x10000)
    assert [(table.section_type, table.size) for table in tables] == [("SHT_RELA", 12)]
    assert symbols is None


def test_plt_rela_requires_supported_dt_pltrel_and_dynamic_symbols():
    from types import SimpleNamespace

    tags = (
        ("DT_JMPREL", "d_ptr", 0x4000), ("DT_PLTRELSZ", "d_val", 12),
        ("DT_PLTREL", "d_val", 7), ("DT_RELAENT", "d_val", 12),
        ("DT_SYMTAB", "d_ptr", 0x5000), ("DT_SYMENT", "d_val", 16),
    )

    class DynamicSegment:
        def __getitem__(self, key):
            return _dynamic_segment_value(key)

        def data(self):
            return _packed_dynamic_segment(self)

        def iter_tags(self):
            return iter(tuple(SimpleNamespace(entry=SimpleNamespace(d_tag=name, **{field: value}))
                              for name, field, value in tags))

    class Section:
        def __init__(self, values):
            self.values = values

        def __getitem__(self, key):
            return self.values[key]

    class RelaSection(Section):
        pass

    relocation = RelaSection({"sh_type": "SHT_RELA", "sh_addr": 0x4000,
                              "sh_size": 12, "sh_entsize": 12, "sh_flags": 2,
                              "sh_offset": 0x4000})
    symbols = Section({"sh_type": "SHT_DYNSYM", "sh_addr": 0x5000,
                       "sh_size": 16, "sh_entsize": 16, "sh_flags": 2,
                       "sh_offset": 0x5000})

    class Elf:
        def iter_segments(self):
            return iter((DynamicSegment(), _FileBackedLoadSegment(0x1010)))

        def iter_sections(self):
            return iter((relocation, symbols))

    tables, dynamic_symbols = _validate_dynamic_relocations(Elf(), RelaSection, 0x10000)
    assert tables[0].is_plt
    assert dynamic_symbols == (0x5000, 1)


def test_plt_relocations_without_dt_pltrel_fail_closed():
    from types import SimpleNamespace

    class DynamicSegment:
        def __getitem__(self, key):
            return _dynamic_segment_value(key)

        def data(self):
            return _packed_dynamic_segment(self)

        def iter_tags(self):
            return iter((
                SimpleNamespace(entry=SimpleNamespace(d_tag="DT_JMPREL", d_ptr=0x4000)),
                SimpleNamespace(entry=SimpleNamespace(d_tag="DT_PLTRELSZ", d_val=8)),
            ))

    class Elf:
        def iter_segments(self):
            return iter((DynamicSegment(), _FileBackedLoadSegment()))

        def iter_sections(self):
            return iter(())

    with pytest.raises(ValueError, match="DT_PLTREL is missing or unsupported"):
        _validate_dynamic_relocations(Elf(), type("RelSection", (), {}), 0x10000)


def test_dynamic_relr_relocations_fail_closed():
    from types import SimpleNamespace

    class DynamicSegment:
        def __getitem__(self, key):
            return _dynamic_segment_value(key)

        def data(self):
            return _packed_dynamic_segment(self)

        def iter_tags(self):
            return iter((SimpleNamespace(entry=SimpleNamespace(d_tag=35, d_val=8)),))

    class ElfWithRelr:
        def iter_segments(self):
            return iter((DynamicSegment(), _FileBackedLoadSegment()))

        def iter_sections(self):
            return iter(())

    with pytest.raises(ValueError, match="DT_RELR"):
        _validate_dynamic_relocations(ElfWithRelr(), type("RelSection", (), {}), 0x10000)


def test_text_relocations_fail_closed():
    from types import SimpleNamespace

    class DynamicSegment:
        def __getitem__(self, key):
            return _dynamic_segment_value(key)

        def data(self):
            return _packed_dynamic_segment(self)

        def iter_tags(self):
            return iter((SimpleNamespace(entry=SimpleNamespace(d_tag=22, d_val=0)),))

    class Elf:
        def iter_segments(self):
            return iter((DynamicSegment(), _FileBackedLoadSegment()))

        def iter_sections(self):
            return iter(())

    with pytest.raises(ValueError, match="DT_TEXTREL"):
        _validate_dynamic_relocations(Elf(), type("RelSection", (), {}), 0x10000)


def test_df_textrel_flag_fails_closed():
    from types import SimpleNamespace

    class DynamicSegment:
        def __getitem__(self, key):
            return _dynamic_segment_value(key)

        def iter_tags(self):
            return iter((SimpleNamespace(entry=SimpleNamespace(d_tag=30, d_val=4)),))

        def data(self):
            return struct.pack("<II", 30, 4) + bytes(8)

    class Elf:
        def iter_segments(self):
            return iter((DynamicSegment(), _FileBackedLoadSegment()))

        def iter_sections(self):
            return iter(())

    with pytest.raises(ValueError, match="DF_TEXTREL"):
        _validate_dynamic_relocations(Elf(), type("RelSection", (), {}), 0x10000)


def test_numeric_android_packed_relocation_tag_fails_closed():
    from types import SimpleNamespace

    class DynamicSegment:
        def __getitem__(self, key):
            return _dynamic_segment_value(key)

        def data(self):
            return _packed_dynamic_segment(self)

        def iter_tags(self):
            return iter((SimpleNamespace(entry=SimpleNamespace(d_tag=0x6000000F, d_ptr=0x4000)),))

    class Elf:
        def iter_segments(self):
            return iter((DynamicSegment(), _FileBackedLoadSegment()))

        def iter_sections(self):
            return iter(())

    with pytest.raises(ValueError, match="Android packed relocations"):
        _validate_dynamic_relocations(Elf(), type("RelSection", (), {}), 0x10000)


def test_symbol_resolution_checks_expected_elf_kind():
    elf = _Elf([_Symbol("table", 0x1000, 24, symbol_type="STT_OBJECT")])
    with pytest.raises(ValueError, match="STT_FUNC"):
        _symbol_details(elf, "table", expected_type="STT_FUNC")


def test_symbol_resolution_enforces_storage_extent():
    elf = _Elf([_Symbol("callbacks", 0x1000, 8, symbol_type="STT_OBJECT")])
    with pytest.raises(ValueError, match="size"):
        _symbol_details(elf, "callbacks", minimum_size=24, expected_type="STT_OBJECT")


def test_executable_ranges_must_be_file_backed_not_zero_filled_segment_tail():
    class Segment:
        def __getitem__(self, key):
            return {"p_type": "PT_LOAD", "p_flags": 1, "p_vaddr": 0x1000,
                    "p_filesz": 0x100, "p_memsz": 0x200}[key]

    class Elf:
        def iter_segments(self):
            return iter((Segment(),))

    assert _range_in_executable_load_segment(Elf(), 0x1000, 0x1100)
    assert not _range_in_executable_load_segment(Elf(), 0x10F0, 0x1110)


def test_probe_rejects_wrong_callback_layout_before_loading_artifact(tmp_path: Path):
    with pytest.raises(ValueError, match="exactly six"):
        run_registration_probe(
            tmp_path / "missing.so", "0" * 64, "entry", "callbacks", "flag",
            (1, 2, 3), (4, 5, 6), 0, 1,
        )
