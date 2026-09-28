# ClarityLink evidence index — 2026-09-28

| Question | Evidence | Verdict | Remaining proof |
|---|---|---|---|
| Android output target | Live display/sysfs/SF snapshots and screencap | Display 1 HDMI, 800×480, about 60 Hz, layer stack 1 | None for Android logical mode |
| HondaHack Screen Casting path | Targeted 7.7.7 APK decompilation plus Screen Casting snapshot | Display 0 captured at 400×240 ARGB_8888; Bitmap via shared MemoryFile/PFD; ImageView/View injected in Honda ExternalDisplay root; full-window Display 1 output | Supported ClarityLink host acquisition/lifecycle |
| Advanced Meter path | Same APK trace and state snapshots | Uses same Xposed-injected externaldisplay View host; content is meter/navigation widgets | Exact runtime child-view to layer mapping |
| Android Display 1 crop | Three SF state dumps | Full-frame 800×480 layers; no smaller Android crop observed | None for current evidence |
| Physical Navigation bounds | Paired Display 1 factory image and full-cluster photo | UNKNOWN. Photo/capture difference supports downstream composition but gives no calibrated rectangle | Physical coordinate mapping / panel transform |
| Framebuffer format | sysfs reports bpp 0 and stride 3200 | UNKNOWN; no raw framebuffer access | Driver metadata only if a later need arises |
| ClarityLink renderer prototype | src/claritylink-renderer and host tests | Synthetic 800×480 RGBA source, explicit frame contract, mock attach/submit/clear/destroy, API 17 View backend skeleton | Compile against API 17 SDK and establish real host |
| Second CarPlay display/session | research/iap2-identification.md and static jmcs model | Raw Identification/second display descriptor/UUID/role unknown | Reconstruct or passively observe protocol advertisement |
| Decoder coexistence | step-reports/03-second-decoder.md | Dual NVIDIA decode plausible; active CarPlay coexistence not established | Revisit only when a second stream/session exists |
| Live evidence availability | captures under ignored research/captures/hondahack-display-path/20260928T152742Z | Factory Navigation, Advanced Meter, Screen Casting snapshots and SHA-256 list saved locally | None for these three states |

Raw evidence, APKs, firmware, forensic images, and sensitive device identifiers are excluded from Git. Sanitized conclusions are recorded in the research and step reports.
