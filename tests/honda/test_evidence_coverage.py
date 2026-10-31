import copy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "honda-readonly-preflight"))

import evidence_coverage


def load_matrix():
    path = ROOT / "docs" / "diagnostics" / "evidence-coverage.json"
    return json.loads(path.read_text(encoding="utf-8"))


def authorized_categories(matrix):
    return {category for row in matrix["objectives"]
            for category in row["live_approval_categories"]
            if category in evidence_coverage.OWNER_APPROVABLE_LIVE_CATEGORIES}


def confirm_offline_and_owner_authorized_rows(matrix):
    verified_refs = set()
    for index, row in enumerate(matrix["objectives"]):
        live_categories = set(row["live_approval_categories"]) - evidence_coverage.OFFLINE_CATEGORIES
        if live_categories - evidence_coverage.OWNER_APPROVABLE_LIVE_CATEGORIES:
            continue
        row["actual_observation_status"] = "CONFIRMED"
        row["evidence_provenance"] = [
            evidence_coverage.CONFIRMATION_PROVENANCE[row["id"]], "CAPTURE_INTEGRITY_VALIDATED",
        ]
        relative = f"objectives/{row['id']}/fixture.raw"
        digest = str(index % 10) * 64
        row["evidence_refs"] = [{"artifact_id": f"fixture-{index}", "objective_id": row["id"],
                                 "relative_path": relative, "sha256": digest}]
        verified_refs.add((relative, digest))
        row["live_authorization_status"] = (
            "OFFLINE_ANALYSIS_REVIEWED" if not live_categories else "APPROVED_EXACT_RUN")
    return verified_refs


def test_matrix_classifies_all_requirements_without_claiming_campaign_success():
    result = evidence_coverage.evaluate_matrix(load_matrix())
    assert result["objective_count"] == len(load_matrix()["objectives"])
    assert result["objective_count"] >= 19
    assert result["evidence_classification_complete"] is True
    assert result["all_required_observations_confirmed"] is False
    assert result["campaign_success"] is False
    assert set(evidence_coverage.REQUIRED_OBJECTIVE_CATEGORIES) == evidence_coverage.REQUIRED_OBJECTIVE_IDS


def test_not_collected_requires_a_bounded_blocker_and_next_action():
    matrix = load_matrix()
    objective = next(row for row in matrix["objectives"]
                     if row["actual_observation_status"] == "NOT_COLLECTED")
    objective["blocker"] = ""
    result = evidence_coverage.evaluate_matrix(matrix)
    assert result["evidence_classification_complete"] is False
    assert result["campaign_success"] is False


def test_invalid_status_is_rejected_instead_of_becoming_success():
    matrix = load_matrix()
    matrix["objectives"][0]["actual_observation_status"] = "ABSENT"
    with pytest.raises(ValueError, match="invalid observation status"):
        evidence_coverage.evaluate_matrix(matrix)


def test_duplicate_objective_ids_are_rejected():
    matrix = load_matrix()
    matrix["objectives"].append(copy.deepcopy(matrix["objectives"][0]))
    with pytest.raises(ValueError, match="duplicate id"):
        evidence_coverage.evaluate_matrix(matrix)


def test_removing_a_baseline_objective_is_rejected():
    matrix = load_matrix()
    matrix["objectives"].pop()
    with pytest.raises(ValueError, match="objective set differs from baseline"):
        evidence_coverage.evaluate_matrix(matrix)


def test_unknown_provenance_is_rejected():
    matrix = load_matrix()
    matrix["objectives"][0]["evidence_provenance"] = ["made_up_source"]
    with pytest.raises(ValueError, match="invalid evidence provenance"):
        evidence_coverage.evaluate_matrix(matrix)


def test_blocked_privileged_objectives_keep_campaign_success_false():
    matrix = load_matrix()
    verified_refs = confirm_offline_and_owner_authorized_rows(matrix)
    result = evidence_coverage.evaluate_matrix(matrix, verified_refs, authorized_categories(matrix))
    assert result["campaign_success"] is False
    assert result["all_required_observations_confirmed"] is False
    assert all(row["actual_observation_status"] != "CONFIRMED" for row in matrix["objectives"]
               if "existing_privileged_read" in row["live_approval_categories"])


def test_confirmation_rejects_no_capture_or_unauthorized_provenance():
    matrix = load_matrix()
    objective = matrix["objectives"][0]
    objective["actual_observation_status"] = "CONFIRMED"
    objective["evidence_provenance"] = ["HONDA_DIRECT_OBSERVATION", "NO_DIRECT_CAPTURE",
                                        "CAPTURE_INTEGRITY_VALIDATED"]
    objective["evidence_refs"] = [{"artifact_id": "placeholder", "objective_id": objective["id"],
                                    "relative_path": f"objectives/{objective['id']}/x.raw",
                                    "sha256": "b" * 64}]
    with pytest.raises(ValueError, match="conflicts with its evidence or authorization"):
        evidence_coverage.evaluate_matrix(matrix)


def test_confirmation_requires_integrity_checked_artifact_reference():
    matrix = load_matrix()
    objective = matrix["objectives"][0]
    objective["actual_observation_status"] = "CONFIRMED"
    objective["evidence_provenance"] = ["HONDA_DIRECT_OBSERVATION",
                                        "CAPTURE_INTEGRITY_VALIDATED"]
    objective["live_authorization_status"] = "APPROVED_EXACT_RUN"
    with pytest.raises(ValueError, match="SHA-256 evidence reference"):
        evidence_coverage.evaluate_matrix(matrix, None, authorized_categories(matrix))


def test_objective_cannot_reuse_another_objectives_artifact():
    matrix = load_matrix()
    objective = matrix["objectives"][0]
    objective["actual_observation_status"] = "CONFIRMED"
    objective["evidence_provenance"] = ["HONDA_DIRECT_OBSERVATION",
                                        "CAPTURE_INTEGRITY_VALIDATED"]
    objective["live_authorization_status"] = "APPROVED_EXACT_RUN"
    objective["evidence_refs"] = [{"artifact_id": "other-objective",
                                    "objective_id": objective["id"],
                                    "relative_path": "objectives/other-objective/evidence.raw",
                                    "sha256": "d" * 64}]
    with pytest.raises(ValueError, match="not scoped to that objective"):
        evidence_coverage.evaluate_matrix(matrix, authorized_categories(matrix))


def test_private_evidence_root_rehashes_referenced_artifacts(tmp_path):
    import hashlib
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    artifact = root / "phase1.raw"
    artifact.write_bytes(b"synthetic evidence")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    (root / "sha256.txt").write_text(f"{digest}  phase1.raw\n")
    refs = {("phase1.raw", digest)}
    verified, manifest_sha256 = evidence_coverage._verify_evidence_root(root, refs)
    assert refs <= verified
    assert len(manifest_sha256) == 64
    artifact.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="fails SHA-256 validation"):
        evidence_coverage._verify_evidence_root(root, refs)


def test_confirmation_requires_exact_approval_status_not_text_matching():
    matrix = load_matrix()
    objective = matrix["objectives"][0]
    objective["actual_observation_status"] = "CONFIRMED"
    objective["evidence_provenance"] = ["HONDA_DIRECT_OBSERVATION",
                                        "CAPTURE_INTEGRITY_VALIDATED"]
    objective["live_authorization_status"] = "BLOCKED_NO_JUSTIFIABLE_ACCESS_METHOD"
    path = f"objectives/{objective['id']}/capture.raw"
    objective["evidence_refs"] = [{"artifact_id": "capture", "objective_id": objective["id"],
                                    "relative_path": path, "sha256": "e" * 64}]
    with pytest.raises(ValueError, match="exact required authorization status"):
        evidence_coverage.evaluate_matrix(
            matrix, {(path, "e" * 64)}, authorized_categories(matrix))


def test_authorization_record_must_be_private_consumed_and_scope_bound(tmp_path):
    record = tmp_path / "authorization.json"
    ledger = tmp_path / "ledger.json"
    data = {"schema": "claritylink-comprehensive-owner-authorization-v1",
            "campaign_id": "CL-HONDA-RUNTIME-EVIDENCE-FOLLOWUP-20261031",
            "approval_status": "PASS", "single_run": True,
            "authorization_id": "auth-run-0001", "run_id": "campaign-run-0001",
            "profile_sha256": "a" * 64, "source_lock_sha256": "b" * 64,
            "evidence_matrix_sha256": "e" * 64, "evidence_manifest_sha256": "f" * 64,
            "nonce_sha256": "c" * 64, "review_packet_sha256": "d" * 64,
            "authorized_categories": ["ordinary_unprivileged_adb"]}
    ledger.write_text(json.dumps({"schema": "claritylink-comprehensive-consumed-authorization-ledger-v1",
                                  "campaign_id": data["campaign_id"], "entries": [
                                      {"authorization_id": data["authorization_id"],
                                       "run_id": data["run_id"], "nonce_sha256": data["nonce_sha256"],
                                       "state": "CONSUMED"}]}))
    ledger.chmod(0o600)
    record.write_text(json.dumps(data))
    record.chmod(0o600)
    args = (record, "a" * 64, "b" * 64, data["run_id"], "e" * 64, "f" * 64, ledger)
    assert evidence_coverage._verify_authorization_record(*args) == {
        "ordinary_unprivileged_adb"}
    data["authorized_categories"] = ["temporary_runtime_instrumentation"]
    record.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="invalid categories"):
        evidence_coverage._verify_authorization_record(*args)
    data["authorized_categories"] = ["ordinary_unprivileged_adb"]
    data["run_id"] = "different-run-0001"
    record.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="consumed exact one-run approval"):
        evidence_coverage._verify_authorization_record(*args)
    data["run_id"] = "campaign-run-0001"
    record.write_text(json.dumps(data))
    ledger_data = json.loads(ledger.read_text())
    ledger_data["entries"].append(dict(ledger_data["entries"][0], run_id="other-run-0001"))
    ledger.write_text(json.dumps(ledger_data))
    with pytest.raises(ValueError, match="not uniquely consumed"):
        evidence_coverage._verify_authorization_record(*args)


@pytest.mark.parametrize("field, wrong_value", [
    ("profile_sha256", "1" * 64), ("source_lock_sha256", "2" * 64),
    ("run_id", "different-run"), ("evidence_matrix_sha256", "3" * 64),
    ("evidence_manifest_sha256", "4" * 64),
])
def test_authorization_record_rejects_each_scope_digest_mismatch(tmp_path, field, wrong_value):
    record = tmp_path / "authorization.json"
    ledger = tmp_path / "ledger.json"
    data = {"schema": "claritylink-comprehensive-owner-authorization-v1",
            "campaign_id": "CL-HONDA-RUNTIME-EVIDENCE-FOLLOWUP-20261031",
            "approval_status": "PASS", "single_run": True,
            "authorization_id": "auth-run-0001", "run_id": "campaign-run-0001",
            "profile_sha256": "a" * 64, "source_lock_sha256": "b" * 64,
            "evidence_matrix_sha256": "e" * 64, "evidence_manifest_sha256": "f" * 64,
            "nonce_sha256": "c" * 64, "review_packet_sha256": "d" * 64,
            "authorized_categories": ["ordinary_unprivileged_adb"]}
    record.write_text(json.dumps(data)); record.chmod(0o600)
    ledger.write_text(json.dumps({"schema": "claritylink-comprehensive-consumed-authorization-ledger-v1",
                                  "campaign_id": data["campaign_id"], "entries": [
                                      {"authorization_id": data["authorization_id"],
                                       "run_id": data["run_id"], "nonce_sha256": data["nonce_sha256"],
                                       "state": "CONSUMED"}]}))
    ledger.chmod(0o600)
    data[field] = wrong_value
    record.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="consumed exact one-run approval"):
        evidence_coverage._verify_authorization_record(
            record, "a" * 64, "b" * 64, "campaign-run-0001", "e" * 64, "f" * 64, ledger)


@pytest.mark.parametrize("ledger_data", [[], None, {"entries": None}])
def test_malformed_consumed_ledger_returns_value_error(tmp_path, ledger_data):
    record = tmp_path / "authorization.json"
    ledger = tmp_path / "ledger.json"
    record.write_text(json.dumps({
        "schema": "claritylink-comprehensive-owner-authorization-v1",
        "campaign_id": "CL-HONDA-RUNTIME-EVIDENCE-FOLLOWUP-20261031",
        "approval_status": "PASS", "single_run": True, "authorization_id": "auth-run-0001",
        "run_id": "campaign-run-0001", "profile_sha256": "a" * 64,
        "source_lock_sha256": "b" * 64, "evidence_matrix_sha256": "e" * 64,
        "evidence_manifest_sha256": "f" * 64, "nonce_sha256": "c" * 64,
        "review_packet_sha256": "d" * 64, "authorized_categories": ["ordinary_unprivileged_adb"],
    }))
    record.chmod(0o600)
    ledger.write_text(json.dumps(ledger_data)); ledger.chmod(0o600)
    with pytest.raises(ValueError):
        evidence_coverage._verify_authorization_record(
            record, "a" * 64, "b" * 64, "campaign-run-0001", "e" * 64, "f" * 64, ledger)


def test_existing_privileged_read_cannot_be_owner_authorized_without_new_reviewed_method(tmp_path):
    record = tmp_path / "authorization.json"
    ledger = tmp_path / "ledger.json"
    data = {"schema": "claritylink-comprehensive-owner-authorization-v1",
            "campaign_id": "CL-HONDA-RUNTIME-EVIDENCE-FOLLOWUP-20261031",
            "approval_status": "PASS", "single_run": True, "authorization_id": "auth-run-0001",
            "run_id": "campaign-run-0001", "profile_sha256": "a" * 64,
            "source_lock_sha256": "b" * 64, "evidence_matrix_sha256": "e" * 64,
            "evidence_manifest_sha256": "f" * 64, "nonce_sha256": "c" * 64,
            "review_packet_sha256": "d" * 64, "authorized_categories": ["existing_privileged_read"]}
    record.write_text(json.dumps(data)); record.chmod(0o600)
    ledger.write_text("{}"); ledger.chmod(0o600)
    with pytest.raises(ValueError, match="invalid categories"):
        evidence_coverage._verify_authorization_record(
            record, "a" * 64, "b" * 64, "campaign-run-0001", "e" * 64, "f" * 64, ledger)


def test_cli_checks_full_run_authorization_binding_without_claiming_campaign_success(tmp_path, monkeypatch, capsys):
    import hashlib
    repo = ROOT
    lock = json.loads((repo / "docs/diagnostics/comprehensive-source-lock.json").read_text())
    lock_digest = hashlib.sha256((repo / "docs/diagnostics/comprehensive-source-lock.json").read_bytes()).hexdigest()
    matrix_data = load_matrix()
    offline_row = next(row for row in matrix_data["objectives"] if row["id"] == "recovery-prerequisites")
    offline_row["actual_observation_status"] = "CONFIRMED"
    offline_row["live_authorization_status"] = "OFFLINE_ANALYSIS_REVIEWED"
    offline_row["evidence_provenance"] = ["OFFLINE_ANALYSIS_COMPLETE", "CAPTURE_INTEGRITY_VALIDATED"]
    relative = "objectives/recovery-prerequisites/recovery.txt"
    offline_row["evidence_refs"] = [{"artifact_id": "offline-review", "objective_id": offline_row["id"],
                                     "relative_path": relative, "sha256": ""}]
    matrix_file = tmp_path / "matrix.json"
    evidence_root = tmp_path / "private-evidence"
    evidence_root.mkdir(mode=0o700)
    artifact = evidence_root / relative
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"offline prerequisite review")
    artifact_digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    offline_row["evidence_refs"][0]["sha256"] = artifact_digest
    manifest = f"{artifact_digest}  {relative}\n".encode()
    (evidence_root / "sha256.txt").write_bytes(manifest)
    manifest_digest = hashlib.sha256(manifest).hexdigest()
    matrix_raw = json.dumps(matrix_data, sort_keys=True).encode()
    matrix_file.write_bytes(matrix_raw)
    record = tmp_path / "authorization.json"
    run_id, auth_id, nonce_digest = "campaign-run-0001", "auth-run-0001", "c" * 64
    record.write_text(json.dumps({
        "schema": "claritylink-comprehensive-owner-authorization-v1",
        "campaign_id": "CL-HONDA-RUNTIME-EVIDENCE-FOLLOWUP-20261031",
        "approval_status": "PASS", "single_run": True, "authorization_id": auth_id,
        "run_id": run_id, "profile_sha256": lock["profile"]["sha256"],
        "source_lock_sha256": lock_digest, "evidence_matrix_sha256": hashlib.sha256(matrix_raw).hexdigest(),
        "evidence_manifest_sha256": manifest_digest, "nonce_sha256": nonce_digest,
        "review_packet_sha256": "d" * 64, "authorized_categories": ["ordinary_unprivileged_adb"],
    }))
    record.chmod(0o600)
    ledger = tmp_path / "ledger.json"
    ledger.write_text(json.dumps({
        "schema": "claritylink-comprehensive-consumed-authorization-ledger-v1",
        "campaign_id": "CL-HONDA-RUNTIME-EVIDENCE-FOLLOWUP-20261031",
        "entries": [{"authorization_id": auth_id, "run_id": run_id,
                     "nonce_sha256": nonce_digest, "state": "CONSUMED"}],
    }))
    ledger.chmod(0o600)
    monkeypatch.setattr(sys, "argv", [
        "evidence_coverage", str(matrix_file), "--evidence-root", str(evidence_root),
        "--authorization-record", str(record), "--authorization-ledger", str(ledger),
        "--run-id", run_id,
    ])
    assert evidence_coverage.main() == 1
    output = capsys.readouterr().out
    assert '"campaign_success": false' in output
    assert "usage:" not in output


def test_malformed_required_field_is_rejected():
    matrix = load_matrix()
    matrix["objectives"][0]["required"] = "true"
    with pytest.raises(ValueError, match="required must be boolean"):
        evidence_coverage.evaluate_matrix(matrix)


def test_non_string_blocker_is_reported_instead_of_crashing():
    matrix = load_matrix()
    matrix["objectives"][0]["actual_observation_status"] = "NOT_COLLECTED"
    matrix["objectives"][0]["blocker"] = None
    result = evidence_coverage.evaluate_matrix(matrix)
    assert result["evidence_classification_complete"] is False


def test_checker_exit_code_fails_when_campaign_is_incomplete(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["evidence_coverage", str(
        ROOT / "docs" / "diagnostics" / "evidence-coverage.json")])
    assert evidence_coverage.main() == 1
    assert '"campaign_success": false' in capsys.readouterr().out


def test_structural_only_is_explicitly_not_campaign_success(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["evidence_coverage", str(
        ROOT / "docs" / "diagnostics" / "evidence-coverage.json"), "--structural-only"])
    assert evidence_coverage.main() == 0
    assert '"campaign_success": false' in capsys.readouterr().out


def test_required_unresolved_objective_prevents_campaign_success():
    matrix = load_matrix()
    verified_refs = confirm_offline_and_owner_authorized_rows(matrix)
    matrix["objectives"][0]["actual_observation_status"] = "UNRESOLVED"
    result = evidence_coverage.evaluate_matrix(matrix, verified_refs, authorized_categories(matrix))
    assert result["campaign_success"] is False


@pytest.mark.parametrize("mutation, message", [
    (lambda item: item.update(schema="wrong"), "unsupported evidence matrix schema"),
    (lambda item: item.update(safeForHonda=True), "must keep safeForHonda false"),
    (lambda item: item["objectives"][0].pop("blocker"), "lacks fields"),
])
def test_invalid_matrix_gate_fields_are_rejected(mutation, message):
    matrix = load_matrix()
    mutation(matrix)
    with pytest.raises(ValueError, match=message):
        evidence_coverage.evaluate_matrix(matrix)


def test_live_objective_cannot_be_reclassified_as_offline_only():
    matrix = load_matrix()
    objective = next(row for row in matrix["objectives"] if row["id"] == "ordinary-adb-identity")
    objective["live_approval_categories"] = ["host_private_evidence_handling"]
    objective["actual_observation_status"] = "CONFIRMED"
    objective["live_authorization_status"] = "OFFLINE_ANALYSIS_REVIEWED"
    objective["evidence_provenance"] = ["HONDA_DIRECT_OBSERVATION", "CAPTURE_INTEGRITY_VALIDATED"]
    objective["evidence_refs"] = [{"artifact_id": "forged-offline", "objective_id": objective["id"],
                                   "relative_path": f"objectives/{objective['id']}/capture.raw",
                                   "sha256": "a" * 64}]
    with pytest.raises(ValueError, match="categories differ from the fixed campaign baseline"):
        evidence_coverage.evaluate_matrix(matrix, {(objective["evidence_refs"][0]["relative_path"], "a" * 64)})


def test_offline_only_objective_can_be_confirmed_without_live_authorization():
    matrix = load_matrix()
    objective = next(row for row in matrix["objectives"] if row["id"] == "recovery-prerequisites")
    objective["actual_observation_status"] = "CONFIRMED"
    objective["live_authorization_status"] = "OFFLINE_ANALYSIS_REVIEWED"
    objective["evidence_provenance"] = ["OFFLINE_ANALYSIS_COMPLETE", "CAPTURE_INTEGRITY_VALIDATED"]
    relative = f"objectives/{objective['id']}/recovery.raw"
    digest = "b" * 64
    objective["evidence_refs"] = [{"artifact_id": "offline-review", "objective_id": objective["id"],
                                   "relative_path": relative, "sha256": digest}]
    result = evidence_coverage.evaluate_matrix(matrix, {(relative, digest)}, authorized_categories=None)
    assert result["evidence_classification_complete"] is True
    assert result["campaign_success"] is False


def test_invalid_matrix_file_returns_cli_error(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["evidence_coverage", "/missing/matrix.json"])
    with pytest.raises(SystemExit) as error:
        evidence_coverage.main()
    assert error.value.code == 2


def test_null_objective_collection_returns_structured_cli_error(tmp_path, monkeypatch):
    malformed = tmp_path / "matrix.json"
    malformed.write_text('{"schema":"claritylink-evidence-coverage-v1","objectives":null}')
    monkeypatch.setattr(sys, "argv", ["evidence_coverage", str(malformed)])
    with pytest.raises(SystemExit) as error:
        evidence_coverage.main()
    assert error.value.code == 2


def test_non_honda_lab_cannot_confirm_a_honda_runtime_objective():
    matrix = load_matrix()
    objective = matrix["objectives"][0]
    objective["actual_observation_status"] = "CONFIRMED"
    objective["evidence_provenance"] = ["NON_HONDA_LAB_RESEARCH"]
    with pytest.raises(ValueError, match="lacks qualifying confirmation provenance"):
        evidence_coverage.evaluate_matrix(matrix)


def test_baseline_objectives_cannot_be_marked_optional():
    matrix = load_matrix()
    matrix["objectives"][0]["required"] = False
    with pytest.raises(ValueError, match="cannot be marked optional"):
        evidence_coverage.evaluate_matrix(matrix)
