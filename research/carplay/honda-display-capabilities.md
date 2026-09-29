# Honda display capability advertisement

## Evidence result

Honda's `AirPlayReceiverSessionScreen_CopyDisplaysInfo` (`jmcs` VA `0x287ae1`) returns one mutable dictionary for `ScreenCopyMain()` / registry element zero. Recovered keys are `edid`, `features`, `maxFPS`, `widthPhysical`, `heightPhysical`, `widthPixels`, `heightPixels`, and `uuid`; see [`honda-copy-displays-info.md`](honda-copy-displays-info.md) for insertion/source details. This proves a local display-info builder, not a phone-facing capability advertisement.

Search of the available `jmcs` generated disassembly found the function definition but no direct call instruction referring to it. Indirect callback/function-pointer use cannot be excluded. The output's enclosing response, caller, phase, serializer, transport, and send path are unresolved. It is not proven to participate in SETUP, Identification, ReceiverInfo, or feature discovery. The Honda receiver initializes one `gMainScreen`; this builder does not enumerate a screen registry or construct an array.

## Findings

| Question | Finding |
|---|---|
| Container | One returned dictionary locally; parent/wire container unknown |
| Display list | None constructed in this function |
| Feature field | `features` numeric value derived through masks; bit meanings unknown |
| Primary UUID | `uuid` key receives a numeric property value; source/lifetime/session scope unknown |
| Secondary/AltScreen field | None identified in this function; receiver-wide absence not established |
| Phone-facing | Unknown; no caller/serializer edge recovered |
| Extensible | Not demonstrated; dictionary is mutable, but no parent display collection is established |

Honda capability signaling therefore cannot yet be augmented at a known phone-facing boundary. Preserve stock primary values if a future caller/send edge is recovered. See `honda-identification-receiver-info.md`, `honda-alt-screen-gating.md`, and `step-reports/28-honda-display-capability-gating.md`.
