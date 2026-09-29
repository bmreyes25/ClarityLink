import pytest
from elf_identity import HondaBuildIdentity
from hook_gate import (BuildRequirements, EnableCheck, HookGateFailure, matches_build,
                       can_enable_honda_hooks, prepare_exact_hook_transaction, verify_fingerprints)
from addressing import (AddressResolutionError, ProcMap, LoadSegment,
                        parse_maps, resolve_runtime_address)
from targets import HookFingerprint
from mock_hooks import (HookPatch, HookInstallError, InstallState,
                        MockAddressSpace, ReversibleHookTransaction)
from modes import BoundedDiagnostics, HookMode, HondaHookSemanticHarness

def identity(**changes):
    fields=dict(elf_sha256="a"*64,text_sha256="b"*64,file_size=4096,
                elf_class=32,endian="little",machine=40,elf_type=3,build_id=None)
    fields.update(changes);return HondaBuildIdentity(**fields)
def required(**changes):
    fields=dict(elf_sha256="a"*64,text_sha256="b"*64,file_size=4096,
                elf_class=32,endian="little",machine=40,elf_type=3,build_id=None,require_build_id=False)
    fields.update(changes);return BuildRequirements(**fields)

def test_exact_build_gate_accepts_only_all_identity_fields():
    good=identity();assert matches_build(good,required())
    for field,value in (("elf_sha256","c"*64),("text_sha256","c"*64),("file_size",4097),
                        ("machine",3),("elf_class",64),("endian","big"),("elf_type",2)):
        assert not matches_build(identity(**{field:value}),required()),field
    assert not matches_build(identity(build_id=b"x"),required(build_id=b"y",require_build_id=True))
    assert not matches_build(good,required(build_id=None,require_build_id=True))

def test_elf_inspector_reads_verified_local_jmcs_when_available():
    from pathlib import Path
    path=Path(__file__).resolve().parents[2]/"extracted/system/system/bin/jmcs"
    if not path.exists():pytest.skip("local ignored forensic ELF is not present")
    from elf_identity import inspect_elf32
    found=inspect_elf32(path.read_bytes()).identity
    assert found.elf_sha256=="cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232"
    assert found.text_sha256=="ca4abfd2f2c1f5f7fe88b4b0bde9e920d22b454f2a699b7de1f4984c901278eb"
    assert found.file_size==13406720 and (found.elf_class,found.endian,found.machine,found.elf_type)==(32,"little",40,3)
    assert found.build_id is None
    from targets import CANDIDATE_FINGERPRINTS,FUNCTION_ENTRY_PROLOGUES
    assert verify_fingerprints(path.read_bytes(),CANDIDATE_FINGERPRINTS+FUNCTION_ENTRY_PROLOGUES,text_va=0x13100,text_offset=0x13100)

def test_build_inspector_rejects_bad_elf():
    from elf_identity import ELFError,inspect_elf32
    with pytest.raises(ELFError):inspect_elf32(b"not ELF")

def test_fingerprint_verification_and_mismatch():
    image=bytearray(80);image[24:28]=bytes.fromhex("f8 f7 bc fd");image[40:42]=b"\x01\x02"
    fps=(HookFingerprint("site",24,"Thumb",bytes.fromhex("f8 f7 bc fd"),"candidate",True),
         HookFingerprint("thumb fn",40,"Thumb",b"\x01\x02","candidate",False))
    assert verify_fingerprints(bytes(image),fps,text_va=0,text_offset=0)
    image[24]=0
    assert not verify_fingerprints(bytes(image),fps,text_va=0,text_offset=0)
    assert not verify_fingerprints(bytes(8),fps,text_va=0,text_offset=0)

def test_thumb_load_bias_and_runtime_address():
    maps=parse_maps("50001000-50003000 r-xp 00001000 08:01 77 /system/bin/jmcs\n")
    segment=(LoadSegment(0x1000,0x1000,0x2000,0x2000,5),)
    assert resolve_runtime_address(0x1800,maps,segment,"/system/bin/jmcs")==0x50001800
    assert resolve_runtime_address(0x1801,maps,segment,"/system/bin/jmcs")==0x50001801

def test_address_resolver_rejects_missing_ambiguous_wrong_permissions_and_overflow():
    segment=(LoadSegment(0x1000,0x1000,0x2000,0x2000,5),)
    with pytest.raises(AddressResolutionError):resolve_runtime_address(0x1800,(),segment,"/system/bin/jmcs")
    duplicate=parse_maps("50001000-50003000 r-xp 00001000 08:01 77 /system/bin/jmcs\n50004000-50006000 r-xp 00001000 08:01 77 /system/bin/jmcs\n")
    with pytest.raises(AddressResolutionError):resolve_runtime_address(0x1800,duplicate,segment,"/system/bin/jmcs")
    noexec=parse_maps("50001000-50003000 rw-p 00001000 08:01 77 /system/bin/jmcs\n")
    with pytest.raises(AddressResolutionError):resolve_runtime_address(0x1800,noexec,segment,"/system/bin/jmcs")
    wrongpath=parse_maps("50001000-50003000 r-xp 00001000 08:01 77 /tmp/other\n")
    with pytest.raises(AddressResolutionError):resolve_runtime_address(0x1800,wrongpath,segment,"/system/bin/jmcs")
    overflow_map=(ProcMap(0xfffff000,0xffffffff,"r-xp",0x1000,"/system/bin/jmcs"),)
    high_segment=(LoadSegment(0x1000,0xffffe000,0x2000,0x2000,5),)
    with pytest.raises(AddressResolutionError):resolve_runtime_address(0xfffff800,overflow_map,high_segment,"/system/bin/jmcs")

def test_enable_check_requires_all_and_augment_has_extra_gates():
    base=dict(build_match=True,fingerprints_match=True,isa_supported=True,address_ranges_valid=True,
              hook_configuration_supported=True,trampoline_ready=True,rollback_ready=True,
              noop_previously_validated=True,explicit_interop_enable=True)
    assert EnableCheck(**base).hooks_may_be_prepared and EnableCheck(**base).augment_may_be_enabled
    assert can_enable_honda_hooks(EnableCheck(**base))
    for key in tuple(base)[:5]:
        assert not EnableCheck(**{**base,key:False}).hooks_may_be_prepared
    assert not can_enable_honda_hooks(EnableCheck(**{**base,"fingerprints_match":False}))
    assert not EnableCheck(**{**base,"trampoline_ready":False}).augment_may_be_enabled
    assert not EnableCheck(**{**base,"noop_previously_validated":False}).augment_may_be_enabled
    assert not EnableCheck(**{**base,"explicit_interop_enable":False}).augment_may_be_enabled

def test_mock_transaction_preflight_no_partial_activation_and_restore():
    space=MockAddressSpace(0x1000,b"ABCDEFGH")
    patches=(HookPatch("a",0x1000,b"AB",b"xy"),HookPatch("b",0x1004,b"EF",b"zz"))
    tx=ReversibleHookTransaction(space,patches);tx.prepare();tx.activate()
    assert tx.state is InstallState.ACTIVE and space.read(0x1000,8)==b"xyCDzzGH"
    tx.rollback();tx.rollback()
    assert tx.state is InstallState.ROLLED_BACK and space.read(0x1000,8)==b"ABCDEFGH"

def test_mock_mismatch_overlap_or_write_failure_restores_all():
    space=MockAddressSpace(0x1000,b"ABCDEFGH")
    bad=ReversibleHookTransaction(space,(HookPatch("a",0x1000,b"AB",b"xy"),HookPatch("b",0x1004,b"XX",b"zz")))
    with pytest.raises(HookInstallError):bad.prepare()
    assert space.read(0x1000,8)==b"ABCDEFGH"
    overlap=ReversibleHookTransaction(space,(HookPatch("a",0x1000,b"ABCD",b"wxyz"),HookPatch("b",0x1002,b"CD",b"12")))
    with pytest.raises(HookInstallError):overlap.prepare()
    failing=ReversibleHookTransaction(space,(HookPatch("a",0x1000,b"AB",b"xy"),HookPatch("b",0x1004,b"EF",b"zz")))
    failing.prepare();space.fail_write_at=2
    with pytest.raises(HookInstallError):failing.activate()
    assert space.read(0x1000,8)==b"ABCDEFGH" and failing.state is InstallState.ROLLED_BACK

def test_noop_exact_stock_delegation_and_bounded_secret_free_event():
    diag=BoundedDiagnostics(2);h=HondaHookSemanticHarness(HookMode.NOOP,diag)
    request={"streams":[{"type":111,"streamConnectionID":999,"secret":b"private"}]};result={"opaque":object()};seen=[]
    out=h.setup(request,lambda q:(seen.append(q),result)[1])
    assert seen[0] is request and out is result
    assert diag.snapshot()[0].category=="setup_noop"
    assert "private" not in repr(diag.snapshot())

def test_observe_mode_non_mutating_counts_types_only_and_is_bounded():
    diag=BoundedDiagnostics(2);h=HondaHookSemanticHarness(HookMode.OBSERVE,diag)
    request={"streams":[{"type":100,"token":"do-not-retain"},{"type":111,"streamConnectionID":7}]}
    original=repr(request); stock_result=(0,{"response":"unchanged"})
    assert h.setup(request,lambda q:stock_result) is stock_result
    event=diag.snapshot()[0]
    assert event.stream_types==(100,111) and event.stream_count==2 and repr(request)==original
    assert "token" not in repr(event) and "7" not in repr(event)
    for _ in range(3):h.setup({},lambda q:stock_result)
    assert len(diag.snapshot())==2

def test_augment_failure_returns_original_result_and_augment_requires_all_prerequisites():
    result=(0,{"stock":"same"});enabled=EnableCheck(True,True,True,True,True,True,True,True,True)
    h=HondaHookSemanticHarness(HookMode.AUGMENT)
    assert h.setup({},lambda _:result,augment=lambda *_:(_ for _ in ()).throw(RuntimeError())) is result
    assert h.setup({},lambda _:result,augment=lambda *_:(0,{}),enable_check=enabled)==(0,{})
    blocked=EnableCheck(True,True,True,True,True,False,True,True,True)
    assert h.setup({},lambda _:result,augment=lambda *_:(0,{}),enable_check=blocked) is result

def test_off_mode_delegates_without_diagnostics():
    d=BoundedDiagnostics();h=HondaHookSemanticHarness(HookMode.OFF,d);result=object()
    assert h.setup({},lambda _:result) is result and not d.snapshot()


def test_exact_hook_group_prepare_requires_build_fp_and_all_sites_before_writes():
    from pathlib import Path
    from targets import JMCS_SHA256,JMCS_TEXT_SHA256,JMCS_FILE_SIZE,JMCS_ELF_CLASS,JMCS_ENDIAN,JMCS_MACHINE,JMCS_TYPE,CANDIDATE_FINGERPRINTS
    image=(Path(__file__).resolve().parents[2]/"extracted/system/system/bin/jmcs").read_bytes()
    req=BuildRequirements(JMCS_SHA256,JMCS_TEXT_SHA256,JMCS_FILE_SIZE,JMCS_ELF_CLASS,JMCS_ENDIAN,JMCS_MACHINE,JMCS_TYPE)
    fps=CANDIDATE_FINGERPRINTS
    base=fps[0].static_va
    patches=tuple(HookPatch(f.name,f.static_va,f.expected_bytes,b"\x00"*len(f.expected_bytes)) for f in fps)
    # The second synthetic site is mapped to the matching bytes by its exact VA.
    mem=MockAddressSpace(base,bytearray(max(f.static_va for f in fps)-base+4))
    for f in fps:
        off=f.static_va-base;mem.data[off:off+len(f.expected_bytes)]=f.expected_bytes
    checks=EnableCheck(True,True,True,True,True,False,True)
    tx=prepare_exact_hook_transaction(image,req,fps,checks,mem,patches)
    assert tx.state is InstallState.PREPARED and mem.write_count==0
    with pytest.raises(HookGateFailure):prepare_exact_hook_transaction(image,required(elf_sha256="0"*64),fps,checks,mem,patches)
    with pytest.raises(HookGateFailure):prepare_exact_hook_transaction(image,req,fps,EnableCheck(False,True,True,True,True,False,True),mem,patches)
    assert mem.write_count==0


def test_observe_mode_classifies_null_bad_response_and_unexpected_request():
    h=HondaHookSemanticHarness(HookMode.OBSERVE)
    h.setup({},lambda _:None)
    h.setup({},lambda _:(0,None))
    h.setup(None,lambda _:(0,{}))
    assert [e.error_class for e in h.diagnostics.snapshot()]==["null_stock_result","unexpected_response_type","unexpected_request_type"]

def test_failed_restore_can_be_retried_without_losing_original_bytes():
    space=MockAddressSpace(0x1000,b"ABCDEFGH")
    tx=ReversibleHookTransaction(space,(HookPatch("a",0x1000,b"AB",b"xy"),HookPatch("b",0x1004,b"EF",b"zz")))
    tx.prepare();tx.activate();space.fail_write_at=4
    with pytest.raises(HookInstallError):tx.rollback()
    space.fail_write_at=None;tx.rollback()
    assert tx.state is InstallState.ROLLED_BACK and space.read(0x1000,8)==b"ABCDEFGH"


def test_noop_and_observe_rethrow_stock_exception_after_bounded_diagnostic():
    for mode in (HookMode.NOOP,HookMode.OBSERVE):
        h=HondaHookSemanticHarness(mode)
        def fail(_):raise RuntimeError("secret-like detail must not be recorded")
        with pytest.raises(RuntimeError):h.setup({},fail)
        event=h.diagnostics.snapshot()[0]
        assert event.error_class=="RuntimeError" and "secret-like" not in repr(event)

def test_diagnostics_are_thread_safe_under_interleaved_callbacks():
    from concurrent.futures import ThreadPoolExecutor
    h=HondaHookSemanticHarness(HookMode.OBSERVE,BoundedDiagnostics(128))
    stock=(0,{})
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda n:h.setup({"streams":[{"type":n}]},lambda _:stock),range(80)))
    events=h.diagnostics.snapshot()
    assert len(events)==80 and sorted(e.stream_types[0] for e in events)==list(range(80))


def test_gnu_build_id_is_parsed_and_can_be_required():
    import struct
    from elf_identity import inspect_elf32
    names=b"\x00.shstrtab\x00.note.gnu.build-id\x00.text\x00"
    name_shstr=1;name_note=11;name_text=30
    note=struct.pack("<III",4,4,3)+b"GNU\x00"+b"ABCD"
    shoff=0x100;names_off=0x80;note_off=0xA8;text_off=0xC8
    blob=bytearray(shoff+4*40)
    ident=b"\x7fELF"+bytes([1,1,1,0])+bytes(8)
    header=struct.pack("<HHIIIIIHHHHHH",3,40,1,0,0,shoff,0,52,0,0,40,4,1)
    blob[:16]=ident;blob[16:52]=header
    blob[names_off:names_off+len(names)]=names
    blob[note_off:note_off+len(note)]=note
    blob[text_off:text_off+4]=b"CODE"
    sections=[
        (0,0,0,0,0,0,0,0,0,0),
        (name_shstr,3,0,0,names_off,len(names),0,0,1,0),
        (name_note,7,0,0,note_off,len(note),0,0,4,0),
        (name_text,1,6,0x1000,text_off,4,0,0,4,0),
    ]
    for i,section in enumerate(sections):struct.pack_into("<IIIIIIIIII",blob,shoff+i*40,*section)
    found=inspect_elf32(bytes(blob)).identity
    assert found.build_id==b"ABCD"
    req=BuildRequirements(found.elf_sha256,found.text_sha256,found.file_size,32,"little",40,3,b"ABCD",True)
    assert matches_build(found,req)
    assert not matches_build(found,BuildRequirements(found.elf_sha256,found.text_sha256,found.file_size,32,"little",40,3,b"EFGH",True))

def test_hook_fingerprints_reject_misaligned_or_non_call_branch_sites():
    with pytest.raises(ValueError):HookFingerprint("misaligned",25,"Thumb",b"\x00\x00","candidate",False)
    with pytest.raises(ValueError):HookFingerprint("not bl",24,"Thumb",b"CALL","candidate",True)

def test_noop_preserves_stock_failure_and_mode_defaults_off():
    result=(-6767,{"stockError":"unchanged"});request={"streams":[{"type":110}]};seen=[]
    h=HondaHookSemanticHarness()
    assert h.mode is HookMode.OFF
    noop=HondaHookSemanticHarness(HookMode.NOOP)
    assert noop.setup(request,lambda x:(seen.append(x),result)[1]) is result
    assert seen==[request] and noop.diagnostics.snapshot()[0].stock_succeeded is False
