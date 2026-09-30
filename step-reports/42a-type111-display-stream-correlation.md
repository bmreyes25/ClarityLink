# Step 42A — Type111 display/stream correlation and Honda handoff audit

**Starting commit:** `0b3abd0`
**Mode:** offline static evidence review and existing host-test validation only.

No vehicle, ADB, staging, boot/partition changes, Honda binary execution, Type111 activation, key use, or live renderer work occurred. The preserved decompiled packages and existing static-analysis reports were inspected; no source model changes were justified.

## Findings

### 1. Type 110 and display correlation

Honda's `AirPlayCopyServerInfo` returns a dictionary whose `displays` property reaches the `/info` binary-plist serializer and HTTP send path (Step 32, confirmed by static dataflow). The property is a CFArray. Honda's stock screen-info builder creates one dictionary from one `ScreenCopyMain()` result and the property callback appends that one result once. The array container can hold multiple entries, but the stock builder is single-display.

The recovered descriptor keys are `edid`, `features`, `maxFPS`, `widthPhysical`, `heightPhysical`, `widthPixels`, `heightPixels`, and `uuid`. `features` and numeric values are opaque; the `uuid` key is inserted using a numeric CF setter. Runtime value and identity semantics are unknown.

In Setup, Type 110 reads `type=110` and a nonzero uint64 `streamConnectionID`. It uses session master material plus that identifier for screen key/IV derivation and initializes the Type 110 screen crypto state. It opens an ephemeral TCP listener and appends `{type:110,dataPort:<assigned>}` to the mutable response `streams` array. No Type 110 response UUID, display ID, or `streamConnectionID` echo is recovered. No analyzed code joins descriptor `uuid` to request `streamConnectionID`.

The listener/`dataPort` pair identifies the TCP endpoint after negotiation; it does not establish the phone's display-to-stream selection rule. **Display/stream correlation is PARTIAL overall and the UUID↔ID relation is UNKNOWN.**

### 2. Type 111 request and security status

Honda's Setup loop reads stream `type`. Type 111 takes the unsupported/default logging path, does not set an error or append a response entry, then continues. The transaction can still return success if other supported work and final `PlatformControl` succeed. This corrects older notes that used “reject” ambiguously: the entry is skipped; stock does not implement Type 111.

Honda Type 110's KDF is sufficiently recovered, but Honda never runs it for Type 111. Reusing the session master material, requiring a distinct Type 111 `streamConnectionID`, deriving separate keys, using a private CTR state, and returning a cloned descriptor with `dataPort`/`streamID=111` are MHI2-derived design candidates, not Honda facts. Honda Type 111 authentication/session reuse, exact response fields, ScreenStream compatibility and decoder reuse remain unknown.

### 3. CarPlay and ExternalDisplay service audit

The preserved manifest and decompiled-source paths show:

- CarPlay AP service: enabled/exported Binder control surface for app/session status, callbacks, phone/audio controls, touch/window state, display config and navigation/ownership operations. `setVideoPath(int)` calls AV `openVideoPath(11)` or `closeVideoPath(11)`; it is not a CarPlay frame input.
- ExternalDisplay AP service: exported Binder for LVDS operations/status, meter content/data and callbacks/diagnostics. Its interface has no `View`, `Surface`, `Bitmap`, pixel buffer, H.264, ScreenStream, socket, or file-descriptor media sink.
- ExternalDisplay output service: owns WindowManager roots used for regular Views on the external display. Although its component is marked exported, `onBind()` returns `null`. `InterfaceWindow.getMainLayout()` and `addView(int,View,boolean)` are static in-process calls, not Binder transactions.
- HondaHack: confirms a View can be inserted and an ImageView can display a bitmap when running through Xposed inside the external-display process. That is evidence of a technical render host, not a supported ClarityLink plugin or stable external API.

Neither CarPlay AP nor ExternalDisplay AP exposes a recovered authenticated Type111 receiver/session handoff. No JNI/native entry point or decoder output contract was found in the reviewed Java sources for this render path. The manifests show `exported=true` and no component-level bind permission on the named services; that does not establish runtime caller acceptance or effective permission grants. The output host requests `SYSTEM_ALERT_WINDOW` and `INTERNAL_SYSTEM_WINDOW`; exact grant/signature status was not established.

### 4. Model alignment

No code change is justified by Honda evidence. Current SETUP response augmentation deliberately models MHI2's cloned Type111 descriptor and must remain labeled prior-art-only. Its required Type111 connection ID and `dataPort`/`streamID` fields are not Honda schema. The display/session model uses UUID-shaped strings for a synthetic candidate identity; Honda's recovered descriptor's numeric `uuid` value is not proven to be that identity. Keep those independent and do not use the synthetic JSON as wire serialization.

Existing model tests already cover stock response preservation and candidate secondary-session invariants. They remain synthetic checks and do not establish iPhone acceptance. No proprietary capture was added.

## Decision gate

```text
TYPE110 DISPLAY/STREAM CORRELATION:
PARTIAL

DISPLAY DESCRIPTOR CONTAINER:
ARRAY

MULTI-DISPLAY REPRESENTABLE:
YES (array schema only; stock builder emits one)

STREAM DESCRIPTOR CONTAINER:
ARRAY

MULTI-STREAM REPRESENTABLE:
YES (response array/mixed handled types; no Type111 handler)

TYPE111 FIELD SUPPORT:
NO (type is read then skipped; no Honda Type111 schema/response)

TYPE111 SECURITY MODEL:
PARTIAL (Type110 confirmed; Type111 path absent)

TYPE111 SCREENSTREAM REUSE:
UNKNOWN

TYPE111 H264 PIPELINE REUSE:
UNKNOWN

EXTERNALDISPLAY API SURFACE:
PARTIAL (exported control Binder; no media/view handoff)

CARPLAYSERVICE API SURFACE:
PARTIAL (exported app/control Binder; no Type111/media handoff)

NON-JMCS RENDERING PATH:
UNKNOWN (ExternalDisplay host exists; supported companion attach/frame handoff not found)

NON-JMCS TYPE111 CONTROL PATH:
NO (no current Honda companion handoff found)

JMCS OR PROXY STILL REQUIRED:
YES for extending the current Honda receiver; alternatively a new independent receiver would need to be built

COMPANION TEST:
NOT READY

TYPE111 LIVE WORK:
NOT READY

LD_PRELOAD STATUS:
PARKED

BIGGEST BLOCKER:
Honda has no Type111 handler or stream/display binding, and the separate ExternalDisplay host exposes no supported frame handoff
```

## Verification

- `python3 -m unittest discover -s tests/negotiation -v`: 18 passed.
- `python3 -m unittest discover -s tests/transport -v`: 29 passed.
- `python3 -m unittest discover -s tests/carplay-session-model -v`: 12 passed.
- `python3 -m unittest discover -s src/claritylink-renderer/tests -v`: 8 passed.
- Host-only Display B integration function invoked directly: passed. Pytest is unavailable; no package was installed.
- `git diff --check`: passed before commit.

## Next action

Review the existing candidate Type111 model and split its test fixtures/provenance explicitly into Honda Type110 facts and MHI2 Type111 hypotheses. Keep the request/response profile synthetic, test stock Type110 preservation, and do not invent the missing Honda correlation or companion handoff.
