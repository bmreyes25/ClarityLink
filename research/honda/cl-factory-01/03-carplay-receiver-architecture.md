# CL-FACTORY-01 / M2 — Factory CarPlay receiver architecture (sanitized)

Status: IN PROGRESS. Evidence OBSERVED_STATIC (deodexed Java + prior native). Offline only. `safeForHonda() == false`.
Exact proprietary identifiers (class/method/AIDL names) are retained in private evidence; this report is role-level.

## Process / ownership map
```mermaid
flowchart LR
  Phone[iPhone CarPlay session] -. USB/iAP2 + native session .-> Native[native carplay receiver\n(carplay_main / jmcs / libcarplay_proxy)]
  UI[CarPlay UI app\n(thin Activity shell)] --- RecvSvc[CarPlay receiver service\n(process: carplayapservice)]
  RecvSvc -->|System.loadLibrary carplay_main| Native
  RecvSvc <-->|AIDL callback surface| NaviSvc[Navigation AP service]
  RecvSvc <-->|AIDL| ExtDispSvc[ExternalDisplay AP service]
  RecvSvc <-->|AIDL| SysDisp[System Display service]
  RecvSvc <-->|AIDL| Others[Phone / Siri / Tel / HFT / Vehicle-info / MediaCore / SteeringSwitch]
  Native -. screen-stream callback (singleton registration, per CL-SYS-01A) .-> Decode[native decode / frame]
  Decode -. no proven admission edge .-> D0[factory display path]
```

## Findings (OBSERVED_STATIC)
- **The CarPlay UI app is a thin shell** (a single foreground Activity + a few Binder classes). It is not the
  receiver.
- **The receiver is a long-running service** in its own process that **loads a native library** (`carplay_main`)
  and exposes a broad **AIDL callback surface**. The Java layer is a service/API wrapper; the actual CarPlay
  session, stream, and decode are **native** (ties to the `jmcs`/`libcarplay_proxy` boundary established in
  CL-SYS-01A). The receiver declares **no Java `native` methods** itself — the native library hosts the receiver.
- **The receiver is Java-coupled, via AIDL, to the Navigation service, the ExternalDisplay service, and a System
  Display service**, plus phone/Siri/telephony/hands-free/vehicle-info/media/steering-switch callback families.
  This AIDL fabric — not a public display API — is the factory's internal integration surface for routing
  CarPlay/navigation content and display state.
- **Display routing is state-based**, using a display-status/mode machine with named states for the CarPlay
  surface, the Display-Audio home, a limited-operation (smartphone) mode, and "other". Routing is by display
  identifier.
- **No Java-layer secondary-stream ("Type111"/second-screen) construct was found.** The Java layer shows only
  single-display status routing; any second-stream capability would have to exist in the native receiver, where
  CL-SYS-01A observed a **singleton** screen-registration table (a duplicate registration is rejected). This is
  **"no supported secondary-stream handoff found"**, not a proof that one is impossible.

## Implications for Type111 feasibility (bounded)
- A genuine second CarPlay stream is not exposed by the Java receiver API, and the native screen-registration seen
  so far is singleton. The remaining places a second stream could be admitted are native (not yet fully traced) or
  via the AIDL display/navigation services (whose admission contract is unknown and defaults to deny in our
  fail-closed model). Authentication ownership for any second stream remains unestablished (no bypass).

## Unknowns → next (M3)
- The Navigation ↔ ExternalDisplay ↔ cluster path (what data crosses, who owns Display 1) — see report 04/06/07.
- Native second-stream capability in `carplay_main` (bounded Ghidra follow-up).
- Whether the display-status machine ever admits non-factory content (fail-closed assumption until proven).
