from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "android/test3-admission-probe/AndroidManifest.xml"
SOURCE = ROOT / "android/test3-admission-probe/java/org/claritylink/android/Test3DisplayAccessProbeActivity.java"
BUILDER = ROOT / "tools/build_test3_admission_probe.sh"
EMULATOR_RUNNER = ROOT / "tools/run_test3_admission_probe_emulator.sh"
ANDROID = "{http://schemas.android.com/apk/res/android}"


def test_probe_manifest_is_api17_permission_free_no_display_launcher():
    manifest = ET.parse(MANIFEST).getroot()
    assert manifest.attrib["package"] == "org.claritylink.admissionprobe"
    uses_sdk = manifest.find("uses-sdk")
    assert uses_sdk is not None
    assert uses_sdk.attrib[ANDROID + "minSdkVersion"] == "17"
    assert uses_sdk.attrib[ANDROID + "targetSdkVersion"] == "17"
    assert not manifest.findall("uses-permission")
    app = manifest.find("application")
    assert app is not None
    assert app.attrib[ANDROID + "allowBackup"] == "false"
    assert app.attrib[ANDROID + "debuggable"] == "false"
    assert len(app) == 1
    activity = app.find("activity")
    assert activity is not None
    assert activity.attrib[ANDROID + "theme"] == "@android:style/Theme.NoDisplay"
    assert activity.attrib[ANDROID + "exported"] == "true"
    assert activity.attrib[ANDROID + "excludeFromRecents"] == "true"
    assert len(activity.findall("intent-filter")) == 1


def test_probe_queries_only_public_display_metadata_and_never_admits_content():
    source = SOURCE.read_text()
    for required in (
        "new DisplayDiscovery(this)",
        "discovery.enumerate()",
        "discovery.select(",
        "DisplayManager.DISPLAY_CATEGORY_PRESENTATION",
        "createDisplayContext(display)",
        "Display.FLAG_SECURE",
        "Display.FLAG_SUPPORTS_PROTECTED_BUFFERS",
        "Process.myUid()",
        "catch (SecurityException",
        "finish();",
        "MAX_DISPLAYS = 8",
    ):
        assert required in source
    discovery = (ROOT / "android/src/main/java/org/claritylink/android/DisplayDiscovery.java").read_text()
    assert "Context.DISPLAY_SERVICE" in discovery
    assert "manager.getDisplays()" in discovery
    for prohibited in (
        "new Presentation",
        "new Surface",
        "SurfaceView",
        "SurfaceHolder",
        "WindowManager",
        "startService(",
        "bindService(",
        "Runtime.exec(",
        "ProcessBuilder",
        "openFileOutput(",
        "HttpURLConnection",
        "Socket(",
    ):
        assert prohibited not in source


def test_probe_builder_refuses_reuse_and_never_recursively_deletes_output():
    builder = BUILDER.read_text()
    assert "TEST3_BUILD_DIR" in builder
    assert "Build output must be a fresh path" in builder
    assert "mkdir \"$out\"" in builder
    assert "chmod 700 \"$out\"" in builder
    assert "rm -rf" not in builder


def test_emulator_runner_owns_its_adb_process_and_fresh_avd_storage():
    runner = EMULATOR_RUNNER.read_text()
    assert "nodaemon server" in runner
    assert "lsof -nP -t -iTCP" in runner
    assert "adb_local kill-server" not in runner
    assert "server_command" in runner
    assert 'run_root=$(mktemp -d "$out/test3-run-XXXXXX")' in runner
    assert 'avd_root="$run_root/avd"' in runner
    assert 'trap cleanup EXIT' in runner
    assert 'probe-log.txt' in runner and 'probe-validation.json' in runner
    assert 'tools/test3_output_validation_v2.py"' in runner
    assert '--expected-uid "$uid"' in runner
    assert '--expected-pid "$probe_pid"' in runner
    assert '--require-public-inventory' in runner
    assert "TEST3_EXPECTED_APK_SHA256" in runner
    assert "reviewed build receipt" in runner
    assert 'apk_sha256=$apk_sha256' in runner
    assert 'logcat -d -v brief -s ClarityLinkTest3Probe:V' in runner
    assert 'listener_pid=$(lsof -nP -t -iTCP:"$adb_port" -sTCP:LISTEN' in runner
    assert "--force" not in runner
    assert "O_EXCL" in runner
    assert r'pm list packages \"$package\"' in runner
    assert "exact Success" in runner
    assert 'awk -v package="$package"' in runner


def test_emulator_runner_installs_cleanup_before_any_run_local_log_creation():
    runner = EMULATOR_RUNNER.read_text()
    assert runner.index('trap cleanup EXIT') < runner.index('O_EXCL')
    assert 'emulator.log' in runner and 'adb-server.log' in runner
