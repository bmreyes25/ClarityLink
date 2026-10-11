# R7E5C: Android 4.2.2 legacy ADB sync mode semantics

## Finding

**Classification:** `DOCUMENTED_ANDROID_4_2_2_AOSP_BEHAVIOR`.

The Android Open Source Project tag `android-4.2.2_r1.2` sends the host file's `st_mode` in the legacy ADB sync `SEND` request. Its receiver masks the incoming mode to `0777`, copies user permission bits into group bits, then copies the now-updated group bits into other bits. The second OR reads the result of the first OR. This makes the transform deterministic and idempotent for modes such as `0444` and `0555`.

**Observed result:** `HONDA_OBSERVED_MATCHES_AOSP_LEGACY_ADB_MODE_TRANSFORM`. In the reviewed A0-W run, the host marker was a regular 58-byte file at mode `0644`; the remote regular file was 58 bytes, owned by `shell:shell`, non-executable, and reported as `0666`. This is exactly the transform's prediction. The result supports behavioral agreement only; it does **not** establish the Honda's ADB daemon binary identity or prove that the target runs unmodified AOSP.

## Source review

The links below are pinned to the requested AOSP tag.

- [`adb/file_sync_client.c`](https://android.googlesource.com/platform/system/core/+/android-4.2.2_r1.2/adb/file_sync_client.c): `do_sync_push` calls `stat` on a local file and passes `st.st_mode` to `sync_send` (around lines 746–799). `sync_send` formats the mode in decimal and appends it to the remote path; it sends the path and mode as the `ID_SEND` request before transferring the data (around lines 301–418).
- [`adb/file_sync_service.c`](https://android.googlesource.com/platform/system/core/+/android-4.2.2_r1.2/adb/file_sync_service.c): `do_send` parses the mode, applies `mode &= 0777`, unlinks the exact destination, then applies the two sequential OR operations before passing the resulting mode to `handle_send_file` (around lines 280–320). `handle_send_file` creates the file using that mode (around lines 155–220).
- [`adb/adb.c`](https://android.googlesource.com/platform/system/core/+/android-4.2.2_r1.2/adb/adb.c): under `#if !ADB_HOST`, `adb_main` calls `umask(000)` (around line 1098). This daemon-side mask does not remove bits from the transformed file mode.

The exact tag's `file_sync_service.c` has no `fs_config`, `is_on_system`, or `/system`-specific mode override in this `do_send` path. Thus `/data/local/tmp` is not subject to a system-path override here; more precisely, this tagged legacy implementation has no such override in the path at all. This is a source-level observation, not a claim about Honda vendor modifications.

## Mode transform

Pure host-side model, implemented as `legacy_adb_v1_remote_mode` in [the R7E5C collector](../../tools/r7e5c_a0wr_collector.py):

```python
mode &= 0o777
mode |= (mode >> 3) & 0o070
mode |= (mode >> 3) & 0o007
return mode
```

The first OR copies owner read/write/execute bits into the corresponding group positions. The second OR shifts the **updated** mode, so those newly populated group bits now occupy the other positions; it then copies them into other. For example, `0644` becomes `0664` after the first OR, then `0666` after the second.

| Host mode | After group OR | Predicted remote mode | Reason |
|---:|---:|---:|---|
| `0644` | `0664` | `0666` | owner read is propagated through group to other; owner write is propagated likewise |
| `0755` | `0775` | `0777` | owner `rwx` is propagated through group to other |
| `0444` | `0444` | `0444` | read bits are already present in all classes |
| `0555` | `0555` | `0555` | read/execute bits are already present in all classes |
| `0600` | `0660` | `0666` | owner read/write propagates to group, then other |
| `0700` | `0770` | `0777` | owner `rwx` propagates to group, then other |

The model deliberately does not claim that every ADB implementation, vendor fork, filesystem, or mount has these semantics. It models the reviewed legacy AOSP implementation.

## A0-W interpretation

The old collector's `A0W_STOP_CONDITION` remains the historical decision and its private raw evidence is unchanged. The reviewed interpretation is `A0W_STOP_CAUSE_EXPECTATION_MISMATCH_LEGACY_ADB_MODE_SEMANTICS`:

- The single push succeeded.
- A regular remote file was observed with exact size 58, owner/group `shell:shell`, and no execute bit.
- Remote `0666` exactly matches the reviewed AOSP transform from host `0644`.
- Exact `/system/bin/rm` succeeded and final exact-path absence was confirmed.
- MD5 was **not** run by that collector version, so transport MD5 remains unproven for that run.

Therefore the transfer and cleanup path was observed, but `A0W_FULL_ACCEPTANCE_NOT_YET_CLOSED`. No target-side chmod is needed: `NO_TARGET_CHMOD_REQUIRED`.

## Future staging policy

- Revised inert A0-WR marker: host staging `0444`, expected remote `0444`. It stays regular, readable, non-writable, and non-executable. Removing a file depends on write/execute permission on its parent directory, not on the marker's own write bit.
- Future Test A executable staging: keep the canonical `claritylink-target-diag` bytes and SHA-256 unchanged. Later create an ignored staging copy with the same bytes/hash and local mode `0555`; the reviewed transform predicts remote `0555` (readable, executable, not writable), with no target chmod. This is planning only. `TEST_A_LEGACY_ADB_STAGING_MODE = 0555`; Test A remains separately unauthorized.

## Reproduction

The pure transform cases, including the two idempotent safer modes, are covered by `tests/tools/test_r7e5c_a0wr_collector.py`. The revised collector also computes its expected remote mode from the exact host staging mode and still requires exact metadata, required MD5, exact cleanup, and exact absence; it does not accept a loose set of permissions.
