# Next action

**Offline: recover the `/info` request handler and its response builder.** Step 31 established that `AirPlayCopyServerInfo` is not dynsym-exported and no imports were found among the 45 mapped shared libraries; the known plist/send path serializes SETUP output only. Follow `/info` string xrefs through HTTP dispatch and determine whether an internal wrapper or alternate builder supplies the response. Keep display-stream correlation and Type-111 behavior unresolved; do not implement negotiation or schedule a live experiment yet. See `step-reports/31-airplay-server-info-consumer.md`.

See step-reports/30-close-altscreen-negotiation-loop.md, research/carplay/honda-server-info.md, and research/carplay/honda-display-capability-send-path.md. Keep vehicle, ADB, ptrace, patches, and hooks out of scope. The unrelated mc_dev_attach registry remains fallback-only.
