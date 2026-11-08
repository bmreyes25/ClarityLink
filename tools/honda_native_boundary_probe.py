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
from functools import cached_property
from dataclasses import dataclass, replace
import hashlib
from io import BytesIO
import re
import struct
from pathlib import Path
import sys
from typing import Callable


PAGE_SIZE = 0x1000
LOAD_BASE = 0x10000
STACK_BASE = 0x700000
IMPORT_BASE = 0x800000
RETURN_BASE = 0x810000
RUNTIME_RESERVED_RANGES = ((STACK_BASE, STACK_BASE + 0x20000),
                           (IMPORT_BASE, IMPORT_BASE + PAGE_SIZE),
                           (RETURN_BASE, RETURN_BASE + PAGE_SIZE))
INSTRUCTION_LIMIT = 2000
MAX_ARTIFACT_BYTES = 128 * 1024 * 1024
MAX_IMAGE_END = STACK_BASE
DEPENDENCY_START_ADDRESS = 0x10000000
MAX_RELOCATION_ENTRIES = 250_000
MAX_DYNAMIC_ENTRIES = 65_536
MAX_DYNAMIC_BYTES = MAX_DYNAMIC_ENTRIES * 8
MAX_PLT_BYTES = 4096
MAX_IMAGE_MAPPING_BYTES = 64 * 1024 * 1024
MAX_IMAGE_LOAD_SEGMENTS = 32
MAX_IMAGE_MAPPING_PAGES = MAX_IMAGE_MAPPING_BYTES // PAGE_SIZE
MAX_DEPENDENCY_SOURCE_BYTES = 256 * 1024 * 1024
MAX_PROGRAM_HEADERS = 65536 // 32
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
class ELF32Dependency:
    """Caller-supplied ELF object and load bias; not an artifact attestation."""

    identity: str
    elf: object
    load_bias: int

    @cached_property
    def dynamic_symbol_index(self):
        section = self.elf.get_section_by_name(".dynsym")
        if section is None:
            return {}
        symbols: dict[str, list[object]] = {}
        for symbol in section.iter_symbols():
            if symbol.name:
                symbols.setdefault(symbol.name, []).append(symbol)
        return {name: tuple(items) for name, items in symbols.items()}


@dataclass(frozen=True)
class ResolvedELF32Symbol:
    address: int
    provider: str
    binding: str
    thumb_target: bool = False


@dataclass(frozen=True)
class ELF32LoadSegmentPlan:
    program_header_index: int
    virtual_address: int
    file_offset: int
    file_size: int
    memory_size: int
    alignment: int
    flags: int


@dataclass(frozen=True)
class ELF32MappingPlan:
    identity: str
    source_sha256: str
    load_bias: int
    image_start: int
    image_end: int
    segments: tuple[ELF32LoadSegmentPlan, ...]
    page_permissions: tuple[tuple[int, int], ...]
    relro_pages: tuple[int, ...]
    max_mapping_bytes: int
    dependency_mapping_budget: int | None = None


def plan_elf32_dependency_mappings(images: tuple[tuple[str, object], ...], *,
                                  start_address: int = DEPENDENCY_START_ADDRESS,
                                  max_total_mapped_bytes: int = 256 * 1024 * 1024,
                                  max_total_source_bytes: int = MAX_DEPENDENCY_SOURCE_BYTES
                                  ) -> tuple[ELF32MappingPlan, ...]:
    """Plan load biases only; this does not map or relocate the dependency closure."""
    if not images or len(images) > 64:
        raise ValueError("dependency image count is outside the supported bound")
    if not 0 < max_total_mapped_bytes <= 256 * 1024 * 1024:
        raise ValueError("total dependency mapping limit is outside the supported bound")
    if not 0 < max_total_source_bytes <= MAX_DEPENDENCY_SOURCE_BYTES:
        raise ValueError("total dependency source limit is outside the supported bound")
    identities = [identity for identity, _elf in images]
    if any(not isinstance(identity, str) or not identity or "\0" in identity for identity in identities):
        raise ValueError("dependency identities must be nonempty strings")
    if len(set(identities)) != len(identities):
        raise ValueError("dependency identities must be unique")
    if not isinstance(start_address, int) or isinstance(start_address, bool) or start_address % PAGE_SIZE:
        raise ValueError("dependency layout start must be a page-aligned address")
    if start_address < DEPENDENCY_START_ADDRESS:
        raise ValueError("dependency layout must begin in the reserved dependency address range")
    cursor = start_address
    mapped_ranges = list(RUNTIME_RESERVED_RANGES)
    plans = []
    total_bytes = 0
    total_source_bytes = 0
    for identity, elf in images:
        _validate_elf_format(elf)
        source_size = _stream_size(elf.stream)
        if source_size > MAX_ARTIFACT_BYTES:
            raise ValueError("ELF artifact exceeds the supported source-size bound")
        total_source_bytes += source_size
        if total_source_bytes > max_total_source_bytes:
            raise ValueError("dependency closure exceeds the total source-size bound")
        _validate_load_segments(elf, source_size)
        loadable = [s for s in elf.iter_segments()
                    if s["p_type"] == "PT_LOAD" and int(s["p_memsz"])]
        if not loadable:
            raise ValueError("dependency image contains no nonempty PT_LOAD segment")
        min_page = min(int(s["p_vaddr"]) & ~(PAGE_SIZE - 1) for s in loadable)
        if min_page > cursor:
            raise ValueError("dependency object would require a negative ARM32 load bias")
        alignment = max([PAGE_SIZE, *(int(s["p_align"]) for s in loadable)])
        if alignment & (alignment - 1):
            raise ValueError("dependency image has a non-power-of-two load alignment")
        load_bias = ((cursor - min_page + alignment - 1) // alignment) * alignment
        plan = plan_elf32_mapping(
            elf, identity, load_bias, mapped_ranges=tuple(mapped_ranges),
        )
        plan = replace(plan, dependency_mapping_budget=max_total_mapped_bytes)
        total_bytes += len(plan.page_permissions) * PAGE_SIZE
        if total_bytes > max_total_mapped_bytes:
            raise ValueError("dependency closure exceeds the total mapping memory bound")
        plans.append(plan)
        mapped_ranges.append((plan.image_start, plan.image_end + PAGE_SIZE))
        cursor = plan.image_end + PAGE_SIZE
        if cursor > 0x1_0000_0000:
            raise ValueError("dependency closure exceeds the ARM32 address space")
    return tuple(plans)


def _stream_size(stream) -> int:
    position = stream.tell()
    try:
        stream.seek(0, 2)
        size = stream.tell()
    finally:
        stream.seek(position)
    return size


def _stream_sha256(stream) -> str:
    position = stream.tell()
    digest = hashlib.sha256()
    try:
        stream.seek(0)
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    finally:
        stream.seek(position)
    return digest.hexdigest()


def _snapshot_elf(elf):
    from elftools.elf.elffile import ELFFile

    try:
        source_view = elf.stream.getbuffer()
    except (AttributeError, BufferError, OSError, ValueError) as exc:
        raise ValueError("ELF mapping requires a bounded in-memory source snapshot") from exc
    try:
        if source_view.nbytes > MAX_ARTIFACT_BYTES:
            raise ValueError("ELF artifact exceeds the supported source-size bound")
        source_bytes = bytes(source_view)
    finally:
        source_view.release()
    return ELFFile(BytesIO(source_bytes))


def _ensure_emulator_usable(uc) -> None:
    if getattr(uc, "_claritylink_loader_failed", False):
        raise RuntimeError("emulator is unusable after a loader failure; create a fresh instance")


def _poison_emulator(uc) -> None:
    try:
        uc._claritylink_loader_failed = True
    except Exception as exc:
        raise RuntimeError("could not mark failed emulator unusable; discard the instance") from exc


def plan_elf32_mapping(elf, identity: str, load_bias: int, *,
                       mapped_ranges: tuple[tuple[int, int], ...] = (),
                       max_mapping_bytes: int = MAX_IMAGE_MAPPING_BYTES
                       ) -> ELF32MappingPlan:
    """Plan bounded PT_LOAD mapping modeled on supported API-17 Bionic cases.

    The caller owns artifact fingerprint/provenance checks. Segment-order page
    protections follow API 17 Bionic: a later PT_LOAD touching a shared page
    supplies its final protection. Unsupported layouts fail closed. No image
    bytes are mapped by this function.
    """
    if not isinstance(identity, str) or not identity or "\0" in identity:
        raise ValueError("ELF mapping identity must be a nonempty string")
    if not isinstance(load_bias, int) or isinstance(load_bias, bool) or not 0 <= load_bias <= 0xFFFFFFFF:
        raise ValueError("ELF load bias must be an unsigned 32-bit address")
    if load_bias % PAGE_SIZE:
        raise ValueError("ELF load bias must be page-aligned")
    if max_mapping_bytes <= 0 or max_mapping_bytes > MAX_IMAGE_MAPPING_BYTES:
        raise ValueError("ELF image mapping limit is outside the supported bound")
    _validate_elf_format(elf)
    file_size = _stream_size(elf.stream)
    if file_size > MAX_ARTIFACT_BYTES:
        raise ValueError("ELF artifact exceeds the supported source-size bound")
    _validate_program_header_bounds(elf, file_size)
    segments = []
    byte_ranges = []
    page_permissions: dict[int, int] = {}
    image_start = None
    image_end = 0
    for index, segment in enumerate(elf.iter_segments()):
        if segment["p_type"] != "PT_LOAD":
            continue
        if len(segments) >= MAX_IMAGE_LOAD_SEGMENTS:
            raise ValueError("ELF has more PT_LOAD segments than the supported limit")
        offset = int(segment["p_offset"])
        vaddr = int(segment["p_vaddr"])
        filesz = int(segment["p_filesz"])
        memsz = int(segment["p_memsz"])
        align = int(segment["p_align"])
        flags = int(segment["p_flags"])
        if not flags & 4:
            raise ValueError("ELF PT_LOAD without read permission is unsupported")
        if filesz > memsz or offset + filesz > file_size:
            raise ValueError("ELF PT_LOAD file or memory bounds are invalid")
        if align not in (0, 1) and (align & (align - 1) or vaddr % align != offset % align):
            raise ValueError("ELF PT_LOAD alignment is invalid")
        if align > 1 and load_bias % align:
            raise ValueError("ELF load bias does not satisfy PT_LOAD alignment")
        if (vaddr & (PAGE_SIZE - 1)) != (offset & (PAGE_SIZE - 1)):
            raise ValueError("ELF PT_LOAD page offsets do not match API 17 mapping requirements")
        start = load_bias + vaddr
        end = start + memsz
        if start > 0xFFFFFFFF or end > 0x1_0000_0000 or end < start:
            raise ValueError("ELF PT_LOAD runtime range overflows ELF32")
        if (memsz > filesz and not flags & 2
                and ((start + filesz) & (PAGE_SIZE - 1))):
            raise ValueError("read-only partial-page BSS differs from the API 17 mapping contract")
        if memsz:
            for old_start, old_end in byte_ranges:
                if start < old_end and old_start < end:
                    raise ValueError("overlapping ELF PT_LOAD memory ranges are unsupported")
            byte_ranges.append((start, end))
            page_start = start & ~(PAGE_SIZE - 1)
            page_end = (end + PAGE_SIZE - 1) & ~(PAGE_SIZE - 1)
            if page_end - page_start > max_mapping_bytes:
                raise ValueError("ELF PT_LOAD exceeds the bounded mapping size")
            for page in range(page_start, page_end, PAGE_SIZE):
                if page not in page_permissions and len(page_permissions) >= MAX_IMAGE_MAPPING_PAGES:
                    raise ValueError("ELF image exceeds the bounded mapping size")
                page_permissions[page] = flags
            image_start = page_start if image_start is None else min(image_start, page_start)
            image_end = max(image_end, page_end)
        segments.append(ELF32LoadSegmentPlan(index, vaddr, offset, filesz, memsz, align, flags))
    if not segments or image_start is None or image_end <= image_start:
        raise ValueError("ELF contains no nonempty PT_LOAD image")
    mapped_bytes = len(page_permissions) * PAGE_SIZE
    if mapped_bytes > max_mapping_bytes or len(page_permissions) > MAX_IMAGE_MAPPING_PAGES:
        raise ValueError("ELF image exceeds the bounded mapping size")
    relro_pages = set()
    for segment in elf.iter_segments():
        if segment["p_type"] != "PT_GNU_RELRO" or not int(segment["p_memsz"]):
            continue
        relro_start = load_bias + int(segment["p_vaddr"])
        relro_end = relro_start + int(segment["p_memsz"])
        if relro_end > 0x1_0000_0000 or relro_end < relro_start:
            raise ValueError("ELF GNU_RELRO range overflows ELF32")
        page_start = relro_start & ~(PAGE_SIZE - 1)
        page_end = (relro_end + PAGE_SIZE - 1) & ~(PAGE_SIZE - 1)
        for page in range(page_start, page_end, PAGE_SIZE):
            if page not in page_permissions:
                raise ValueError("ELF GNU_RELRO page is outside mapped PT_LOAD memory")
            if page_permissions[page] & 2:
                relro_pages.add(page)
            page_permissions[page] &= ~2
    if any(flags & 2 and flags & 1 for flags in page_permissions.values()):
        raise ValueError("ELF PT_LOAD permissions would create a writable executable page")
    for page in page_permissions:
        if any(page < end and start < page + PAGE_SIZE for start, end in mapped_ranges):
            raise ValueError("ELF mapping overlaps an existing image or reserved mapping")
    return ELF32MappingPlan(
        identity, _stream_sha256(elf.stream), load_bias, image_start, image_end, tuple(segments),
        tuple(sorted(page_permissions.items())), tuple(sorted(relro_pages)), max_mapping_bytes,
    )


def map_elf32_segments(uc, elf, plan: ELF32MappingPlan, *,
                       max_total_mapped_bytes: int = 256 * 1024 * 1024) -> tuple[tuple[int, int, int], ...]:
    """Map one source-verified PT_LOAD plan; callers discard failed emulators."""
    return _map_elf32_snapshot(
        uc, _snapshot_elf(elf), plan,
        max_total_mapped_bytes=max_total_mapped_bytes,
    )


def map_elf32_dependency_segments(
    uc, images: tuple[tuple[str, object], ...], plans: tuple[ELF32MappingPlan, ...], *,
    max_total_mapped_bytes: int = 256 * 1024 * 1024,
) -> tuple[tuple[int, int, int], ...]:
    """Map a planned dependency batch atomically, rolling back prior images on failure."""
    if not images or len(images) > 64 or len(images) != len(plans):
        raise ValueError("dependency image and plan counts must match and be within 1..64")
    if tuple(identity for identity, _elf in images) != tuple(plan.identity for plan in plans):
        raise ValueError("dependency image identities do not match their mapping plans")
    if any(plan.image_start < DEPENDENCY_START_ADDRESS
           or plan.image_end <= plan.image_start for plan in plans):
        raise ValueError("dependency plan lies outside the reserved dependency address range")
    total_source_bytes = sum(_stream_size(elf.stream) for _identity, elf in images)
    if (any(_stream_size(elf.stream) > MAX_ARTIFACT_BYTES for _identity, elf in images)
            or total_source_bytes > MAX_DEPENDENCY_SOURCE_BYTES):
        raise ValueError("dependency closure exceeds the total source-size bound")
    mapped_plan_pages: set[int] = set()
    for plan in plans:
        plan_pages = {page for page, _flags in plan.page_permissions}
        if mapped_plan_pages.intersection(plan_pages):
            raise ValueError("dependency mapping plans overlap each other")
        mapped_plan_pages.update(plan_pages)
    mapping_budgets = {plan.dependency_mapping_budget for plan in plans}
    if len(mapping_budgets) != 1 or None in mapping_budgets:
        raise ValueError("dependency plans do not share one validated mapping budget")
    effective_mapping_budget = min(max_total_mapped_bytes, next(iter(mapping_budgets)))
    mapped_regions = []
    try:
        for (_identity, elf), plan in zip(images, plans, strict=True):
            mapped_regions.extend(map_elf32_segments(
                uc, elf, plan, max_total_mapped_bytes=effective_mapping_budget,
            ))
    except BaseException as exc:
        cleanup_errors = []
        for start, end, _flags in reversed(mapped_regions):
            try:
                uc.mem_unmap(start, end - start)
            except BaseException as cleanup_error:
                cleanup_errors.append(cleanup_error)
        if cleanup_errors:
            _poison_emulator(uc)
            raise RuntimeError(
                "dependency mapping failed and batch rollback was incomplete; discard emulator"
            ) from exc
        raise
    return tuple(mapped_regions)


def _map_elf32_snapshot(uc, source_elf, plan: ELF32MappingPlan, *,
                        max_total_mapped_bytes: int = 256 * 1024 * 1024
                        ) -> tuple[tuple[int, int, int], ...]:
    """Map a caller-isolated byte snapshot after verifying it against the plan."""
    from unicorn import UC_PROT_EXEC, UC_PROT_READ, UC_PROT_WRITE

    _ensure_emulator_usable(uc)
    if not isinstance(source_elf.stream, BytesIO):
        raise ValueError("internal segment mapper requires its isolated byte snapshot")
    if not 0 < max_total_mapped_bytes <= 256 * 1024 * 1024:
        raise ValueError("total emulator mapping limit is outside the supported bound")
    if plan.dependency_mapping_budget is not None:
        if not 0 < plan.dependency_mapping_budget <= 256 * 1024 * 1024:
            raise ValueError("planned dependency mapping budget is invalid")
        max_total_mapped_bytes = min(max_total_mapped_bytes, plan.dependency_mapping_budget)
    # Replanning verifies the source-derived layout. Runtime and prior-image
    # exclusions are checked against the fixed ranges and live emulator map below.
    verified = plan_elf32_mapping(
        source_elf, plan.identity, plan.load_bias,
        max_mapping_bytes=plan.max_mapping_bytes,
    )
    verified = replace(verified, dependency_mapping_budget=plan.dependency_mapping_budget)
    if verified != plan:
        raise ValueError("ELF mapping plan does not match current source bytes or program headers")
    regions = tuple((int(start), int(end) + 1) for start, end, _flags in uc.mem_regions())
    for page, _flags in plan.page_permissions:
        if any(start < page + PAGE_SIZE and page < end
               for start, end in RUNTIME_RESERVED_RANGES):
            raise ValueError("ELF image overlaps a reserved emulator runtime mapping")
        if any(start < page + PAGE_SIZE and page < end for start, end in regions):
            raise ValueError("ELF image overlaps an existing emulator mapping")
    new_bytes = len(plan.page_permissions) * PAGE_SIZE
    if sum(end - start for start, end in regions) + new_bytes > max_total_mapped_bytes:
        raise ValueError("ELF dependency mapping exceeds the total emulator memory bound")

    pages = {page: bytearray(PAGE_SIZE) for page, _flags in plan.page_permissions}
    stream = source_elf.stream
    for segment in plan.segments:
        if not segment.memory_size:
            continue
        runtime_start = plan.load_bias + segment.virtual_address
        page_start = runtime_start & ~(PAGE_SIZE - 1)
        file_page_start = segment.file_offset & ~(PAGE_SIZE - 1)
        file_end = segment.file_offset + segment.file_size
        if segment.file_size or segment.file_offset & (PAGE_SIZE - 1):
            mapped_file_end = (file_end + PAGE_SIZE - 1) & ~(PAGE_SIZE - 1)
            mapped_length = mapped_file_end - file_page_start
            for page_offset in range(0, mapped_length, PAGE_SIZE):
                page = page_start + page_offset
                if page in pages:
                    chunk_size = min(PAGE_SIZE, mapped_length - page_offset)
                    stream.seek(file_page_start + page_offset)
                    page_bytes = stream.read(chunk_size)
                    if len(page_bytes) < chunk_size:
                        page_bytes += bytes(chunk_size - len(page_bytes))
                    pages[page][:] = page_bytes.ljust(PAGE_SIZE, b"\0")
            bss_start = runtime_start + segment.file_size
        else:
            bss_start = runtime_start
        bss_end = runtime_start + segment.memory_size
        if segment.flags & 2 and bss_start & (PAGE_SIZE - 1):
            bss_end = max(bss_end, (bss_start + PAGE_SIZE - 1) & ~(PAGE_SIZE - 1))
        if segment.memory_size > segment.file_size:
            bss_end = max(bss_end, (runtime_start + segment.memory_size + PAGE_SIZE - 1)
                          & ~(PAGE_SIZE - 1))
        zero_start = bss_start
        while zero_start < bss_end:
            page = zero_start & ~(PAGE_SIZE - 1)
            page_end = min(bss_end, page + PAGE_SIZE)
            if page in pages:
                pages[page][zero_start - page:page_end - page] = bytes(page_end - zero_start)
            zero_start = page_end
    mapped_pages = []
    try:
        for page, flags in plan.page_permissions:
            permission = ((UC_PROT_READ if flags & 4 else 0)
                          | (UC_PROT_WRITE if flags & 2 else 0)
                          | (UC_PROT_EXEC if flags & 1 else 0))
            uc.mem_map(page, PAGE_SIZE, permission)
            mapped_pages.append(page)
            uc.mem_write(page, bytes(pages[page]))
    except BaseException as exc:
        cleanup_errors = []
        for page in reversed(mapped_pages):
            try:
                uc.mem_unmap(page, PAGE_SIZE)
            except BaseException as cleanup_error:
                cleanup_errors.append(cleanup_error)
        if cleanup_errors:
            _poison_emulator(uc)
            raise RuntimeError("segment mapping failed and rollback was incomplete; discard emulator") from exc
        raise
    return tuple(
        (page, page + PAGE_SIZE,
         ((UC_PROT_READ if flags & 4 else 0)
          | (UC_PROT_WRITE if flags & 2 else 0)
          | (UC_PROT_EXEC if flags & 1 else 0)))
        for page, flags in plan.page_permissions
    )


def _defined_symbol_is_mapped(elf, section_index: int | str, address: int,
                              size: int, symbol_type: str) -> bool:
    if section_index == "SHN_ABS":
        return True
    if not isinstance(section_index, int) or section_index <= 0 or section_index >= elf.num_sections():
        return False
    section = elf.get_section(section_index)
    if not int(section["sh_flags"]) & 2:  # SHF_ALLOC
        return False
    size = max(1, size)
    section_start = int(section["sh_addr"])
    section_end = section_start + int(section["sh_size"])
    if address < section_start or address + size > section_end:
        return False
    required_flags = {"STT_FUNC": 1, "STT_OBJECT": 4}.get(symbol_type, 0)
    return any(
        segment["p_type"] == "PT_LOAD"
        and int(segment["p_filesz"]) <= int(segment["p_memsz"])
        and int(segment["p_vaddr"]) <= address
        and address + size <= int(segment["p_vaddr"]) + int(
            segment["p_filesz"] if symbol_type == "STT_FUNC" else segment["p_memsz"]
        )
        and (int(segment["p_flags"]) & required_flags) == required_flags
        for segment in elf.iter_segments()
    )


def _api17_resolve_symbol(name: str, requester: ELF32Dependency,
                          needed: tuple[ELF32Dependency, ...], *, weak_undefined: bool = False
                          ) -> ResolvedELF32Symbol | None:
    """Resolve a dynamic symbol using API 17's requester-then-DT_NEEDED order.

    Inputs must be immutable, fingerprint-validated ELF objects. This models
    requester and ordered direct-needed lookup only; process-global preloads and
    main-executable scope are outside this resolver. It follows the pinned
    Bionic linker rule that the first global or weak definition wins.
    The caller must establish artifact identity and keep the ELF source immutable;
    this helper enforces neither provenance nor file immutability. It does not load
    dependencies or initialize their runtime state.
    """
    if not name or "\0" in name:
        raise ValueError("dynamic symbol name must be nonempty and contain no NUL")
    ordered = (requester, *needed)
    identities = [item.identity for item in ordered]
    if any(not identity for identity in identities) or len(set(identities)) != len(identities):
        raise ValueError("dependency identities must be nonempty and unique in lookup scope")
    for dependency in ordered:
        _validate_elf_format(dependency.elf)
        matches = []
        for symbol in dependency.dynamic_symbol_index.get(name, ()):
            if symbol["st_shndx"] == "SHN_UNDEF":
                continue
            binding = symbol["st_info"]["bind"]
            visibility = symbol["st_other"]["visibility"]
            if binding not in {"STB_GLOBAL", "STB_WEAK"}:
                continue
            if visibility not in {"STV_DEFAULT", "STV_PROTECTED"}:
                raise ValueError("hidden symbol visibility is outside the supported lookup contract")
            if symbol["st_info"]["type"] in {"STT_TLS", "STT_GNU_IFUNC"}:
                raise ValueError("TLS and IFUNC symbols require unsupported address semantics")
            section_index = symbol["st_shndx"]
            if section_index == "SHN_ABS":
                raise ValueError("absolute symbol mapping is unsupported")
            if not isinstance(section_index, int) or section_index >= dependency.elf.num_sections():
                raise ValueError("defined dynamic symbol has an invalid section index")
            symbol_value = int(symbol["st_value"])
            symbol_type = symbol["st_info"]["type"]
            mapped_value = symbol_value & ~1 if symbol_type == "STT_FUNC" else symbol_value
            symbol_size = int(symbol["st_size"])
            if not _defined_symbol_is_mapped(
                dependency.elf, section_index, mapped_value, symbol_size, symbol_type
            ):
                raise ValueError("defined dynamic symbol is outside allocated loadable memory")
            matches.append((symbol, binding))
        if len(matches) > 1:
            # Bionic's hash lookup selects one entry; without reproducing the
            # provider's validated hash-chain order, duplicate same-object
            # names cannot be resolved faithfully.
            raise ValueError("provider has duplicate eligible dynamic symbol definitions")
        if matches:
            symbol, binding = matches[0]
            symbol_type = symbol["st_info"]["type"]
            value = int(symbol["st_value"])
            address = value + dependency.load_bias
            if not 0 <= address <= 0xFFFFFFFF:
                raise ValueError("resolved ELF32 symbol address overflows 32 bits")
            return ResolvedELF32Symbol(
                address, dependency.identity, binding,
                symbol_type == "STT_FUNC" and bool(value & 1),
            )
    if weak_undefined:
        return None
    raise ValueError(f"unresolved strong ELF32 dynamic symbol: {name}")


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


def _read_elf(path: Path, expected_sha256: str, *, allow_textrel: bool = False):
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
        elf, RelocationSection, len(raw), allow_textrel=allow_textrel
    )
    return elf, raw, relocation_tables, dynamic_symbol_table


def _validate_elf_format(elf) -> None:
    if elf.elfclass != 32 or not elf.little_endian or elf["e_machine"] != "EM_ARM":
        raise ValueError("only little-endian ELF32 ARM artifacts are supported")
    if elf["e_type"] != "ET_DYN":
        raise ValueError("only ET_DYN shared objects are supported")
    if int(elf["e_flags"]) & 0xFF000000 != 0x05000000:
        raise ValueError("only ARM EABI5 objects are supported")


def _validate_load_segments(elf, file_size: int) -> None:
    _validate_program_header_bounds(elf, file_size)
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


def _validate_program_header_bounds(elf, file_size: int) -> None:
    offset = int(elf["e_phoff"])
    count = int(elf["e_phnum"])
    entry_size = int(elf["e_phentsize"])
    if (count < 1 or count > MAX_PROGRAM_HEADERS or entry_size != 32
            or offset > file_size or count > (file_size - offset) // entry_size):
        raise ValueError("ELF program-header table is outside file bounds")


def _parse_dynamic_entries(raw: bytes) -> tuple[tuple[int, int], ...]:
    if len(raw) > MAX_DYNAMIC_BYTES:
        raise ValueError("PT_DYNAMIC exceeds the supported entry-count bound")
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


def _validate_dynamic_relocations(elf, relocation_section_type, file_size: int, *,
                                  allow_textrel: bool = False):
    relocation_sections = [section for section in elf.iter_sections()
                           if isinstance(section, relocation_section_type)]
    numeric_names = {
        2: "DT_PLTRELSZ", 5: "DT_STRTAB", 6: "DT_SYMTAB", 7: "DT_RELA", 8: "DT_RELASZ",
        9: "DT_RELAENT", 11: "DT_SYMENT", 17: "DT_REL", 18: "DT_RELSZ",
        10: "DT_STRSZ", 19: "DT_RELENT", 20: "DT_PLTREL", 22: "DT_TEXTREL", 23: "DT_JMPREL",
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
        if size > MAX_DYNAMIC_BYTES:
            raise ValueError("PT_DYNAMIC exceeds the supported entry-count bound")
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
                if not allow_textrel:
                    raise ValueError("DT_TEXTREL relocations are unsupported")
            if name == "DT_FLAGS" and value & 4:
                if not allow_textrel:
                    raise ValueError("DF_TEXTREL relocations are unsupported")
            if name.startswith("DT_ANDROID_REL") or name.startswith("DT_ANDROID_RELR"):
                raise ValueError("Android packed relocations are unsupported")
            relocation_tags = {
                "DT_REL", "DT_RELSZ", "DT_RELENT", "DT_RELA", "DT_RELASZ", "DT_RELAENT",
                "DT_JMPREL", "DT_PLTRELSZ", "DT_PLTREL", "DT_RELR", "DT_RELRSZ", "DT_RELRENT",
                "DT_SYMTAB", "DT_SYMENT", "DT_STRTAB", "DT_STRSZ", "DT_FLAGS",
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

    symbol_relocations = any(table.is_plt for table in tables)
    dynamic_symbols = None
    for table in tables:
        section = next(section for section in relocation_sections
                       if int(section["sh_addr"]) == table.address
                       and int(section["sh_size"]) == table.size
                       and section["sh_type"] == table.section_type)
        raw = section.data()
        for offset in range(0, len(raw), table.entry_size):
            info = struct.unpack_from("<I", raw, offset + 4)[0]
            if (info & 0xFF) in {2, 21, 22}:
                symbol_relocations = True
    if symbol_relocations:
        string_address = dynamic_tags.get("DT_STRTAB", 0)
        string_size = dynamic_tags.get("DT_STRSZ", 0)
        string_sections = [section for section in elf.iter_sections()
                           if section.name == ".dynstr"
                           and section["sh_type"] == "SHT_STRTAB"
                           and int(section["sh_addr"]) == string_address
                           and int(section["sh_size"]) == string_size
                           and int(section["sh_flags"]) & 2]
        if not string_address or not string_size or len(string_sections) != 1:
            raise ValueError("DT_STRTAB/DT_STRSZ do not identify one allocated .dynstr table")
        string_section = string_sections[0]
        if not _file_backed_load_mapping(
            elf, string_address, string_size, int(string_section["sh_offset"]), file_size
        ):
            raise ValueError("dynamic string table is outside consistent file-backed PT_LOAD data")
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
                      explicit_addend: int | None = None, import_stub: int = IMPORT_BASE,
                      symbol_address: int | None = None, thumb_target: bool = False) -> int:
    if kind == 23:  # R_ARM_RELATIVE
        addend = implicit_addend if explicit_addend is None else explicit_addend
        return (load_base + addend) & 0xFFFFFFFF
    if kind == 22:  # R_ARM_JUMP_SLOT
        if symbol_address is None:
            return import_stub | 1
        if not isinstance(symbol_address, int) or isinstance(symbol_address, bool) or not 0 <= symbol_address <= 0xFFFFFFFF:
            raise ValueError("R_ARM_JUMP_SLOT requires a resolved ELF32 symbol address")
        return symbol_address | int(thumb_target)
    if kind == 21:  # R_ARM_GLOB_DAT: S; the REL addend is not part of this relocation.
        if (symbol_address is None or not isinstance(symbol_address, int)
                or isinstance(symbol_address, bool) or not 0 <= symbol_address <= 0xFFFFFFFF):
            raise ValueError("R_ARM_GLOB_DAT requires a resolved ELF32 symbol address")
        return symbol_address | int(thumb_target)
    if kind == 2:  # R_ARM_ABS32: (S + A) | T modulo 2^32.
        if (symbol_address is None or not isinstance(symbol_address, int)
                or isinstance(symbol_address, bool) or not 0 <= symbol_address <= 0xFFFFFFFF):
            raise ValueError("R_ARM_ABS32 requires a resolved ELF32 symbol address")
        addend = implicit_addend if explicit_addend is None else explicit_addend
        return ((symbol_address + addend) | int(thumb_target)) & 0xFFFFFFFF
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


def _range_in_any_load_segment(elf, start: int, size: int) -> bool:
    end = start + size
    return any(
        segment["p_type"] == "PT_LOAD"
        and int(segment["p_vaddr"]) <= start
        and end <= int(segment["p_vaddr"]) + int(segment["p_memsz"])
        for segment in elf.iter_segments()
    )


def _elf_declares_textrel(elf) -> bool:
    file_size = _stream_size(elf.stream)
    if file_size > MAX_ARTIFACT_BYTES:
        raise ValueError("ELF artifact exceeds the supported source-size bound")
    _validate_program_header_bounds(elf, file_size)
    dynamic_segments = [
        segment for segment in elf.iter_segments() if segment["p_type"] == "PT_DYNAMIC"
    ]
    if len(dynamic_segments) > 1:
        raise ValueError("multiple PT_DYNAMIC segments are unsupported")
    declared = False
    for segment in dynamic_segments:
        address = int(segment["p_vaddr"])
        size = int(segment["p_filesz"])
        offset = int(segment["p_offset"])
        if size > MAX_DYNAMIC_BYTES:
            raise ValueError("PT_DYNAMIC exceeds the supported entry-count bound")
        if (size > int(segment["p_memsz"])
                or not _file_backed_load_mapping(elf, address, size, offset, file_size)):
            raise ValueError("PT_DYNAMIC is outside consistent file-backed PT_LOAD data")
        declared |= any(
            tag == 22 or (tag == 30 and value & 4)
            for tag, value in _parse_dynamic_entries(segment.data())
        )
    return declared


def _validate_emulator_permissions(regions, *, stack: int, import_stub: int,
                                   return_stub: int, read: int, write: int, execute: int) -> None:
    permissions = {start: flags for start, _end, flags in regions}
    stack_flags = permissions.get(stack, 0)
    if stack_flags & execute or stack_flags & (read | write) != (read | write):
        raise RuntimeError("emulator stack must be readable/writable and non-executable")
    for address in (import_stub, return_stub):
        if permissions.get(address) != read | execute:
            raise RuntimeError("emulator import and return stubs must be read-only executable")


def _load_image(uc, elf, relocation_tables, dynamic_symbol_table, *,
                symbol_resolver: Callable[[str, bool], ResolvedELF32Symbol | None] | None = None,
                identity: str = "synthetic-root", load_bias: int = LOAD_BASE,
                map_runtime_support: bool = True,
                allow_textrel: bool = False) -> None:
    _ensure_emulator_usable(uc)
    try:
        source_elf = _snapshot_elf(elf)
        source_size = _stream_size(source_elf.stream)
        _validate_elf_format(source_elf)
        _validate_load_segments(source_elf, source_size)
        if _elf_declares_textrel(source_elf) and not allow_textrel:
            raise ValueError("ELF declares text relocations but textrel support is disabled")
        from elftools.elf.relocation import RelocationSection

        verified_tables, verified_symbols = _validate_dynamic_relocations(
            source_elf, RelocationSection, _stream_size(source_elf.stream),
            allow_textrel=allow_textrel,
        )
        if (tuple(relocation_tables) != verified_tables
                or dynamic_symbol_table != verified_symbols):
            raise ValueError("relocation metadata does not match the immutable ELF snapshot")
        _load_image_impl(
            uc, source_elf, verified_tables, verified_symbols,
            symbol_resolver=symbol_resolver, identity=identity, load_bias=load_bias,
            map_runtime_support=map_runtime_support,
            allow_textrel=allow_textrel,
        )
    except BaseException:
        _poison_emulator(uc)
        raise


def _load_image_impl(uc, elf, relocation_tables, dynamic_symbol_table, *,
                symbol_resolver: Callable[[str, bool], ResolvedELF32Symbol | None] | None = None,
                identity: str = "synthetic-root", load_bias: int = LOAD_BASE,
                map_runtime_support: bool = True,
                allow_textrel: bool = False
                ) -> None:
    from unicorn import UC_PROT_EXEC, UC_PROT_READ, UC_PROT_WRITE

    segments = [s for s in elf.iter_segments() if s["p_type"] == "PT_LOAD"]
    segments = [s for s in segments if int(s["p_memsz"])]
    if not segments:
        raise ValueError("ELF contains no loadable segments")
    textrel_declared = _elf_declares_textrel(elf)
    if textrel_declared and not allow_textrel:
        raise ValueError("ELF declares text relocations but textrel support is disabled")
    mapping_plan = plan_elf32_mapping(
        elf, identity, load_bias, mapped_ranges=RUNTIME_RESERVED_RANGES,
    )
    if mapping_plan.image_end > MAX_IMAGE_END:
        raise ValueError("root ELF exceeds the reserved root image address range")
    _map_elf32_snapshot(uc, elf, mapping_plan)
    page_flags = dict(mapping_plan.page_permissions)

    if map_runtime_support:
        uc.mem_map(STACK_BASE, 0x20000, UC_PROT_READ | UC_PROT_WRITE)
        uc.mem_map(IMPORT_BASE, PAGE_SIZE, UC_PROT_READ | UC_PROT_WRITE)
        uc.mem_map(RETURN_BASE, PAGE_SIZE, UC_PROT_READ | UC_PROT_WRITE)
        # Thumb `movs r0,#0; bx lr`; synthetic probes opt into this helper map.
        uc.mem_write(IMPORT_BASE, b"\x00\x20\x70\x47")
        uc.mem_write(RETURN_BASE, b"\x70\x47")
        uc.mem_protect(IMPORT_BASE, PAGE_SIZE, UC_PROT_READ | UC_PROT_EXEC)
        uc.mem_protect(RETURN_BASE, PAGE_SIZE, UC_PROT_READ | UC_PROT_EXEC)

    table_snapshots = tuple(
        (table, bytes(uc.mem_read(load_bias + table.address, table.size)))
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
            if kind in {2, 21, 22} and symbol_index:
                if dynamic_symbol_table is None:
                    raise ValueError("symbol relocation requires DT_SYMTAB")
                if symbol_index >= dynamic_symbol_table[1]:
                    message = ("R_ARM_JUMP_SLOT symbol index exceeds DT_SYMTAB" if kind == 22
                               else "symbol relocation index exceeds DT_SYMTAB")
                    raise ValueError(message)
                required_symbols.add(symbol_index)
            elif kind in {21, 22}:
                raise ValueError("symbol relocation requires a nonzero dynamic symbol index")
            parsed_relocations.append((table, target_offset, kind, symbol_index, addend))

    symbol_snapshots = {}
    if required_symbols:
        symbol_address, _symbol_count = dynamic_symbol_table
        for symbol_index in required_symbols:
            symbol_snapshots[symbol_index] = bytes(uc.mem_read(
                load_bias + symbol_address + symbol_index * 16, 16
            ))

    metadata_ranges = [(table.address, table.address + table.size) for table in relocation_tables]
    metadata_ranges.extend(
        (int(segment["p_vaddr"]), int(segment["p_vaddr"]) + int(segment["p_memsz"]))
        for segment in elf.iter_segments() if segment["p_type"] == "PT_DYNAMIC"
    )
    if dynamic_symbol_table is not None:
        symbol_address, symbol_count = dynamic_symbol_table
        metadata_ranges.append((symbol_address, symbol_address + symbol_count * 16))
        dynamic_string_sections = [section for section in elf.iter_sections()
                                   if section.name == ".dynstr"]
        if len(dynamic_string_sections) != 1:
            raise ValueError("dynamic symbol relocation requires one validated .dynstr table")
        string_section = dynamic_string_sections[0]
        metadata_ranges.append((int(string_section["sh_addr"]),
                                int(string_section["sh_addr"]) + int(string_section["sh_size"])))
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
        if kind in {2, 21, 22} and symbol_index:
            symbol_bytes = symbol_snapshots[symbol_index]
            _name_offset, _value, _size, _symbol_info, _symbol_other, section_index = struct.unpack(
                "<IIIBBH", symbol_bytes
            )
            if kind == 22 and section_index != 0:
                raise ValueError("defined-symbol PLT calls are unsupported")
        if kind == 23 and symbol_index:
            raise ValueError("R_ARM_RELATIVE relocations must use the null symbol")
        target_end = target_offset + 4
        if not _range_in_any_load_segment(elf, target_offset, 4):
            raise ValueError("ARM relocation target is outside loadable memory")
        # API 17 only unprotects non-writable PT_LOAD pages when the object
        # declares text relocations. GNU RELRO is separately protected after
        # ordinary relocations, so those pages remain eligible here.
        if (not _range_in_writable_load_segment(elf, target_offset, 4)
                and not (allow_textrel and textrel_declared)):
            raise ValueError("ARM relocation target is outside writable loadable data")
        target_pages = tuple(range(
            (load_bias + target_offset) & ~(PAGE_SIZE - 1),
            ((load_bias + target_end - 1) & ~(PAGE_SIZE - 1)) + PAGE_SIZE,
            PAGE_SIZE,
        ))
        if any(page not in page_flags for page in target_pages):
            raise ValueError("ARM relocation target page is outside mapped ELF memory")
        temporary_pages = tuple(page for page in target_pages if not page_flags[page] & 2)
        relro_pages = set(mapping_plan.relro_pages)
        requires_textrel = any(page not in relro_pages for page in temporary_pages)
        if requires_textrel and not (allow_textrel and textrel_declared):
            raise ValueError("read-only PT_LOAD relocation page requires declared text relocation support")
        destination = load_bias + target_offset
        implicit_addend = 0 if addend is not None else struct.unpack("<I", uc.mem_read(destination, 4))[0]
        symbol_address = None
        thumb_target = False
        if kind in {2, 21, 22}:
            if symbol_index == 0:
                symbol_address = 0
            else:
                (symbol_name_offset, symbol_value, _symbol_size,
                 info_byte, other_byte, section_index) = struct.unpack(
                    "<IIIBBH", symbol_snapshots[symbol_index]
                )
                if section_index != 0:
                    symbol_type = info_byte & 0xF
                    thumb_target = symbol_type == 2 and bool(symbol_value & 1)
                    binding = info_byte >> 4
                    visibility = other_byte & 0x3
                    if binding == 0:
                        if visibility != 0:
                            raise ValueError("local requester symbol has unsupported visibility")
                        if section_index == 0xFFF1:
                            raise ValueError("absolute local requester symbols are unsupported")
                        if (not isinstance(section_index, int) or section_index <= 0
                                or section_index >= elf.num_sections()):
                            raise ValueError("relocation symbol has an unsupported section index")
                        mapped_value = symbol_value & ~1 if symbol_type == 2 else symbol_value
                        if not _defined_symbol_is_mapped(
                            elf, section_index, mapped_value, _symbol_size,
                            {2: "STT_FUNC", 1: "STT_OBJECT"}.get(symbol_type, "STT_NOTYPE"),
                        ):
                            raise ValueError("requester symbol is outside allocated loadable memory")
                        symbol_address = load_bias + mapped_value
                    elif binding in {1, 2} and visibility == 0:
                        if symbol_resolver is None:
                            raise ValueError("defined global requester symbol requires API17 lookup")
                        dynamic_string_sections = [section for section in elf.iter_sections()
                                                   if section.name == ".dynstr"]
                        if (len(dynamic_string_sections) != 1
                                or symbol_name_offset >= int(dynamic_string_sections[0]["sh_size"])):
                            raise ValueError("dynamic import name is outside the unique .dynstr table")
                        try:
                            symbol_name = dynamic_string_sections[0].get_string(symbol_name_offset)
                        except UnicodeDecodeError as exc:
                            raise ValueError("dynamic symbol name is not valid UTF-8") from exc
                        if not symbol_name:
                            raise ValueError("dynamic symbol name is empty")
                        resolved = symbol_resolver(symbol_name, binding == 2)
                        if resolved is None:
                            if binding != 2:
                                raise ValueError("unresolved strong dynamic symbol")
                            symbol_address = 0
                        else:
                            symbol_address = resolved.address
                            if (not isinstance(symbol_address, int)
                                    or isinstance(symbol_address, bool)
                                    or symbol_address < 0
                                    or symbol_address > 0xFFFFFFFF):
                                raise ValueError("resolved symbol address is outside ELF32")
                            thumb_target = resolved.thumb_target
                    else:
                        raise ValueError("defined requester symbol binding or visibility is unsupported")
                else:
                    if kind == 22 and symbol_resolver is None:
                        # Existing CL-48 synthetic probe contract: its isolated
                        # no-side-effect PLT return stub is not a dependency.
                        symbol_address = IMPORT_BASE | 1
                    else:
                        if symbol_resolver is None:
                            raise ValueError("symbol relocation requires dependency-backed symbol resolution")
                        dynamic_string_sections = [section for section in elf.iter_sections()
                                                   if section.name == ".dynstr"]
                        if (len(dynamic_string_sections) != 1
                                or symbol_name_offset >= int(dynamic_string_sections[0]["sh_size"])):
                            raise ValueError("dynamic import name is outside the unique .dynstr table")
                        try:
                            symbol_name = dynamic_string_sections[0].get_string(symbol_name_offset)
                        except UnicodeDecodeError as exc:
                            raise ValueError("dynamic symbol name is not valid UTF-8") from exc
                        binding = (info_byte >> 4) & 0xF
                        if not symbol_name or binding not in {1, 2}:
                            raise ValueError("relocation import name or binding is unsupported")
                        resolved = symbol_resolver(symbol_name, binding == 2)
                        if resolved is None:
                            if binding != 2:
                                raise ValueError("unresolved strong dynamic symbol")
                            symbol_address = 0
                        else:
                            symbol_address = resolved.address
                            if (not isinstance(symbol_address, int)
                                    or isinstance(symbol_address, bool)
                                    or symbol_address < 0
                                    or symbol_address > 0xFFFFFFFF):
                                raise ValueError("resolved symbol address is outside ELF32")
                            thumb_target = resolved.thumb_target
        value = _relocation_value(
            kind, load_base=load_bias, implicit_addend=implicit_addend,
            explicit_addend=addend, symbol_address=symbol_address,
            thumb_target=thumb_target,
        )
        if temporary_pages:
            original_permissions = []
            try:
                for page in temporary_pages:
                    flags = page_flags[page]
                    permission = ((UC_PROT_READ if flags & 4 else 0)
                                  | (UC_PROT_WRITE if flags & 2 else 0)
                                  | (UC_PROT_EXEC if flags & 1 else 0))
                    temporary_permission = (permission | UC_PROT_READ | UC_PROT_WRITE) & ~UC_PROT_EXEC
                    uc.mem_protect(page, PAGE_SIZE, temporary_permission)
                    original_permissions.append((page, permission))
                uc.mem_write(destination, struct.pack("<I", value & 0xFFFFFFFF))
            finally:
                restore_errors = []
                for page, permission in reversed(original_permissions):
                    try:
                        uc.mem_protect(page, PAGE_SIZE, permission)
                    except BaseException as restore_error:
                        restore_errors.append(restore_error)
                if restore_errors:
                    _poison_emulator(uc)
                    raise RuntimeError("relocation page protection restore failed; discard emulator") from restore_errors[0]
        else:
            uc.mem_write(destination, struct.pack("<I", value & 0xFFFFFFFF))

    if map_runtime_support:
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
    _ensure_emulator_usable(uc)
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
    symbol_resolver: Callable[[str, bool], ResolvedELF32Symbol | None] | None = None,
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
        _load_image(uc, elf, relocation_tables, dynamic_symbol_table,
                    symbol_resolver=symbol_resolver)
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
