"""Timeout evidence must preserve host elapsed time and terminal markers."""
import subprocess

import pytest

from tools import run_r7e6_api17_runtime as runtime


def test_host_timeout_records_observed_terminal_markers(monkeypatch):
    class Server:
        def poll(self):
            return None

    class Child:
        pid = 987654
        def __init__(self, *_args, **_kwargs):
            self.calls = 0
        def communicate(self, timeout=None):
            self.calls += 1
            if self.calls == 1:
                raise subprocess.TimeoutExpired("adb", timeout)
            return (b"SUPERVISOR_CHILD_STARTED parent_pid=1 child_pid=2\n"
                    b"SELF_TEST_PASS\n", b"")

    monkeypatch.setattr(runtime.subprocess, "Popen", Child)
    monkeypatch.setattr(runtime.os, "killpg", lambda *_args: None)
    with pytest.raises(runtime.RuntimeFailure) as captured:
        runtime.run_client(["adb", "shell"], {}, 12.0, Server(), "repeat 52 self-test")
    message = str(captured.value)
    assert "host_elapsed_seconds=" in message
    assert "stdout_bytes=" in message
    assert "'self_test_pass': True" in message
    assert "'child_reaped': False" in message
    assert "'guest_status': False" in message
