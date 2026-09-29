# AltScreen transport and presentation are separate planes

**Step 34 synthesis, 2026-09-29.** Honda ELF findings are authoritative for Honda. MHI2 source is receiver-specific prior art.

## Plane A: transport and media security

```text
SETUP streams[i]
  -> type dispatch
  -> streamConnectionID (uint64)
  -> session master key + ID -> stock screen key/IV derivation
  -> per-screen security setup
  -> TCP listener -> dataPort response
  -> accepted socket / screen framing / decrypted video
```

Honda confirms the Type-110 chain through listener allocation and `{type:110,dataPort}` response. Its `streamConnectionID` is a screen-crypto input. The direct derivation function does not receive the stream type or display UUID. Honda's Type-111 branch currently rejects before this setup. Whether an independent Type-111 stream can reuse the same stock derivation primitive is structurally plausible and demonstrated by MHI2, but remains unproven for Honda until the receiver contract and hook seam are validated.

## Plane B: display capability and UI ownership

```text
/info displays[] / display UUID and capability
  -> phone's display and UI selection
  -> suggestUI / showUI / stopUI / ViewArea control
  -> presentation ownership on the display
```

Honda's `/info` path sends a main display descriptor. Its setup trace has not shown that UUID in the stream crypto flow. The Honda ELF exposes PlatformControl and SessionControl symbols, but static string inspection finds no `suggestUI`, `showUI`, `stopUI`, `ViewArea`, `altScreen`, or instrument-cluster URL literals. Their Honda command handling and semantics remain unknown.

## Architecture consequence

Do not make `display UUID == streamConnectionID` or a direct mapping a prerequisite for modeling the media socket. A per-stream listener can bind the accepted connection to a transport generation by the port it arrived on. Display UUID/capability still matters to phone-side negotiation and presentation ownership, so it remains a control-plane question.

MHI2's pinned source treats stream/session generation separately from `suggestUI`, `showUI` and ViewArea transitions. It reports the Type-111 receiver remains established across ordinary provider/UI changes and treats a changed stream connection/session generation as a transport boundary. Thus Type-111 transport-before-UI-selection is YES in that implementation's model, but this is not a Honda guarantee.

## First transport-only success criterion

For a future explicitly reviewed experiment: retain the stock primary CarPlay session; make a controlled `/info` display advertisement; observe a phone Type-111 request; preserve unknown request fields; return a Type-111 response with a reachable listener port; accept the phone connection; and identify/decrypt a valid screen header or VideoConfig using the established stock session context. Rendering, Apple Maps UI ownership, and ViewArea can follow in a separate phase.

**Step 34 status:** offline schema/crypto model partly ready; no live transport test is ready. Honda Type-111 semantics, delegate/error behavior, receiver-version compatibility, and Honda screen-record framing remain blockers.
