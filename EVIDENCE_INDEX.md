# Evidence index — Step 5

| Question | Current evidence | Verdict | Next proof |
|---|---|---|---|
| OEM cluster Navigation safe rectangle | `research/navigation-safe-area.md`; Step 2 viewport profile; copied Navigation/ExternalDisplay ODEX/config; cluster helpers and `disp_com_meter` | Unknown; cast-layout local rectangle is not an OEM bound | Paired HDMI frame + perpendicular photo on factory Navigation page; if externally composed, native read-only meter page/framebuffer metadata |
| iAP2 Identification contents | `research/iap2-identification.md`; `jmcs` symbols/strings; `j_config.xml` | Exact packet unknown; iAP2 ID and AirPlay screen-info paths are distinct | Passive USB pcapng from before reconnect through Identification Accepted |
| CarPlay display/session descriptor | `jmcs` `mc_carplay_app_init`, `screen_add_props`, `AirPlayReceiverSessionScreen_CopyDisplaysInfo`; focused audit | One configured primary screen; UUID and serialized descriptor unknown | Capture screen-info response on observed transport after initial setup |
| Decoder concurrency | `step-reports/03-second-decoder.md`, prior local decoder reports/fixtures | Two NVIDIA decoders produced 28/30 frames with CarPlay disconnected; host software replay passed | Separate reviewed active-CarPlay coexistence test; not part of Step 5 |
| Verified acquisition | `/Users/bmreyes24/ClarityLab/forensic/CLARITY_FORENSIC_20260925_211500_COMPLETE_WORKING` | Complete verified local copy; never modified by Step 5 | None |

The pristine backup and forensic original are immutable and outside Git. The index contains no raw binary payloads or packet dump.
