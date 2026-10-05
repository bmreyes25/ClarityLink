from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/claritylink-jmcs"))
sys.path.insert(0, str(ROOT / "tools"))

from claritylink_jmcs.mfi_oracle import (
    AccessoryAuthenticator, AuthPhase, HondaFactoryMfiOracle, HondaFactoryMfiOracleModel,
    OracleError, SyntheticMfiOracle,
)
from check_r6d_oracle_boundary import check


def test_honda_oracle_is_inert():
    oracle = HondaFactoryMfiOracle()
    assert oracle.bus_path == "/dev/i2c-2"
    assert oracle.configured_address == 0x10
    for action in (lambda: oracle.acquire(1), oracle.protocol_major,
                   lambda: oracle.read_certificate(100), lambda: oracle.sign_challenge(b"x")):
        with pytest.raises(OracleError, match="EVIDENCE_REQUIRED"):
            action()
    oracle.release()


def test_synthetic_oracle_lifecycle_and_generation():
    auth = AccessoryAuthenticator(SyntheticMfiOracle())
    auth.start(1)
    assert b"SYNTHETIC_ONLY" in auth.certificate(1)
    with pytest.raises(OracleError, match="stale_generation"):
        auth.signature(2, b"fake")
    assert b"SYNTHETIC_ONLY" in auth.signature(1, b"fake")
    auth.accept(1)
    auth.session_ready(1)
    assert auth.phase is AuthPhase.CARPLAY_SESSION_READY
    auth.close()
    assert auth.phase is AuthPhase.CLOSED
    auth.start(2)
    auth.close()


def test_fail_closed_bounds_and_rollback():
    auth = AccessoryAuthenticator(SyntheticMfiOracle())
    auth.start(1)
    auth.certificate(1)
    with pytest.raises(OracleError, match="challenge_size"):
        auth.signature(1, b"")
    assert auth.phase is AuthPhase.CLOSED
    with pytest.raises(OracleError, match="oracle_not_acquired"):
        SyntheticMfiOracle().protocol_major()


def test_provider_independence_and_boundary():
    assert check() == []
    with pytest.raises(OracleError, match="EVIDENCE_REQUIRED"):
        AccessoryAuthenticator(HondaFactoryMfiOracle()).start(1)
    assert not hasattr(SyntheticMfiOracle(), "transport_handle")


def test_honda_lifecycle_model_is_exclusive_and_synthetic():
    model = HondaFactoryMfiOracleModel()
    model.acquire(1)
    with pytest.raises(OracleError, match="active_generation"):
        model.acquire(2)
    assert model.read_certificate(100).startswith(b"SYNTHETIC_ONLY")
    model.release()
    model.acquire(2)
    assert model.sign_challenge(b"fake").startswith(b"SYNTHETIC_ONLY")
    model.release()


def test_oracle_failure_releases_state_without_logging(caplog):
    class FailingOracle(SyntheticMfiOracle):
        def sign_challenge(self, challenge: bytes) -> bytes:
            raise OracleError("synthetic_sign_failure")

    auth = AccessoryAuthenticator(FailingOracle())
    auth.start(5)
    auth.certificate(5)
    marker = b"SYNTHETIC_ONLY_PRIVATE_CHALLENGE_MARKER"
    with pytest.raises(OracleError, match="synthetic_sign_failure"):
        auth.signature(5, marker)
    assert auth.phase is AuthPhase.CLOSED
    assert marker.decode() not in caplog.text
