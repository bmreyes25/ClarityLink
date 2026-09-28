# ClarityLink evidence index — Step 5B

| Question | Current evidence | Verdict | Next proof |
|---|---|---|---|
| Android output/display devices | Live `dumpsys display`, SurfaceFlinger, `/proc/fb`, and framebuffer sysfs; `research/cluster-display-diagnostics.md` | Display 0 built-in and display 1 HDMI, both 800×480; `fb1`/`tegradc.1` likely matches display 1; BPP reports 0 | Display-1 `screencap` frame after user shows factory Navigation and replies READY |
| Cluster navigation target rectangle | `research/navigation-safe-area.md`; Honda Hack 584×215 local layout; saved display evidence | Unknown; Honda Hack layout coordinates do not prove factory bounds | Identify Honda destination path first; then read-only frame and matched normal Navigation state/photo if needed |
| Honda render path | Honda Hack cast observation; `research/native/receiver-multidisplay-audit.md`; cluster helpers and `disp_com_meter` | HDMI reaches cluster; exact underlying composition surface and native destination remain uncertain | Bounded Honda service/component inspection and runtime display inventory |
| iAP2 Identification contents | `research/iap2-identification.md`; static `jmcs` symbols/strings; `j_config.xml` | Exact packet unknown; no raw exchange captured | Exhaust read-only USB-monitor/logging options; analyzer only if needed after evidence review |
| CarPlay display/session descriptor | `jmcs` `mc_carplay_app_init`, `screen_add_props`, `AirPlayReceiverSessionScreen_CopyDisplaysInfo` | One configured primary screen; UUID and serialized descriptor unknown | Observe existing logs/transport read-only; identify endpoints before any later passive capture |
| Decoder concurrency | `step-reports/03-second-decoder.md` and local fixtures | Two NVIDIA decoders produced 28/30 frames with CarPlay disconnected; host replay passed | No repeat unless new receiver/session evidence requires it |
| Forensic acquisition | Acquisition reports; original and working copies outside Git | Verified local acquisition; immutable original preserved | None |
| Step 5B ADB availability | Read-only ADB diagnostics on 2026-09-28 | Connected at `192.168.86.102:5555`; root confirmed; no writes; frame pending READY | User shows normal factory Navigation with casting off and replies READY |

Raw firmware, forensic images, phone/location data, and raw capture artifacts are not committed. The project scope and current evidence gate are summarized in `PROJECT_STATE.md` and `step-reports/05b-display-diagnostics.md`.
