# P2-C5 — read-only Display 1 diagnostic plan

**Starting HEAD:** `90c3dd948b107d24b5d09d19f37e25db990ddd4d`. Scope is offline package review only. No Honda ADB, display operation, install, execution, root, iPhone session, or stock modification occurred.

## Three separate questions

| Capability | Finding | What evidence can establish |
|---|---|---|
| `DISPLAY_ENUMERATION` | Existing public API17 `DisplayManager.getDisplays()` is available to an Android app with an app `Context`. Existing saved Honda diagnostics already record HDMI Display 1 as 800×480. A non-app shell can request the display service's read-only dump using the existing `dumpsys display` utility under shell UID 2000, subject to the target's actual `DUMP` grant. | Logical display IDs, device names/types and reported logical modes, as emitted by the service dump. The plan preserves raw output; it does not infer more from an undocumented format. |
| `WINDOW_ADMISSION` | Not established by enumeration, `dumpsys`, or shell identity. A separately hosted Android `Presentation` requires a framework app context and an admitted window token. An uninstalled native process has neither through the public Java app path. | Requires a separate admitted app or an OEM external-window contract. The P2-C5 collector deliberately does not attempt it. |
| `VISIBLE_RENDERING` | Not established by either preceding item. Honda physical transform, safe rectangle and warning priority remain unknown. | Requires a separate authorized and safety-reviewed rendering experiment after admission and geometry gates pass. |

API17 exposes `DisplayManager.getDisplays()` through framework APIs and its presentation category filters by display type. The P2-C2 emulator verified the app-side route only on AOSP API17. In AOSP API17, the shell package receives `android.permission.DUMP` and the platform permission mapping assigns DUMP to shell; this supports using the existing `dumpsys` utility without installing ClarityLink. Honda's exact framework and effective shell grant are not independently reverified in this milestone, so the proposed collector checks `id` and stops unless it sees `uid=2000(shell)`. See [API17 DisplayManager](https://android.googlesource.com/platform/frameworks/base/+/android-4.2.2_r1/core/java/android/hardware/display/DisplayManager.java), [Shell manifest](https://android.googlesource.com/platform/frameworks/base/+/android-4.2.2_r1/packages/Shell/AndroidManifest.xml), [AOSP platform permission mapping](https://android.googlesource.com/platform/frameworks/base/+/android-4.2.2_r1/data/etc/platform.xml), and the local [API17 audit](43t1-r4c-api17-external-display-static-review.md).

The `dumpsys` route is a shell diagnostic invocation, not proof that a temporary ClarityLink binary has general Binder/service authority. A native executable running as shell has shell UID/SELinux restrictions; Dalvik `DisplayManager` calls rely on application `Context` and framework IPC setup. Neither provides a free-standing Activity/window token. The ADB shell can launch built-in `dumpsys` without installing ClarityLink; the collector does not add a new binary to the vehicle or invoke hidden Binder transactions.

## Frozen offline package

| Artifact | SHA256 |
|---|---|
| `tools/p2c5_display1_collector.py` | `39278b643a58b7f32bf624a6fa04ea90da26f7dedbb91518ed05c24a4576383b` |
| `research/architecture/p2c5-display1-manifest.json` | `e136920f4eb61afbacebc998f2efce72c006fca1fd963ff349049d047daed8a4` |
| `research/architecture/p2c5-display-observation.schema.json` | `e5f5764912f04dc208599697de92aab27e169bf59c6f38c2c567ea4ee81ab814` |

The collector is default-disabled. Default invocation exits `NOT_AUTHORIZED`; `--dry-run` prints the exact fixed sequence and performs zero ADB calls. It verifies exact source and manifest hashes, one operator-supplied serial (no `auto`), exact target state, `uid=2000(shell)`, API level 17, and nonempty display dump. It writes raw output only beneath ignored `build/p2c5/evidence/` (directory 0700, file 0600). It uses at most 12 seconds per command, no retries/fallbacks, and stops on any unexpected status, stderr, timeout, empty output, identity mismatch, or contract/hash mismatch. The fake-ADB tests never contact a device.

Proposed commands, after fresh single-use authorization only:

```text
adb -s <EXACT_CONFIRMED_SERIAL> get-state
adb -s <EXACT_CONFIRMED_SERIAL> shell id
adb -s <EXACT_CONFIRMED_SERIAL> shell getprop ro.build.version.sdk
adb -s <EXACT_CONFIRMED_SERIAL> shell dumpsys display
```

There is no ADB inventory scan, connect/disconnect, server restart, `service call`, `dumpsys window`, SurfaceFlinger query, screenshot, display setting, or write. The serial must be freshly operator-confirmed and identical in every command. Shell UID mismatch ends before the display query. The collector does not test physical device system version; the data is raw and should be reviewed with the frozen manifest.

## What this observation can change

A fresh dump could correct the current logical display identity/mode if the saved observation is stale or if the target differs. It cannot change the `PRESENTATION` decision: API17 public API semantics and the existing Honda service's process ownership are already established, while normal-app caller admission is not. It cannot prove a visible window, safe geometry, warning precedence, or no-APK app context. If it confirms the saved 800×480 HDMI Display 1, it adds freshness only; window/rendering decisions remain blocked.

## Future single-use authorization proposal

This wording is preparation only and is **not** the present authorization:

> I authorize one read-only P2-C5 inspection using collector SHA256 `39278b643a58b7f32bf624a6fa04ea90da26f7dedbb91518ed05c24a4576383b`, manifest SHA256 `e136920f4eb61afbacebc998f2efce72c006fca1fd963ff349049d047daed8a4`, and observation schema SHA256 `e5f5764912f04dc208599697de92aab27e169bf59c6f38c2c567ea4ee81ab814`. The only target commands are the four exact commands listed in the plan with my freshly confirmed exact serial. I confirm the vehicle is stationary and safely parked, center display booted, cluster normal, no unexpected warnings, an exclusive ADB window, and no manual ADB commands during the inspection. Timeout is 12 seconds per command, retries zero. Stop on any timeout, mismatch, unexpected output, stderr, or transport anomaly. This authorizes display enumeration diagnostics only; it does not authorize window admission, visible rendering, installation, configuration changes, cleanup, or process execution.

Before any future invocation, repeat local package/hash verification and dry-run; obtain all fresh confirmations in that future turn. A user message must separately provide the exact serial and single-use authorization. No command remains authorized by this document after that run.

## Decision

**`READ_ONLY_PACKAGE_REVIEW_READY`** — a narrow shell-owned read-only inventory query can be prepared without APK installation and a default-disabled, hash-bound collector is covered by fake-ADB tests. This means package review only; no Honda run occurred. The ClarityLink no-APK native process itself still has no public `Presentation` context/token, and enumeration does not admit or render a window.
