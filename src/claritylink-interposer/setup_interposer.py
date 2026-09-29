"""Stock-first Type-111 augmentation with configurable response profiles."""
from __future__ import annotations
from copy import deepcopy
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Callable
from models import ResponseStrategy, Type111ResponseProfile, SecretBytes
from listener import FakeSecondaryListenerFactory
from transaction import ClarityLinkType111Transaction, TransactionState
from lifecycle_coord import Event

TYPE111=111
class SetupInterposerError(ValueError): pass
class StockSetupDelegate:
    def __init__(self, callback): self.callback=callback
    def setup(self, original_request): return self.callback(original_request)

@dataclass(frozen=True)
class Type111RequestView:
    descriptor: Mapping[str, Any]
    stream_connection_id: int

def parse_type111_view(request: Mapping[str, Any]) -> Type111RequestView | None:
    if not isinstance(request, Mapping): raise SetupInterposerError("request must be a mapping")
    streams=request.get("streams", [])
    if not isinstance(streams, (list, tuple)): raise SetupInterposerError("streams must be an array")
    matches=[]
    for item in streams:
        if not isinstance(item, Mapping): continue
        if "type" not in item: continue
        kind=item["type"]
        if isinstance(kind,bool) or not isinstance(kind,int): raise SetupInterposerError("stream type must be an integer")
        if kind == TYPE111: matches.append(item)
    if len(matches)>1: raise SetupInterposerError("duplicate Type-111 descriptors fail closed")
    if not matches: return None
    cid=matches[0].get("streamConnectionID")
    if isinstance(cid,bool) or not isinstance(cid,int) or not 1<=cid<(1<<64): raise SetupInterposerError("Type-111 streamConnectionID must be a nonzero uint64")
    return Type111RequestView(matches[0],cid)

class ClarityLinkType111ResponseBuilder:
    def __init__(self, profile: Type111ResponseProfile): self.profile=profile
    def build(self, view: Type111RequestView, port: int) -> dict[str,Any]:
        if isinstance(port,bool) or not isinstance(port,int) or not 1<=port<=65535: raise SetupInterposerError("invalid assigned port")
        if self.profile.strategy is ResponseStrategy.MINIMAL: result={"type":111,"dataPort":port}
        else:
            result=deepcopy(dict(view.descriptor)); result["dataPort"]=port
            if self.profile.include_stream_id: result["streamID"]=111
        for key,value in self.profile.custom_fields.items(): result[key]=deepcopy(value)
        return result

def append_response(stock: Mapping[str,Any], entry: Mapping[str,Any]) -> dict[str,Any]:
    if not isinstance(stock,Mapping): raise SetupInterposerError("stock response must be a mapping")
    streams=stock.get("streams",[])
    if not isinstance(streams,(list,tuple)) or any(not isinstance(x,Mapping) for x in streams): raise SetupInterposerError("stock response streams must be mappings")
    copied=deepcopy(dict(stock)); copied["streams"]=[*deepcopy(list(streams)),deepcopy(dict(entry))]
    return copied

class ClarityLinkSetupInterposer:
    """Calls stock with the exact original request; project failures return stock intact."""
    def __init__(self, stock: StockSetupDelegate, listener_factory, security_provider, response_builder, publisher: Callable[[Mapping[str,Any]],bool] | None=None, diagnostics=None):
        self.stock=stock; self.listener_factory=listener_factory; self.security_provider=security_provider
        self.response_builder=response_builder; self.publisher=publisher or (lambda _r: True)
        self.diagnostics=diagnostics
        self.current=None
    def _emit(self,event,**metadata):
        if self.diagnostics is not None: self.diagnostics.emit(event,**metadata)
    def setup(self, original_request: Mapping[str,Any], *, enabled=True):
        self._emit(Event.SETUP_BEGIN)
        status, stock_response=self.stock.setup(original_request)
        if status != 0 or stock_response is None:
            self._emit(Event.STOCK_SETUP_FAILURE)
            return status, stock_response
        self._emit(Event.STOCK_SETUP_SUCCESS)
        stable=deepcopy(dict(stock_response))
        if not enabled: return status, stable
        tx=ClarityLinkType111Transaction()
        try:
            view=parse_type111_view(original_request)
            if view is None:
                self._emit(Event.TYPE111_NOT_REQUESTED)
                return status, stable
            self._emit(Event.TYPE111_REQUESTED,stream_connection_id=view.stream_connection_id)
            if self.current is not None: raise SetupInterposerError("existing Type-111 generation must be torn down first")
            security=self.security_provider(view.stream_connection_id)
            key,iv=security
            secret_key=SecretBytes(key); secret_iv=SecretBytes(iv)
            tx.own(secret_key.clear); tx.own(secret_iv.clear)
            tx.advance(TransactionState.CREATED,TransactionState.SECURITY_READY)
            self._emit(Event.TYPE111_SECURITY_READY,stream_connection_id=view.stream_connection_id)
            listener=self.listener_factory.create(0); tx.own(listener.close)
            tx.advance(TransactionState.SECURITY_READY,TransactionState.LISTENER_READY)
            self._emit(Event.TYPE111_LISTENER_READY,stream_connection_id=view.stream_connection_id,data_port=listener.port)
            response=self.response_builder.build(view,listener.port)
            candidate=append_response(stable,response)
            tx.advance(TransactionState.LISTENER_READY,TransactionState.RESPONSE_READY)
            self._emit(Event.TYPE111_RESPONSE_APPENDED,stream_connection_id=view.stream_connection_id,data_port=listener.port)
            if not self.publisher(candidate):
                self._emit(Event.SERIALIZATION_FAILURE,stream_connection_id=view.stream_connection_id,data_port=listener.port)
                raise SetupInterposerError("serializer/publisher rejected response")
            tx.commit()
            self.current=PreparedGeneration(view.stream_connection_id,listener.port,listener,secret_key,secret_iv,tx)
            return status,candidate
        except Exception:
            self._emit(Event.TYPE111_ROLLBACK)
            try: tx.rollback()
            except Exception: pass
            return status,stable

@dataclass
class ClarityLinkType111Session:
    stream_connection_id: int
    data_port: int
    listener: Any
    key: SecretBytes
    iv: SecretBytes
    transaction: ClarityLinkType111Transaction
    state: str="PREPARED"
    generation: int | None=None
    receiver: Any=None
    accepted_socket: Any=None
    def accept(self):
        if self.state != "ACTIVE": raise SetupInterposerError("session must be active before accept")
        if self.accepted_socket is not None: raise SetupInterposerError("session already accepted a socket")
        self.accepted_socket=self.listener.accept()
        return self.accepted_socket
    def feed(self, data: bytes):
        if self.state != "ACTIVE" or self.receiver is None: raise SetupInterposerError("receiver is not active")
        return self.receiver.feed(data)
    def clear(self):
        errors=[]
        if self.accepted_socket is not None:
            try: self.accepted_socket.close()
            except Exception as exc: errors.append(exc)
            self.accepted_socket=None
        try: self.transaction.rollback()
        except Exception as exc: errors.append(exc)
        self.key.clear(); self.iv.clear(); self.receiver=None
        self.stream_connection_id=None; self.data_port=None; self.generation=None
        self.state="CLOSED"
        if errors: raise RuntimeError("session cleanup encountered an error after releasing owned state") from errors[0]


# Compatibility name for the prepared generation object.
PreparedGeneration = ClarityLinkType111Session
