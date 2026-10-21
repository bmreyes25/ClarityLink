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
    assert not hasattr(oracle, "bus_path")
    assert not hasattr(oracle, "configured_address")
    assert not hasattr(oracle, "address_semantics")
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


def test_partial_acquire_failure_attempts_release_and_preserves_original_error():
    class PartiallyAcquiredOracle(SyntheticMfiOracle):
        def __init__(self):
            super().__init__()
            self.release_calls = 0

        def acquire(self, generation: int) -> None:
            super().acquire(generation)
            raise OracleError("synthetic_acquire_failure")

        def release(self) -> None:
            self.release_calls += 1
            super().release()

    oracle = PartiallyAcquiredOracle()
    auth = AccessoryAuthenticator(oracle)
    with pytest.raises(OracleError, match="synthetic_acquire_failure"):
        auth.start(3)
    assert oracle.release_calls == 1
    assert auth.phase is AuthPhase.CLOSED
    assert auth._generation is None
    with pytest.raises(OracleError, match="oracle_not_acquired"):
        oracle.protocol_major()


def test_failed_partial_acquire_cleanup_preserves_error_and_blocks_retry():
    class FailedCleanupOracle(SyntheticMfiOracle):
        def __init__(self):
            super().__init__()
            self.acquire_calls = 0

        def acquire(self, generation: int) -> None:
            self.acquire_calls += 1
            super().acquire(generation)
            raise OracleError("synthetic_acquire_failure")

        def release(self) -> None:
            raise OracleError("synthetic_release_failure")

    oracle = FailedCleanupOracle()
    auth = AccessoryAuthenticator(oracle)
    with pytest.raises(OracleError, match="synthetic_acquire_failure") as failure:
        auth.start(4)
    assert isinstance(failure.value.__cause__, OracleError)
    assert failure.value.__cause__.code == "synthetic_release_failure"
    assert auth.phase is AuthPhase.CLOSED
    with pytest.raises(OracleError, match="oracle_cleanup_failed"):
        auth.start(5)
    assert oracle.acquire_calls == 1


@pytest.mark.parametrize("failure_point", ["certificate", "signature"])
def test_operation_and_cleanup_failures_preserve_primary_error(failure_point):
    class FailedCleanupOracle(SyntheticMfiOracle):
        def read_certificate(self, maximum_output_length: int) -> bytes:
            if failure_point == "certificate":
                raise OracleError("synthetic_certificate_failure")
            return super().read_certificate(maximum_output_length)

        def sign_challenge(self, challenge: bytes) -> bytes:
            raise OracleError("synthetic_signature_failure")

        def release(self) -> None:
            raise OracleError("synthetic_release_failure")

    oracle = FailedCleanupOracle()
    auth = AccessoryAuthenticator(oracle)
    auth.start(6)
    if failure_point == "signature":
        auth.certificate(6)
    primary = "synthetic_certificate_failure" if failure_point == "certificate" else "synthetic_signature_failure"
    operation = (lambda: auth.certificate(6)) if failure_point == "certificate" else (lambda: auth.signature(6, b"challenge"))
    with pytest.raises(OracleError, match=primary) as failure:
        operation()
    assert isinstance(failure.value.__cause__, OracleError)
    assert failure.value.__cause__.code == "synthetic_release_failure"
    assert auth.phase is AuthPhase.CLOSED
    with pytest.raises(OracleError, match="oracle_cleanup_failed"):
        auth.start(7)


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


def test_oracle_boundary_rejects_attribute_file_open(tmp_path):
    target = tmp_path / "unsafe.py"
    target.write_text("from pathlib import Path\nPath('x').open('w')\n")
    assert any("forbidden call open" in error for error in check(target))


def test_oracle_boundary_rejects_builtins_file_open(tmp_path):
    target = tmp_path / "unsafe.py"
    target.write_text("import builtins\nbuiltins.open('x')\n")
    assert any("forbidden call open" in error for error in check(target))


@pytest.mark.parametrize("operation", ["read_bytes", "read_text", "write_bytes", "write_text"])
def test_oracle_boundary_rejects_path_file_operations(tmp_path, operation):
    target = tmp_path / "candidate.py"
    target.write_text(f"from pathlib import Path\nPath('x').{operation}()\n")
    assert any(f"forbidden call {operation}" in error for error in check(target))
