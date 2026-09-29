"""Host-only OFF/NOOP/OBSERVE/AUGMENT stock-delegation semantics."""
from collections import deque
from dataclasses import dataclass
from enum import Enum
from threading import RLock
from typing import Any,Callable

class HookMode(str,Enum): OFF="off"; NOOP="noop"; OBSERVE="observe"; AUGMENT="augment"
@dataclass(frozen=True)
class HookEvent:
    category:str
    stock_succeeded:bool
    stream_types:tuple[int,...]=()
    stream_count:int=0
    error_class:str|None=None

class BoundedDiagnostics:
    def __init__(self,capacity:int=128):
        if capacity<1:raise ValueError("capacity must be positive")
        self._events=deque(maxlen=capacity); self._lock=RLock()
    def record(self,event:HookEvent):
        with self._lock:self._events.append(event)
    def snapshot(self):
        with self._lock:return tuple(self._events)

class HondaHookSemanticHarness:
    def __init__(self,mode:HookMode=HookMode.OFF,diagnostics:BoundedDiagnostics|None=None):
        self.mode=mode; self.diagnostics=diagnostics or BoundedDiagnostics()
    def setup(self,request:Any,stock:Callable[[Any],Any],*,augment:Callable[[Any,Any],Any]|None=None,enable_check=None):
        # All modes delegate with the caller's exact input object.
        try:
            stock_result=stock(request)
        except Exception as exc:
            if self.mode in (HookMode.NOOP,HookMode.OBSERVE):
                self.diagnostics.record(HookEvent("setup_noop" if self.mode is HookMode.NOOP else "setup_observe",False,error_class=type(exc).__name__))
            raise
        if self.mode is HookMode.OFF:return stock_result
        success=stock_result is not None and not (isinstance(stock_result,tuple) and stock_result and isinstance(stock_result[0],int) and stock_result[0]!=0)
        if self.mode is HookMode.NOOP:
            self.diagnostics.record(HookEvent("setup_noop",success))
            return stock_result
        if self.mode is HookMode.OBSERVE:
            self.diagnostics.record(_observe(request,success,stock_result))
            return stock_result
        if self.mode is HookMode.AUGMENT:
            if enable_check is None or not enable_check.augment_may_be_enabled or augment is None:return stock_result
            try:return augment(request,stock_result)
            except Exception:
                self.diagnostics.record(HookEvent("augment_failure_stock_preserved",success,error_class="project"))
                return stock_result
        return stock_result

def _observe(request:Any,success:bool,result:Any)->HookEvent:
    if result is None:return HookEvent("setup_observe",False,error_class="null_stock_result")
    if isinstance(result,tuple) and len(result)>1 and result[0]==0 and not isinstance(result[1],dict):
        return HookEvent("setup_observe",success,error_class="unexpected_response_type")
    if not isinstance(request,dict):return HookEvent("setup_observe",success,error_class="unexpected_request_type")
    streams=request.get("streams")
    if not isinstance(streams,(list,tuple)):return HookEvent("setup_observe",success,error_class="unexpected_stream_container")
    values=[]
    for entry in streams:
        if isinstance(entry,dict):
            t=entry.get("type")
            if isinstance(t,int) and not isinstance(t,bool):values.append(t)
    return HookEvent("setup_observe",success,tuple(values),len(streams))
