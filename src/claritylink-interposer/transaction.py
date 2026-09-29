"""Project-owned staged transaction and idempotent reverse-order cleanup."""
from enum import Enum, auto

class TransactionState(Enum): CREATED=auto(); SECURITY_READY=auto(); LISTENER_READY=auto(); RESPONSE_READY=auto(); COMMITTED=auto(); ROLLED_BACK=auto()
class ClarityLinkType111Transaction:
    def __init__(self): self.state=TransactionState.CREATED; self._cleanups=[]
    def own(self, cleanup): self._cleanups.append(cleanup)
    def advance(self, expected, new):
        if self.state is not expected: raise RuntimeError(f"invalid transaction transition {self.state.name}")
        self.state=new
    def rollback(self):
        if self.state is TransactionState.ROLLED_BACK: return
        errors=[]
        for cleanup in reversed(self._cleanups):
            try: cleanup()
            except Exception as exc: errors.append(exc)
        self._cleanups.clear(); self.state=TransactionState.ROLLED_BACK
        if errors: raise RuntimeError("one or more project cleanup actions failed") from errors[0]
    def commit(self):
        if self.state is not TransactionState.RESPONSE_READY: raise RuntimeError("response is not ready")
        self.state=TransactionState.COMMITTED
