"""Fail-closed exact-build gate and evidence-only readiness policy."""
from dataclasses import dataclass
from elf_identity import HondaBuildIdentity
from targets import HookFingerprint

@dataclass(frozen=True)
class BuildRequirements:
    elf_sha256:str; text_sha256:str; file_size:int; elf_class:int; endian:str; machine:int; elf_type:int
    build_id:bytes|None=None; require_build_id:bool=False

def matches_build(identity:HondaBuildIdentity,required:BuildRequirements)->bool:
    if not isinstance(identity,HondaBuildIdentity) or not isinstance(required,BuildRequirements): return False
    return (identity.elf_sha256==required.elf_sha256 and identity.text_sha256==required.text_sha256
        and identity.file_size==required.file_size and identity.elf_class==required.elf_class
        and identity.endian==required.endian and identity.machine==required.machine
        and identity.elf_type==required.elf_type
        and (not required.require_build_id or (required.build_id is not None and identity.build_id==required.build_id)))

def verify_fingerprints(image:bytes,fingerprints:tuple[HookFingerprint,...],*,text_va:int,text_offset:int)->bool:
    if text_va<0 or text_offset<0:return False
    for fp in fingerprints:
        address=fp.static_va&~1; offset=text_offset+(address-text_va)
        if offset<text_offset or offset+len(fp.expected_bytes)>len(image):return False
        if image[offset:offset+len(fp.expected_bytes)]!=fp.expected_bytes:return False
    return True

@dataclass(frozen=True)
class EnableCheck:
    build_match:bool; fingerprints_match:bool; isa_supported:bool; address_ranges_valid:bool
    hook_configuration_supported:bool; trampoline_ready:bool; rollback_ready:bool
    noop_previously_validated:bool=False; explicit_interop_enable:bool=False
    @property
    def hooks_may_be_prepared(self)->bool:
        return all((self.build_match,self.fingerprints_match,self.isa_supported,self.address_ranges_valid,self.hook_configuration_supported))
    @property
    def augment_may_be_enabled(self)->bool:
        return all((self.hooks_may_be_prepared,self.trampoline_ready,self.rollback_ready,self.noop_previously_validated,self.explicit_interop_enable))


class HookGateFailure(RuntimeError): pass

def prepare_exact_hook_transaction(image:bytes,requirements:BuildRequirements,
                                   fingerprints:tuple[HookFingerprint,...],checks:EnableCheck,
                                   address_space,patches):
    """Return a prepared mock transaction only after every static gate matches."""
    from elf_identity import inspect_elf32
    from mock_hooks import ReversibleHookTransaction
    if not fingerprints or not patches: raise HookGateFailure("empty hook group")
    if len(fingerprints)!=len(patches): raise HookGateFailure("patch set does not cover the complete fingerprint group")
    if any(not any(p.address==(f.static_va&~1) and p.expected==f.expected_bytes for f in fingerprints) for p in patches):
        raise HookGateFailure("patch target is outside the fingerprint group")
    try: inspection=inspect_elf32(image)
    except Exception as exc: raise HookGateFailure("binary identity could not be inspected") from exc
    if not matches_build(inspection.identity,requirements): raise HookGateFailure("exact binary identity mismatch")
    if not verify_fingerprints(image,fingerprints,text_va=inspection.text_vaddr,text_offset=inspection.text_offset):
        raise HookGateFailure("candidate instruction fingerprint mismatch")
    if not isinstance(checks,EnableCheck) or not checks.hooks_may_be_prepared: raise HookGateFailure("hook group prerequisites are incomplete")
    transaction=ReversibleHookTransaction(address_space,tuple(patches))
    transaction.prepare()
    return transaction


def can_enable_honda_hooks(checks:EnableCheck)->bool:
    """The all-or-nothing hook group predicate; no installation occurs here."""
    return isinstance(checks,EnableCheck) and checks.hooks_may_be_prepared
