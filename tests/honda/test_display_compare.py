from pathlib import Path
import hashlib
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "honda-readonly-preflight"))

import display_compare


def write_snapshot(root: Path, phase: str, *, display: str, window: str, layers: str) -> None:
    directory = root / phase / "display"
    directory.mkdir(parents=True)
    if "Logical Displays:" not in display:
        display = display.rstrip() + "\nLogical Displays: size=1\n    mDisplayId=1\n"
    (directory / "dumpsys_display.raw").write_text(display)
    entries = re.findall(r"Window\{([0-9a-fA-F]+\s+u\d+\s*[^}]{0,512})\}", window)
    if entries:
        display_match = re.search(r"\bmDisplayId\s*=\s*(\d+)", window)
        display_id = display_match.group(1) if display_match else "1"
        window = "WINDOW MANAGER WINDOWS (dumpsys window windows)\n" + "".join(
            f"Window #{index} Window{{{entry}}}:\n  mDisplayId={display_id}\n"
            for index, entry in enumerate(entries)
        )
    (directory / "dumpsys_window.raw").write_text(window)
    (directory / "dumpsys_SurfaceFlinger.raw").write_text(layers)


def write_integrity_manifest(root: Path) -> None:
    entries = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "sha256.txt":
            entries.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(root)}")
    (root / "sha256.txt").write_text("\n".join(entries) + "\n")


def test_compare_normalizes_volatile_window_and_layer_pointers(tmp_path):
    capture = tmp_path / "capture"
    display = ('DisplayDeviceInfo{"Built-in Screen": 800 x 480, type BUILT_IN}\n'
               'mBaseDisplayInfo=DisplayInfo{"HDMI Screen", layerStack 1, type HDMI}\n')
    write_snapshot(capture, "disconnected", display=display,
                   window="Display: mDisplayId=1\n  Window{aaa0 u0 FactoryLauncher}\n",
                   layers="+ Layer 0xaaa0 (FactoryLauncher)\n+ Layer 0xbbb0 (StatusBar)\n")
    write_snapshot(capture, "connected", display=display,
                   window="Display: mDisplayId=1\n  Window{ccc0 u0 CarPlayActivity}\n",
                   layers="+ Layer 0xccc0 (CarPlayActivity)\n+ Layer 0xddd0 (StatusBar)\n")
    write_integrity_manifest(capture)

    result = display_compare.compare_capture(capture, ["disconnected", "connected"], "1")
    delta = result["deltas"]["disconnected_to_connected"]
    assert result["comparison_status"] == "SNAPSHOT_COMPARISON_COMPLETE"
    assert result["campaign_identity_status"] == "NOT_CHECKED_BY_SNAPSHOT_COMPARATOR"
    assert result["surfaceflinger_display_attribution"] == "UNAVAILABLE_GLOBAL_LAYER_DUMP"
    assert result["capture_integrity"]["status"] == "VERIFIED"
    assert delta["display"]["inventory_unchanged"]
    assert delta["window"]["windows_by_display_id"]["1"] == {
        "added": ["CarPlayActivity"], "removed": ["FactoryLauncher"], "persisting": []}
    assert delta["surfaceflinger"]["named_layers"] == {
        "added": ["CarPlayActivity"], "removed": ["FactoryLauncher"], "persisting": ["StatusBar"]}
    assert "do not establish causality" in result["interpretation_limit"]


def test_missing_source_is_not_reported_as_an_empty_success(tmp_path):
    capture = tmp_path / "capture"
    for phase in ("one", "two"):
        directory = capture / phase / "display"
        directory.mkdir(parents=True)
        (directory / "dumpsys_window.raw").write_text("Display: mDisplayId=1\n")
    result = display_compare.compare_capture(capture, ["one", "two"])
    assert result["comparison_status"] == "INCOMPLETE"
    assert result["snapshots"]["one"]["sources"]["display"]["status"] == "NOT_COLLECTED"
    assert result["snapshots"]["one"]["sources"]["surfaceflinger"]["status"] == "NOT_COLLECTED"


def test_permission_denial_is_preserved_as_a_distinct_status(tmp_path):
    capture = tmp_path / "capture"
    directory = capture / "one" / "display"
    directory.mkdir(parents=True)
    (directory / "dumpsys_display.raw").write_text("Permission denied\n")
    result = display_compare.parse_snapshot(directory)
    assert result["sources"]["display"]["status"] == "PERMISSION_DENIED"


def test_snapshot_size_limit_is_fail_closed(tmp_path):
    directory = tmp_path / "display"
    directory.mkdir()
    (directory / "dumpsys_display.raw").write_bytes(b"x" * (display_compare.MAX_SNAPSHOT_BYTES + 1))
    assert display_compare.parse_snapshot(directory)["sources"]["display"]["status"] == "FAILED"


def test_duplicate_phase_names_rejected(tmp_path):
    import pytest
    with pytest.raises(ValueError, match="unique ordered phases"):
        display_compare.compare_capture(tmp_path, ["same", "same"])


def test_phase_traversal_and_absolute_paths_are_rejected(tmp_path):
    import pytest
    for phase in ("..", "../escape", "/tmp/escape"):
        with pytest.raises(ValueError, match="safe single path segments"):
            display_compare.compare_capture(tmp_path, [phase, "valid"])


def test_phase_directory_symlink_is_rejected(tmp_path):
    import pytest
    outside = tmp_path / "outside"
    outside.mkdir()
    capture = tmp_path / "capture"
    capture.mkdir()
    (capture / "phase").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="must not be symlinks"):
        display_compare.compare_capture(capture, ["phase", "valid"])


def test_capture_root_symlink_is_rejected_by_library_entry_point(tmp_path):
    import pytest
    real = tmp_path / "real"
    real.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(real, target_is_directory=True)
    with pytest.raises(ValueError, match="capture root must not be a symlink"):
        display_compare.compare_capture(alias, ["one", "two"])


def test_global_focus_window_is_not_attributed_to_last_display(tmp_path):
    capture = tmp_path / "capture"
    directory = capture / "one" / "display"
    directory.mkdir(parents=True)
    (directory / "dumpsys_display.raw").write_text(
        'DisplayDeviceInfo{"Built-in": 800 x 480, type BUILT_IN}\n')
    (directory / "dumpsys_window.raw").write_text(
        "WINDOW MANAGER WINDOWS (dumpsys window windows)\n"
        "Window #0 Window{aaaa u0 NavigationWindow}:\n  mDisplayId=1\n"
        "mCurrentFocus=Window{bbbb u0 GlobalFocus}\n")
    (directory / "dumpsys_SurfaceFlinger.raw").write_text(
        "+ Layer 0xaaaa (NavigationWindow)\n")
    result = display_compare.parse_snapshot(directory)
    assert result["sources"]["window"]["windows_by_display_id"]["1"] == ["NavigationWindow"]
    assert result["sources"]["window"]["all_named_windows"] == ["GlobalFocus", "NavigationWindow"]


def test_nested_window_references_do_not_inherit_owner_display(tmp_path):
    directory = tmp_path / "display"
    directory.mkdir()
    (directory / "dumpsys_window.raw").write_text(
        "WINDOW MANAGER WINDOWS (dumpsys window windows)\n"
        "Window #0 Window{aaaa u0 PrimaryWindow}:\n  mDisplayId=1\n"
        "    child=Window{bbbb u0 ReferencedWindow}\n")
    parsed = display_compare.parse_snapshot(directory)["sources"]["window"]
    assert parsed["windows_by_display_id"]["1"] == ["PrimaryWindow"]
    assert parsed["all_named_windows"] == ["PrimaryWindow", "ReferencedWindow"]


def test_empty_display_sections_do_not_confirm_window_capture(tmp_path):
    directory = tmp_path / "display"
    directory.mkdir()
    (directory / "dumpsys_window.raw").write_text(
        "DisplayContents:\n  Display: mDisplayId=1\n")
    assert display_compare.parse_snapshot(directory)["sources"]["window"]["status"] == "UNSUPPORTED"


def test_duplicate_surface_layers_keep_counts_and_normalize_ids(tmp_path):
    capture = tmp_path / "capture"
    for phase, layer_ids in (("a", (11, 12)), ("b", (21, 22, 23))):
        write_snapshot(capture, phase,
                       display='DisplayDeviceInfo{"Built-in": 800 x 480, type BUILT_IN}\n',
                       window="Display: mDisplayId=1\nWindow{abcd u0 App}\n",
                       layers="".join(f"+ Layer 0x{i:x} (A Surface#{i})\n" for i in layer_ids))
    write_integrity_manifest(capture)
    delta = display_compare.compare_capture(capture, ["a", "b"], "1")["deltas"]["a_to_b"]
    assert delta["surfaceflinger"]["named_layers"] == {
        "added": ["A Surface#<id>"], "removed": [], "persisting": ["A Surface#<id>", "A Surface#<id>"]}


def test_missing_or_tampered_integrity_manifest_prevents_complete_status(tmp_path):
    capture = tmp_path / "capture"
    display = 'DisplayDeviceInfo{"Built-in": 800 x 480, type BUILT_IN}\n'
    for phase in ("a", "b"):
        write_snapshot(capture, phase, display=display,
                       window="Display: mDisplayId=1\nWindow{abcd u0 App}\n",
                       layers="+ Layer 0xaaaa (App)\n")
    result = display_compare.compare_capture(capture, ["a", "b"], "1")
    assert result["comparison_status"] == "INCOMPLETE"
    assert result["capture_integrity"]["status"] == "NOT_COLLECTED"
    write_integrity_manifest(capture)
    (capture / "a/display/dumpsys_window.raw").write_text("tampered\n")
    result = display_compare.compare_capture(capture, ["a", "b"], "1")
    assert result["comparison_status"] == "INCOMPLETE"
    assert result["capture_integrity"]["reason"] == "snapshot_hash_mismatch"


def test_supplied_logical_id_does_not_claim_factory_display1_mapping(tmp_path):
    capture = tmp_path / "capture"
    display = 'DisplayDeviceInfo{"Built-in": 800 x 480, type BUILT_IN}\n'
    for phase in ("a", "b"):
        write_snapshot(capture, phase, display=display,
                       window="Display: mDisplayId=2\nWindow{abcd u0 App}\n",
                       layers="+ Layer 0xaaaa (App)\n")
    write_integrity_manifest(capture)
    result = display_compare.compare_capture(capture, ["a", "b"], "1")
    assert result["capture_integrity"]["status"] == "VERIFIED"
    assert result["target_display_attribution_status"] == "LOGICAL_DISPLAY_ID_PRESENT"
    assert result["factory_display1_mapping_status"] == "NOT_VERIFIED_BY_SNAPSHOT_COMPARATOR"
    assert result["window_presence_by_phase"] == {"a": "NO_WINDOW_REPORTED", "b": "NO_WINDOW_REPORTED"}
    assert result["comparison_status"] == "SNAPSHOT_COMPARISON_COMPLETE"


def test_valid_window_dump_with_no_reported_window_is_not_a_parser_failure(tmp_path):
    capture = tmp_path / "capture"
    display = ('DisplayDeviceInfo{"Built-in": 800 x 480, type BUILT_IN}\n'
               'Logical Displays: size=1\n    mDisplayId=1\n')
    for phase in ("a", "b"):
        write_snapshot(capture, phase, display=display,
                       window="WINDOW MANAGER WINDOWS (dumpsys window windows)\n",
                       layers="+ Layer 0xaaaa (StatusBar)\n")
    write_integrity_manifest(capture)
    result = display_compare.compare_capture(capture, ["a", "b"], "1")
    assert result["comparison_status"] == "SNAPSHOT_COMPARISON_COMPLETE"
    assert result["window_presence_by_phase"] == {"a": "NO_WINDOW_REPORTED", "b": "NO_WINDOW_REPORTED"}


def test_display_id_mentions_outside_logical_display_inventory_do_not_prove_target(tmp_path):
    capture = tmp_path / "capture"
    for phase in ("a", "b"):
        write_snapshot(capture, phase,
                       display='DisplayDeviceInfo{"Built-in": 800 x 480, type BUILT_IN}\n'
                               '  diagnostic mDisplayId=1\nLogical Displays: size=1\n',
                       window="Display: mDisplayId=1\nWindow{abcd u0 App}\n",
                       layers="+ Layer 0xaaaa (App)\n")
    write_integrity_manifest(capture)
    result = display_compare.compare_capture(capture, ["a", "b"], "1")
    assert result["target_display_attribution_status"] == "UNRESOLVED"
    assert result["comparison_status"] == "INCOMPLETE"


def test_default_display_zero_cannot_stand_in_for_factory_display1(tmp_path):
    import pytest
    with pytest.raises(ValueError, match="positive numeric display id"):
        display_compare.compare_capture(tmp_path, ["a", "b"], "0")


def test_manifest_rejects_unsafe_entries_and_missing_expected_snapshot(tmp_path):
    import pytest
    capture = tmp_path / "capture"
    display = 'DisplayDeviceInfo{"Built-in": 800 x 480, type BUILT_IN}\n'
    for phase in ("a", "b"):
        write_snapshot(capture, phase, display=display,
                       window="Display: mDisplayId=1\nWindow{abcd u0 App}\n",
                       layers="+ Layer 0xaaaa (App)\n")
    write_integrity_manifest(capture)
    manifest = capture / "sha256.txt"
    original = manifest.read_text()
    manifest.write_text(original + "0" * 64 + "  ../outside\n")
    result = display_compare.compare_capture(capture, ["a", "b"], "1")
    assert result["comparison_status"] == "INCOMPLETE"
    assert result["capture_integrity"]["reason"] == "unsafe_or_duplicate_integrity_path"
    manifest.write_text("\n".join(line for line in original.splitlines()
                                   if "b/display/dumpsys_window.raw" not in line) + "\n")
    result = display_compare.compare_capture(capture, ["a", "b"], "1")
    assert result["capture_integrity"]["status"] == "NOT_COLLECTED"
    assert result["comparison_status"] == "INCOMPLETE"


def test_symlinked_snapshot_is_not_read_even_with_matching_manifest(tmp_path):
    capture = tmp_path / "capture"
    display = 'DisplayDeviceInfo{"Built-in": 800 x 480, type BUILT_IN}\n'
    for phase in ("a", "b"):
        write_snapshot(capture, phase, display=display,
                       window="Display: mDisplayId=1\nWindow{abcd u0 App}\n",
                       layers="+ Layer 0xaaaa (App)\n")
    write_integrity_manifest(capture)
    target = capture / "a/display/dumpsys_window.raw"
    outside = tmp_path / "outside.raw"
    outside.write_text(target.read_text())
    target.unlink()
    target.symlink_to(outside)
    result = display_compare.compare_capture(capture, ["a", "b"], "1")
    assert result["capture_integrity"]["status"] == "FAILED"
    assert result["comparison_status"] == "INCOMPLETE"


def test_comparator_parses_the_same_bytes_that_were_hash_verified(tmp_path, monkeypatch):
    capture = tmp_path / "capture"
    display = 'DisplayDeviceInfo{"Built-in": 800 x 480, type BUILT_IN}\n'
    for phase in ("a", "b"):
        write_snapshot(capture, phase, display=display,
                       window="Display: mDisplayId=1\n  Window{abcd u0 VerifiedApp}\n",
                       layers="+ Layer 0xaaaa (VerifiedApp)\n")
    write_integrity_manifest(capture)
    original = display_compare._verify_snapshot_hashes
    def verify_then_mutate(root, phases):
        result = original(root, phases)
        (root / "a/display/dumpsys_window.raw").write_text(
            "Display: mDisplayId=1\n  Window{abcd u0 SwappedAfterHash}\n")
        return result
    monkeypatch.setattr(display_compare, "_verify_snapshot_hashes", verify_then_mutate)
    result = display_compare.compare_capture(capture, ["a", "b"], "1")
    assert result["comparison_status"] == "SNAPSHOT_COMPARISON_COMPLETE"
    assert result["snapshots"]["a"]["sources"]["window"]["all_named_windows"] == ["VerifiedApp"]


def test_incidental_permission_phrase_does_not_mark_snapshot_denied(tmp_path):
    directory = tmp_path / "display"
    directory.mkdir()
    (directory / "dumpsys_display.raw").write_text(
        'DisplayDeviceInfo{"Built-in": 800 x 480, type BUILT_IN}\n'
        "This help text mentions permission denied as an example.\n")
    assert display_compare.parse_snapshot(directory)["sources"]["display"]["status"] == "CONFIRMED"


def test_unknown_and_empty_service_output_are_not_confirmed(tmp_path):
    directory = tmp_path / "display"
    directory.mkdir()
    (directory / "dumpsys_display.raw").write_text("Can't find service: display\n")
    (directory / "dumpsys_window.raw").write_text("not a WindowManager dump\n")
    (directory / "dumpsys_SurfaceFlinger.raw").write_text("\n")
    result = display_compare.parse_snapshot(directory)["sources"]
    assert result["display"]["status"] == "UNSUPPORTED"
    assert result["window"]["status"] == "UNSUPPORTED"
    assert result["surfaceflinger"]["status"] == "FAILED"


def test_hondahack_casting_lifecycle_states_compare_without_ownership_claim(tmp_path):
    capture = tmp_path / "capture"
    display = 'DisplayDeviceInfo{"Built-in": 800 x 480, type BUILT_IN}\n'
    states = {
        "casting_off": "FactoryLauncher",
        "casting_on": "HondaHackCastingView",
        "navigation_deselected": "FactoryLauncher",
        "navigation_reselected": "HondaHackCastingView",
        "casting_stopped": "FactoryLauncher",
    }
    for phase, window_name in states.items():
        write_snapshot(capture, phase, display=display,
                       window=f"Display: mDisplayId=1\n  Window{{abcd u0 {window_name}}}\n",
                       layers=f"+ Layer 0xabcd ({window_name})\n")
    write_integrity_manifest(capture)
    capture.chmod(0o700)
    result = display_compare.compare_capture(capture, list(states), "1")
    assert result["comparison_status"] == "SNAPSHOT_COMPARISON_COMPLETE"
    assert result["deltas"]["casting_off_to_casting_on"]["window"]["windows_by_display_id"]["1"]["added"] == ["HondaHackCastingView"]
    assert result["deltas"]["navigation_deselected_to_navigation_reselected"]["surfaceflinger"]["named_layers"]["added"] == ["HondaHackCastingView"]
    assert result["deltas"]["navigation_reselected_to_casting_stopped"]["window"]["windows_by_display_id"]["1"]["removed"] == ["HondaHackCastingView"]
    assert "do not establish causality" in result["interpretation_limit"]


def test_private_capture_directory_is_required(tmp_path):
    import pytest
    directory = tmp_path / "shared"
    directory.mkdir()
    directory.chmod(0o755)
    with pytest.raises(ValueError, match="owner-only directory"):
        display_compare._require_private_directory(directory, "capture root")


def test_cli_writes_private_output_after_verified_multi_phase_compare(tmp_path, monkeypatch):
    capture = tmp_path / "capture"
    display = 'DisplayDeviceInfo{"Built-in": 800 x 480, type BUILT_IN}\n'
    for phase in ("a", "b"):
        write_snapshot(capture, phase, display=display,
                       window="Display: mDisplayId=1\nWindow{abcd u0 App}\n",
                       layers="+ Layer 0xaaaa (App)\n")
    write_integrity_manifest(capture)
    capture.chmod(0o700)
    output = capture / "display-comparison.json"
    monkeypatch.setattr(sys, "argv", ["display_compare", str(capture), "--phase", "a",
                                      "--phase", "b", "--target-display-id", "1", "--output", str(output)])
    assert display_compare.main() == 0
    assert output.stat().st_mode & 0o777 == 0o600
    assert '"comparison_status": "SNAPSHOT_COMPARISON_COMPLETE"' in output.read_text()


def test_cli_refuses_overwrite_and_worktree_output(tmp_path, monkeypatch):
    import pytest
    capture = tmp_path / "capture"
    display = 'DisplayDeviceInfo{"Built-in": 800 x 480, type BUILT_IN}\n'
    for phase in ("a", "b"):
        write_snapshot(capture, phase, display=display,
                       window="Display: mDisplayId=1\nWindow{abcd u0 App}\n",
                       layers="+ Layer 0xaaaa (App)\n")
    write_integrity_manifest(capture)
    capture.chmod(0o700)
    output = capture / "display-comparison.json"
    output.write_text("existing")
    monkeypatch.setattr(sys, "argv", ["display_compare", str(capture), "--phase", "a",
                                      "--phase", "b", "--target-display-id", "1"])
    with pytest.raises(SystemExit) as error:
        display_compare.main()
    assert error.value.code == 2
    output.unlink()
    monkeypatch.setattr(display_compare, "_git_worktree_roots", lambda _repo: [capture.resolve()])
    with pytest.raises(SystemExit) as error:
        display_compare.main()
    assert error.value.code == 2


def test_cli_returns_failure_for_unresolved_display1_attribution(tmp_path, monkeypatch):
    capture = tmp_path / "capture"
    display = ('DisplayDeviceInfo{"Built-in": 800 x 480, type BUILT_IN}\n'
               'Logical Displays: size=1\n    mDisplayId=2\n')
    for phase in ("a", "b"):
        write_snapshot(capture, phase, display=display,
                       window="Display: mDisplayId=2\nWindow{abcd u0 App}\n",
                       layers="+ Layer 0xaaaa (App)\n")
    write_integrity_manifest(capture)
    capture.chmod(0o700)
    output = capture / "result.json"
    monkeypatch.setattr(sys, "argv", ["display_compare", str(capture), "--phase", "a",
                                      "--phase", "b", "--target-display-id", "1",
                                      "--output", str(output)])
    assert display_compare.main() == 1


def test_cli_removes_partial_output_after_write_failure(tmp_path, monkeypatch):
    import pytest
    capture = tmp_path / "capture"
    display = 'DisplayDeviceInfo{"Built-in": 800 x 480, type BUILT_IN}\n'
    for phase in ("a", "b"):
        write_snapshot(capture, phase, display=display,
                       window="Display: mDisplayId=1\nWindow{abcd u0 App}\n",
                       layers="+ Layer 0xaaaa (App)\n")
    write_integrity_manifest(capture)
    capture.chmod(0o700)
    output = capture / "result.json"
    monkeypatch.setattr(sys, "argv", ["display_compare", str(capture), "--phase", "a",
                                      "--phase", "b", "--target-display-id", "1",
                                      "--output", str(output)])
    monkeypatch.setattr(display_compare.json, "dumps", lambda *_a, **_k: (_ for _ in ()).throw(OSError("synthetic write failure")))
    with pytest.raises(SystemExit) as error:
        display_compare.main()
    assert error.value.code == 2
    assert not output.exists()


def test_cli_requires_existing_private_output_parent(tmp_path, monkeypatch):
    import pytest
    capture = tmp_path / "capture"
    display = 'DisplayDeviceInfo{"Built-in": 800 x 480, type BUILT_IN}\n'
    for phase in ("a", "b"):
        write_snapshot(capture, phase, display=display,
                       window="Display: mDisplayId=1\nWindow{abcd u0 App}\n",
                       layers="+ Layer 0xaaaa (App)\n")
    write_integrity_manifest(capture)
    capture.chmod(0o700)
    output = tmp_path / "missing" / "result.json"
    monkeypatch.setattr(sys, "argv", ["display_compare", str(capture), "--phase", "a",
                                      "--phase", "b", "--target-display-id", "1",
                                      "--output", str(output)])
    with pytest.raises(SystemExit) as error:
        display_compare.main()
    assert error.value.code == 2
    assert not output.exists()


def test_cli_rejects_single_phase_with_argument_error(tmp_path, monkeypatch):
    capture = tmp_path / "capture"
    capture.mkdir(mode=0o700)
    monkeypatch.setattr(sys, "argv", ["display_compare", str(capture), "--phase", "only"])
    import pytest
    with pytest.raises(SystemExit) as error:
        display_compare.main()
    assert error.value.code == 2


def test_fifo_snapshot_fails_without_blocking(tmp_path):
    import os
    directory = tmp_path / "display"
    directory.mkdir()
    os.mkfifo(directory / "dumpsys_display.raw")
    assert display_compare.parse_snapshot(directory)["sources"]["display"]["status"] == "FAILED"


def test_adb_error_output_is_failed_not_unsupported(tmp_path):
    directory = tmp_path / "display"
    directory.mkdir()
    (directory / "dumpsys_display.raw").write_text("adb: error: device offline\n")
    assert display_compare.parse_snapshot(directory)["sources"]["display"]["status"] == "FAILED"
