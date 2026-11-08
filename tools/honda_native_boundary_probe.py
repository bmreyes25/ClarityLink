#!/usr/bin/env python3
"""Run a bounded six-slot ARM32 callback-registration probe.

Callers provide the artifact digest, function/table/flag symbols, expected
first/second registration results, and synthetic callback values. The digest
checks byte identity only; it does not establish source provenance or authority.
The probe requires a clean initial table/flag and the flag to become 1 after the
first registration. Only six-slot registration behavior is modeled.
Undefined imported functions use side-effect-free local stubs that return zero;
defined-symbol PLT calls are rejected because this loader does not resolve them.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
from io import BytesIO
import re
import struct
from pathlib import Path
import sys


PAGE_SIZE = 0x1000
LOAD_BASE = 0x10000
STACK_BASE = 0x700000
IMPORT_BASE = 0x800000
RETURN_BASE = 0x810000
INSTRUCTION_LIMIT = 2000
MAX_ARTIFACT_BYTES = 128 * 1024 * 1024
MAX_IMAGE_END = STACK_BASE
MAX_RELOCATION_ENTRIES = 250_000
MAX_PLT_BYTES = 4096
SHA256_PATTERN = re.compile(r"[0-9a-fA-F]{64}\Z")


@dataclass(frozen=True)
class ProbeObservation:
    first_return: int
    second_return: int
    first_table: bytes
    second_table: bytes
    registration_flag: int
    expected_returns_match: bool
    first_table_matches: bool
    second_table_preserved: bool
    registration_flag_matches: bool

    @property
    def matches_expectation(self) -> bool:
        return all((self.expected_returns_match, self.first_table_matches,
                    self.second_table_preserved, self.registration_flag_matches))


@dataclass(frozen=True)
class RelocationTable:
    address: int
    size: int
    section_type: str
    entry_size: int
    is_plt: bool = False


@dataclass(frozen=True)
class ProbeResult:
    observations: tuple[ProbeObservation, ...]

    @property
    def emulator_instances(self) -> int:
        return len(self.observations)

    @property
    def matching_instances(self) -> int:
        return sum(observation.matches_expectation for observation in self.observations)

    @property
    def matches_expectation(self) -> bool:
        return bool(self.observations) and all(item.matches_expectation for item in self.observations)

    def _reported(self) -> ProbeObservation:
        if not self.observations:
            raise RuntimeError("probe completed no emulation repetitions")
        return next((item for item in self.observations if not item.matches_expectation),
                    self.observations[-1])

    @property
    def first_return(self) -> int:
        return self._reported().first_return

    @property
    def second_return(self) -> int:
        return self._reported().second_return

    @property
    def first_table(self) -> bytes:
        return self._reported().first_table

    @property
    def second_table(self) -> bytes:
        return self._reported().second_table

    @property
    def registration_flag(self) -> int:
        return self._reported().registration_flag


def _read_elf(path: Path, expected_sha256: str):
    try:
        from elftools.elf.elffile import ELFFile
        from elftools.elf.relocation import RelocationSection
    except ImportError as exc:
        raise RuntimeError("install pyelftools to inspect ARM ELF artifacts") from exc
    if not SHA256_PATTERN.fullmatch(expected_sha256):
        raise ValueError("SHA-256 must contain exactly 64 hexadecimal characters")
    with path.open("rb") as source:
        raw = source.read(MAX_ARTIFACT_BYTES + 1)
    if len(raw) > MAX_ARTIFACT_BYTES:
        raise ValueError("artifact exceeds the 128 MiB inspection limit")
    observed = hashlib.sha256(raw).hexdigest()
    if observed.lower() != expected_sha256.lower():
        raise ValueError("artifact SHA-256 does not match the caller-supplied fingerprint")
    # Parse the same immutable bytes that were fingerprinted; do not reopen a
    # caller-controlled path between validation and ELF parsing.
    elf = ELFFile(BytesIO(raw))
    _validate_elf_format(elf)
    _validate_load_segments(elf, len(raw))
    relocation_tables, dynamic_symbol_table = _validate_dynamic_relocations(
        elf, RelocationSection, len(raw)
    )
    return elf, raw, relocation_tables, dynamic_symbol_table


def _validate_elf_format(elf) -> None:
    if elf.elfclass != 32 or not elf.little_endian or elf["e_machine"] != "EM_ARM":
        raise ValueError("only little-endian ELF32 ARM artifacts are supported")
    if elf["e_type"] != "ET_DYN":
        raise ValueError("only ET_DYN shared objects are supported")


def _validate_load_segments(elf, file_size: int) -> None:
    ranges = []
    for segment in elf.iter_segments():
        if segment["p_type"] != "PT_LOAD":
            continue
        offset, address = int(segment["p_offset"]), int(segment["p_vaddr"])
        file_bytes, memory_bytes = int(segment["p_filesz"]), int(segment["p_memsz"])
        if file_bytes > memory_bytes or offset + file_bytes > file_size:
            raise ValueError("ELF load segment is truncated or has an invalid file/memory size")
        if memory_bytes:
            ranges.append((address, address + memory_bytes))
    ranges.sort()
    if any(start < previous_end for (_previous_start, previous_end), (start, _end)
           in zip(ranges, ranges[1:])):
        raise ValueError("overlapping PT_LOAD memory ranges are unsupported")


def _parse_dynamic_entries(raw: bytes) -> tuple[tuple[int, int], ...]:
    if len(raw) % 8:
        raise ValueError("PT_DYNAMIC size is not aligned to ELF32 dynamic entries")
    entries = []
    terminated = False
    for offset in range(0, len(raw), 8):
        tag, value = struct.unpack_from("<II", raw, offset)
        if tag == 0:
            terminated = True
            break
        entries.append((tag, value))
    if not terminated:
        raise ValueError("PT_DYNAMIC lacks an in-bounds DT_NULL terminator")
    return tuple(entries)


def _file_backed_load_mapping(elf, address: int, size: int, file_offset: int, file_size: int) -> bool:
    if size < 0 or file_offset < 0 or file_offset + size > file_size:
        return False
    return any(
        segment["p_type"] == "PT_LOAD"
        and int(segment["p_filesz"]) <= int(segment["p_memsz"])
        and int(segment["p_offset"]) + int(segment["p_filesz"]) <= file_size
        and int(segment["p_vaddr"]) <= address
        and address + size <= int(segment["p_vaddr"]) + int(segment["p_filesz"])
        and file_offset == int(segment["p_offset"]) + address - int(segment["p_vaddr"])
        for segment in elf.iter_segments()
    )


def _validate_dynamic_relocations(elf, relocation_section_type, file_size: int):
    relocation_sections = [section for section in elf.iter_sections()
                           if isinstance(section, relocation_section_type)]
    numeric_names = {
        2: "DT_PLTRELSZ", 6: "DT_SYMTAB", 7: "DT_RELA", 8: "DT_RELASZ",
        9: "DT_RELAENT", 11: "DT_SYMENT", 17: "DT_REL", 18: "DT_RELSZ",
        19: "DT_RELENT", 20: "DT_PLTREL", 22: "DT_TEXTREL", 23: "DT_JMPREL",
        30: "DT_FLAGS", 35: "DT_RELRSZ",
        36: "DT_RELR", 37: "DT_RELRENT",
    }
    android_relocation_tags = {
        0x6000000F, 0x60000010, 0x60000011, 0x60000012,
        0x6FFFE000, 0x6FFFE001, 0x6FFFE003, 0x6FFFE005,
    }
    dynamic_tags = {}
    relr_present = False
    dynamic_segments = [segment for segment in elf.iter_segments() if segment["p_type"] == "PT_DYNAMIC"]
    if len(dynamic_segments) > 1:
        raise ValueError("multiple PT_DYNAMIC segments are unsupported")
    for segment in dynamic_segments:
        address, size, offset = int(segment["p_vaddr"]), int(segment["p_filesz"]), int(segment["p_offset"])
        if size > int(segment["p_memsz"]) or not _file_backed_load_mapping(
            elf, address, size, offset, file_size
        ):
            raise ValueError("PT_DYNAMIC is outside consistent file-backed PT_LOAD data")
        entries = _parse_dynamic_entries(segment.data())
        for raw_name, value in entries:
            if isinstance(raw_name, int) and raw_name in android_relocation_tags:
                raise ValueError("Android packed relocations are unsupported")
            name = numeric_names.get(raw_name, str(raw_name)) if isinstance(raw_name, int) else raw_name
            if name == "DT_TEXTREL":
                raise ValueError("DT_TEXTREL relocations are unsupported")
            if name == "DT_FLAGS" and value & 4:
                raise ValueError("DF_TEXTREL relocations are unsupported")
            if name.startswith("DT_ANDROID_REL") or name.startswith("DT_ANDROID_RELR"):
                raise ValueError("Android packed relocations are unsupported")
            relocation_tags = {
                "DT_REL", "DT_RELSZ", "DT_RELENT", "DT_RELA", "DT_RELASZ", "DT_RELAENT",
                "DT_JMPREL", "DT_PLTRELSZ", "DT_PLTREL", "DT_RELR", "DT_RELRSZ", "DT_RELRENT",
                "DT_SYMTAB", "DT_SYMENT", "DT_FLAGS",
            }
            if name in relocation_tags and name in dynamic_tags:
                raise ValueError(f"duplicate dynamic relocation tag {name}")
            dynamic_tags[name] = int(value)
            if name in {"DT_RELR", "DT_RELRSZ", "DT_RELRENT"} and (name == "DT_RELR" or int(value)):
                relr_present = True
    if relr_present:
        raise ValueError("DT_RELR relocations are unsupported")

    table_specs = []
    for address_tag, size_tag, entry_tag, expected_entry, section_type in (
        ("DT_REL", "DT_RELSZ", "DT_RELENT", 8, "SHT_REL"),
        ("DT_RELA", "DT_RELASZ", "DT_RELAENT", 12, "SHT_RELA"),
    ):
        size = dynamic_tags.get(size_tag, 0)
        if size:
            entry_size = dynamic_tags.get(entry_tag, 0)
            if entry_size != expected_entry or size % expected_entry:
                raise ValueError(f"{entry_tag} does not match the supported relocation entry layout")
            table_specs.append((dynamic_tags.get(address_tag, 0), size, section_type,
                                expected_entry, False))
    plt_size = dynamic_tags.get("DT_PLTRELSZ", 0)
    if plt_size:
        plt_type = {17: "SHT_REL", 7: "SHT_RELA"}.get(dynamic_tags.get("DT_PLTREL"))
        if plt_type is None:
            raise ValueError("DT_PLTREL is missing or unsupported")
        plt_entry_size = dynamic_tags.get("DT_RELENT" if plt_type == "SHT_REL" else "DT_RELAENT", 0)
        expected_entry = 8 if plt_type == "SHT_REL" else 12
        if plt_entry_size != expected_entry or plt_size % expected_entry:
            raise ValueError("PLT relocation entry size does not match DT_PLTREL")
        table_specs.append((dynamic_tags.get("DT_JMPREL", 0), plt_size, plt_type,
                            expected_entry, True))

    tables = []
    matched_sections = set()
    for address, size, section_type, entry_size, is_plt in table_specs:
        if not address:
            raise ValueError("dynamic relocation table has no address")
        matching = [section for section in relocation_sections
                    if section["sh_type"] == section_type
                    and int(section["sh_addr"]) == address
                    and int(section["sh_size"]) == size
                    and int(section["sh_entsize"]) == entry_size
                    and int(section["sh_flags"]) & 2]
        if len(matching) != 1:
            raise ValueError("active dynamic relocation table lacks an exact matching section")
        section = matching[0]
        matched_sections.add(id(section))
        section_offset = int(section["sh_offset"])
        if not _file_backed_load_mapping(elf, address, size, section_offset, file_size):
            raise ValueError("dynamic relocation section offset disagrees with its PT_LOAD mapping")
        tables.append(RelocationTable(address, size, section_type, entry_size, is_plt))

    if {id(section) for section in relocation_sections} != matched_sections:
        raise ValueError("unreferenced or unsupported relocation sections are present")
    if sum(table.size // table.entry_size for table in tables) > MAX_RELOCATION_ENTRIES:
        raise ValueError("dynamic relocation count exceeds the inspection limit")

    jump_slots = any(table.is_plt for table in tables)
    dynamic_symbols = None
    if jump_slots:
        symbol_address = dynamic_tags.get("DT_SYMTAB", 0)
        symbol_entry = dynamic_tags.get("DT_SYMENT", 0)
        if not symbol_address or symbol_entry != 16:
            raise ValueError("dynamic symbol table metadata is missing or unsupported")
        symbol_sections = [section for section in elf.iter_sections()
                           if section["sh_type"] == "SHT_DYNSYM"
                           and int(section["sh_addr"]) == symbol_address
                           and int(section["sh_entsize"]) == symbol_entry
                           and int(section["sh_size"]) % symbol_entry == 0
                           and int(section["sh_flags"]) & 2]
        if len(symbol_sections) != 1:
            raise ValueError("DT_SYMTAB does not identify one readable dynamic symbol table")
        symbol_section = symbol_sections[0]
        symbol_size = int(symbol_section["sh_size"])
        if not _file_backed_load_mapping(
            elf, symbol_address, symbol_size, int(symbol_section["sh_offset"]), file_size
        ):
            raise ValueError("dynamic symbol section offset disagrees with its PT_LOAD mapping")
        dynamic_symbols = (symbol_address, symbol_size // symbol_entry)
    return tuple(tables), dynamic_symbols


def _symbol_details(
    elf, name: str, *, maximum_size: int | None = None, minimum_size: int = 1,
    expected_type: str | None = None,
) -> tuple[int, int, str]:
    matches = []
    for section in elf.iter_sections():
        if section.name not in {".symtab", ".dynsym"}:
            continue
        for symbol in section.iter_symbols():
            if symbol.name == name and symbol["st_shndx"] not in {"SHN_UNDEF", "SHN_ABS"}:
                matches.append((int(symbol["st_value"]), int(symbol["st_size"]), symbol["st_info"]["type"]))
    matches = list(dict.fromkeys(matches))
    if len(matches) != 1:
        raise ValueError("each requested symbol must resolve to exactly one defined ELF symbol")
    address, size, symbol_type = matches[0]
    if expected_type is not None and symbol_type != expected_type:
        raise ValueError(f"requested symbol must have ELF type {expected_type}")
    if size < minimum_size or (maximum_size is not None and size > maximum_size):
        raise ValueError("requested function symbol has an invalid or excessive size")
    return address, size, symbol_type


def _symbol(elf, name: str, *, maximum_size: int | None = None) -> tuple[int, int]:
    address, size, _symbol_type = _symbol_details(elf, name, maximum_size=maximum_size)
    return address, size


def _relocation_value(kind: int, *, load_base: int, implicit_addend: int = 0,
                      explicit_addend: int | None = None, import_stub: int = IMPORT_BASE) -> int:
    if kind == 23:  # R_ARM_RELATIVE
        addend = implicit_addend if explicit_addend is None else explicit_addend
        return (load_base + addend) & 0xFFFFFFFF
    if kind == 22:  # R_ARM_JUMP_SLOT
        return import_stub | 1
    raise ValueError(f"unsupported ARM relocation type {kind}")


def _page_permissions(segments) -> dict[int, int]:
    page_permissions: dict[int, int] = {}
    for segment in segments:
        start = LOAD_BASE + int(segment["p_vaddr"])
        filesz = int(segment["p_filesz"])
        memsz = int(segment["p_memsz"])
        if not memsz:
            continue
        if filesz > memsz:
            raise ValueError("ELF load segment file size exceeds its memory size")
        end = start + memsz
        if end <= start or end > MAX_IMAGE_END:
            raise ValueError("ELF load segment overlaps the reserved emulator stack or exceeds image bounds")
        lo = start & ~(PAGE_SIZE - 1)
        hi = (end + PAGE_SIZE - 1) & ~(PAGE_SIZE - 1)
        flags = int(segment["p_flags"])
        permission = (1 if flags & 4 else 0) | (2 if flags & 2 else 0) | (4 if flags & 1 else 0)
        for page in range(lo, hi, PAGE_SIZE):
            page_permissions[page] = page_permissions.get(page, 0) | permission
    if any(permission & 2 and permission & 4 for permission in page_permissions.values()):
        raise ValueError("ELF load segments would create a writable executable page")
    return page_permissions


def _range_in_executable_load_segment(elf, start: int, end: int) -> bool:
    return any(
        segment["p_type"] == "PT_LOAD"
        and int(segment["p_flags"]) & 1
        and int(segment["p_vaddr"]) <= start
        and end <= int(segment["p_vaddr"]) + int(segment["p_filesz"])
        for segment in elf.iter_segments()
    )


def _range_in_writable_load_segment(elf, start: int, size: int) -> bool:
    end = start + size
    return any(
        segment["p_type"] == "PT_LOAD"
        and int(segment["p_flags"]) & 2
        and int(segment["p_vaddr"]) <= start
        and end <= int(segment["p_vaddr"]) + int(segment["p_memsz"])
        for segment in elf.iter_segments()
    )


def _validate_emulator_permissions(regions, *, stack: int, import_stub: int,
                                   return_stub: int, read: int, write: int, execute: int) -> None:
    permissions = {start: flags for start, _end, flags in regions}
    stack_flags = permissions.get(stack, 0)
    if stack_flags & execute or stack_flags & (read | write) != (read | write):
        raise RuntimeError("emulator stack must be readable/writable and non-executable")
    for address in (import_stub, return_stub):
        if permissions.get(address) != read | execute:
            raise RuntimeError("emulator import and return stubs must be read-only executable")


def _load_image(uc, elf, relocation_tables, dynamic_symbol_table) -> None:
    from unicorn import UC_PROT_EXEC, UC_PROT_READ, UC_PROT_WRITE

    segments = [s for s in elf.iter_segments() if s["p_type"] == "PT_LOAD"]
    segments = [s for s in segments if int(s["p_memsz"])]
    if not segments:
        raise ValueError("ELF contains no loadable segments")
    for segment in segments:
        if int(segment["p_filesz"]) > int(segment["p_memsz"]):
            raise ValueError("ELF load segment file size exceeds its memory size")
    page_permissions = _page_permissions(segments)
    for page, permissions in page_permissions.items():
        uc.mem_map(page, PAGE_SIZE, permissions)

    for segment in segments:
        start = LOAD_BASE + int(segment["p_vaddr"])
        if segment.data():
            uc.mem_write(start, segment.data())

    uc.mem_map(STACK_BASE, 0x20000, UC_PROT_READ | UC_PROT_WRITE)
    uc.mem_map(IMPORT_BASE, PAGE_SIZE, UC_PROT_READ | UC_PROT_WRITE)
    uc.mem_map(RETURN_BASE, PAGE_SIZE, UC_PROT_READ | UC_PROT_WRITE)
    # Thumb `movs r0,#0; bx lr`; imports have no side effects and return zero.
    uc.mem_write(IMPORT_BASE, b"\x00\x20\x70\x47")
    uc.mem_write(RETURN_BASE, b"\x70\x47")
    uc.mem_protect(IMPORT_BASE, PAGE_SIZE, UC_PROT_READ | UC_PROT_EXEC)
    uc.mem_protect(RETURN_BASE, PAGE_SIZE, UC_PROT_READ | UC_PROT_EXEC)

    table_snapshots = tuple(
        (table, bytes(uc.mem_read(LOAD_BASE + table.address, table.size)))
        for table in relocation_tables
    )
    parsed_relocations = []
    required_symbols = set()
    for table, raw in table_snapshots:
        is_rela = table.section_type == "SHT_RELA"
        for offset in range(0, len(raw), table.entry_size):
            if is_rela:
                target_offset, info, addend = struct.unpack_from("<IIi", raw, offset)
            else:
                target_offset, info = struct.unpack_from("<II", raw, offset)
                addend = None
            kind, symbol_index = info & 0xFF, info >> 8
            if kind == 22:
                if not symbol_index or dynamic_symbol_table is None:
                    raise ValueError("R_ARM_JUMP_SLOT requires a dynamic imported symbol")
                if symbol_index >= dynamic_symbol_table[1]:
                    raise ValueError("R_ARM_JUMP_SLOT symbol index exceeds DT_SYMTAB")
                required_symbols.add(symbol_index)
            parsed_relocations.append((table, target_offset, kind, symbol_index, addend))

    symbol_snapshots = {}
    if required_symbols:
        symbol_address, _symbol_count = dynamic_symbol_table
        for symbol_index in required_symbols:
            symbol_snapshots[symbol_index] = bytes(uc.mem_read(
                LOAD_BASE + symbol_address + symbol_index * 16, 16
            ))

    metadata_ranges = [(table.address, table.address + table.size) for table in relocation_tables]
    if dynamic_symbol_table is not None:
        symbol_address, symbol_count = dynamic_symbol_table
        metadata_ranges.append((symbol_address, symbol_address + symbol_count * 16))
    relocated_targets = set()
    for _table, target_offset, kind, symbol_index, addend in parsed_relocations:
        if target_offset & 3:
            raise ValueError("ARM word relocation target is misaligned")
        target_end = target_offset + 4
        if any(target_offset < end and start < target_end for start, end in metadata_ranges):
            raise ValueError("relocation target overlaps dynamic relocation or symbol metadata")
        if target_offset in relocated_targets:
            raise ValueError("duplicate ARM relocation target is unsupported")
        relocated_targets.add(target_offset)
        if kind == 22:
            symbol_bytes = symbol_snapshots[symbol_index]
            _name, _value, _size, _info, _other, section_index = struct.unpack(
                "<IIIBBH", symbol_bytes
            )
            if section_index != 0:
                raise ValueError("defined-symbol PLT calls are unsupported")
        if kind == 23 and symbol_index:
            raise ValueError("R_ARM_RELATIVE relocations must use the null symbol")
        if not _range_in_writable_load_segment(elf, target_offset, 4):
            raise ValueError("ARM relocation target is outside writable loadable data")
        destination = LOAD_BASE + target_offset
        implicit_addend = 0 if addend is not None else struct.unpack("<I", uc.mem_read(destination, 4))[0]
        value = _relocation_value(
            kind, load_base=LOAD_BASE, implicit_addend=implicit_addend,
            explicit_addend=addend,
        )
        uc.mem_write(destination, struct.pack("<I", value & 0xFFFFFFFF))

    _validate_emulator_permissions(
        uc.mem_regions(), stack=STACK_BASE, import_stub=IMPORT_BASE,
        return_stub=RETURN_BASE, read=UC_PROT_READ, write=UC_PROT_WRITE,
        execute=UC_PROT_EXEC,
    )

    return None


def _execute_bounded(uc, *, entry: int, allowed_ranges: tuple[tuple[int, int], ...],
                     sentinel: int, import_stub: int, instruction_limit: int,
                     return_register: int,
                     arm_ranges: tuple[tuple[int, int], ...] = ()) -> tuple[int, int]:
    from unicorn import UC_HOOK_CODE
    from unicorn.arm_const import UC_ARM_REG_CPSR

    steps = 0
    returned = False
    escaped: int | None = None
    import_stub_next = False

    def guard(engine, address, _size, _user):
        nonlocal steps, returned, escaped, import_stub_next
        steps += 1
        pc = address & ~1
        thumb_state = bool(engine.reg_read(UC_ARM_REG_CPSR) & (1 << 5))
        if not thumb_state:
            if any(start <= pc and pc + _size <= end for start, end in arm_ranges):
                return
            escaped = pc
            engine.emu_stop()
            return
        if pc == sentinel:
            returned = True
            engine.emu_stop()
            return
        if pc == import_stub and _size == 2:
            import_stub_next = True
            return
        if pc == import_stub + 2 and _size == 2 and import_stub_next:
            import_stub_next = False
            return
        import_stub_next = False
        if any(start <= pc and pc + _size <= end for start, end in allowed_ranges):
            return
        escaped = pc
        engine.emu_stop()

    handle = uc.hook_add(UC_HOOK_CODE, guard)
    try:
        uc.emu_start(entry | 1, sentinel + 0x100, timeout=1_000_000,
                     count=instruction_limit)
    finally:
        uc.hook_del(handle)
    if escaped is not None:
        raise RuntimeError(f"ARM execution escaped its function/PLT allowlist at {escaped:#x}")
    if not returned:
        raise RuntimeError("ARM function did not return within the instruction budget")
    return steps, int(uc.reg_read(return_register))


def run_registration_probe(
    artifact: Path,
    expected_sha256: str,
    function_symbol: str,
    callback_storage_symbol: str,
    registration_flag_symbol: str,
    first_callbacks: tuple[int, ...],
    second_callbacks: tuple[int, ...],
    expected_first_return: int,
    expected_second_return: int,
    repetitions: int = 1,
) -> ProbeResult:
    if len(first_callbacks) != 6 or len(second_callbacks) != 6:
        raise ValueError("callback tables must each contain exactly six 32-bit synthetic pointers")
    if first_callbacks == second_callbacks:
        raise ValueError("first and second callback tables must differ to make preservation observable")
    if any(not 0 <= value <= 0xFFFFFFFF for value in
           (expected_first_return, expected_second_return)):
        raise ValueError("expected return values must be unsigned 32-bit integers")
    if not 1 <= repetitions <= 20:
        raise ValueError("repetitions must be between 1 and 20")
    if any(not 0 < value <= 0xFFFFFFFF for value in first_callbacks + second_callbacks):
        raise ValueError("callback pointers must be nonzero 32-bit values")
    try:
        from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB
        from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_R0, UC_ARM_REG_SP
    except ImportError as exc:
        raise RuntimeError("install unicorn to execute the isolated ARM probe") from exc

    elf, _raw, relocation_tables, dynamic_symbol_table = _read_elf(artifact, expected_sha256)
    fn_value, fn_size, _fn_type = _symbol_details(
        elf, function_symbol, maximum_size=4096, minimum_size=1, expected_type="STT_FUNC"
    )
    if not (fn_value & 1):
        raise ValueError("only Thumb function symbols are supported")
    function_start = fn_value & ~1
    function_end = function_start + fn_size
    if not _range_in_executable_load_segment(elf, function_start, function_end):
        raise ValueError("function symbol range is outside executable PT_LOAD data")
    plt = elf.get_section_by_name(".plt")
    plt_range = None
    if plt is not None and int(plt["sh_size"]):
        plt_range = (int(plt["sh_addr"]), int(plt["sh_addr"]) + int(plt["sh_size"]))
        if not _range_in_executable_load_segment(elf, *plt_range):
            raise ValueError("PLT range is outside executable PT_LOAD data")
        plt_slots = sum(table.size // table.entry_size for table in relocation_tables if table.is_plt)
        if int(plt["sh_flags"]) & 6 != 6:
            raise ValueError("PLT section must be allocated and executable")
        if not plt_slots or int(plt["sh_size"]) < 4 * plt_slots:
            raise ValueError("PLT size is inconsistent with dynamic jump-slot coverage")
        if int(plt["sh_size"]) > min(MAX_PLT_BYTES, 32 + 16 * plt_slots):
            raise ValueError("PLT section exceeds the bounded size for its dynamic jump slots")
        if function_start < plt_range[1] and plt_range[0] < function_end:
            raise ValueError("function symbol overlaps the PLT section")
    storage, storage_size, _storage_type = _symbol_details(
        elf, callback_storage_symbol, minimum_size=24, expected_type="STT_OBJECT"
    )
    flag, flag_size, _flag_type = _symbol_details(
        elf, registration_flag_symbol, minimum_size=4, expected_type="STT_OBJECT"
    )
    if not _range_in_writable_load_segment(elf, storage, max(storage_size, 24)):
        raise ValueError("callback storage symbol is outside writable PT_LOAD data")
    if not _range_in_writable_load_segment(elf, flag, max(flag_size, 4)):
        raise ValueError("registration flag symbol is outside writable PT_LOAD data")
    storage_end = storage + max(storage_size, 24)
    flag_end = flag + max(flag_size, 4)
    if storage < flag_end and flag < storage_end:
        raise ValueError("callback storage and registration flag ranges overlap")
    storage_address = LOAD_BASE + storage
    flag_address = LOAD_BASE + flag
    observations = []
    for _ in range(repetitions):
        uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
        _load_image(uc, elf, relocation_tables, dynamic_symbol_table)
        first_callbacks_bytes = struct.pack("<6I", *first_callbacks)
        initial_table = bytes(uc.mem_read(storage_address, 24))
        initial_flag = struct.unpack("<I", uc.mem_read(flag_address, 4))[0]
        if initial_flag != 0 or initial_table == first_callbacks_bytes:
            raise ValueError("initial callback registration state is not clean for measurement")
        function = (LOAD_BASE + function_start) | 1
        allowed_ranges = [(LOAD_BASE + function_start, LOAD_BASE + function_end)]
        if plt_range is not None:
            allowed_ranges.append((LOAD_BASE + plt_range[0], LOAD_BASE + plt_range[1]))

        def invoke(callbacks: tuple[int, ...]) -> int:
            argument = STACK_BASE + 0x1E000
            uc.mem_write(argument, struct.pack("<6I", *callbacks))
            uc.reg_write(UC_ARM_REG_SP, STACK_BASE + 0x10000)
            uc.reg_write(UC_ARM_REG_R0, argument)
            uc.reg_write(UC_ARM_REG_LR, RETURN_BASE | 1)
            _steps, result_r0 = _execute_bounded(
                uc, entry=function, allowed_ranges=tuple(allowed_ranges),
                sentinel=RETURN_BASE, import_stub=IMPORT_BASE,
                instruction_limit=INSTRUCTION_LIMIT, return_register=UC_ARM_REG_R0,
                arm_ranges=(() if plt_range is None else ((
                    LOAD_BASE + plt_range[0], LOAD_BASE + plt_range[1]
                ),)),
            )
            return result_r0

        first = invoke(first_callbacks)
        first_table = bytes(uc.mem_read(storage_address, 24))
        first_flag = struct.unpack("<I", uc.mem_read(flag_address, 4))[0]
        second = invoke(second_callbacks)
        second_table = bytes(uc.mem_read(storage_address, 24))
        current_flag = struct.unpack("<I", uc.mem_read(flag_address, 4))[0]
        observations.append(ProbeObservation(
            first_return=first,
            second_return=second,
            first_table=first_table,
            second_table=second_table,
            registration_flag=current_flag,
            expected_returns_match=(first == expected_first_return and second == expected_second_return),
            first_table_matches=(first_table == first_callbacks_bytes),
            second_table_preserved=(second_table == first_table),
            registration_flag_matches=(first_flag == 1 and current_flag == first_flag),
        ))

    return ProbeResult(tuple(observations))


def _parse_words(value: str) -> tuple[int, ...]:
    try:
        words = tuple(int(item, 0) for item in value.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected comma-separated base-0 integers") from exc
    if len(words) != 6:
        raise argparse.ArgumentTypeError("expected exactly six comma-separated values")
    return words


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--function-symbol", required=True)
    parser.add_argument("--callback-storage-symbol", required=True)
    parser.add_argument("--registration-flag-symbol", required=True)
    parser.add_argument("--first-callbacks", type=_parse_words, required=True)
    parser.add_argument("--second-callbacks", type=_parse_words, required=True)
    parser.add_argument("--first-return", type=lambda v: int(v, 0), required=True)
    parser.add_argument("--second-return", type=lambda v: int(v, 0), required=True)
    parser.add_argument("--repetitions", type=int, default=1)
    args = parser.parse_args()
    try:
        result = run_registration_probe(
            args.artifact, args.sha256, args.function_symbol,
            args.callback_storage_symbol, args.registration_flag_symbol,
            args.first_callbacks, args.second_callbacks, args.first_return,
            args.second_return, args.repetitions,
        )
    except Exception as exc:
        detail = str(exc).replace(str(args.artifact), "<artifact>")
        print(f"probe failed ({type(exc).__name__}): {detail}", file=sys.stderr)
        return 2
    print(
        f"EMULATION_OBSERVED status={'MATCH' if result.matches_expectation else 'MISMATCH'} "
        "evidence_class=UNKNOWN execution=UNICORN_EMULATION target_runtime=false "
        f"instances={result.emulator_instances} matching={result.matching_instances}/{result.emulator_instances} "
        f"first={result.first_return} returns_match={result._reported().expected_returns_match} "
        f"first_table_matches={result._reported().first_table_matches} second={result.second_return} "
        f"table_preserved={result._reported().second_table_preserved} "
        f"registration_flag={result.registration_flag} "
        f"registration_flag_matches={result._reported().registration_flag_matches}"
    )
    return 0 if result.matches_expectation else 1


if __name__ == "__main__":
    raise SystemExit(main())
