"""Mock-address-space hook transaction. Never opens /proc or writes a process."""
from dataclasses import dataclass
from enum import Enum,auto

class HookInstallError(RuntimeError): pass
class InstallState(Enum): NEW=auto(); PREPARED=auto(); ACTIVE=auto(); ROLLED_BACK=auto()

@dataclass(frozen=True)
class HookPatch:
    name:str; address:int; expected:bytes; replacement:bytes
    def __post_init__(self):
        if isinstance(self.address,bool) or not isinstance(self.address,int) or self.address<0: raise ValueError("patch address must be a nonnegative integer")
        if not isinstance(self.expected,bytes) or not isinstance(self.replacement,bytes): raise TypeError("mock patch bytes must be bytes")
        if not self.expected or len(self.expected)!=len(self.replacement): raise ValueError("mock patch must replace equal nonzero byte lengths")

class MockAddressSpace:
    def __init__(self,base:int,data:bytes):
        self.base=base; self.data=bytearray(data); self.fail_write_at=None; self.write_count=0
    def read(self,address:int,size:int)->bytes:
        start=address-self.base
        if start<0 or start+size>len(self.data): raise HookInstallError("address outside mock image")
        return bytes(self.data[start:start+size])
    def write(self,address:int,value:bytes):
        self.write_count+=1
        if self.fail_write_at==self.write_count: raise HookInstallError("injected mock write failure")
        start=address-self.base
        if start<0 or start+len(value)>len(self.data): raise HookInstallError("address outside mock image")
        self.data[start:start+len(value)]=value

class ReversibleHookTransaction:
    """Validates the complete hook group before changing synthetic memory."""
    def __init__(self,address_space:MockAddressSpace,patches:tuple[HookPatch,...]):
        self.space=address_space; self.patches=patches; self.state=InstallState.NEW
    def prepare(self):
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
        if self.state is not InstallState.PREPARED: raise HookInstallError("transaction is not prepared")
        changed=[]
        try:
            for patch in self.patches:
                self.space.write(patch.address,patch.replacement); changed.append(patch)
            if any(self.space.read(p.address,len(p.replacement))!=p.replacement for p in changed):
                raise HookInstallError("mock activation verification failed")
            self.state=InstallState.ACTIVE
        except Exception:
            for patch in reversed(changed):
                try: self.space.write(patch.address,patch.expected)
                except Exception: pass
            self.state=InstallState.ROLLED_BACK
            raise
    def rollback(self):
        if self.state is InstallState.ROLLED_BACK:return
        if self.state is InstallState.NEW:
            self.state=InstallState.ROLLED_BACK;return
        for patch in reversed(self.patches):
            current=self.space.read(patch.address,len(patch.replacement))
            if current==patch.replacement: self.space.write(patch.address,patch.expected)
            elif current!=patch.expected: raise HookInstallError(f"refusing unknown bytes during restore: {patch.name}")
        if any(self.space.read(p.address,len(p.expected))!=p.expected for p in self.patches):
            raise HookInstallError("original-byte restoration did not verify")
        self.state=InstallState.ROLLED_BACK
