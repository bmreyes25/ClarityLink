"""Host-only MFi oracle contracts and synthetic authentication choreography.

This module does not implement iAP2 messages, MFi-SAP, or Honda device I/O.
Certificate/signature values used here are synthetic test data only.
"""
from __future__ import annotations

from enum import Enum, auto
from typing import Protocol


MAX_CERTIFICATE = 8192
MAX_CHALLENGE = 256
MAX_SIGNATURE = 8192


class OracleError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class MfiAuthOracle(Protocol):
    def acquire(self, generation: int) -> None: ...
    def protocol_major(self) -> int: ...
    def read_certificate(self, maximum_output_length: int) -> bytes: ...
    def sign_challenge(self, challenge: bytes) -> bytes: ...
    def release(self) -> None: ...


class Iap2Transport(Protocol):
    def send_message(self, payload: bytes) -> None: ...
    def receive_message(self) -> bytes: ...
    def close(self) -> None: ...


class Iap2AccessoryAuthentication(Protocol):
    def certificate(self, generation: int) -> bytes: ...
    def signature(self, generation: int, challenge: bytes) -> bytes: ...


class AirPlayAuthentication(Protocol):
    def certificate(self, generation: int) -> bytes: ...
    def signature(self, generation: int, challenge: bytes) -> bytes: ...


class CarPlayControlSession(Protocol):
    def close(self) -> None: ...


class HondaFactoryMfiOracle:
    """Static factory-channel metadata. Every authentication operation fails closed."""

    bus_path = "/dev/i2c-2"
    configured_address = 0x10
    # R6D confirms direct I2C_SLAVE use in jmcs, but no target I/O is allowed.
    address_semantics = "HONDA_STATIC_7BIT_I2C_SLAVE"

    def acquire(self, generation: int) -> None:
        raise OracleError("EVIDENCE_REQUIRED_LIVE_HONDA_ORACLE")

    def protocol_major(self) -> int:
        raise OracleError("EVIDENCE_REQUIRED_LIVE_HONDA_ORACLE")

    def read_certificate(self, maximum_output_length: int) -> bytes:
        raise OracleError("EVIDENCE_REQUIRED_LIVE_HONDA_ORACLE")

    def sign_challenge(self, challenge: bytes) -> bytes:
        raise OracleError("EVIDENCE_REQUIRED_LIVE_HONDA_ORACLE")

    def release(self) -> None:
        return None

    close = release


class SyntheticMfiOracle:
    """SYNTHETIC_ONLY: exercises ownership and bounds, never authenticates an iPhone."""

    def __init__(self) -> None:
        self._generation: int | None = None

    def acquire(self, generation: int) -> None:
        if generation < 1 or self._generation is not None:
            raise OracleError("invalid_or_active_generation")
        self._generation = generation

    def _require(self) -> None:
        if self._generation is None:
            raise OracleError("oracle_not_acquired")

    def protocol_major(self) -> int:
        self._require()
        return 0  # deliberately non-production synthetic value

    def read_certificate(self, maximum_output_length: int) -> bytes:
        self._require()
        value = b"SYNTHETIC_ONLY_CERTIFICATE"
        if maximum_output_length < len(value) or maximum_output_length > MAX_CERTIFICATE:
            raise OracleError("certificate_size_invalid")
        return value

    def sign_challenge(self, challenge: bytes) -> bytes:
        self._require()
        if not isinstance(challenge, bytes) or not 0 < len(challenge) <= MAX_CHALLENGE:
            raise OracleError("challenge_size_invalid")
        return b"SYNTHETIC_ONLY_SIGNATURE"

    def release(self) -> None:
        self._generation = None

    close = release


class HondaFactoryMfiOracleModel(SyntheticMfiOracle):
    """SYNTHETIC_ONLY single-owner lifecycle model for the Honda call graph.

    No device path is opened; inherited outputs are visibly fake. Reacquire
    after release models Honda's obtain/release around each auth operation.
    """


class AuthPhase(Enum):
    CLOSED = auto()
    TRANSPORT_READY = auto()
    CERTIFICATE_SUPPLIED = auto()
    SIGNATURE_SUPPLIED = auto()
    AUTH_ACCEPTED = auto()
    CARPLAY_SESSION_READY = auto()


class AccessoryAuthenticator:
    """Host-only state/ownership model; caller owns protocol messages and acceptance."""

    def __init__(self, oracle: MfiAuthOracle) -> None:
        self._oracle = oracle
        self._generation: int | None = None
        self.phase = AuthPhase.CLOSED

    def start(self, generation: int) -> None:
        if self.phase is not AuthPhase.CLOSED or generation < 1:
            raise OracleError("invalid_auth_start")
        self._oracle.acquire(generation)
        self._generation = generation
        self.phase = AuthPhase.TRANSPORT_READY

    def _require(self, generation: int, phase: AuthPhase) -> None:
        if self._generation != generation or self.phase is not phase:
            raise OracleError("stale_generation_or_phase")

    def certificate(self, generation: int) -> bytes:
        self._require(generation, AuthPhase.TRANSPORT_READY)
        try:
            cert = self._oracle.read_certificate(MAX_CERTIFICATE)
            if not isinstance(cert, bytes) or not 0 < len(cert) <= MAX_CERTIFICATE:
                raise OracleError("certificate_size_invalid")
        except Exception:
            self.close()
            raise
        self.phase = AuthPhase.CERTIFICATE_SUPPLIED
        return cert

    def signature(self, generation: int, challenge: bytes) -> bytes:
        self._require(generation, AuthPhase.CERTIFICATE_SUPPLIED)
        if not isinstance(challenge, bytes) or not 0 < len(challenge) <= MAX_CHALLENGE:
            self.close()
            raise OracleError("challenge_size_invalid")
        try:
            signature = self._oracle.sign_challenge(challenge)
            if not isinstance(signature, bytes) or not 0 < len(signature) <= MAX_SIGNATURE:
                raise OracleError("signature_size_invalid")
        except Exception:
            self.close()
            raise
        self.phase = AuthPhase.SIGNATURE_SUPPLIED
        return signature

    def accept(self, generation: int) -> None:
        """Called only after an external protocol verifier accepts authentication."""
        self._require(generation, AuthPhase.SIGNATURE_SUPPLIED)
        self.phase = AuthPhase.AUTH_ACCEPTED

    def session_ready(self, generation: int) -> None:
        self._require(generation, AuthPhase.AUTH_ACCEPTED)
        self.phase = AuthPhase.CARPLAY_SESSION_READY

    def close(self) -> None:
        try:
            self._oracle.release()
        finally:
            self._generation = None
            self.phase = AuthPhase.CLOSED
