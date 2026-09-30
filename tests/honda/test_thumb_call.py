import pytest

from thumb_call import (
    BL_MAX_DISPLACEMENT,
    BL_MIN_DISPLACEMENT,
    ThumbEncodingError,
    can_direct_call,
    decode_thumb_bl,
    encode_thumb_bl,
    encode_thumb_veneer,
    normalize_thumb_pointer,
    thumb_function_pointer,
)
from callsite import HONDA_CALLSITES, StaticCallSite
from mock_hooks import HookPatch, InstallState, MockAddressSpace, ReversibleHookTransaction


def test_exact_jmcs_call_sites_decode_to_stock_targets():
    info = decode_thumb_bl(0x28A158, bytes.fromhex("f8 f7 bc fd"))
    setup = decode_thumb_bl(0x28AF72, bytes.fromhex("fa f7 b5 fa"))
    assert (info.target, info.displacement, info.return_address) == (0x282CD4, -0x7488, 0x28A15C)
    assert (setup.target, setup.displacement, setup.return_address) == (0x2854E0, -0x5A96, 0x28AF76)
    assert encode_thumb_bl(info.call_address, info.target) == bytes.fromhex("f8 f7 bc fd")
    assert encode_thumb_bl(setup.call_address, setup.target) == bytes.fromhex("fa f7 b5 fa")


def test_callsite_patch_model_only_replaces_fingerprinted_bl_and_checks_runtime_target():
    site = HONDA_CALLSITES[0]
    patch = site.patch_for(site.static_address + 0x40000000, 0x40290000)
    assert isinstance(patch, HookPatch)
    assert len(patch.replacement) == len(site.expected_bytes) == 4
    bad = StaticCallSite("bad", site.static_address, site.expected_bytes, site.stock_target + 2)
    with pytest.raises(ValueError, match="stock call target"):
        bad.patch_for(site.static_address, 0x28B000)
    with pytest.raises(ValueError, match="outside"):
        site.patch_for(site.static_address, 0x50000000)


@pytest.mark.parametrize("site,target", [(0x10000, 0x20000), (0x2000000, 0x1000004), (0x2000000, 0x3000002)])
def test_encode_decode_roundtrip(site, target):
    assert decode_thumb_bl(site, encode_thumb_bl(site, target)).target == target


def test_branch_range_inclusive_edges_and_outside_values():
    site = 0x02000000
    low = site + 4 + BL_MIN_DISPLACEMENT
    high = site + 4 + BL_MAX_DISPLACEMENT
    assert can_direct_call(site, low) and can_direct_call(site, high)
    assert not can_direct_call(site, low - 2)
    assert not can_direct_call(site, high + 2)
    assert decode_thumb_bl(site, encode_thumb_bl(site, low)).displacement == BL_MIN_DISPLACEMENT
    assert decode_thumb_bl(site, encode_thumb_bl(site, high)).displacement == BL_MAX_DISPLACEMENT


@pytest.mark.parametrize("site,target", [(1, 0x100), (0, 3), (0xFFFFFFFC, 0xFFFFFFFE), (0, 0xFFFFFFFE)])
def test_invalid_alignment_and_address_overflow_are_rejected(site, target):
    with pytest.raises(ThumbEncodingError):
        encode_thumb_bl(site, target)


def test_thumb_function_pointer_bit_is_explicit():
    assert normalize_thumb_pointer(0x1235) == 0x1234
    assert thumb_function_pointer(0x1234) == 0x1235
    with pytest.raises(ThumbEncodingError):
        normalize_thumb_pointer(0x1234)
    with pytest.raises(ThumbEncodingError):
        encode_thumb_bl(0x1000, 0x1235)


def test_veneer_emits_thumb_literal_branch_without_touching_argument_registers():
    assert encode_thumb_veneer(0x11000, 0x12345679) == bytes.fromhex("df f8 04 c0 60 47 00 00 79 56 34 12")
    with pytest.raises(ThumbEncodingError):
        encode_thumb_veneer(0x11002, 0x12345679)
    with pytest.raises(ThumbEncodingError):
        encode_thumb_veneer(0x11000, 0x12345678)


def test_unicorn_executes_bl_veneer_noop_delegation_and_return_when_installed():
    unicorn = pytest.importorskip("unicorn")
    from unicorn import Uc, UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_THUMB
    from unicorn.arm_const import (
        UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_R4,
        UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7, UC_ARM_REG_R8, UC_ARM_REG_R9,
        UC_ARM_REG_R10, UC_ARM_REG_R11, UC_ARM_REG_SP,
    )

    caller, veneer, shim, original = 0x10000, 0x11000, 0x12000, 0x13000
    original_call = encode_thumb_bl(caller, original)
    replacement_call = encode_thumb_bl(caller, veneer)
    patch_space = MockAddressSpace(caller, original_call)
    patch_tx = ReversibleHookTransaction(
        patch_space, (HookPatch("synthetic-call", caller, original_call, replacement_call),)
    )
    patch_tx.prepare()
    patch_tx.activate()
    call = patch_space.read(caller, 4)
    assert call == replacement_call
    # `push {r4,lr}; mov r4,lr; bl original; mov lr,r4; pop {r4,pc}`.
    shim_code = bytes.fromhex("10 b5 74 46") + encode_thumb_bl(shim + 4, original) + bytes.fromhex("a6 46 10 bd")
    # Stand-in original callee: increment r0 and return; r1 is deliberately untouched.
    original_code = bytes.fromhex("01 30 70 47")
    # Caller continuation contains NOP then BKPT; stop at its first instruction.
    caller_code = call + bytes.fromhex("00 bf 00 be")
    mu = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    mu.mem_map(0x10000, 0x10000)
    mu.mem_map(0x70000, 0x10000)
    mu.mem_write(caller, caller_code)
    mu.mem_write(veneer, encode_thumb_veneer(veneer, shim | 1))
    mu.mem_write(shim, shim_code)
    mu.mem_write(original, original_code)
    initial_sp = 0x80000
    mu.reg_write(UC_ARM_REG_SP, initial_sp)
    mu.reg_write(UC_ARM_REG_R0, 41)
    mu.reg_write(UC_ARM_REG_R1, 0x1234)
    mu.reg_write(UC_ARM_REG_R2, 0x2345)
    mu.reg_write(UC_ARM_REG_R3, 0x3456)
    callee_saved = {
        UC_ARM_REG_R4: 0x4444, UC_ARM_REG_R5: 0x5555, UC_ARM_REG_R6: 0x6666,
        UC_ARM_REG_R7: 0x7777, UC_ARM_REG_R8: 0x8888, UC_ARM_REG_R9: 0x9999,
        UC_ARM_REG_R10: 0xAAAA, UC_ARM_REG_R11: 0xBBBB,
    }
    for register, value in callee_saved.items():
        mu.reg_write(register, value)
    continuation = caller + 4
    reached = []

    def stop_at_continuation(uc, address, _size, _user):
        if address == continuation:
            reached.append(address)
            uc.emu_stop()

    mu.hook_add(UC_HOOK_CODE, stop_at_continuation)
    mu.emu_start(caller | 1, 0x20000, count=100)
    assert mu.reg_read(UC_ARM_REG_R0) == 42
    assert mu.reg_read(UC_ARM_REG_R1) == 0x1234
    assert mu.reg_read(UC_ARM_REG_R2) == 0x2345
    assert mu.reg_read(UC_ARM_REG_R3) == 0x3456
    for register, value in callee_saved.items():
        assert mu.reg_read(register) == value
    assert mu.reg_read(UC_ARM_REG_SP) == initial_sp
    assert reached == [continuation]
    patch_tx.rollback()
    assert patch_tx.state is InstallState.ROLLED_BACK
    assert patch_space.read(caller, 4) == original_call
