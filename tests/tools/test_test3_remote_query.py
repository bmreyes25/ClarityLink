import pytest

from tests.tools.local_tool_gate import require_local_tools

require_local_tools(__file__, "test3_remote_query.py")

from tools.test3_remote_query import parse_reply


def test_process_query_requires_valid_nonempty_table_and_remote_success():
    assert parse_reply(
        "USER PID PPID VSIZE RSS WCHAN PC NAME\nshell 42 1 100 20 poll 0 adb\nCLARITYLINK_REMOTE_RC=0\n",
        "processes",
    ).splitlines()[1].split()[1] == "42"
    for invalid in (
        "CLARITYLINK_REMOTE_RC=0\n",
        "not a process table\nCLARITYLINK_REMOTE_RC=0\n",
        "USER PID PPID VSIZE RSS WCHAN PC NAME\nbad row\nCLARITYLINK_REMOTE_RC=0\n",
        "CLARITYLINK_REMOTE_RC=1\n",
        "USER PID PPID VSIZE RSS WCHAN PC NAME\nCLARITYLINK_REMOTE_RC=0\nerror\n",
        "USER PID PPID VSIZE RSS WCHAN PC NAME\nCLARITYLINK_REMOTE_RC=0\nCLARITYLINK_REMOTE_RC=0\n",
    ):
        with pytest.raises(ValueError):
            parse_reply(invalid, "processes")


def test_package_query_distinguishes_absent_from_failed_or_ambiguous():
    assert parse_reply("CLARITYLINK_REMOTE_RC=0\n", "packages", "org.claritylink.admissionprobe") == ""
    assert parse_reply(
        "package:org.claritylink.admissionprobe\nCLARITYLINK_REMOTE_RC=0\n",
        "packages",
        "org.claritylink.admissionprobe",
    ) == "package:org.claritylink.admissionprobe"
    for invalid in (
        "",
        "CLARITYLINK_REMOTE_RC=1\n",
        "package:org.claritylink.admissionprobe\npackage:foreign.app\nCLARITYLINK_REMOTE_RC=0\n",
        "error: transport unavailable\nCLARITYLINK_REMOTE_RC=0\n",
        "package:foreign.app\nCLARITYLINK_REMOTE_RC=0\n",
    ):
        with pytest.raises(ValueError):
            parse_reply(invalid, "packages", "org.claritylink.admissionprobe")


def test_window_query_requires_expected_nonempty_framework_dump():
    valid = "WINDOW MANAGER WINDOWS (dumpsys window windows)\nCLARITYLINK_REMOTE_RC=0\n"
    assert "WINDOW MANAGER WINDOWS" in parse_reply(valid, "windows")
    for invalid in ("CLARITYLINK_REMOTE_RC=0\n", "remote error\nCLARITYLINK_REMOTE_RC=0\n",
                    "WINDOW MANAGER WINDOWS\nCLARITYLINK_REMOTE_RC=1\n"):
        with pytest.raises(ValueError):
            parse_reply(invalid, "windows")
