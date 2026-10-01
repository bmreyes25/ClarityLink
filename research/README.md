# Research index

`research/` preserves detailed Honda reverse-engineering evidence and model work. These notes are not all equally authoritative: check each document's evidence labels and the root [EVIDENCE_INDEX.md](../EVIDENCE_INDEX.md) before relying on a claim.

## Main areas

- [`carplay/`](carplay/) — Honda `/info`, Setup, Type110/Type111, crypto, and transport analysis.
- [`display/`](display/) — cluster geometry and renderer/ExternalDisplay integration.
- [`architecture/`](architecture/) — target architecture, contracts, and alternatives.
- [`hondahack/`](hondahack/) — HondaHack display-path research and interface notes.
- [`simulator/`](simulator/) — offline digital twin, protocol models, and simulator research.
- [`runtime/`](runtime/) and [`deployment/`](deployment/) — offline process/runtime and load-seam findings; live readiness remains separately gated.
- [`evidence/`](evidence/) and [`inventory/`](inventory/) — artifact provenance and inventory.
- [`adr/`](adr/) and [`plans/`](plans/) — decisions and bounded research plans.
- [`captures/`](captures/) — local/ignored capture policy and limited tracked planning/status notes. Private capture payloads are not part of this public index and must not be committed.

## Curated starting points

- [Source-pinned CarPlay AltScreen prior art](../docs/research/carplay-altscreen-prior-art.md)
- [Honda-specific Type111 research plan](../docs/research/honda-type111-research-plan.md)
- [Honda `/info` capabilities](carplay/honda-info-capabilities.md)
- [Type111 display/stream correlation](carplay/type111-display-stream-correlation.md)
- [Type111 unknown register](carplay/type111-unknown-register.md)
- [Host H.264 decode stage](simulator/host-h264-decode-stage.md)
- [Visual cluster twin](simulator/visual-cluster-demo.md)

Use [step-reports/](../step-reports/README.md) for the chronological record of milestones. Root status files remain the current source of truth.
