"""Host-only fake-ADB rehearsal for the conditional Phase C state machine."""
import subprocess

import pytest

from tests.tools.local_tool_gate import require_local_tools

require_local_tools(__file__, "r7e7i_phase_c_cleanup.py", "r7e6_test_a_collector.py")

from tools import r7e7i_phase_c_cleanup as c
from tools import r7e6_test_a_collector as test_a


LIST = "-r-xr-xr-x shell shell 7904 Oct 12 00:00 " + c.REMOTE.rsplit("/", 1)[-1] + "\n"


class FakeADB:
    _phase_c_fake_adb = True

    def __init__(self, fault=""):
        self.fault = fault
        self.calls = []
        self.deleted = False

    def __call__(self, argv, **kwargs):
        self.calls.append(argv)
        assert kwargs["timeout"] == c.TIMEOUT
        if self.fault == "timeout" and len(self.calls) == 3:
            raise subprocess.TimeoutExpired(argv, c.TIMEOUT)
        if self.fault == "permission" and argv[-3:] == ["ls", "-ld", c.REMOTE]:
            return subprocess.CompletedProcess(argv, 1, "", "Permission denied\n")
        if argv[-1:] == ["version"]:
            out = ("Android Debug Bridge version 1.0.41\nVersion " + test_a.ADB_VERSION + "\n")
            return subprocess.CompletedProcess(argv, 0, out, "")
        if argv[-1:] == ["devices"]:
            return subprocess.CompletedProcess(argv, 0, "List of devices attached\nTESTSER\tdevice\n", "")
        if argv[-3:] == ["ls", "-ld", c.REMOTE]:
            if self.deleted:
                return subprocess.CompletedProcess(argv, 1, "", f"{c.REMOTE}: No such file or directory\n")
            if self.fault == "absent":
                return subprocess.CompletedProcess(argv, 1, "", f"{c.REMOTE}: No such file or directory\n")
            if self.fault == "metadata":
                return subprocess.CompletedProcess(argv, 0, LIST.replace("7904", "9000"), "")
            return subprocess.CompletedProcess(argv, 0, LIST, "")
        if argv[-2:] == ["/system/bin/md5", c.REMOTE]:
            md5 = "0" * 32 if self.fault == "mismatch" else c.MD5
            return subprocess.CompletedProcess(argv, 0, f"{md5}  {c.REMOTE}\n", "")
        if argv[-2:] == ["/system/bin/rm", c.REMOTE]:
            self.deleted = True
            return subprocess.CompletedProcess(argv, 0, "", "")
        raise AssertionError(argv)


def test_default_and_dry_run_never_call_adb(monkeypatch, capsys):
    monkeypatch.setattr(c.subprocess, "run", lambda *_a, **_k: pytest.fail("ADB invoked"))
    assert c.main([]) == 0
    assert c.main(["--dry-run"]) == 0
    assert '"adb_operations": 0' in capsys.readouterr().out
    with pytest.raises(c.Stop, match="PACKAGE_NOT_FROZEN"):
        c.execute(c.parser().parse_args(["--execute-authorized-phase-c", "--authorization-sha256", "a" * 64]))
    assert c.rehearse("TESTSER", subprocess.run) == "REHEARSAL_REQUIRES_FAKE_ADB"


def test_single_exact_delete_after_fresh_identity_and_postcheck():
    fake = FakeADB()
    assert c.rehearse("TESTSER", fake) == "EXACT_PATH_ABSENT_AFTER_SINGLE_DELETE"
    assert fake.calls[-3][3:] == ["shell", "/system/bin/md5", c.REMOTE]
    assert fake.calls[-2][3:] == ["shell", "/system/bin/rm", c.REMOTE]
    assert fake.calls[-1][3:] == ["shell", "ls", "-ld", c.REMOTE]
    assert sum(call[-2:] == ["/system/bin/rm", c.REMOTE] for call in fake.calls) == 1


@pytest.mark.parametrize("fault,expected,max_calls", [
    ("mismatch", "FRESH_FILE_DIGEST_MISMATCH", 4),
    ("absent", "EXACT_PATH_ABSENT_NO_DELETE", 3),
    ("metadata", "FRESH_FILE_IDENTITY_MISMATCH", 3),
    ("timeout", "TIMEOUT_STOP_NO_RETRY", 3),
    ("permission", "COMMAND_FAILURE_STOP_NO_RETRY", 3),
])
def test_predelete_faults_stop_without_delete(fault, expected, max_calls):
    fake = FakeADB(fault)
    assert c.rehearse("TESTSER", fake) == expected
    assert len(fake.calls) <= max_calls
    assert all(call[-2:] != ["/system/bin/rm", c.REMOTE] for call in fake.calls)


def test_postdelete_verification_failure_does_not_retry():
    class BadVerify(FakeADB):
        def __call__(self, argv, **kwargs):
            if self.deleted and argv[-3:] == ["ls", "-ld", c.REMOTE]:
                self.calls.append(argv)
                return subprocess.CompletedProcess(argv, 0, LIST, "")
            return super().__call__(argv, **kwargs)
    fake = BadVerify()
    assert c.rehearse("TESTSER", fake) == "POST_DELETE_VERIFICATION_FAILED_NO_RETRY"
    assert sum(call[-2:] == ["/system/bin/rm", c.REMOTE] for call in fake.calls) == 1
