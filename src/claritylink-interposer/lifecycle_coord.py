"""Lifecycle coordination, diagnostics, gates, and future ABI adapter contracts."""
from dataclasses import dataclass
from enum import Enum
from typing import Any

class Event(str,Enum):
    INFO_MAIN_ONLY="INFO_MAIN_ONLY"; INFO_CLUSTER_ADDED="INFO_CLUSTER_ADDED"; SETUP_BEGIN="SETUP_BEGIN"
    STOCK_SETUP_SUCCESS="STOCK_SETUP_SUCCESS"; STOCK_SETUP_FAILURE="STOCK_SETUP_FAILURE"; TYPE111_NOT_REQUESTED="TYPE111_NOT_REQUESTED"
    TYPE111_REQUESTED="TYPE111_REQUESTED"; TYPE111_SECURITY_READY="TYPE111_SECURITY_READY"; TYPE111_LISTENER_READY="TYPE111_LISTENER_READY"
    TYPE111_RESPONSE_APPENDED="TYPE111_RESPONSE_APPENDED"; TYPE111_COMMITTED="TYPE111_COMMITTED"; TYPE111_ROLLBACK="TYPE111_ROLLBACK"
    TYPE111_TORN_DOWN="TYPE111_TORN_DOWN"; SERIALIZATION_FAILURE="SERIALIZATION_FAILURE"
@dataclass(frozen=True)
class RedactedEvent:
    event: Event
    generation: int | None = None
    stream_connection_id: int | None = None
    data_port: int | None = None
    fields: tuple[str,...] = ()

class ClarityLinkRedactedDiagnostics:
    def __init__(self): self.events=[]
    def emit(self,event,**metadata):
        safe={k:v for k,v in metadata.items() if k in {"generation","stream_connection_id","data_port"}}
        self.events.append(RedactedEvent(event,**safe))

class ClarityLinkLifecycleCoordinator:
    def __init__(self, interposer, diagnostics=None): self.interposer=interposer; self.diagnostics=diagnostics or ClarityLinkRedactedDiagnostics(); self.generation=0; self.cluster_advertised=False
    def note_info(self, advertised: bool):
        self.cluster_advertised=advertised
        self.diagnostics.emit(Event.INFO_CLUSTER_ADDED if advertised else Event.INFO_MAIN_ONLY)
    def session_start(self, stock_start_succeeded: bool) -> bool:
        g=self.interposer.current
        if not stock_start_succeeded:
            self.teardown_type111_generation(); return False
        if g is None: return True
        self.generation+=1; g.state="ACTIVE"; g.generation=self.generation
        self.diagnostics.emit(Event.TYPE111_COMMITTED,generation=self.generation,stream_connection_id=g.stream_connection_id,data_port=g.data_port)
        return True
    def teardown_type111_generation(self):
        g=self.interposer.current
        if g is None: return
        generation=getattr(g,"generation",None); stream_id=g.stream_connection_id; data_port=g.data_port
        try: g.clear()
        finally: self.interposer.current=None
        self.diagnostics.emit(Event.TYPE111_TORN_DOWN,generation=generation,stream_connection_id=stream_id,data_port=data_port)
    teardown=teardown_type111_generation

@dataclass(frozen=True)
class ExpectedFunctionIdentity:
    name: str
    address: int
    instruction_set: str
    binary_sha256: str
    expected_prologue: bytes

@dataclass(frozen=True)
class HondaBinaryIdentity:
    sha256: str
    elf_class: int
    endian: str
    machine: str

class HookGroupGate:
    """Data-only exact identity gate. It never reads memory or installs hooks."""
    def __init__(self, expected_binary: HondaBinaryIdentity, functions: tuple[ExpectedFunctionIdentity,...]): self.expected_binary=expected_binary; self.functions=functions
    def eligible(self, binary: HondaBinaryIdentity, prologues: dict[str,bytes], *, all_adapters_available: bool) -> bool:
        if not all_adapters_available or binary != self.expected_binary: return False
        return all(f.binary_sha256==binary.sha256 and prologues.get(f.name)==f.expected_prologue for f in self.functions)

class FailClosedHookPolicy:
    REQUIRED_GROUP=("server_info","setup","session_start","session_teardown")
    @classmethod
    def enabled(cls, matches: dict[str,bool]) -> bool: return all(matches.get(k,False) for k in cls.REQUIRED_GROUP)

class HondaInfoHookAdapter: pass
class HondaSetupHookAdapter: pass
class HondaSessionStartAdapter: pass
class HondaSessionTearDownAdapter: pass
