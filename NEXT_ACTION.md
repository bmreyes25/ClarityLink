# Next action

**Offline: recover the exact Honda phone-facing screen descriptor and SETUP response serializer/ABI.** Compare `AirPlayReceiverSessionScreen_CopyDisplaysInfo`, `AirPlayReceiverSessionSetup`, and `AirPlayReceiverSessionScreen_Setup` against the pinned Type-111 prior art. Establish whether a narrow wrapper can preserve Honda's primary response while advertising a second descriptor and returning its own dataPort. Do not implement an interposer or run a vehicle experiment yet. Keep ptrace paused; it is fallback research only.

See `research/carplay/honda-altscreen-gap-analysis.md`, `research/carplay/claritylink-display-b-architecture.md`, and `step-reports/25-altscreen-prior-art-pivot.md`.
