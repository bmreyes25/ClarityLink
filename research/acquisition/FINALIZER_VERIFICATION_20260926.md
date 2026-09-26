# FAT32 finalizer recovery verification

The selected storage data passed USB SHA-256 verification, and eight labeled runtime states were captured on the Mac. USB removal during runtime staging interrupted finalization. The surviving staging files were preserved under the new forensic sibling's metadata directory; no original backup or completed raw chunk was overwritten or removed.

A retry completed the runtime copy but rejected macOS's paired `._runtime` AppleDouble metadata file on FAT32. The finalizer now accepts only recognized, paired AppleDouble metadata at approved top-level names and retains its bytes in the checksum inventory. Unrecognized top-level files still abort. A published runtime directory can be resumed only when its exact payload file set and SHA-256 hashes match the reviewed Mac source. Mismatched, extra, or symlinked data aborts without overwriting the existing copy. New runtime payload copies use content-only copying to avoid unnecessary file metadata sidecars.

## Evidence

User journey: finalize the reviewed USB sibling after a safe, interrupted runtime-copy retry, while preserving existing backups and refusing ambiguous data.

| Guarantee | Evidence |
|---|---|
| Valid paired AppleDouble metadata is retained and hashed | `test_appledouble_metadata_is_retained` |
| A verified runtime copy resumes without rewriting its payload | `test_resumes_verified_runtime_without_overwrite` |
| Changed runtime bytes abort without overwriting them | `test_changed_existing_runtime_aborts_without_overwrite` |
| Extra runtime payload files abort | `test_unexpected_existing_runtime_aborts` |
| Unrecognized top-level metadata still aborts | `test_invalid_appledouble_header_is_rejected` |
| Existing source-hash, state, identity, manifest, and display guards remain | The original seven finalizer tests |

Command: `python3 -m unittest discover -s research/acquisition -p test_finalize_on_mac.py`.

RED: 12 tests executed; two failures and two errors reproduced the unsupported resume/metadata behavior. Checkpoint: `65fe681` on `main`.

GREEN: the same 12 tests passed after the minimal fix. Checkpoint: `51d1d56` on `main`. Standard-library `trace` measured **83.3% line coverage of `finalize_on_mac.py`** (186 executable lines). This is finalizer module coverage, not project-wide or branch coverage. These tests use temporary synthetic files; production archive content and real USB integrity were separately checked against hashes and tar structures.

The repaired finalizer completed against the real USB: eight runtime states passed its declared command checks and all retained files were hashed/verified. A separate output review found 158 optional `/proc` maps/fd reads reporting permission denied even though legacy ADB returned transport exit zero. Their output is preserved, and a hashed availability review explicitly records them as unavailable. No security settings were weakened. A successful runtime snapshot does not reveal iAP2 packet contents or establish CarPlay decoder coexistence.

Build/types/lint: no separate package build applies to this helper; Python executed the modified code in the test target and real finalization. Diff and staged-content review are required before the sanitized GitHub checkpoint. All raw images, private outputs, coverage artifacts, manifests, and captures remain excluded from Git.
