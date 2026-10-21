# CL-R12-F API 17 Runtime Recovery Receipt

Status: **runtime smoke verified; CL-R12-C/D/E acceptance incomplete**  
Workflow: [run 39547044685](https://github.com/bmreyes25/ClarityLink/actions/runs/39547044685)  
Tested pull request merge commit: `4a630cf7c78187a67d93ccbc3f91fa0ead181b20`  
PR head at execution: `4b34bd4a59fe86ccca9d5a1e2fb99eef9842fbf0`

## Runtime

| Field | Observed value |
| --- | --- |
| Host | GitHub-hosted Ubuntu 22.04 x86-64 runner |
| CPU / acceleration | x86_64, KVM present and accessible (`/dev/kvm`); 4 vCPUs, 15 GiB RAM |
| Guest | Android API 17, release 4.2.2, ABI x86 |
| Guest fingerprint | `generic_x86/google_sdk_x86/generic_x86:4.2.2/JB_MR1.1/eng.wdu.20191212.215704:eng/test-keys` |
| Emulator package | 37.2.12 |
| Graphics | `swiftshader_indirect` (headless) |
| ADB serial | `emulator-5554` (the sole expected emulator) |
| Platform package | `platforms;android-17` revision 3 |
| System image | `system-images;android-17;default;x86` revision 7 |
| Platform `android.jar` SHA-256 | `2bf921bd5efce9e4b2966a394d8b9b332e548fa30df7a158e029c7fa823dd799` |
| System image `system.img` SHA-256 | `7e6f66f39d7541d8bc5821ce3e178a229955d5e378db27adc74514ee15633db4` |
| Emulator executable SHA-256 | `27e9a8cbd545529ba2c1aca973e5bc060f50b36a68d2c03296b0162291a16b83` |
| Freshly built APK SHA-256 | `94bc9812fc79d72003e89790f979c656fb81cfffbf2cd25f3f5ab68de731c5b4` |
| Source tree SHA-256 | `f2acbf3cf4c60e1cf3c8cec71e436449bbf51bbcff4853326386188cbee06dec` |

The workflow queried SDK Manager and confirmed the API 17 platform and authentic x86 image packages were available. It installed these packages into a per-workspace SDK, built a fresh APK, booted the emulator, verified API/release/ABI and boot completion, installed the APK, started `MessengerFrameLabActivity`, checked its explicit test result, collected logcat, and stopped the emulator. The official archive download fallback was not needed.

## Executed synthetic scenario

`CL_R12_API17_RUNTIME_PASS` and `CL_R12_MESSENGER_LAB_PASS` were emitted by the running activity. Logcat confirms Type111 fixture decode, MemoryFile/PFD/Messenger transfer, exact pixel-byte identity, one-frame queue bound, stale generation rejection, navigation withdrawal, interrupt preemption, synthetic host-process crash and recovery, and Type110 isolation. The workflow's cleanup step killed the guest; the emulator action also completed its teardown.

This demonstrates that GitHub-hosted Linux x86-64 is a working API 17 runtime path. It does **not** constitute the full original CL-R12-C lifecycle suite, the CL-R12-E fault matrix, or the required 30-second and 10-minute performance acceptance. No original-versus-optimized A/B run or stage-specific instrumentation was completed. The optimized local source remains preserved in its original dirty worktree and has not been verified or published.

## CI and review notes

The API 17 runtime workflow passed. CodeQL passed for this tested source revision. The Offline CI workflow failed only at the repository hygiene job because its tracked CL-R0 review-scope digests for `.gitignore`, `tests/display/test_cl_imp_04_ipc_contract.py`, and `tools/build_cl_imp_03_apks.sh` are stale relative to this candidate. The existing review-scope record was not rewritten to imply review. Independent ECC review was unavailable; no approval is claimed. The PR remains draft and unmerged.

No Honda data, vehicle, ADB device, firmware, APK, CAN, or live iPhone was used. `safeForHonda() == false`.
