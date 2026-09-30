"""Mock-address-space hook transaction. Never opens /proc or writes a process."""
from dataclasses import dataclass
from enum import Enum,auto

class HookInstallError(RuntimeError): pass
class CriticalRestoreError(HookInstallError):
    category="CRITICAL_EXECUTABLE_RESTORE_FAILURE"

class InstallState(Enum): NEW=auto(); PREPARED=auto(); ACTIVE=auto(); ROLLED_BACK=auto(); CRITICAL_RESTORE_FAILURE=auto()

@dataclass(frozen=True)
class ProcessEpoch:
    """Synthetic process identity; runtime addresses are valid only for this epoch."""
    pid:int
    start_token:str
    elf_sha256:str
    load_bias:int
    def __post_init__(self):
        if isinstance(self.pid,bool) or not isinstance(self.pid,int) or self.pid<=0:raise ValueError("pid must be positive")
        if not isinstance(self.start_token,str) or not self.start_token or len(self.start_token)>128:raise ValueError("start token must be bounded and nonempty")
        if not isinstance(self.elf_sha256,str) or len(self.elf_sha256)!=64 or any(c not in "0123456789abcdef" for c in self.elf_sha256):raise ValueError("ELF hash must be lowercase SHA-256")
        if isinstance(self.load_bias,bool) or not isinstance(self.load_bias,int) or not 0<=self.load_bias<=0xffffffff:raise ValueError("load bias must be unsigned 32-bit")

@dataclass(frozen=True)
class HookPatch:
    name:str; address:int; expected:bytes; replacement:bytes
    def __post_init__(self):
        if not isinstance(self.name,str) or not self.name or len(self.name)>128:raise ValueError("patch name must be bounded and nonempty")
        if isinstance(self.address,bool) or not isinstance(self.address,int) or not 0<=self.address<=0xffffffff: raise ValueError("patch address must be unsigned 32-bit")
        if not isinstance(self.expected,bytes) or not isinstance(self.replacement,bytes): raise TypeError("mock patch bytes must be bytes")
        if not self.expected or len(self.expected)!=len(self.replacement) or self.address+len(self.expected)>0x1_0000_0000: raise ValueError("mock patch must fit 32-bit space and replace equal nonzero byte lengths")

class MockAddressSpace:
    def __init__(self,base:int,data:bytes,*,epoch:ProcessEpoch|None=None):
        if isinstance(base,bool) or not isinstance(base,int) or not 0<=base<=0xffffffff:raise ValueError("mock base must be unsigned 32-bit")
        if not isinstance(data,(bytes,bytearray)) or base+len(data)>0x1_0000_0000:raise ValueError("mock data must fit 32-bit address space")
        self.base=base; self.data=bytearray(data); self.epoch=epoch
        self.fail_write_at=None; self.partial_write_at=None; self.fail_read_at=None; self.corrupt_after_write_at=None
        self.write_count=0; self.read_count=0
    def read(self,address:int,size:int)->bytes:
        self.read_count+=1
        if self.fail_read_at==self.read_count:raise HookInstallError("injected mock read failure")
        if isinstance(address,bool) or not isinstance(address,int) or isinstance(size,bool) or not isinstance(size,int) or size<0:raise HookInstallError("invalid mock read range")
        start=address-self.base
        if start<0 or start+size>len(self.data): raise HookInstallError("address outside mock image")
        return bytes(self.data[start:start+size])
    def write(self,address:int,value:bytes):
        self.write_count+=1
        if self.fail_write_at==self.write_count: raise HookInstallError("injected mock write failure")
        if not isinstance(value,bytes):raise HookInstallError("mock writes require bytes")
        if isinstance(address,bool) or not isinstance(address,int) or not 0<=address<=0xffffffff or address+len(value)>0x1_0000_0000:raise HookInstallError("invalid mock write range")
        start=address-self.base
        if start<0 or start+len(value)>len(self.data): raise HookInstallError("address outside mock image")
        if self.partial_write_at==self.write_count:
            prefix=max(1,len(value)//2)
            self.data[start:start+prefix]=value[:prefix]
            raise HookInstallError("injected partial mock write failure")
        self.data[start:start+len(value)]=value
        if self.corrupt_after_write_at==self.write_count and value:
            self.data[start+len(value)-1]^=1

class ReversibleHookTransaction:
    """Validates the complete hook group before changing synthetic memory."""
    def __init__(self,address_space:MockAddressSpace,patches:tuple[HookPatch,...]):
        self.space=address_space; self.patches=patches; self.state=InstallState.NEW; self.epoch=address_space.epoch
    def _check_epoch(self):
        if self.epoch is not None and self.space.epoch!=self.epoch:
            raise HookInstallError("process identity or load bias changed; stale runtime patch refused")
    def prepare(self):
        self._check_epoch()
        if self.state is not InstallState.NEW: raise HookInstallError("transaction is not new")
        if not self.patches: raise HookInstallError("hook group cannot be empty")
        if len({p.name for p in self.patches})!=len(self.patches): raise HookInstallError("hook names must be unique")
        ordered=sorted(self.patches,key=lambda p:p.address)
        for a,b in zip(ordered,ordered[1:]):
            if a.address+len(a.expected)>b.address: raise HookInstallError("overlapping patch ranges")
        for patch in self.patches:
            if self.space.read(patch.address,len(patch.expected))!=patch.expected: raise HookInstallError(f"fingerprint mismatch: {patch.name}")
        self.state=InstallState.PREPARED
    def activate(self):
        self._check_epoch()
        if self.state is not InstallState.PREPARED: raise HookInstallError("transaction is not prepared")
        changed=[]
        try:
            for patch in self.patches:
                # Record before write so a simulated/real partial write is recoverable.
                changed.append(patch); self.space.write(patch.address,patch.replacement)
            if any(self.space.read(p.address,len(p.replacement))!=p.replacement for p in changed):
                raise HookInstallError("mock activation verification failed")
            self.state=InstallState.ACTIVE
        except Exception as cause:
            restore_error=None
            for patch in reversed(changed):
                try:
                    current=self.space.read(patch.address,len(patch.expected))
                    if current!=patch.expected:self.space.write(patch.address,patch.expected)
                    if self.space.read(patch.address,len(patch.expected))!=patch.expected:raise HookInstallError("rollback bytes did not verify")
                except Exception as exc:
                    restore_error=exc
            self.state=InstallState.CRITICAL_RESTORE_FAILURE if restore_error else InstallState.ROLLED_BACK
            if restore_error:raise CriticalRestoreError(CriticalRestoreError.category) from restore_error
            raise
    def rollback(self):
        if self.state is InstallState.ROLLED_BACK:return
        # A caller may explicitly retry restoration after a loud critical failure;
        # the transaction remains unusable for any install or session continuation.
        self._check_epoch()
        if self.state is InstallState.NEW:
            self.state=InstallState.ROLLED_BACK;return
        try:
            for patch in reversed(self.patches):
                current=self.space.read(patch.address,len(patch.replacement))
                if current==patch.replacement:self.space.write(patch.address,patch.expected)
                elif current!=patch.expected:raise HookInstallError(f"refusing unknown bytes during restore: {patch.name}")
            if any(self.space.read(p.address,len(p.expected))!=p.expected for p in self.patches):raise HookInstallError("original-byte restoration did not verify")
        except Exception as exc:
            self.state=InstallState.CRITICAL_RESTORE_FAILURE
            raise CriticalRestoreError(CriticalRestoreError.category) from exc
        self.state=InstallState.ROLLED_BACK
