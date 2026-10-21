from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
ACTIVITY = (REPO / "android/cl-imp-03-app/java/org/claritylink/android/MessengerFramePerformanceActivity.java").read_text()


def test_host_disconnect_before_timed_run_uses_activity_failure_cleanup():
    callback = ACTIVITY[
        ACTIVITY.index("public void onServiceDisconnected(ComponentName name)"):
        ACTIVITY.index("\n        }\n    };", ACTIVITY.index("public void onServiceDisconnected(ComponentName name)"))
    ]

    assert 'finishWithError("unexpected_ipc_closure")' in callback
    assert "if (running) finishWithError" not in callback


def test_unexpected_disconnect_cleanup_records_setup_failure_and_finishes():
    cleanup = ACTIVITY[
        ACTIVITY.index("private void finishWithError(String reason)"):
        ACTIVITY.index("private static int fdCount()", ACTIVITY.index("private void finishWithError(String reason)"))
    ]

    assert 'Log.e(TAG, "R12B_SETUP_FAILED reason=" + reason)' in cleanup
    assert "ui.postDelayed(new Runnable() { public void run() { finish(); } }, 250L)" in cleanup
