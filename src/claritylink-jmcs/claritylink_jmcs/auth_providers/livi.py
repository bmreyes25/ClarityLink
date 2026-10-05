"""Narrow adapter for a reviewed LIVI control-session delegate.

This module does not authenticate a phone or provide an MFi implementation.
It accepts only a bridge opened by the LIVI delegate described in
research/runtime/r6g-livi-upstream-adapter-design.md.
"""
from __future__ import annotations

from typing import Protocol

from ..authentication import (
    AuthenticatedSessionHandoff,
    AuthenticationError,
    AuthorityType,
    SessionOrigin,
)
from ..session_transport import ControlRequest, ControlResponse, TransportError, validate_control_request


class LiviBridge(Protocol):
    """One LIVI-owned authenticated control channel; never exposes auth secrets."""

    @property
    def authenticated(self) -> bool: ...
    @property
    def session_identifier(self) -> str: ...
    @property
    def generation(self) -> int: ...
    def read_request(self, timeout: float) -> ControlRequest: ...
    def write_response(self, response: ControlResponse) -> None: ...
    def close(self) -> None: ...


class LiviBridgeFactory(Protocol):
    """Implemented by the local LIVI delegate process after its auth gate."""

    def open_authenticated(self, generation: int) -> LiviBridge: ...
    def close(self) -> None: ...


class LiviControlTransport:
    """ClarityLink view of the single LIVI-owned request/response channel."""

    __slots__ = ("_bridge", "_generation", "_closed")

    def __init__(self, bridge: LiviBridge, generation: int) -> None:
        session_identifier = getattr(bridge, "session_identifier", None)
        if (type(generation) is not int or generation < 1 or
                getattr(bridge, "authenticated", False) is not True or
                getattr(bridge, "generation", None) != generation or
                not isinstance(session_identifier, str) or not session_identifier or
                len(session_identifier) > 128):
            raise AuthenticationError("livi_authenticated_bridge_required")
        for name in ("read_request", "write_response", "close"):
            if not callable(getattr(bridge, name, None)):
                raise AuthenticationError("livi_bridge_contract_invalid")
        self._bridge = bridge
        self._generation = generation
        self._closed = False

    @property
    def authenticated(self) -> bool:
        return not self._closed and getattr(self._bridge, "authenticated", False) is True

    @property
    def generation(self) -> int:
        return self._generation

    @property
    def session_identifier(self) -> str:
        return self._bridge.session_identifier

    def read_request(self, timeout: float) -> ControlRequest:
        if not self.authenticated:
            raise TransportError("transport_closed")
        if not 0 < timeout <= 30:
            raise TransportError("invalid_timeout")
        try:
            request = self._bridge.read_request(timeout)
        except (TimeoutError, EOFError, ConnectionError):
            raise TransportError("livi_peer_disconnected_or_timeout") from None
        except Exception:
            raise TransportError("livi_request_read_failed") from None
        validate_control_request(request, self._generation)
        return request

    def write_response(self, response: ControlResponse) -> None:
        if not self.authenticated:
            raise TransportError("stale_or_closed_transport")
        if not isinstance(response, ControlResponse) or not 100 <= response.status <= 599:
            raise TransportError("malformed_response")
        if response.generation != self._generation:
            raise TransportError("stale_or_closed_transport")
        validate_control_request(
            ControlRequest("RESPONSE", "/", response.body, self._generation),
            self._generation,
        )
        try:
            self._bridge.write_response(response)
        except Exception:
            raise TransportError("livi_response_write_failed") from None

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self._bridge.close()
        except Exception:
            raise TransportError("livi_bridge_close_failed") from None

    def __repr__(self) -> str:
        return f"LiviControlTransport(generation={self._generation}, authenticated={self.authenticated}, closed={self._closed})"

    def __reduce__(self) -> None:
        raise AuthenticationError("livi_transport_not_serializable")


class LiviAuthority:
    """Authority adapter over LIVI Link and the LIVI control delegate.

    `explicitly_authorized` must be set from operator-verified hardware
    provenance; it cannot make an absent or unverified bridge authenticate.
    """

    identity = "livi-link"
    authority_type = AuthorityType.GENUINE_MFI_COPROCESSOR

    def __init__(self, *, bridge_factory: LiviBridgeFactory,
                 explicitly_authorized: bool = False) -> None:
        self._factory = bridge_factory
        self.explicitly_authorized = explicitly_authorized
        self._handoff: AuthenticatedSessionHandoff | None = None
        self._closed = False

    def open(self, generation: int) -> AuthenticatedSessionHandoff:
        if self._closed or self._handoff is not None:
            raise AuthenticationError("livi_authority_unavailable")
        if not self.explicitly_authorized:
            raise AuthenticationError("livi_hardware_authorization_required")
        if type(generation) is not int or generation < 1:
            raise AuthenticationError("invalid_generation")
        bridge: LiviBridge | None = None
        try:
            bridge = self._factory.open_authenticated(generation)
            transport = LiviControlTransport(bridge, generation)
            handoff = AuthenticatedSessionHandoff(
                session_identifier=transport.session_identifier,
                generation=generation,
                origin=SessionOrigin.AUTHENTICATED_LAB,
                auth_owner=self.identity,
                transport=transport,
                authority_type=self.authority_type,
                authenticated=True,
                capabilities={"control_delegation": True},
            )
        except (AuthenticationError, TransportError):
            if bridge is not None:
                try:
                    bridge.close()
                except Exception:
                    pass
            raise
        except Exception:
            if bridge is not None:
                try:
                    bridge.close()
                except Exception:
                    pass
            raise AuthenticationError("livi_bridge_open_failed") from None
        self._handoff = handoff
        return handoff

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self._factory.close()
        except Exception:
            raise AuthenticationError("livi_factory_close_failed") from None

    def __repr__(self) -> str:
        return "LiviAuthority(identity='livi-link', bridge_state=redacted)"
