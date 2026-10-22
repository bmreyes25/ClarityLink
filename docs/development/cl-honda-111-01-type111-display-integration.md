# CL-HONDA-111-01 / M5 — Type111 decoded frames to the Navigation pane (synthetic integration)

Offline, synthetic, fail-closed. `safeForHonda() == false`; `safe_for_honda() == False`. No protected media, no Honda IPC, no factory window attachment, no Honda call of any kind. A pass here proves ClarityLink's own contract. It does not show that the Honda receiver can admit a Type111 child or that any frame can reach the cluster; those are the two critical gates in the [boundaries document](cl-honda-111-01-critical-boundaries.md).

## 1. Intended pipeline, and what exists

```
iPhone
 → authenticated Honda CarPlay parent session                [factory-owned; NOT reachable]
 → accepted Type111 child stream                              ← type111_child_authority.py (synthetic)
 → authorized receiver-owned protected-media handling         [Type111 KDF/profile UNKNOWN; fail-closed]
 → VideoConfig                                                 ← Type111PaneBridge.video_config
 → Android-compatible H.264 decode                             [existing host decode; API17 decode not exercised here]
 → generation-bound decoded-frame handoff                      ← DecodedFrame + bounded FrameGate
 → controlled Navigation-pane renderer                         ← NavigationPaneHost lease/present
 → Honda external-display main-content hierarchy               [UNSUPPORTED: no admission contract]
 → instrument-cluster Navigation presentation                  [UNKNOWN: aperture, warning precedence]

iPhone → Honda Type110 receiver → original decoder/video output → Display 0
          (untouched; a Type111 failure has no path to it)
```

Bracketed stages cannot be advanced offline. Everything else is implemented and tested with generated data.

## 2. What was added

| Module | Role | Tests |
|---|---|---|
| `src/claritylink-negotiation/type111_child_authority.py` | `ParentAuthority` (synthetic only; a non-synthetic parent cannot be built), single-use `ChildGrant`, `Type111Child` with contained once-only end callbacks. Parent loss revokes the child permanently. Holds no key, secret, socket or Type110 reference. | `tests/negotiation/test_cl_honda_111_01_child_authority.py` (30) |
| `src/claritylink-honda/navigation_pane_host.py` | Simulated host that tracks display, window layers (reusing `SimulatedClusterHost`), selectable page, viewport and a revocable generation-bound **lease**. Page and interrupt can be driven from reported (content class, status) observations with staleness expiry. Defines the `DecodedFrame` contract and `fit_rect`. | `tests/honda/test_cl_honda_111_01_navigation_pane_host.py` (63) |
| `src/claritylink-honda/type111_pane_bridge.py` | `Type111PaneBridge` ties child → lease → bounded frame queue; `FactorySinkAdapter` always denies. | `tests/integration/test_cl_honda_111_01_type111_pane_bridge.py` (46) |

Reused unchanged: `FrameGate`, `SimulatedClusterHost`, `FactoryIntegrationContract`. No existing source file was modified. The jmcs `Receiver` and the CL-AUTH-01 grants (PR #78, unmerged) are not touched; this work is compatible with them but does not depend on them.

**Totals:** 139 new tests. Full offline suite on this branch: 1665 passed, 29 skipped, 0 failed (baseline on the same `origin/main`: 1526 passed, 29 skipped). Mutation checks: removing the frame release, the parent-loss revoke, or the lease-to-withdrawn transition was caught by the tests. Removing the host's withdrawal of its underlying main layer survived at first because only lease validity was asserted; new assertions (`main_layer_occupied`, one case per revocation cause) now catch it. Disabling the host's own stale-generation guard is an equivalent mutant: the reused `SimulatedClusterHost` enforces the same rule, so behaviour is unchanged.

## 3. The decoded-frame handoff (E1)

`DecodedFrame` carries what the brief lists and is aligned field by field with the merged API17 `DecodedFrame.java` so both sides accept and reject the same frames.

| Brief item | Python field | API17 analogue | Note |
|---|---|---|---|
| Stream identity | `stream_connection_id` | none (single stream) | Needed for the dual-generation model. |
| Session generation | `parent_generation` | none | Parent authority generation. |
| Stream generation | `stream_generation` | `generation` | Child generation, lifetime-monotonic on the parent. |
| VideoConfig generation | `config_generation` | none | New config opens a new generation; older frames refused. |
| Frame number | `sequence` | none | Strictly increasing per child; duplicates and replays refused. |
| Timestamp | `presentation_time_ns` | `presentationTimeNs` | Non-negative. |
| Width, height | `width`, `height` | `width`, `height` | ≤ 3840 × 2160, same as Java. |
| Format and stride | `pixel_format` (`RGBA_8888`, byte order R,G,B,A), `stride` | CPU RGBA, `rowStride` | Stride ≥ width × 4. |
| Crop and transform | `crop` (left, top, right, bottom; right/bottom exclusive), `rotation` (0/90/180/270) | `cropLeft…cropBottom`, `rotationDegrees` | Same convention. |
| Pixel or Surface ownership | `storage` (`CPU_BUFFER` accepted, `SURFACE` refused) | CPU only; Surface contract-only | No Surface owner exists. |
| Size bound | ≤ 4 MiB including padding | `MAX_RGBA_BYTES` | Same limit. |
| Resource release | `release_callback`, called **exactly once** on every path | none | Dropped, rejected, withdrawn or presented. |
| Error and stale behaviour | typed `OfferStatus` / `PresentStatus` reasons | exceptions | The Java side throws; a mapping is in the Codex handoff. |

## 4. Four generations, kept apart

| Generation | Owner | Bumped by | Used to reject |
|---|---|---|---|
| Parent | `ParentAuthority` | construction only | A child or frame from another parent session |
| Stream | `ParentAuthority` | every `grant_child` | A frame from an earlier child with the same stream id |
| Config | bridge | every changed `video_config` | Frames decoded under an older configuration |
| Pane | bridge, floor set by the host | every `start`/`resume` attempt | A revoked lease being revived; presentation after any hazard |

A fresh bridge asks the host for `next_generation()` rather than guessing; a dead lease cannot be revived whatever number it carries.

## 5. The campaign's fifteen scenarios

| # | Brief scenario | Test (in `test_cl_honda_111_01_type111_pane_bridge.py` unless noted) |
|---|---|---|
| 1 | Type110 remains active | `test_type110_stays_active_across_the_whole_type111_lifecycle` |
| 2 | Type111 begins | `test_type111_begins_config_is_accepted_and_frames_reach_the_pane` |
| 3 | VideoConfig accepted | same test; `test_video_config_replacement_opens_a_new_generation_and_drops_old_frames`; invalid configs parametrized |
| 4 | Decoded frames reach the simulated pane | same test as 2 |
| 5 | Pane deselection withdraws Type111 | `test_page_deselect_withdraws_and_reselect_requires_explicit_fresh_ownership` |
| 6 | Reselection needs valid current ownership | same test; `test_resume_while_page_is_still_away_stays_pending_without_a_lease`; `test_starting_while_the_page_is_not_selected_waits_without_presenting` |
| 7 | A warning withdraws content | `test_warning_withdraws_and_clearing_it_never_revives_old_content`; `test_start_is_refused_by_the_host_during_an_active_warning` |
| 8 | Warning removal does not revive stale content | same test; host-level `test_interrupt_revokes_and_clearing_it_does_not_restore_content` |
| 9 | Host loss clears retained resources | `test_host_loss_releases_every_retained_frame_and_recovery_needs_fresh_generation` |
| 10 | Host recovery needs a fresh generation | same test; `test_invalid_display_never_rebuilds_the_pane` |
| 11 | Type111 disconnect leaves Type110 working | `test_type111_disconnect_leaves_type110_working_and_restores_factory_content` |
| 12 | Parent loss revokes all children | `test_parent_loss_revokes_child_pane_and_blocks_restart`; authority-level `test_parent_loss_revokes_child_and_runs_callbacks_once` |
| 13 | Invalid geometry rejects presentation | `test_missing_or_inadmissible_viewport_blocks_the_pane`; `test_changing_the_viewport_mid_stream_withdraws_instead_of_stretching`; host-level viewport tests |
| 14 | Malformed frames reject | `test_malformed_or_foreign_frames_are_rejected_and_released` (9 cases) plus host-level malformed cases |
| 15 | Full teardown restores simulated factory content | `test_full_teardown_restores_simulated_factory_content_and_leaves_nothing_behind` |

Additional properties covered: bounded queue with latest-wins presentation; duplicate and out-of-order frames; no Type110 identity frames in the pane; exactly-once release across mixed outcomes; 60 failure cycles with no leaked lease, child or frame; a three-producer concurrency smoke while the pane is repeatedly revoked; the real-facing sink always denying; the page and interrupt layers driven end to end from reported selection.

**Type110 isolation by construction.** `Type111PaneBridge` has no parameter, attribute or call that names the center-display stream. The tests hold their own Type110 `FrameGate` beside it and assert its generation, closed state and counters are identical before and after every Type111 event. This demonstrates independence of the *models*, not of the real factory path.

## 6. What this does not show

- **Factory admission.** `FactorySinkAdapter` is the only real-facing path and it always denies. `FactoryIntegrationContract.submit_frame_to_factory` still returns `SAFE_FOR_HONDA_FALSE`.
- **API17 behaviour.** These are host-side Python tests. No API17 build, emulator or hardware run is claimed. The merged API17 renderer was inspected, not modified.
- **Performance.** No latency, frame-rate, memory or thermal figure is produced or claimed.
- **Security.** The Type111 KDF, profile and VideoConfig protection are unknown. The bridge carries decoded frames only; it never sees ciphertext or keys. The parent is synthetic and cannot be made non-synthetic.
- **Warning precedence and geometry.** Modelled, not proven. A viewport can only be synthetic or (reserved) authoritative; no authoritative measurement exists.
- **The host's view of the page.** `observe_contents` models a host that reports its selection. Whether the real host exposes such a report to any authorized caller is part of Gate 2.

## 7. Codex dependency

The concrete renderer tasks this exposes (a page-and-warning callback on `Display1OutputBackend.Host`, a lease-shaped detach, status-code mapping, and three-generation mapping) are specified in the [Codex handoff](cl-honda-111-01-codex-handoff.md). No overlapping Android file was edited here.
