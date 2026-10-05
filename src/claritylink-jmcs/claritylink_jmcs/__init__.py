"""Offline receiver laboratory, with explicit Honda evidence boundaries.

No vehicle adapter, MFi authentication, or live Honda deployment is provided.
"""

from .receiver import Receiver, ReceiverError, ReceiverState
from .setup import SetupRequest, SetupResponse, StreamDescriptor

__all__ = ["Receiver", "ReceiverError", "ReceiverState", "SetupRequest", "SetupResponse", "StreamDescriptor"]
