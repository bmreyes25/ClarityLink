# Large Java classes (inventory only)

Files of 450 lines or more on `main`, by line count. This is an inventory for a future, separate maintenance task. **No refactor is proposed as part of the recovery work**: a broad rewrite of the compositor or the lab Activity would put the verified API17 lifecycle evidence at risk and is justified only when it directly fixes a defect.

| Lines | File | What makes it hard to review |
|---|---|---|
| 3455 | `android/cl-imp-03-app/java/org/claritylink/android/ClarityLinkDisplayActivity.java` | The lab Activity: orchestration of discovery, IPC clients, Type111 control, geometry, warnings and many scenario drivers in one class. |
| 2720 | `android/cl-imp-03-app/java/org/claritylink/android/CompositorService.java` | The compositor: ownership registry, Binder admission, teardown, View closing and writer threads in one service. |
| 1367 | `android/r7c2-test/java/org/claritylink/android/R7C2RuntimeActivity.java` | A runtime test Activity with many scenarios. |
| 823 | `android/cl-imp-03-app/java/org/claritylink/android/MessengerFramePerformanceActivity.java` | The CL-R12 harness: scheduler, sender, reply handling, profiling and result reporting. |
| 514 | `android/cl-imp-03-app/java/org/claritylink/android/FrameLabSink.java` | Single class with several responsibilities; see the file. |
| 511 | `src/claritylink-renderer/android-api17/ClarityLinkContentView.java` | Single class with several responsibilities; see the file. |
| 478 | `android/cl-imp-03-app/java/org/claritylink/android/FrameIpcClient.java` | Single class with several responsibilities; see the file. |
| 471 | `android/cl-imp-03-app/java/org/claritylink/android/FrameViewSink.java` | Single class with several responsibilities; see the file. |
| 469 | `android/cl-imp-03-app/java/org/claritylink/android/MessengerFrameLabActivity.java` | Single class with several responsibilities; see the file. |
| 460 | `android/cl-imp-03-app/java/org/claritylink/android/CompositorOwnerDeathTestService.java` | Single class with several responsibilities; see the file. |
| 456 | `android/cl-imp-03-app/java/org/claritylink/android/Type110LabProbeOwnership.java` | Single class with several responsibilities; see the file. |

## If this is ever tackled

- Do it per class, behind the existing API17 acceptance cases, with the lifecycle and teardown tests passing before and after.
- Extract by responsibility (for example scenario drivers out of the Activity) rather than by size, and never change message formats, generation rules, or ownership checks in the same change.
- Treat `CompositorService` and `ClarityLinkDisplayActivity` as the highest-risk files: they hold the ownership, authorization and teardown logic that CL-R4 accepted.
