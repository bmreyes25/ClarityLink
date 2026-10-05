from dataclasses import asdict
from pathlib import Path
import pickle
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "claritylink-jmcs"))

from claritylink_jmcs.authentication import AuthenticationError
from claritylink_jmcs.honda_substrate import (
    HondaAuthenticationProvider, HondaCarPlaySessionTransport,
    HondaIap2Transport, HondaOpaqueContext, HondaSubstrateError,
)
from claritylink_jmcs.session_transport import ControlResponse, TransportError


def test_target_adapters_fail_closed_without_honda_abi():
    auth = HondaAuthenticationProvider()
    assert not auth.session_ready()
    with pytest.raises(AuthenticationError, match="EVIDENCE_REQUIRED"):
        auth.initialize()
    with pytest.raises(AuthenticationError, match="EVIDENCE_REQUIRED"):
        auth.authenticate()
    with pytest.raises(HondaSubstrateError, match="EVIDENCE_REQUIRED"):
        HondaIap2Transport().open()
    control = HondaCarPlaySessionTransport()
    assert not control.authenticated
    with pytest.raises(TransportError, match="EVIDENCE_REQUIRED"):
        control.read_request(1.0)
    with pytest.raises(TransportError, match="EVIDENCE_REQUIRED"):
        control.write_response(ControlResponse(200, {}, 1))


def test_opaque_context_is_generation_scoped_and_not_printable():
    secret_sentinel = object()
    context = HondaOpaqueContext(3, secret_sentinel)
    assert context.require(3) is secret_sentinel
    assert repr(secret_sentinel) not in repr(context)
    with pytest.raises(HondaSubstrateError, match="not_serializable"):
        pickle.dumps(context)
    with pytest.raises(TypeError):
        asdict(context)
    with pytest.raises(HondaSubstrateError, match="stale_or_closed"):
        context.require(4)
    context.close()
    assert context.handle is None
    with pytest.raises(HondaSubstrateError, match="stale_or_closed"):
        context.require(3)
