# Honda PlatformControl and SessionControl — Step 34

**Binary:** acquired `extracted/system/system/bin/jmcs`, SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`. Offline static symbol/string review only.

## Recovered symbols and boundary

The binary has symbols for `AirPlayReceiverSessionPlatformControl` (`0x28cd88`), `AirPlayReceiverSessionControl` (`0x287264`), `AirPlayReceiverSessionMakeModeStateFromDictionary`, `_AirPlayHandleSessionControl`, and platform/session callback functions. Strings show commands or helper routines for session UI requests, Siri action, mode changes, night mode, limited UI, and `AirPlayReceiverSessionSendCommand`.

These establish that Honda has a generic platform/session control path and mode/UI-related facilities. They do not establish which incoming command maps to a function, ownership semantics, state transitions, or any relation to a Type-111 stream. No Honda control transaction has been reconstructed at dictionary-field level in Step 34.

## Exact AltScreen/UI search

An exact ELF string scan found no `suggestUI`, `showUI`, `stopUI`, `ViewArea`, `altScreen`, `viewAreas`, `maps:/car`, or `instrumentcluster` literal. This does not rule out dynamically generated keys, encoded strings, generic dictionary parsing, or control semantics hidden behind a generic callback. The symbol `AirPlayReceiverSessionPlatformControl` alone is not evidence Honda implements those messages.

| Honda question | Step 34 status |
|---|---|
| PlatformControl function exists | Confirmed |
| SessionControl function exists | Confirmed |
| Mode parsing exists | Confirmed by symbol |
| Generic UI/mode operations exist | Confirmed by symbols/strings |
| Honda `suggestUI` / `showUI` / `stopUI` semantics | Unknown; matching strings absent |
| ViewArea / cluster URL support | Unknown; matching strings absent |
| UI control required before Type 111 | Unknown for Honda |

MHI2 current source separately wraps PlatformControl and SessionControl, forwards most commands to stock, and has a project-specific `suggestUI` behavior once its private Type-111 session exists. That target-specific behavior supports treating transport lifetime and UI ownership as separate concerns, not copying its control implementation to Honda. See pinned [MHI2 hook map](https://github.com/harman-f/mhi2_altscreen_carplay/blob/c2f811f1a5c84dae3a62f4cf9b4a9e65fc3f7b3c/docs/research/MU1440_GEN2_HOOK_MAP.md).
