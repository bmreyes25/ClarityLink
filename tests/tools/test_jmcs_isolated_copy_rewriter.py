import hashlib
import shutil
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.jmcs_integration import isolated_copy_rewriter as rewriter
import callsite_plan
from callsite import HONDA_CALLSITES
from thumb_call import encode_thumb_bl


TEXT_OFFSET = 0x100
TEXT_VA = 0x28A000
CAVE_OFFSET = 0x1100
FILE_SIZE = 0x1491
SECTION_OFFSET = 0x1400
STRING_OFFSET = 0x1480
STRINGS = b"\0.text\0.shstrtab\0"


def synthetic_jmcs(*, second_cave=False, short_cave=False, cave_overlaps_text=False,
                   split_executable_segment=False) -> bytes:
    """Build an ELF fixture with both pinned calls and controlled cave layouts."""
    raw = bytearray(FILE_SIZE)
    raw[:7] = b"\x7fELF\x01\x01\x01"
    struct.pack_into("<HHI", raw, 16, 3, 40, 1)  # ET_DYN, EM_ARM, EV_CURRENT
    # The first executable PT_LOAD maps the callsites and, normally, the cave.
    phoff = 52
    phnum = 3 if split_executable_segment else 2
    struct.pack_into("<I", raw, 28, phoff)
    struct.pack_into("<I", raw, 36, 0x05000000)  # ARM EABI5
    struct.pack_into("<HHHHHH", raw, 40, 52, 32, phnum, 40, 3, 2)
    first_filesz = CAVE_OFFSET if split_executable_segment else 0x1300
    segment_base = TEXT_VA - TEXT_OFFSET
    struct.pack_into("<IIIIIIII", raw, phoff, 6, phoff, segment_base + phoff,
                     segment_base + phoff, phnum * 32, phnum * 32, 4, 4)
    struct.pack_into("<IIIIIIII", raw, phoff + 32, 1, 0, segment_base,
                     segment_base, first_filesz, first_filesz, 5, 1)
    raw[phoff + phnum * 32:TEXT_OFFSET] = b"\x99" * (TEXT_OFFSET - (phoff + phnum * 32))
    if split_executable_segment:
        far_va = 0x128B000
        struct.pack_into("<IIIIIIII", raw, phoff + 64, 1, CAVE_OFFSET, far_va,
                         far_va, 0x200, 0x200, 5, 1)

    raw[TEXT_OFFSET:TEXT_OFFSET + 0x1000] = b"\xcc" * 0x1000
    info = HONDA_CALLSITES[0]
    info_off = TEXT_OFFSET + info.static_address - TEXT_VA
    raw[info_off:info_off + 4] = info.expected_bytes
    context_off = TEXT_OFFSET + callsite_plan.CONTEXT_VA - TEXT_VA
    raw[context_off:context_off + len(callsite_plan.CONTEXT_BYTES)] = callsite_plan.CONTEXT_BYTES
    prologue_off = TEXT_OFFSET + callsite_plan.PROLOGUE_VA - TEXT_VA
    raw[prologue_off:prologue_off + len(callsite_plan.PROLOGUE_BYTES)] = callsite_plan.PROLOGUE_BYTES

    if short_cave:
        raw[CAVE_OFFSET:CAVE_OFFSET + 2 * rewriter.STUB_SIZE - 1] = b"\0" * (2 * rewriter.STUB_SIZE - 1)
        raw[CAVE_OFFSET + 2 * rewriter.STUB_SIZE - 1:0x1300] = b"\xaa" * (0x1300 - (2 * rewriter.STUB_SIZE - 1 + CAVE_OFFSET))
    elif cave_overlaps_text:
        # A .text section covering the otherwise-zero run makes it ineligible.
        pass
    elif second_cave:
        raw[CAVE_OFFSET + 0x200] = 0x7f
        raw[CAVE_OFFSET + 0x201:0x1380] = b"\0" * (0x1380 - CAVE_OFFSET - 0x201)
        first_filesz = 0x1380
        struct.pack_into("<I", raw, phoff + 32 + 16, first_filesz)
        struct.pack_into("<I", raw, phoff + 32 + 20, first_filesz)

    raw[STRING_OFFSET:STRING_OFFSET + len(STRINGS)] = STRINGS
    # Three section records: null, .text, .shstrtab.
    text_size = 0x1200 if cave_overlaps_text else 0x1000
    struct.pack_into("<IIIIIIIIII", raw, SECTION_OFFSET + 40,
                     1, 1, 6, TEXT_VA, TEXT_OFFSET, text_size, 0, 0, 4, 0)
    struct.pack_into("<IIIIIIIIII", raw, SECTION_OFFSET + 80,
                     7, 3, 0, 0, STRING_OFFSET, len(STRINGS), 0, 0, 1, 0)
    struct.pack_into("<I", raw, 32, SECTION_OFFSET)
    return bytes(raw)


class IsolatedCopyRewriterTests(unittest.TestCase):
    def _with_fixture_identity(self, data):
        return patch.object(callsite_plan, "REFERENCE_SHA256", hashlib.sha256(data).hexdigest())

    def test_plan_uses_exact_honda_boundaries_and_stock_passthrough(self):
        data = synthetic_jmcs()
        with self._with_fixture_identity(data):
            plan = rewriter.build_patch_plan(data)
        self.assertEqual([item.site_va for item in plan.patches], [0x28A158, 0x28AFBA])
        self.assertEqual([item.stock_target for item in plan.patches], [0x282CD4, 0x289F60])
        self.assertEqual(len(plan.changed_offsets), 16)
        for item in plan.patches:
            self.assertEqual(len(item.stub_bytes), 4)
            self.assertEqual(rewriter.decode_thumb_b_w(item.stub_va, item.stub_bytes), item.stock_target)
            self.assertEqual(decode(item.site_va, item.replacement), item.stub_va)

    def test_creates_deterministic_isolated_copy_and_preserves_input(self):
        original = synthetic_jmcs()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "jmcs.fixture"
            first, second = root / "copy-a", root / "copy-b"
            source.write_bytes(original)
            with self._with_fixture_identity(original):
                receipt_a = rewriter.rewrite_isolated_copy(source, first)
                receipt_b = rewriter.rewrite_isolated_copy(source, second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(receipt_a.output_sha256, receipt_b.output_sha256)
            self.assertEqual(source.read_bytes(), original)
            patched = first.read_bytes()
            self.assertEqual(len(patched), len(original))
            self.assertLessEqual(receipt_a.changed_byte_count, 16)
            self.assertGreater(receipt_a.changed_byte_count, 8)
            with self._with_fixture_identity(original):
                plan = rewriter.build_patch_plan(original)
            for item in plan.patches:
                self.assertEqual(patched[item.site_offset:item.site_offset + 4], item.replacement)
                self.assertEqual(patched[item.stub_offset:item.stub_offset + rewriter.STUB_SIZE], item.stub_bytes)
            self.assertTrue(receipt_a.pass_through_only)
            self.assertFalse(receipt_a.type111_supported)

    def test_appended_pt_loads_relocate_phdr_and_keep_ro_rx_separate(self):
        original = synthetic_jmcs(short_cave=True)
        with self._with_fixture_identity(original):
            plan = rewriter.build_appended_load_plan(original)
        self.assertEqual(plan.method, "appended-PT_LOAD")
        self.assertEqual(len(plan.expected_segments), 2)
        ro, rx = plan.expected_segments
        self.assertEqual(ro[4] & 2, 0)
        self.assertEqual(rx[4] & 2, 0)
        self.assertEqual(rx[4] & 1, 1)
        patched = rewriter._apply_plan(original, plan)
        rewriter._validate_patched_copy(original, patched, plan)
        self.assertEqual(struct.unpack_from("<I", patched, 28)[0], plan.expected_phoff)
        self.assertEqual(struct.unpack_from("<H", patched, 44)[0], plan.expected_phnum)
        self.assertEqual(patched[:len(original)][52:52 + 64], original[52:52 + 64])
        for item in plan.patches:
            self.assertEqual(decode(item.site_va,
                                    patched[item.site_offset:item.site_offset + 4]), item.stub_va)
            self.assertEqual(rewriter.decode_thumb_b_w(
                item.stub_va, patched[item.stub_offset:item.stub_offset + 4]), item.stock_target)

    def test_appended_pt_load_method_creates_only_a_new_isolated_copy(self):
        original = synthetic_jmcs(short_cave=True)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, output = root / "original", root / "isolated-copy"
            source.write_bytes(original)
            with self._with_fixture_identity(original):
                receipt = rewriter.rewrite_isolated_copy(source, output, "appended-PT_LOAD")
            self.assertTrue(receipt.output_sha256)
            self.assertEqual(source.read_bytes(), original)
            self.assertGreater(output.stat().st_size, len(original))
            self.assertGreater(receipt.changed_byte_count, output.stat().st_size - len(original))

    def test_appended_pt_load_rejects_missing_original_pt_phdr(self):
        data = bytearray(synthetic_jmcs(short_cave=True))
        struct.pack_into("<I", data, 52, 0)  # remove the only PT_PHDR in this fixture
        data = bytes(data)
        with self._with_fixture_identity(data):
            with self.assertRaisesRegex(rewriter.RewriteError, "exactly one PT_PHDR"):
                rewriter.build_appended_load_plan(data)

    def test_rejects_wrong_reference_hash_and_wrong_info_call_bytes(self):
        data = synthetic_jmcs()
        with patch.object(callsite_plan, "REFERENCE_SHA256", "0" * 64):
            with self.assertRaisesRegex(rewriter.RewriteError, "SHA-256"):
                rewriter.build_patch_plan(data)

        changed = bytearray(data)
        info_off = TEXT_OFFSET + HONDA_CALLSITES[0].static_address - TEXT_VA
        changed[info_off] ^= 1
        changed = bytes(changed)
        with self._with_fixture_identity(changed):
            with self.assertRaisesRegex(rewriter.RewriteError, "/info stock call bytes"):
                rewriter.build_patch_plan(changed)

    def test_rejects_missing_or_ambiguous_executable_cave(self):
        for data, phrase in (
            (synthetic_jmcs(short_cave=True), "found 0"),
            (synthetic_jmcs(second_cave=True), "found 2"),
            (synthetic_jmcs(cave_overlaps_text=True), "found 0"),
        ):
            with self.subTest(phrase=phrase), self._with_fixture_identity(data):
                with self.assertRaisesRegex(rewriter.RewriteError, phrase):
                    rewriter.build_patch_plan(data)

    def test_rejects_out_of_range_thumb_redirect(self):
        data = synthetic_jmcs(split_executable_segment=True)
        with self._with_fixture_identity(data):
            with self.assertRaisesRegex(rewriter.RewriteError, "outside the signed 25-bit"):
                rewriter.build_patch_plan(data)

    def test_rejects_existing_output_and_repository_output_directory(self):
        data = synthetic_jmcs()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, output = root / "source", root / "copy"
            source.write_bytes(data)
            with self._with_fixture_identity(data):
                with self.assertRaisesRegex(rewriter.RewriteError, "already exists"):
                    rewriter.rewrite_isolated_copy(source, source)
            output.write_bytes(b"preserve")
            with self._with_fixture_identity(data):
                with self.assertRaisesRegex(rewriter.RewriteError, "already exists"):
                    rewriter.rewrite_isolated_copy(source, output)
            self.assertEqual(output.read_bytes(), b"preserve")
            inside_repo = rewriter.ROOT / "jmcs-test-output-not-created"
            with self._with_fixture_identity(data):
                with self.assertRaisesRegex(rewriter.RewriteError, "outside the public Git"):
                    rewriter.rewrite_isolated_copy(source, inside_repo)
            self.assertFalse(inside_repo.exists())

    def test_nonzero_cave_bytes_are_never_overwritten(self):
        data = bytearray(synthetic_jmcs())
        data[CAVE_OFFSET:0x1300] = b"\xaa" * (0x1300 - CAVE_OFFSET)
        data[CAVE_OFFSET:CAVE_OFFSET + 2 * rewriter.STUB_SIZE - 1] = b"\0" * (2 * rewriter.STUB_SIZE - 1)
        data = bytes(data)
        with self._with_fixture_identity(data):
            with self.assertRaisesRegex(rewriter.RewriteError, "found 0"):
                rewriter.build_patch_plan(data)

    def test_written_copy_validation_rejects_changes_outside_patch_allowlist(self):
        data = synthetic_jmcs()
        with self._with_fixture_identity(data):
            plan = rewriter.build_patch_plan(data)
        patched = bytearray(rewriter._apply_plan(data, plan))
        patched[0x20] ^= 1
        with self.assertRaisesRegex(rewriter.RewriteError, "outside the exact patch allowlist"):
            rewriter._validate_patched_copy(data, bytes(patched), plan)

    def test_arm_emulator_executes_each_stub_once_and_restores_abi_state(self):
        try:
            from unicorn import Uc, UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_THUMB
            from unicorn.arm_const import (UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0,
                                           UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
                                           UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6,
                                           UC_ARM_REG_R7, UC_ARM_REG_R8, UC_ARM_REG_R9,
                                           UC_ARM_REG_R10, UC_ARM_REG_R11, UC_ARM_REG_SP)
        except ImportError:
            self.skipTest("install requirements-test.txt to run ARM/Thumb emulation")

        callsite_va, stub_va, stack_va = 0x10000, 0x10100, 0x20000
        args = (0x11, 0x22, 0x33, 0x44)
        for stock_target in (0x282CD4, 0x289F60):
            machine = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
            for page in (0x10000, stock_target & ~0xFFF, 0x20000):
                machine.mem_map(page, 0x1000)
            machine.mem_write(callsite_va, encode_thumb_bl(callsite_va, stub_va))
            machine.mem_write(stub_va, rewriter.encode_thumb_b_w(stub_va, stock_target))
            machine.mem_write(stock_target, bytes.fromhex("42 20 70 47"))  # movs r0,#0x42; bx lr
            initial_sp = stack_va + 0x800
            callee_saved = (0x55667788, 0x01020304, 0x11121314, 0x21222324,
                            0x31323334, 0x41424344, 0x51525354, 0x61626364)
            for reg, value in zip((UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3), args):
                machine.reg_write(reg, value)
            for reg, value in zip((UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7,
                                   UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R10, UC_ARM_REG_R11), callee_saved):
                machine.reg_write(reg, value)
            machine.reg_write(UC_ARM_REG_SP, initial_sp)
            machine.reg_write(UC_ARM_REG_LR, 0x7777 | 1)
            seen = []

            def on_code(uc, address, size, _):
                if address == stock_target:
                    seen.append((uc.reg_read(UC_ARM_REG_R0), uc.reg_read(UC_ARM_REG_R1),
                                 uc.reg_read(UC_ARM_REG_R2), uc.reg_read(UC_ARM_REG_R3),
                                 uc.reg_read(UC_ARM_REG_SP), uc.reg_read(UC_ARM_REG_LR)))

            machine.hook_add(UC_HOOK_CODE, on_code)
            continuation = callsite_va + 4
            machine.emu_start(callsite_va | 1, continuation, count=32)
            self.assertEqual(seen, [(*args, initial_sp, continuation | 1)])
            self.assertEqual(machine.reg_read(UC_ARM_REG_R0), 0x42)
            for reg, value in zip((UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7,
                                   UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R10, UC_ARM_REG_R11), callee_saved):
                self.assertEqual(machine.reg_read(reg), value)
            self.assertEqual(machine.reg_read(UC_ARM_REG_SP), initial_sp)
            self.assertEqual(machine.reg_read(UC_ARM_REG_LR), continuation | 1)
            self.assertEqual(machine.reg_read(UC_ARM_REG_PC) & ~1, continuation)

    @unittest.skipUnless(shutil.which("clang"), "clang is required for the native template check")
    def test_assembly_templates_compile_to_two_thumb_jump_relocations(self):
        with tempfile.TemporaryDirectory() as temp:
            obj = Path(temp) / "stock.o"
            subprocess.run([
                shutil.which("clang"), "-target", "armv7-none-eabi", "-c",
                str(rewriter.ROOT / "src/claritylink-negotiation/thumb_stock_passthrough.S"),
                "-o", str(obj),
            ], check=True, capture_output=True, text=True)
            data = obj.read_bytes()
        shoff = struct.unpack_from("<I", data, 32)[0]
        shentsize, shnum, shstrndx = struct.unpack_from("<HHH", data, 46)
        sections = [struct.unpack_from("<IIIIIIIIII", data, shoff + i * shentsize)
                    for i in range(shnum)]
        names_section = sections[shstrndx]
        section_names = data[names_section[4]:names_section[4] + names_section[5]]

        def section_name(section):
            end = section_names.find(b"\0", section[0])
            return section_names[section[0]:end].decode("ascii")

        by_name = {section_name(section): section for section in sections}
        text = by_name[".text"]
        self.assertEqual(data[text[4]:text[4] + text[5]], bytes.fromhex("ff f7 fe bf ff f7 fe bf"))
        reloc = by_name[".rel.text"]
        symbols = sections[reloc[6]]
        symbol_strings_section = sections[symbols[6]]
        symbol_strings = data[symbol_strings_section[4]:symbol_strings_section[4] + symbol_strings_section[5]]
        symbol_names = []
        for offset in range(symbols[4], symbols[4] + symbols[5], symbols[9]):
            name_offset = struct.unpack_from("<I", data, offset)[0]
            end = symbol_strings.find(b"\0", name_offset)
            symbol_names.append(symbol_strings[name_offset:end].decode("ascii"))
        relocations = []
        for offset in range(reloc[4], reloc[4] + reloc[5], reloc[9]):
            place, info = struct.unpack_from("<II", data, offset)
            relocations.append((place, info & 0xFF, symbol_names[info >> 8]))
        self.assertEqual(relocations, [
            (0, 30, "AirPlayCopyServerInfo"),
            (4, 30, "_requestSendPlistResponse"),
        ])


def decode(address, raw):
    return rewriter.decode_thumb_bl(address, raw).target


if __name__ == "__main__":
    unittest.main()
