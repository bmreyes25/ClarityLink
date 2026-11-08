import argparse
from dataclasses import replace
import hashlib
from io import BytesIO
from pathlib import Path
import struct

import pytest
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_PROT_READ, UC_PROT_WRITE, UC_PROT_EXEC
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_SP

from tools.honda_native_boundary_probe import (
    IMPORT_BASE,
    DEPENDENCY_START_ADDRESS,
    LOAD_BASE,
    PAGE_SIZE,
    MAX_DYNAMIC_BYTES,
    RETURN_BASE,
    STACK_BASE,
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
    _elf_declares_textrel,
    plan_elf32_mapping,
    map_elf32_segments,
    map_elf32_dependency_segments,
    ELF32Dependency,
    ResolvedELF32Symbol,
    _api17_resolve_symbol,
    plan_elf32_dependency_mappings,
    _relocation_value,
    run_registration_probe,
)


def _synthetic_arm_shared_object(path: Path, *, thumb_function: bool = True,
                                plt_executable: bool = True,
                                plt_section_flags: int = 6,
                                plt_flags: int | None = None,
                                plt_address: int = 0x3000,
                                plt_file_offset: int = 0x3000,
                                plt_alignment: int = 0x1000,
                                defined_import: bool = False,
                                plt_size_override: int | None = None,
                                relative_target: int = 0x2020,
                                relative_initial_addend: int | None = None,
                                relative_symbol_index: int = 0,
                                glob_dat_symbol_index: int | None = None,
                                abs32_symbol_index: int | None = None,
                                import_binding: int = 1,
                                callback_table_section_index: int = 2,
                                jump_symbol_index: int = 4,
                                pt_dynamic_offset_delta: int = 0,
                                rel_dyn_section_offset_delta: int = 0,
                                dynstr_address_override: int | None = None,
                                data_bss_bytes: int = 0,
                                declare_textrel: bool = False,
                                register_symbol_info: int = 0x12,
                                dynsym_first_global: int = 1,
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
    data = bytearray(struct.pack("<6I", *initial_callback_table)
                     + struct.pack("<I", initial_registration_flag) + bytes(4)
                     + struct.pack("<II", 0x10, 0x20))
    if relative_initial_addend is not None:
        if 0x1000 <= relative_target < 0x1000 + len(code):
            struct.pack_into("<I", code, relative_target - 0x1000, relative_initial_addend)
        elif 0x2000 <= relative_target < 0x2000 + len(data):
            struct.pack_into("<I", data, relative_target - 0x2000, relative_initial_addend)
        else:
            raise ValueError("synthetic relocation addend must be in the code or data fixture")
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
    dynsym += struct.pack("<IIIBBH", dynstr_offsets["register_cb"], function_value, 48,
                          register_symbol_info, 0, 1)
    dynsym += struct.pack("<IIIBBH", dynstr_offsets["callback_table"], 0x2000, 24, 0x11, 0,
                          callback_table_section_index)
    dynsym += struct.pack("<IIIBBH", dynstr_offsets["registration_flag"],
                          registration_flag_address, 4, 0x11, 0, 2)
    import_shndx = 1 if defined_import else 0
    dynsym += struct.pack("<IIIBBH", dynstr_offsets["external_probe"], 0, 0,
                          (import_binding << 4) | 2, 0, import_shndx)
    relative_relocation = struct.pack("<II", relative_target, (relative_symbol_index << 8) | 23)
    glob_dat_relocation = (b"" if glob_dat_symbol_index is None else
                           struct.pack("<II", 0x2024, (glob_dat_symbol_index << 8) | 21))
    abs32_relocation = (b"" if abs32_symbol_index is None else
                        struct.pack("<II", 0x2024, (abs32_symbol_index << 8) | 2))
    rel_dyn = relative_relocation + glob_dat_relocation + abs32_relocation
    jump_slot_relocation = struct.pack("<II", 0x201C, (jump_symbol_index << 8) | 22)

    text_offset, data_offset = 0x1000, 0x2000
    plt_offset = plt_file_offset
    metadata_offset = 0x4000
    metadata = bytearray(rel_dyn + jump_slot_relocation)
    dynsym_relative = len(metadata)
    metadata.extend(dynsym)
    dynstr_relative = len(metadata)
    metadata.extend(dynstr)
    dynamic_relative = (len(metadata) + 3) & ~3
    metadata.extend(bytes(dynamic_relative - len(metadata)))
    dynamic_tags = (
        (17, metadata_offset), (18, len(rel_dyn)), (19, 8),
        (23, metadata_offset + len(rel_dyn)), (2, len(jump_slot_relocation)),
        (20, 17), (5, metadata_offset + dynstr_relative if dynstr_address_override is None
                   else dynstr_address_override), (10, len(dynstr)),
        (6, metadata_offset + dynsym_relative), (11, 16), (0, 0),
    )
    if declare_textrel:
        dynamic_tags = dynamic_tags[:-1] + ((22, 0), dynamic_tags[-1])
    dynamic = b"".join(struct.pack("<II", *item) for item in dynamic_tags)
    metadata.extend(dynamic)
    rel_dyn_offset = metadata_offset
    rel_plt_offset = metadata_offset + len(rel_dyn)
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
                         len(data), len(data) + data_bss_bytes, 6, 0x1000)
    phdrs += struct.pack("<IIIIIIII", 1, plt_offset, plt_address, plt_address,
                         len(plt), len(plt),
                         plt_flags if plt_flags is not None else (5 if plt_executable else 6),
                         plt_alignment)
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
    sections.append(section(".plt", 1, plt_flags if plt_flags is not None else plt_section_flags,
                            plt_address, plt_offset, len(plt), align=4))
    sections.append(section(".shstrtab", 3, 0, 0, shstr_offset, len(shstr)))
    sections.append(section(".dynstr", 3, 2, dynstr_offset, dynstr_offset, len(dynstr)))
    sections.append(section(".dynsym", 11, 2, dynsym_offset, dynsym_offset, len(dynsym),
                            link=5, info=dynsym_first_global, align=4, entsize=16))
    sections.append(section(".rel.dyn", 9, 2, rel_dyn_offset,
                            rel_dyn_offset + rel_dyn_section_offset_delta, len(rel_dyn),
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


def _synthetic_mapping_elf(path: Path, **options):
    digest = _synthetic_arm_shared_object(path, **options)
    raw = path.read_bytes()
    return _elf32_file(raw), raw, digest


def _elf32_file(raw):
    from elftools.elf.elffile import ELFFile

    return ELFFile(BytesIO(raw))


def test_segment_mapper_copies_load_images_and_zeroes_bss(tmp_path: Path):
    artifact = tmp_path / "mapping-bss.so"
    _initial_elf, _raw, digest = _synthetic_mapping_elf(artifact, data_bss_bytes=32)
    raw = bytearray(artifact.read_bytes())
    data_load = next(
        segment for segment in _initial_elf.iter_segments()
        if segment["p_type"] == "PT_LOAD" and int(segment["p_vaddr"]) == 0x2000
    )
    file_tail = int(data_load["p_offset"]) + int(data_load["p_filesz"])
    raw[file_tail:file_tail + 32] = bytes([0xA5]) * 32
    artifact.write_bytes(raw)
    source_digest = hashlib.sha256(raw).hexdigest()
    elf = _elf32_file(raw)
    plan = plan_elf32_mapping(elf, "synthetic-provider", 0x01000000)
    emulator = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    regions = map_elf32_segments(emulator, elf, plan)

    assert emulator.mem_read(0x01002000, int(data_load["p_filesz"])) == raw[
        int(data_load["p_offset"]):file_tail
    ]
    assert bytes(raw[file_tail:file_tail + 32]) == bytes([0xA5]) * 32
    assert emulator.mem_read(0x01002000 + int(data_load["p_filesz"]), 32) == bytes(32)
    assert [region[2] for region in regions if region[0] == 0x01001000] == [UC_PROT_READ | UC_PROT_EXEC]
    assert [region[2] for region in regions if region[0] == 0x01002000] == [UC_PROT_READ | UC_PROT_WRITE]
    assert hashlib.sha256(artifact.read_bytes()).hexdigest() == source_digest


def test_writable_unaligned_file_tail_is_zeroed_without_explicit_bss(tmp_path: Path):
    artifact = tmp_path / "mapping-writable-page-tail.so"
    _initial_elf, raw, _digest = _synthetic_mapping_elf(artifact)
    data_load_index = next(
        index for index in range(struct.unpack_from("<H", raw, 44)[0])
        if struct.unpack_from("<I", raw, 52 + index * 32)[0] == 1
        and struct.unpack_from("<I", raw, 52 + index * 32 + 8)[0] == 0x2000
    )
    header = 52 + data_load_index * 32
    file_size = 0x19
    patched = bytearray(raw)
    struct.pack_into("<II", patched, header + 16, file_size, file_size)
    patched[0x2000 + file_size:0x3000] = bytes([0xA5]) * (PAGE_SIZE - file_size)
    artifact.write_bytes(patched)
    elf = _elf32_file(patched)
    plan = plan_elf32_mapping(elf, "writable-tail", 0x01000000)
    emulator = Uc(UC_ARCH_ARM, UC_MODE_THUMB)

    map_elf32_segments(emulator, elf, plan)

    assert emulator.mem_read(0x01002000, file_size) == patched[0x2000:0x2000 + file_size]
    assert emulator.mem_read(0x01002000 + file_size, PAGE_SIZE - file_size) == bytes(PAGE_SIZE - file_size)


def test_segment_mapper_rejects_reserved_runtime_range_before_mapping(tmp_path: Path):
    artifact = tmp_path / "mapping-reserved-runtime.so"
    elf, _raw, _digest = _synthetic_mapping_elf(artifact)
    load_bias = STACK_BASE - 0x1000
    plan = plan_elf32_mapping(elf, "reserved-runtime", load_bias)
    emulator = Uc(UC_ARCH_ARM, UC_MODE_THUMB)

    with pytest.raises(ValueError, match="reserved emulator runtime mapping"):
        map_elf32_segments(emulator, elf, plan)
    assert tuple(emulator.mem_regions()) == ()


def test_root_loader_rejects_dependency_address_range(tmp_path: Path):
    artifact = tmp_path / "root-dependency-range.so"
    digest = _synthetic_arm_shared_object(artifact)
    elf, _raw, relocation_tables, dynamic_symbols = _read_elf(artifact, digest)
    emulator = Uc(UC_ARCH_ARM, UC_MODE_THUMB)

    with pytest.raises(ValueError, match="reserved root image address range"):
        _load_image(
            emulator, elf, relocation_tables, dynamic_symbols,
            load_bias=DEPENDENCY_START_ADDRESS - 0x1000,
            map_runtime_support=False,
        )
    assert tuple(emulator.mem_regions()) == ()


def test_root_loader_keeps_runtime_range_reserved_without_optional_stubs(tmp_path: Path):
    artifact = tmp_path / "root-runtime-range.so"
    digest = _synthetic_arm_shared_object(artifact)
    elf, _raw, relocation_tables, dynamic_symbols = _read_elf(artifact, digest)
    emulator = Uc(UC_ARCH_ARM, UC_MODE_THUMB)

    with pytest.raises(ValueError, match="overlaps an existing image or reserved mapping"):
        _load_image(
            emulator, elf, relocation_tables, dynamic_symbols,
            load_bias=STACK_BASE - 0x1000, map_runtime_support=False,
        )
    assert tuple(emulator.mem_regions()) == ()


def test_segment_mapper_rejects_source_bytes_changed_after_planning(tmp_path: Path):
    artifact = tmp_path / "mapping-source-changed.so"
    elf, raw, _digest = _synthetic_mapping_elf(artifact)
    plan = plan_elf32_mapping(elf, "source-bound-plan", 0x02000000)
    changed = bytearray(raw)
    changed[0x1010] ^= 0x01
    changed_elf = _elf32_file(changed)
    emulator = Uc(UC_ARCH_ARM, UC_MODE_THUMB)

    with pytest.raises(ValueError, match="plan does not match current source bytes"):
        map_elf32_segments(emulator, changed_elf, plan)
    assert tuple(emulator.mem_regions()) == ()


def test_segment_mapper_rechecks_plan_specific_mapping_limit(tmp_path: Path):
    artifact = tmp_path / "mapping-plan-limit.so"
    elf, _raw, _digest = _synthetic_mapping_elf(artifact)
    plan = plan_elf32_mapping(elf, "plan-limit", 0x02000000)
    constrained = replace(plan, max_mapping_bytes=PAGE_SIZE)
    emulator = Uc(UC_ARCH_ARM, UC_MODE_THUMB)

    with pytest.raises(ValueError, match="bounded mapping size"):
        map_elf32_segments(emulator, elf, constrained)
    assert tuple(emulator.mem_regions()) == ()


def test_segment_mapper_reads_only_from_its_verified_source_snapshot(tmp_path: Path):
    from elftools.elf.elffile import ELFFile

    artifact = tmp_path / "mapping-snapshot-source.so"
    _initial, raw, _digest = _synthetic_mapping_elf(artifact)

    class MutableStream(BytesIO):
        mutate_reads = False

        def read(self, size=-1):
            data = super().read(size)
            if self.mutate_reads:
                return bytes((byte ^ 0xFF) for byte in data)
            return data

    stream = MutableStream(raw)
    elf = ELFFile(stream)
    plan = plan_elf32_mapping(elf, "snapshot-bound", 0x02000000)
    stream.mutate_reads = True
    emulator = Uc(UC_ARCH_ARM, UC_MODE_THUMB)

    map_elf32_segments(emulator, elf, plan)

    assert emulator.mem_read(0x02001000, 32) == raw[0x1000:0x1020]


def test_segment_planner_rejects_source_above_artifact_limit(tmp_path: Path, monkeypatch):
    artifact = tmp_path / "mapping-source-limit.so"
    elf, raw, _digest = _synthetic_mapping_elf(artifact)
    monkeypatch.setattr("tools.honda_native_boundary_probe.MAX_ARTIFACT_BYTES", len(raw) - 1)

    with pytest.raises(ValueError, match="source-size bound"):
        plan_elf32_mapping(elf, "oversized-source", 0x02000000)


def test_segment_mapper_rejects_oversized_source_before_snapshot_copy(tmp_path: Path, monkeypatch):
    artifact = tmp_path / "mapping-snapshot-limit.so"
    elf, raw, _digest = _synthetic_mapping_elf(artifact)
    plan = plan_elf32_mapping(elf, "snapshot-size-limit", 0x02000000)
    monkeypatch.setattr("tools.honda_native_boundary_probe.MAX_ARTIFACT_BYTES", len(raw) - 1)
    emulator = Uc(UC_ARCH_ARM, UC_MODE_THUMB)

    with pytest.raises(ValueError, match="source-size bound"):
        map_elf32_segments(emulator, elf, plan)
    assert tuple(emulator.mem_regions()) == ()


def test_segment_mapper_shared_page_uses_later_api17_segment_protection(tmp_path: Path):
    artifact = tmp_path / "mapping-shared-page.so"
    elf, _raw, _digest = _synthetic_mapping_elf(
        artifact, plt_address=0x1FF0, plt_file_offset=0x1FF0,
        plt_alignment=0x1000, plt_flags=6,
    )
    plan = plan_elf32_mapping(elf, "shared-page", 0x02000000)
    emulator = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    regions = map_elf32_segments(emulator, elf, plan)

    assert emulator.mem_read(0x02001000, 32) == elf.stream.getvalue()[0x1000:0x1020]
    assert emulator.mem_read(0x02001FF0, 12) == elf.stream.getvalue()[0x1FF0:0x1FFC]
    page = next(region for region in regions if region[0] == 0x02001000)
    assert page[2] == UC_PROT_READ | UC_PROT_WRITE


def test_segment_mapper_shared_page_permissions_follow_final_program_header(tmp_path: Path):
    artifact = tmp_path / "mapping-shared-page-reversed.so"
    _elf, raw, _digest = _synthetic_mapping_elf(
        artifact, plt_address=0x1FF0, plt_file_offset=0x1FF0,
        plt_alignment=0x1000, plt_flags=6,
    )
    data = bytearray(raw)
    first = bytes(data[52:84])
    third = bytes(data[52 + 64:52 + 96])
    data[52:84] = third
    data[52 + 64:52 + 96] = first
    struct.pack_into("<I", data, 52 + 4, 0x3FF0)
    artifact.write_bytes(data)
    elf = _elf32_file(data)
    plan = plan_elf32_mapping(elf, "reversed-page-order", 0x02100000)
    emulator = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    regions = map_elf32_segments(emulator, elf, plan)

    sharing_segments = [
        segment for segment in elf.iter_segments()
        if segment["p_type"] == "PT_LOAD"
        and ((0x02100000 + int(segment["p_vaddr"])) & ~(PAGE_SIZE - 1)) == 0x02101000
    ]
    assert len(sharing_segments) >= 2
    earlier, later = sharing_segments[-2:]
    earlier_file_page = int(earlier["p_offset"]) & ~(PAGE_SIZE - 1)
    later_file_page = int(later["p_offset"]) & ~(PAGE_SIZE - 1)
    assert earlier_file_page != later_file_page
    assert data[earlier_file_page + 0xFF0:earlier_file_page + 0xFFC] != data[
        later_file_page + 0xFF0:later_file_page + 0xFFC
    ]
    assert emulator.mem_read(0x02101000, PAGE_SIZE) == data[later_file_page:later_file_page + PAGE_SIZE]
    assert emulator.mem_read(0x02101FF0, 12) == data[0x1FF0:0x1FFC]
    page = next(region for region in regions if region[0] == 0x02101000)
    assert page[2] == UC_PROT_READ | UC_PROT_EXEC


def test_segment_mapper_shared_page_maps_the_later_file_page(tmp_path: Path):
    artifact = tmp_path / "mapping-shared-page-different-file-page.so"
    elf, raw, _digest = _synthetic_mapping_elf(
        artifact, plt_address=0x1FF0, plt_file_offset=0x3FF0,
        plt_alignment=0x1000, plt_flags=5,
    )
    plan = plan_elf32_mapping(elf, "shared-page-later-file", 0x02400000)
    emulator = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    map_elf32_segments(emulator, elf, plan)

    assert emulator.mem_read(0x02401000, PAGE_SIZE) == raw[0x3000:0x4000]
    assert emulator.mem_read(0x02401FF0, 12) == raw[0x3FF0:0x3FFC]


def test_segment_mapper_three_shared_headers_apply_last_bss_page(tmp_path: Path):
    artifact = tmp_path / "mapping-three-shared-headers.so"
    _elf, raw, _digest = _synthetic_mapping_elf(artifact)
    data = bytearray(raw)
    for index, file_offset, virtual_address, file_size, memory_size, flags in (
        (0, 0x1000, 0x1000, 0x20, 0x20, 5),
        (1, 0x2020, 0x1020, 0x8, 0x8, 6),
        (2, 0x3028, 0x1028, 0, 0x40, 6),
    ):
        header = 52 + index * 32
        struct.pack_into("<III", data, header + 4,
                         file_offset, virtual_address, virtual_address)
        struct.pack_into("<III", data, header + 16,
                         file_size, memory_size, flags)
    elf = _elf32_file(data)
    plan = plan_elf32_mapping(elf, "three-shared-headers", 0x02600000)
    emulator = Uc(UC_ARCH_ARM, UC_MODE_THUMB)

    regions = map_elf32_segments(emulator, elf, plan)

    assert emulator.mem_read(0x02601000, 0x28) == data[0x3000:0x3028]
    assert emulator.mem_read(0x02601028, 0xD8) == bytes(0xD8)
    page = next(region for region in regions if region[0] == 0x02601000)
    assert page[2] == UC_PROT_READ | UC_PROT_WRITE


def test_segment_planner_rejects_readonly_partial_page_bss(tmp_path: Path):
    artifact = tmp_path / "mapping-readonly-bss.so"
    _synthetic_arm_shared_object(artifact, data_bss_bytes=32)
    raw = bytearray(artifact.read_bytes())
    struct.pack_into("<I", raw, 52 + 32 + 24, 4)
    elf = _elf32_file(raw)
    with pytest.raises(ValueError, match="read-only partial-page BSS"):
        plan_elf32_mapping(elf, "readonly-bss", 0x02500000)


def test_segment_planner_rejects_readonly_unaligned_zero_filesz_segment(tmp_path: Path):
    artifact = tmp_path / "mapping-readonly-zero-filesz.so"
    _synthetic_arm_shared_object(artifact)
    data = bytearray(artifact.read_bytes())
    phdr = 52 + 32
    struct.pack_into("<III", data, phdr + 4, 0x2028, 0x2028, 0x2028)
    struct.pack_into("<II", data, phdr + 16, 0, 0x20)
    struct.pack_into("<I", data, phdr + 24, 4)
    elf = _elf32_file(data)

    with pytest.raises(ValueError, match="read-only partial-page BSS"):
        plan_elf32_mapping(elf, "readonly-zero-filesz", 0x02510000)


@pytest.mark.parametrize(
    ("options", "message"),
    [
        ({"plt_address": 0x1FF0, "plt_file_offset": 0x3FF0, "plt_flags": 7},
         "writable executable page"),
        ({"data_bss_bytes": -1}, "file or memory bounds"),
    ],
)
def test_segment_mapper_rejects_unsafe_segment_layout(tmp_path: Path, options, message):
    artifact = tmp_path / "invalid-mapping.so"
    elf, _raw, _digest = _synthetic_mapping_elf(artifact, **options)
    with pytest.raises(ValueError, match=message):
        plan_elf32_mapping(elf, "invalid", 0x03000000)


def test_segment_mapper_rejects_unaligned_bias_and_empty_identity(tmp_path: Path):
    artifact = tmp_path / "mapping-arguments.so"
    elf, _raw, _digest = _synthetic_mapping_elf(artifact)
    with pytest.raises(ValueError, match="page-aligned"):
        plan_elf32_mapping(elf, "image", 0x01000001)
    with pytest.raises(ValueError, match="identity"):
        plan_elf32_mapping(elf, "", 0x01000000)


def test_segment_mapper_rejects_load_bias_overflow_and_existing_overlap(tmp_path: Path):
    artifact = tmp_path / "mapping-bounds.so"
    elf, _raw, _digest = _synthetic_mapping_elf(artifact)
    with pytest.raises(ValueError, match="overflows ELF32"):
        plan_elf32_mapping(elf, "overflow", 0xFFFFF000)
    with pytest.raises(ValueError, match="overlaps an existing image"):
        plan_elf32_mapping(elf, "collision", 0x01000000,
                           mapped_ranges=((0x01001000, 0x01002000),))


def test_segment_mapper_rejects_invalid_file_offset(tmp_path: Path):
    from elftools.elf.elffile import ELFFile

    artifact = tmp_path / "mapping-invalid-offset.so"
    _synthetic_arm_shared_object(artifact)
    raw = bytearray(artifact.read_bytes())
    struct.pack_into("<I", raw, 88, len(raw) + 1)
    elf = ELFFile(BytesIO(raw))
    with pytest.raises(ValueError, match="file or memory bounds"):
        plan_elf32_mapping(elf, "bad-file-range", 0x04000000)


def test_segment_planner_rejects_nonreadable_load_segment(tmp_path: Path):
    artifact = tmp_path / "mapping-nonreadable.so"
    _synthetic_arm_shared_object(artifact)
    raw = bytearray(artifact.read_bytes())
    struct.pack_into("<I", raw, 52 + 24, 1)
    elf = _elf32_file(raw)
    with pytest.raises(ValueError, match="without read permission"):
        plan_elf32_mapping(elf, "nonreadable-load", 0x04000000)


def test_textrel_inspection_rejects_out_of_file_dynamic_segment(tmp_path: Path):
    from elftools.elf.elffile import ELFFile

    artifact = tmp_path / "mapping-invalid-dynamic.so"
    _synthetic_arm_shared_object(artifact, declare_textrel=True)
    raw = bytearray(artifact.read_bytes())
    original = ELFFile(BytesIO(raw))
    dynamic_index = next(
        index for index, segment in enumerate(original.iter_segments())
        if segment["p_type"] == "PT_DYNAMIC"
    )
    struct.pack_into("<I", raw, 52 + dynamic_index * 32 + 4, len(raw) + 1)

    with pytest.raises(ValueError, match="PT_DYNAMIC is outside consistent"):
        _elf_declares_textrel(ELFFile(BytesIO(raw)))


def test_dynamic_segment_rejects_excessive_entry_count_before_read(tmp_path: Path):
    from elftools.elf.elffile import ELFFile
    from elftools.elf.relocation import RelocationSection

    artifact = tmp_path / "mapping-oversized-dynamic.so"
    _synthetic_arm_shared_object(artifact)
    raw = bytearray(artifact.read_bytes())
    original = ELFFile(BytesIO(raw))
    dynamic_index = next(
        index for index, segment in enumerate(original.iter_segments())
        if segment["p_type"] == "PT_DYNAMIC"
    )
    dynamic_header = 52 + dynamic_index * 32
    excessive_size = MAX_DYNAMIC_BYTES + 8
    struct.pack_into("<II", raw, dynamic_header + 16, excessive_size, excessive_size)
    elf = ELFFile(BytesIO(raw))

    with pytest.raises(ValueError, match="PT_DYNAMIC exceeds the supported entry-count bound"):
        _elf_declares_textrel(elf)
    with pytest.raises(ValueError, match="PT_DYNAMIC exceeds the supported entry-count bound"):
        _validate_dynamic_relocations(elf, RelocationSection, len(raw))


def test_segment_mapper_rejects_out_of_bounds_program_header_table(tmp_path: Path):
    artifact = tmp_path / "mapping-invalid-phdr-table.so"
    _synthetic_arm_shared_object(artifact)
    raw = bytearray(artifact.read_bytes())
    struct.pack_into("<I", raw, 28, len(raw) + 1)
    elf = _elf32_file(raw)
    with pytest.raises(ValueError, match="program-header table is outside file bounds"):
        plan_elf32_mapping(elf, "bad-phdr-table", 0x04000000)
    with pytest.raises(ValueError, match="program-header table is outside file bounds"):
        plan_elf32_dependency_mappings((("bad-phdr-table", elf),))


def test_segment_mapper_rejects_invalid_program_alignment(tmp_path: Path):
    from elftools.elf.elffile import ELFFile

    artifact = tmp_path / "mapping-invalid-alignment.so"
    _synthetic_arm_shared_object(artifact)
    raw = bytearray(artifact.read_bytes())
    struct.pack_into("<I", raw, 112, 3)
    elf = ELFFile(BytesIO(raw))
    with pytest.raises(ValueError, match="alignment is invalid"):
        plan_elf32_mapping(elf, "bad-alignment", 0x04000000)


def test_segment_mapper_rejects_memory_limit_and_emulator_collision(tmp_path: Path):
    artifact = tmp_path / "mapping-limits.so"
    elf, _raw, _digest = _synthetic_mapping_elf(artifact)
    with pytest.raises(ValueError, match="mapping size"):
        plan_elf32_mapping(elf, "too-large", 0x01000000, max_mapping_bytes=PAGE_SIZE)
    plan = plan_elf32_mapping(elf, "mapped", 0x01000000)
    emulator = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    emulator.mem_map(0x01001000, 0x1000, UC_PROT_READ)
    with pytest.raises(ValueError, match="overlaps an existing emulator mapping"):
        map_elf32_segments(emulator, elf, plan)

    with pytest.raises(ValueError, match="total emulator memory bound"):
        map_elf32_segments(Uc(UC_ARCH_ARM, UC_MODE_THUMB), elf, plan,
                           max_total_mapped_bytes=PAGE_SIZE)


def test_segment_mapper_rolls_back_partial_mapping_after_write_failure(tmp_path: Path):
    artifact = tmp_path / "mapping-write-failure.so"
    elf, _raw, _digest = _synthetic_mapping_elf(artifact)
    plan = plan_elf32_mapping(elf, "rollback-fixture", 0x02300000)

    class FailingWriteUc:
        def __init__(self):
            self.inner = Uc(UC_ARCH_ARM, UC_MODE_THUMB)

        def __getattr__(self, name):
            return getattr(self.inner, name)

        def mem_write(self, _address, _data):
            raise RuntimeError("injected host write failure")

    emulator = FailingWriteUc()
    with pytest.raises(RuntimeError, match="injected host write failure"):
        map_elf32_segments(emulator, elf, plan)
    assert tuple(emulator.mem_regions()) == ()


def test_segment_mapper_handles_bss_only_unaligned_segment(tmp_path: Path):
    artifact = tmp_path / "mapping-bss-only.so"
    _elf, raw, _digest = _synthetic_mapping_elf(artifact)
    data = bytearray(raw)
    phdr = 52 + 32
    struct.pack_into("<III", data, phdr + 4, 0x2028, 0x2028, 0x2028)
    struct.pack_into("<II", data, phdr + 16, 0, 0x20)
    artifact.write_bytes(data)
    elf = _elf32_file(data)
    plan = plan_elf32_mapping(elf, "bss-only", 0x02200000)
    emulator = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    map_elf32_segments(emulator, elf, plan)

    assert emulator.mem_read(0x02202000, 0x48) == data[0x2000:0x2028] + bytes(0x20)


def test_relocation_loader_uses_mapped_image_load_bias(tmp_path: Path):
    artifact = tmp_path / "biased-relocation.so"
    digest = _synthetic_arm_shared_object(artifact)
    elf, _raw, relocation_tables, dynamic_symbols = _read_elf(artifact, digest)
    bias = 0x00600000
    emulator = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    _load_image(
        emulator, elf, relocation_tables, dynamic_symbols,
        identity="biased-fixture", load_bias=bias,
        map_runtime_support=True,
    )
    assert struct.unpack("<I", emulator.mem_read(bias + 0x2020, 4))[0] == bias + 0x10


def test_writable_segment_relocation_uses_temporary_nx_on_readonly_shared_page(tmp_path: Path):
    artifact = tmp_path / "writable-relocation-shared-page.so"
    _synthetic_arm_shared_object(
        artifact, plt_address=0x1FF0, plt_file_offset=0x1FF0,
        plt_flags=6, plt_alignment=0x1000, declare_textrel=True,
    )
    raw = bytearray(artifact.read_bytes())
    first = bytes(raw[52:84])
    third = bytes(raw[52 + 64:52 + 96])
    raw[52:84] = third
    raw[52 + 64:52 + 96] = first
    struct.pack_into("<I", raw, 0x4000, 0x1FF0)
    artifact.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    elf, _raw, relocation_tables, dynamic_symbols = _read_elf(
        artifact, digest, allow_textrel=True,
    )

    class RecordingUc:
        def __init__(self):
            self.inner = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
            self.protections = []
            self.write_permissions = []

        def __getattr__(self, name):
            return getattr(self.inner, name)

        def mem_protect(self, address, size, permissions):
            self.protections.append((address, size, permissions))
            return self.inner.mem_protect(address, size, permissions)

        def mem_write(self, address, data):
            page = address & ~(PAGE_SIZE - 1)
            region = next((region for region in self.inner.mem_regions()
                           if region[0] <= page <= region[1]), None)
            self.write_permissions.append((address, None if region is None else region[2]))
            return self.inner.mem_write(address, data)

    emulator = RecordingUc()
    _load_image(emulator, elf, relocation_tables, dynamic_symbols, allow_textrel=True)
    initial_addend = struct.unpack_from("<I", raw, 0x1FF0)[0]
    assert struct.unpack("<I", emulator.mem_read(LOAD_BASE + 0x1FF0, 4))[0] == (
        LOAD_BASE + initial_addend
    ) & 0xFFFFFFFF
    assert (LOAD_BASE + 0x1000, PAGE_SIZE, UC_PROT_READ | UC_PROT_WRITE) in emulator.protections
    assert (LOAD_BASE + 0x1000, PAGE_SIZE, UC_PROT_READ | UC_PROT_EXEC) in emulator.protections
    assert not any(flags & UC_PROT_WRITE and flags & UC_PROT_EXEC
                   for _address, _size, flags in emulator.protections)
    target_write = [flags for address, flags in emulator.write_permissions
                    if address == LOAD_BASE + 0x1FF0]
    assert target_write[-1] == UC_PROT_READ | UC_PROT_WRITE


def test_writable_segment_shared_with_readonly_page_requires_textrel(tmp_path: Path):
    artifact = tmp_path / "undeclared-shared-page-relocation.so"
    _synthetic_arm_shared_object(
        artifact, plt_address=0x1FF0, plt_file_offset=0x1FF0,
        plt_flags=6, plt_alignment=0x1000,
    )
    raw = bytearray(artifact.read_bytes())
    first = bytes(raw[52:84])
    third = bytes(raw[52 + 64:52 + 96])
    raw[52:84] = third
    raw[52 + 64:52 + 96] = first
    struct.pack_into("<I", raw, 0x4000, 0x1FF0)
    artifact.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    elf, _raw, relocation_tables, dynamic_symbols = _read_elf(artifact, digest)

    with pytest.raises(ValueError, match="requires declared text relocation support"):
        _load_image(Uc(UC_ARCH_ARM, UC_MODE_THUMB), elf,
                    relocation_tables, dynamic_symbols)


def test_relocation_rejects_readonly_segment_even_when_shared_page_is_writable(tmp_path: Path):
    artifact = tmp_path / "readonly-relocation-shared-page.so"
    _synthetic_arm_shared_object(
        artifact, plt_address=0x1F00, plt_file_offset=0x1F00,
        plt_flags=5, plt_alignment=0x1000,
    )
    raw = bytearray(artifact.read_bytes())
    raw[0x1F10:0x1F10 + 40] = raw[0x2000:0x2028]
    data_phdr = bytes(raw[52 + 32:52 + 64])
    plt_phdr = bytes(raw[52 + 64:52 + 96])
    raw[52 + 32:52 + 64] = plt_phdr
    raw[52 + 64:52 + 96] = data_phdr
    struct.pack_into("<III", raw, 52 + 64 + 4, 0x1F10, 0x1F10, 0x1F10)
    struct.pack_into("<I", raw, 0x4000, 0x1F00)
    artifact.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    elf, _raw, relocation_tables, dynamic_symbols = _read_elf(artifact, digest)

    with pytest.raises(ValueError, match="outside writable loadable data"):
        _load_image(Uc(UC_ARCH_ARM, UC_MODE_THUMB), elf,
                    relocation_tables, dynamic_symbols)


def test_api17_gnu_relro_is_read_only_after_relocation(tmp_path: Path):
    artifact = tmp_path / "gnu-relro.so"
    digest = _synthetic_arm_shared_object(artifact)
    raw = bytearray(artifact.read_bytes())
    struct.pack_into("<H", raw, 44, 6)
    relro = struct.pack("<IIIIIIII", 0x6474E552, 0x2000, 0x2000, 0x2000,
                        0x28, 0x28, 4, 4)
    raw[52 + 5 * 32:52 + 6 * 32] = relro
    artifact.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    elf, _raw, relocation_tables, dynamic_symbols = _read_elf(artifact, digest)
    emulator = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    _load_image(emulator, elf, relocation_tables, dynamic_symbols)

    assert struct.unpack("<I", emulator.mem_read(LOAD_BASE + 0x2020, 4))[0] == LOAD_BASE + 0x10
    data_page = next(region for region in emulator.mem_regions()
                     if region[0] == LOAD_BASE + 0x2000)
    assert data_page[2] == UC_PROT_READ


def test_api17_relro_rounding_protects_a_shared_writable_page(tmp_path: Path):
    artifact = tmp_path / "gnu-relro-shared-page.so"
    _synthetic_arm_shared_object(artifact)
    raw = bytearray(artifact.read_bytes())
    shared_data_offset = 0x3028
    shared_data_header = 52 + 6 * 32
    struct.pack_into("<H", raw, 44, 7)
    struct.pack_into(
        "<IIIIIIII", raw, shared_data_header,
        1, shared_data_offset, 0x2028, 0x2028, 0x10, 0x10, 6, 0x1000,
    )
    relro_header = 52 + 5 * 32
    struct.pack_into(
        "<IIIIIIII", raw, relro_header,
        0x6474E552, 0x2000, 0x2000, 0x2000, 0x28, 0x28, 4, 4,
    )
    elf = _elf32_file(raw)
    plan = plan_elf32_mapping(elf, "relro-shared-page", LOAD_BASE)
    emulator = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    regions = map_elf32_segments(emulator, elf, plan)

    page = next(region for region in regions if region[0] == LOAD_BASE + 0x2000)
    assert page[2] == UC_PROT_READ
    assert emulator.mem_read(LOAD_BASE + 0x2028, 0x10) == raw[shared_data_offset:shared_data_offset + 0x10]


def test_textrel_disabled_rejects_before_mapping_segments(tmp_path: Path):
    artifact = tmp_path / "textrel-disabled.so"
    digest = _synthetic_arm_shared_object(
        artifact, relative_target=0x1020, relative_initial_addend=0, declare_textrel=True,
    )
    elf, _raw, tables, symbols = _read_elf(artifact, digest, allow_textrel=True)
    emulator = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    with pytest.raises(ValueError, match="support is disabled"):
        _load_image(emulator, elf, tables, symbols)
    assert tuple(emulator.mem_regions()) == ()
    with pytest.raises(RuntimeError, match="unusable after a loader failure"):
        _load_image(emulator, elf, tables, symbols)
    with pytest.raises(RuntimeError, match="unusable after a loader failure"):
        _execute_bounded(
            emulator, entry=LOAD_BASE + 0x1000,
            allowed_ranges=((LOAD_BASE + 0x1000, LOAD_BASE + 0x1038),),
            sentinel=RETURN_BASE, import_stub=IMPORT_BASE,
            instruction_limit=8, return_register=UC_ARM_REG_R0,
        )


def test_api17_textrel_write_is_temporary_and_final_permissions_are_restored(tmp_path: Path):
    artifact = tmp_path / "textrel.so"
    digest = _synthetic_arm_shared_object(
        artifact, relative_target=0x1020, relative_initial_addend=0, declare_textrel=True,
    )
    elf, _raw, relocation_tables, dynamic_symbols = _read_elf(
        artifact, digest, allow_textrel=True,
    )
    class RecordingUc:
        def __init__(self):
            self.inner = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
            self.protections = []
            self.write_permissions = []

        def __getattr__(self, name):
            return getattr(self.inner, name)

        def mem_protect(self, address, size, permissions):
            self.protections.append((address, size, permissions))
            return self.inner.mem_protect(address, size, permissions)

        def mem_write(self, address, data):
            page = address & ~(PAGE_SIZE - 1)
            region = next((region for region in self.inner.mem_regions()
                           if region[0] <= page <= region[1]), None)
            self.write_permissions.append((address, None if region is None else region[2]))
            return self.inner.mem_write(address, data)

    emulator = RecordingUc()
    _load_image(
        emulator, elf, relocation_tables, dynamic_symbols,
        identity="textrel-fixture", allow_textrel=True,
    )
    assert struct.unpack("<I", emulator.mem_read(LOAD_BASE + 0x1020, 4))[0] == LOAD_BASE
    assert (LOAD_BASE + 0x1000, PAGE_SIZE, UC_PROT_READ | UC_PROT_WRITE) in emulator.protections
    assert (LOAD_BASE + 0x1000, PAGE_SIZE, UC_PROT_READ | UC_PROT_EXEC) in emulator.protections
    assert not any(flags & UC_PROT_WRITE and flags & UC_PROT_EXEC
                   for _address, _size, flags in emulator.protections)
    target_write = [flags for address, flags in emulator.write_permissions
                    if address == LOAD_BASE + 0x1020]
    assert target_write[-1] == UC_PROT_READ | UC_PROT_WRITE
    final_page = next(region for region in emulator.mem_regions()
                      if region[0] == LOAD_BASE + 0x1000)
    assert final_page[2] == UC_PROT_READ | UC_PROT_EXEC


def test_textrel_requires_explicit_support_and_declared_elf_flag(tmp_path: Path):
    declared = tmp_path / "declared-textrel.so"
    digest = _synthetic_arm_shared_object(
        declared, relative_target=0x1020, relative_initial_addend=0, declare_textrel=True,
    )
    with pytest.raises(ValueError, match="DT_TEXTREL relocations are unsupported"):
        _read_elf(declared, digest)
    elf, _raw, tables, symbols = _read_elf(declared, digest, allow_textrel=True)
    with pytest.raises(ValueError, match="support is disabled"):
        _load_image(Uc(UC_ARCH_ARM, UC_MODE_THUMB), elf, tables, symbols)

    undeclared = tmp_path / "undeclared-textrel.so"
    digest = _synthetic_arm_shared_object(
        undeclared, relative_target=0x1020, relative_initial_addend=0,
    )
    elf, _raw, tables, symbols = _read_elf(undeclared, digest)
    with pytest.raises(ValueError, match="outside writable loadable data"):
        _load_image(
            Uc(UC_ARCH_ARM, UC_MODE_THUMB), elf, tables, symbols,
            allow_textrel=True,
        )


def test_relocation_rejects_misaligned_word_target(tmp_path: Path):
    artifact = tmp_path / "misaligned-relocation-target.so"
    digest = _synthetic_arm_shared_object(artifact, relative_target=0x1FFE)
    elf, _raw, relocation_tables, dynamic_symbols = _read_elf(artifact, digest)

    with pytest.raises(ValueError, match="ARM word relocation target is misaligned"):
        _load_image(Uc(UC_ARCH_ARM, UC_MODE_THUMB), elf, relocation_tables, dynamic_symbols)


def test_dependency_layout_is_deterministic_and_keeps_images_distinct(tmp_path: Path):
    first_path, second_path = tmp_path / "first.so", tmp_path / "second.so"
    first, _first_raw, _ = _synthetic_mapping_elf(first_path)
    second, _second_raw, _ = _synthetic_mapping_elf(second_path)
    images = (("requester", first), ("provider", second))
    one = plan_elf32_dependency_mappings(images)
    two = plan_elf32_dependency_mappings(images)
    assert one == two
    assert one[0].identity == "requester"
    assert one[1].identity == "provider"
    assert one[0].image_end + PAGE_SIZE <= one[1].image_start
    assert one[0].load_bias != one[1].load_bias


def test_dependency_plans_map_as_distinct_images_in_one_emulator(tmp_path: Path):
    first, first_raw, _ = _synthetic_mapping_elf(tmp_path / "mapped-first.so")
    second, second_raw, _ = _synthetic_mapping_elf(tmp_path / "mapped-second.so")
    plans = plan_elf32_dependency_mappings((
        ("mapped-first", first), ("mapped-second", second),
    ))
    emulator = Uc(UC_ARCH_ARM, UC_MODE_THUMB)

    images = (("mapped-first", first), ("mapped-second", second))
    mapped = map_elf32_dependency_segments(emulator, images, plans)

    assert all(mapped)
    assert plans[0].image_end + PAGE_SIZE <= plans[1].image_start
    first_regions = tuple(
        region for region in mapped if plans[0].image_start <= region[0] < plans[0].image_end
    )
    second_regions = tuple(
        region for region in mapped if plans[1].image_start <= region[0] < plans[1].image_end
    )
    for first_region in first_regions:
        for second_region in second_regions:
            assert not (first_region[0] < second_region[1]
                        and second_region[0] < first_region[1])
    first_segment = next(segment for segment in plans[0].segments if segment.file_size)
    second_segment = next(segment for segment in plans[1].segments if segment.file_size)
    assert emulator.mem_read(
        plans[0].load_bias + first_segment.virtual_address, first_segment.file_size,
    ) == first_raw[first_segment.file_offset:first_segment.file_offset + first_segment.file_size]
    assert emulator.mem_read(
        plans[1].load_bias + second_segment.virtual_address, second_segment.file_size,
    ) == second_raw[second_segment.file_offset:second_segment.file_offset + second_segment.file_size]


def test_dependency_mapper_enforces_aggregate_source_limit(tmp_path: Path, monkeypatch):
    first, _first_raw, _ = _synthetic_mapping_elf(tmp_path / "source-first.so")
    second, _second_raw, _ = _synthetic_mapping_elf(tmp_path / "source-second.so")
    images = (("source-first", first), ("source-second", second))
    plans = plan_elf32_dependency_mappings(images)
    monkeypatch.setattr("tools.honda_native_boundary_probe.MAX_DEPENDENCY_SOURCE_BYTES", 1)
    emulator = Uc(UC_ARCH_ARM, UC_MODE_THUMB)

    with pytest.raises(ValueError, match="total source-size bound"):
        map_elf32_dependency_segments(emulator, images, plans)
    assert tuple(emulator.mem_regions()) == ()


def test_dependency_mapper_enforces_planned_mapping_budget(tmp_path: Path):
    first, _first_raw, _ = _synthetic_mapping_elf(tmp_path / "budget-first.so")
    second, _second_raw, _ = _synthetic_mapping_elf(tmp_path / "budget-second.so")
    images = (("budget-first", first), ("budget-second", second))
    plans = plan_elf32_dependency_mappings(images)
    first_image_bytes = len(plans[0].page_permissions) * PAGE_SIZE
    constrained = tuple(replace(plan, dependency_mapping_budget=first_image_bytes)
                       for plan in plans)
    emulator = Uc(UC_ARCH_ARM, UC_MODE_THUMB)

    with pytest.raises(ValueError, match="total emulator memory bound"):
        map_elf32_dependency_segments(emulator, images, constrained)
    assert tuple(emulator.mem_regions()) == ()


def test_dependency_mapper_rejects_more_than_64_images_before_mapping():
    emulator = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    images = tuple((f"image-{index}", None) for index in range(65))

    with pytest.raises(ValueError, match="within 1..64"):
        map_elf32_dependency_segments(emulator, images, ())
    assert tuple(emulator.mem_regions()) == ()


def test_dependency_batch_rolls_back_prior_images_when_later_map_fails(tmp_path: Path):
    first, _first_raw, _ = _synthetic_mapping_elf(tmp_path / "rollback-first.so")
    second, _second_raw, _ = _synthetic_mapping_elf(tmp_path / "rollback-second.so")
    images = (("rollback-first", first), ("rollback-second", second))
    plans = plan_elf32_dependency_mappings(images)
    second_start = plans[1].image_start

    class FailingSecondImageUc:
        def __init__(self):
            self.inner = Uc(UC_ARCH_ARM, UC_MODE_THUMB)

        def __getattr__(self, name):
            return getattr(self.inner, name)

        def mem_write(self, address, data):
            if address >= second_start:
                raise RuntimeError("injected second-image write failure")
            return self.inner.mem_write(address, data)

    emulator = FailingSecondImageUc()
    with pytest.raises(RuntimeError, match="injected second-image write failure"):
        map_elf32_dependency_segments(emulator, images, plans)
    assert tuple(emulator.mem_regions()) == ()


def test_segment_mapper_poisons_emulator_when_rollback_fails(tmp_path: Path):
    artifact = tmp_path / "rollback-failure.so"
    elf, _raw, _digest = _synthetic_mapping_elf(artifact)
    plan = plan_elf32_mapping(elf, "rollback-failure", 0x02200000)

    class FailingCleanupUc:
        def __init__(self):
            self.inner = Uc(UC_ARCH_ARM, UC_MODE_THUMB)

        def __getattr__(self, name):
            return getattr(self.inner, name)

        def mem_write(self, _address, _data):
            raise RuntimeError("injected page-write failure")

        def mem_unmap(self, _address, _size):
            raise RuntimeError("injected rollback failure")

    emulator = FailingCleanupUc()
    with pytest.raises(RuntimeError, match="rollback was incomplete"):
        map_elf32_segments(emulator, elf, plan)
    assert emulator._claritylink_loader_failed is True
    with pytest.raises(RuntimeError, match="emulator is unusable"):
        map_elf32_segments(emulator, elf, plan)


def test_dependency_batch_rejects_matching_plan_below_dependency_range(tmp_path: Path):
    elf, _raw, _ = _synthetic_mapping_elf(tmp_path / "dependency-low-plan.so")
    plan = plan_elf32_mapping(elf, "low-dependency", 0x02000000)
    emulator = Uc(UC_ARCH_ARM, UC_MODE_THUMB)

    with pytest.raises(ValueError, match="outside the reserved dependency address range"):
        map_elf32_dependency_segments(emulator, (("low-dependency", elf),), (plan,))
    assert tuple(emulator.mem_regions()) == ()


def test_dependency_batch_rejects_pairwise_overlapping_plans(tmp_path: Path):
    first, _raw, _ = _synthetic_mapping_elf(tmp_path / "overlap-first.so")
    second, _raw2, _ = _synthetic_mapping_elf(tmp_path / "overlap-second.so")
    images = (("overlap-first", first), ("overlap-second", second))
    shared_bias = DEPENDENCY_START_ADDRESS - 0x1000
    plans = (
        plan_elf32_mapping(first, "overlap-first", shared_bias),
        plan_elf32_mapping(second, "overlap-second", shared_bias),
    )
    emulator = Uc(UC_ARCH_ARM, UC_MODE_THUMB)

    with pytest.raises(ValueError, match="plans overlap each other"):
        map_elf32_dependency_segments(emulator, images, plans)
    assert tuple(emulator.mem_regions()) == ()


def test_dependency_layout_rejects_negative_load_bias(tmp_path: Path):
    artifact = tmp_path / "dependency-negative-bias.so"
    _synthetic_arm_shared_object(artifact)
    raw = bytearray(artifact.read_bytes())
    elf = _elf32_file(raw)
    for index, segment in enumerate(elf.iter_segments()):
        if segment["p_type"] == "PT_LOAD":
            header = 52 + index * 32
            address = int(segment["p_vaddr"]) + 0x20000000
            struct.pack_into("<II", raw, header + 8, address, address)
    elf = _elf32_file(raw)

    with pytest.raises(ValueError, match="negative ARM32 load bias"):
        plan_elf32_dependency_mappings((("negative-bias", elf),))


def test_dependency_layout_rejects_duplicate_identity_and_memory_budget(tmp_path: Path):
    artifact = tmp_path / "dependency-identity.so"
    elf, raw, _ = _synthetic_mapping_elf(artifact)
    with pytest.raises(ValueError, match="identities must be unique"):
        plan_elf32_dependency_mappings((("duplicate", elf), ("duplicate", elf)))
    with pytest.raises(ValueError, match="memory bound"):
        plan_elf32_dependency_mappings((("bounded", elf),), max_total_mapped_bytes=PAGE_SIZE)
    with pytest.raises(ValueError, match="total source-size bound"):
        plan_elf32_dependency_mappings(
            (("first", elf), ("second", elf)), max_total_source_bytes=len(raw),
        )


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
        headers = {"e_phoff": 0, "e_phnum": 2, "e_phentsize": 32}

        def __getitem__(self, key):
            return self.headers[key]

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
            return {"e_machine": "EM_ARM", "e_type": "ET_EXEC", "e_flags": 0x05000000}[key]

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
        "DT_PLTRELSZ": 2, "DT_STRTAB": 5, "DT_SYMTAB": 6, "DT_RELA": 7, "DT_RELASZ": 8,
        "DT_STRSZ": 10,
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

        def data(self):
            return struct.pack("<II", 0x4020, 23)

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

        def data(self):
            return struct.pack("<IIi", 0x4020, 23, 0)

    class Elf:
        def iter_segments(self):
            return iter((DynamicSegment(), _FileBackedLoadSegment()))

        def iter_sections(self):
            return iter((RelaSection(),))

    tables, symbols = _validate_dynamic_relocations(Elf(), RelaSection, 0x10000)
    assert [(table.section_type, table.size) for table in tables] == [("SHT_RELA", 12)]
    assert symbols is None


def test_dynamic_symbol_names_require_dt_strtab_to_match_allocated_dynstr(tmp_path: Path):
    artifact = tmp_path / "mismatched-dynstr.so"
    digest = _synthetic_arm_shared_object(artifact, dynstr_address_override=0x4100)
    with pytest.raises(ValueError, match="DT_STRTAB/DT_STRSZ"):
        _read_elf(artifact, digest)


def test_loader_rejects_relocation_target_inside_dynamic_string_table(tmp_path: Path):
    artifact = tmp_path / "relocation-overwrites-dynstr.so"
    digest = _synthetic_arm_shared_object(artifact, relative_target=0x4060)
    elf, _raw, tables, symbols = _read_elf(artifact, digest)
    uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    with pytest.raises(ValueError, match="overlaps dynamic relocation or symbol metadata"):
        _load_image(uc, elf, tables, symbols)


def test_plt_rela_requires_supported_dt_pltrel_and_dynamic_symbols():
    from types import SimpleNamespace

    tags = (
        ("DT_JMPREL", "d_ptr", 0x4000), ("DT_PLTRELSZ", "d_val", 12),
        ("DT_PLTREL", "d_val", 7), ("DT_RELAENT", "d_val", 12),
        ("DT_SYMTAB", "d_ptr", 0x5000), ("DT_SYMENT", "d_val", 16),
        ("DT_STRTAB", "d_ptr", 0x4800), ("DT_STRSZ", "d_val", 16),
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
            self.name = values.get("name", "")

        def __getitem__(self, key):
            return self.values[key]

        def data(self):
            return struct.pack("<IIi", 0x4020, 22, 0)

    class RelaSection(Section):
        pass

    relocation = RelaSection({"sh_type": "SHT_RELA", "sh_addr": 0x4000,
                              "sh_size": 12, "sh_entsize": 12, "sh_flags": 2,
                              "sh_offset": 0x4000})
    symbols = Section({"sh_type": "SHT_DYNSYM", "sh_addr": 0x5000,
                       "sh_size": 16, "sh_entsize": 16, "sh_flags": 2,
                       "sh_offset": 0x5000})
    strings = Section({"name": ".dynstr", "sh_type": "SHT_STRTAB", "sh_addr": 0x4800,
                       "sh_size": 16, "sh_flags": 2, "sh_offset": 0x4800})

    class Elf:
        def iter_segments(self):
            return iter((DynamicSegment(), _FileBackedLoadSegment(0x1010)))

        def iter_sections(self):
            return iter((relocation, symbols, strings))

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


class _DynamicSymbol:
    def __init__(self, name, value, *, bind="STB_GLOBAL", visibility="STV_DEFAULT",
                 section=1, symbol_type="STT_OBJECT", size=4):
        self.name = name
        self.values = {
            "st_value": value,
            "st_size": size,
            "st_shndx": section,
            "st_info": {"bind": bind, "type": symbol_type},
            "st_other": {"visibility": visibility},
        }

    def __getitem__(self, key):
        return self.values[key]


class _DynamicSymbolTable:
    def __init__(self, symbols):
        self.symbols = tuple(symbols)

    def iter_symbols(self):
        return iter(self.symbols)


class _ResolverELF:
    elfclass = 32
    little_endian = True

    def __init__(self, symbols=(), *, machine="EM_ARM", e_type="ET_DYN", sections=4,
                 section_flags=2):
        self.symbol_table = _DynamicSymbolTable(symbols)
        self.machine = machine
        self.e_type = e_type
        self.e_flags = 0x05000000
        self.sections = sections
        self.section_flags = section_flags
        definitions = [s for s in self.symbol_table.symbols if isinstance(s["st_shndx"], int)]
        self.segment_start = min((s["st_value"] for s in definitions), default=0)
        segment_end = max((s["st_value"] + max(1, s.values.get("st_size", 0))
                           for s in definitions), default=self.segment_start + 1)
        self.segment_size = max(1, segment_end - self.segment_start)
        self.segment_file_size = self.segment_size

    def get_section_by_name(self, name):
        return self.symbol_table if name == ".dynsym" else None

    def num_sections(self):
        return self.sections

    def get_section(self, index):
        if index != 1:
            return None
        return {"sh_flags": self.section_flags, "sh_addr": self.segment_start,
                "sh_size": self.segment_size}

    def iter_segments(self):
        return iter(({
            "p_type": "PT_LOAD", "p_filesz": self.segment_file_size,
            "p_memsz": self.segment_size,
            "p_vaddr": self.segment_start, "p_flags": 5,
        },))

    def __getitem__(self, key):
        return {"e_machine": self.machine, "e_type": self.e_type, "e_flags": self.e_flags}[key]


def _dependency(identity, symbols=(), *, bias=0x10000, **kwargs):
    return ELF32Dependency(identity, _ResolverELF(symbols, **kwargs), bias)


def test_api17_resolver_uses_first_needed_definition_and_load_bias():
    requester = _dependency("requester")
    first = _dependency("first.so", [_DynamicSymbol("object", 0x1234)], bias=0x20000)
    second = _dependency("second.so", [_DynamicSymbol("object", 0x5678)], bias=0x30000)
    resolved = _api17_resolve_symbol("object", requester, (first, second))
    assert resolved is not None
    assert (resolved.address, resolved.provider, resolved.binding) == (0x21234, "first.so", "STB_GLOBAL")


def test_api17_resolver_prefers_requester_scope():
    requester = _dependency("requester", [_DynamicSymbol("object", 0x111)], bias=0x10000)
    needed = _dependency("needed.so", [_DynamicSymbol("object", 0x222)], bias=0x20000)
    assert _api17_resolve_symbol("object", requester, (needed,)).address == 0x10111


def test_api17_resolver_keeps_first_weak_definition_per_bionic_order():
    requester = _dependency("requester")
    weak = _dependency("weak.so", [_DynamicSymbol("object", 0x100, bind="STB_WEAK")], bias=0x1000)
    strong = _dependency("strong.so", [_DynamicSymbol("object", 0x200)], bias=0x2000)
    assert _api17_resolve_symbol("object", requester, (weak, strong)).address == 0x1100


def test_api17_resolver_rejects_unresolved_strong_symbol():
    with pytest.raises(ValueError, match="unresolved strong"):
        _api17_resolve_symbol("missing", _dependency("requester"), ())


def test_api17_resolver_allows_unresolved_weak_symbol_as_zero_result():
    assert _api17_resolve_symbol("missing", _dependency("requester"), (), weak_undefined=True) is None


def test_api17_resolver_skips_local_definitions():
    requester = _dependency("requester")
    local = _dependency("local.so", [_DynamicSymbol("object", 1, bind="STB_LOCAL")])
    later = _dependency("later.so", [_DynamicSymbol("object", 0x44)], bias=0x4000)
    assert _api17_resolve_symbol("object", requester, (local, later)).address == 0x4044


def test_api17_resolver_rejects_hidden_visibility_instead_of_guessing():
    hidden = _dependency("hidden.so", [_DynamicSymbol("object", 1, visibility="STV_HIDDEN")])
    later = _dependency("later.so", [_DynamicSymbol("object", 0x44)], bias=0x4000)
    with pytest.raises(ValueError, match="hidden symbol visibility"):
        _api17_resolve_symbol("object", _dependency("requester"), (hidden, later))


@pytest.mark.parametrize("kwargs", [
    {"machine": "EM_X86_64"}, {"e_type": "ET_EXEC"}, {"sections": 1},
])
def test_api17_resolver_rejects_wrong_architecture_or_symbol_section(kwargs):
    requester = _dependency("requester", [_DynamicSymbol("object", 0x100)], **kwargs)
    with pytest.raises(ValueError):
        _api17_resolve_symbol("object", requester, ())


def test_api17_resolver_rejects_incompatible_arm_eabi():
    requester = _dependency("requester", [_DynamicSymbol("object", 0x100)])
    requester.elf.e_flags = 0
    with pytest.raises(ValueError, match="EABI5"):
        _api17_resolve_symbol("object", requester, ())


def test_api17_resolver_rejects_duplicate_same_object_definitions():
    provider = _dependency("provider.so", [
        _DynamicSymbol("object", 0x100), _DynamicSymbol("object", 0x200),
    ])
    with pytest.raises(ValueError, match="duplicate eligible"):
        _api17_resolve_symbol("object", _dependency("requester"), (provider,))


def test_api17_resolver_rejects_non_allocated_definition():
    provider = ELF32Dependency(
        "provider.so", _ResolverELF([_DynamicSymbol("object", 0x100)], section_flags=0), 0x1000
    )
    with pytest.raises(ValueError, match="outside allocated loadable memory"):
        _api17_resolve_symbol("object", _dependency("requester"), (provider,))


def test_api17_resolver_rejects_symbol_extent_outside_load_segment():
    provider = _dependency("provider.so", [_DynamicSymbol("object", 0x100, size=8)], bias=0x1000)
    provider.elf.segment_size = 4
    with pytest.raises(ValueError, match="outside allocated loadable memory"):
        _api17_resolve_symbol("object", _dependency("requester"), (provider,))


def test_api17_resolver_rejects_function_in_zero_filled_segment_tail():
    provider = _dependency(
        "provider.so", [_DynamicSymbol("function", 0x100, symbol_type="STT_FUNC", size=8)],
        bias=0x1000,
    )
    provider.elf.segment_file_size = 4
    with pytest.raises(ValueError, match="outside allocated loadable memory"):
        _api17_resolve_symbol("function", _dependency("requester"), (provider,))


def test_api17_resolver_rejects_load_bias_overflow():
    provider = _dependency("provider.so", [_DynamicSymbol("object", 0xFFFFFFF0)], bias=0x20)
    with pytest.raises(ValueError, match="overflows 32 bits"):
        _api17_resolve_symbol("object", _dependency("requester"), (provider,))


def test_r_arm_glob_dat_writes_resolved_symbol_address_not_addend():
    # API 17 Bionic writes S for GLOB_DAT; the REL word is not used as A.
    assert _relocation_value(21, load_base=0x10000, implicit_addend=0xFFFF,
                             symbol_address=0x23456789) == 0x23456789


def test_r_arm_glob_dat_requires_dependency_backed_address():
    with pytest.raises(ValueError, match="requires a resolved"):
        _relocation_value(21, load_base=0x10000)


def test_r_arm_glob_dat_resolves_defined_requester_symbol(tmp_path: Path):
    artifact = tmp_path / "defined-glob-dat.so"
    digest = _synthetic_arm_shared_object(artifact, glob_dat_symbol_index=2)
    elf, _raw, tables, symbols = _read_elf(artifact, digest)
    uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    _load_image(
        uc, elf, tables, symbols,
        symbol_resolver=lambda _name, _weak: ResolvedELF32Symbol(
            LOAD_BASE + 0x2000, "verified-fixture-requester", "STB_GLOBAL"
        ),
    )
    assert struct.unpack("<I", uc.mem_read(LOAD_BASE + 0x2024, 4))[0] == LOAD_BASE + 0x2000


def test_loader_preserves_thumb_bit_for_local_glob_dat_function(tmp_path: Path):
    artifact = tmp_path / "local-thumb-glob-dat.so"
    digest = _synthetic_arm_shared_object(
        artifact, glob_dat_symbol_index=1, register_symbol_info=0x02,
        dynsym_first_global=2,
    )
    elf, _raw, tables, symbols = _read_elf(artifact, digest)
    uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    _load_image(uc, elf, tables, symbols)
    assert struct.unpack("<I", uc.mem_read(LOAD_BASE + 0x2024, 4))[0] == LOAD_BASE + 0x1001


def test_r_arm_glob_dat_rejects_defined_global_without_lookup(tmp_path: Path):
    artifact = tmp_path / "defined-global-no-lookup.so"
    digest = _synthetic_arm_shared_object(artifact, glob_dat_symbol_index=2)
    elf, _raw, tables, symbols = _read_elf(artifact, digest)
    uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    with pytest.raises(ValueError, match="defined global requester symbol requires API17 lookup"):
        _load_image(uc, elf, tables, symbols)


def test_r_arm_abs32_uses_symbol_plus_rel_addend_modulo_32_bits():
    assert _relocation_value(2, load_base=0x10000, implicit_addend=0x30,
                             symbol_address=0x12340000) == 0x12340030
    assert _relocation_value(2, load_base=0x10000, explicit_addend=-1,
                             symbol_address=0) == 0xFFFFFFFF


def test_r_arm_abs32_requires_a_resolved_symbol_address():
    with pytest.raises(ValueError, match="requires a resolved"):
        _relocation_value(2, load_base=0x10000, implicit_addend=4)


def test_r_arm_abs32_preserves_thumb_state_bit():
    assert _relocation_value(2, load_base=0x10000, implicit_addend=0x20,
                             symbol_address=0x12340000, thumb_target=True) == 0x12340021


def test_loader_applies_dependency_backed_glob_dat(tmp_path: Path):
    artifact = tmp_path / "external-glob-dat.so"
    digest = _synthetic_arm_shared_object(artifact, glob_dat_symbol_index=4)
    elf, _raw, tables, symbols = _read_elf(artifact, digest)
    uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    resolved_address = 0x23456000
    _load_image(
        uc, elf, tables, symbols,
        symbol_resolver=lambda _name, _weak: ResolvedELF32Symbol(
            resolved_address, "verified-fixture-provider", "STB_GLOBAL"
        ),
    )
    assert struct.unpack("<I", uc.mem_read(LOAD_BASE + 0x2024, 4))[0] == resolved_address


def test_loader_rejects_unresolved_strong_glob_dat(tmp_path: Path):
    artifact = tmp_path / "missing-strong-glob-dat.so"
    digest = _synthetic_arm_shared_object(artifact, glob_dat_symbol_index=4)
    elf, _raw, tables, symbols = _read_elf(artifact, digest)
    uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    with pytest.raises(ValueError, match="unresolved strong"):
        _load_image(uc, elf, tables, symbols, symbol_resolver=lambda _name, _weak: None)


def test_loader_resolves_unresolved_weak_glob_dat_to_zero(tmp_path: Path):
    artifact = tmp_path / "missing-weak-glob-dat.so"
    digest = _synthetic_arm_shared_object(
        artifact, glob_dat_symbol_index=4, import_binding=2,
    )
    elf, _raw, tables, symbols = _read_elf(artifact, digest)
    uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    _load_image(uc, elf, tables, symbols, symbol_resolver=lambda _name, _weak: None)
    assert struct.unpack("<I", uc.mem_read(LOAD_BASE + 0x2024, 4))[0] == 0


def test_loader_rejects_glob_dat_symbol_index_outside_dynsym(tmp_path: Path):
    artifact = tmp_path / "invalid-glob-dat-index.so"
    digest = _synthetic_arm_shared_object(artifact, glob_dat_symbol_index=5)
    elf, _raw, tables, symbols = _read_elf(artifact, digest)
    uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    with pytest.raises(ValueError, match="symbol relocation index exceeds DT_SYMTAB"):
        _load_image(uc, elf, tables, symbols)


def test_loader_requires_lookup_for_defined_global_requester_symbol(tmp_path: Path):
    artifact = tmp_path / "non-allocated-requester-symbol.so"
    digest = _synthetic_arm_shared_object(
        artifact, glob_dat_symbol_index=2, callback_table_section_index=4,
    )
    elf, _raw, tables, symbols = _read_elf(artifact, digest)
    uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    with pytest.raises(ValueError, match="defined global requester symbol requires API17 lookup"):
        _load_image(uc, elf, tables, symbols)


def test_loader_applies_dependency_backed_abs32(tmp_path: Path):
    artifact = tmp_path / "external-abs32.so"
    digest = _synthetic_arm_shared_object(artifact, abs32_symbol_index=4)
    elf, _raw, tables, symbols = _read_elf(artifact, digest)
    uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    resolved_address = 0x12340000
    _load_image(
        uc, elf, tables, symbols,
        symbol_resolver=lambda _name, _weak: ResolvedELF32Symbol(
            resolved_address, "verified-fixture-provider", "STB_GLOBAL"
        ),
    )
    assert struct.unpack("<I", uc.mem_read(LOAD_BASE + 0x2024, 4))[0] == resolved_address + 0x20


@pytest.mark.parametrize("relocation", ["glob_dat", "abs32"])
def test_loader_rejects_dependency_address_outside_elf32(tmp_path: Path, relocation: str):
    artifact = tmp_path / f"out-of-range-{relocation}.so"
    digest = _synthetic_arm_shared_object(
        artifact,
        glob_dat_symbol_index=4 if relocation == "glob_dat" else None,
        abs32_symbol_index=4 if relocation == "abs32" else None,
    )
    elf, _raw, tables, symbols = _read_elf(artifact, digest)
    uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    with pytest.raises(ValueError, match="resolved symbol address is outside ELF32"):
        _load_image(
            uc, elf, tables, symbols,
            symbol_resolver=lambda _name, _weak: ResolvedELF32Symbol(
                0x1_0000_0000, "verified-fixture-provider", "STB_GLOBAL"
            ),
        )


def test_loader_rejects_unresolved_strong_abs32(tmp_path: Path):
    artifact = tmp_path / "missing-strong-abs32.so"
    digest = _synthetic_arm_shared_object(artifact, abs32_symbol_index=4)
    elf, _raw, tables, symbols = _read_elf(artifact, digest)
    uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    with pytest.raises(ValueError, match="unresolved strong"):
        _load_image(uc, elf, tables, symbols, symbol_resolver=lambda _name, _weak: None)
