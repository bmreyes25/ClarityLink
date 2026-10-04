# 43T1-R3C expanded — extension-path matrix and dynamic closure

**Method:** offline `xcrun llvm-objdump -p -T -R -d` on 350 preserved `*.so` files under `extracted/system-vendor/system` plus `bin/jmcs` (351 ELF paths). Examined `DT_NEEDED`, dynamic symbols, dynamic relocations (`.rel.plt`/`.rel.dyn`), `.plt/.got` implications, and init/fini tags. Matched exact AirPlay/serializer names as well as relevant generic screen/proxy symbols; generic `Setup`/`Finalize` hits in codecs/DRM are unrelated and were excluded by component and caller evidence. `.symtab`/focused disassembly and prior hash-matched static traces supply internal-call context. This bounds the conclusion to preserved ELF files; missing launch files and unrecovered modules remain `UNKNOWN`.

`HONDA_CONFIRMED`: `jmcs` needs `libcarplay_proxy.so` and has six proxy registration `R_ARM_JUMP_SLOT` relocations. Proxy exports its callback registration and stream trampoline symbols. None of the 351 dynamic-symbol/relocation inventories showed an **undefined import/relocation** for `AirPlayReceiverSessionSetup/Start/TearDown/PlatformControl/SetDelegate`, `_requestSendPlistResponse`, `CFPropertyListCreateData`, or `ScreenStreamCreate` crossing another Honda module. `jmcs` itself defines some `ScreenStream*` dynamic symbols; definition visibility is not an actual caller/import edge. The direct same-ELF Setup/serializer path remains as traced by [R3A](43t1-r3a-setup-path-seam-map.md). Proxy `DT_FINI_ARRAY` is generic unload cleanup, not a session callback. Generic `dlopen/dlsym` sites map to SQLite/dynamic support, with no evidenced CarPlay plugin name or Setup lookup ([load sites](jmcs-dlopen-sites.md)).

| Candidate | Honda evidence | Session-addressable? | Additive? | Existing path? | Setup context? | Response mutable? | Project-owned cleanup possible? | Runtime write needed? | Persistent change needed? | Type110 risk | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Direct `jmcs` Setup/serializer | Direct same-ELF call, R3A | Internal pointer only | No project entry | Yes internally | Yes internally | Yes internally | No project callback | Yes to enter | Unknown | High | REJECT_RUNTIME_WRITE |
| Proxy screen registration | PLT import + one copied 24-byte table, [audit](43t1-r3c-libcarplay-proxy-interface-audit.md) | No | No, second rejected | Yes | No | No | No | Replacement/write | Binary or preload | High | REJECT_REPLACEMENT |
| Proxy `ScreenStream*` exports | Stock media trampoline | Stream object only | No project observer | Yes | No | No | No correlated entry | Interposition/load | Likely | High | REJECT_TOO_LATE |
| Honda session delegate/finalizer | 44-byte record; R3B | Raw pointer internal | No | Yes | Internal only | No at finalizer | No child lookup | Replacement | Unknown | High | REJECT_REPLACEMENT |
| Global destroyed event | 24-byte slot, interface+event | No | No | Yes | No | No | No | Replacement | Unknown | High | REJECT_NO_SESSION_ID |
| Generic `ScreenRegister` | Appends screen objects, stock reads index 0 | Screen object, not session | Array yes; integration no | Yes | No | No | No | New entry needs load/write | Unknown | Medium/high | REJECT_NO_SETUP_CONTEXT |
| Device-manager attach registry | Generic ranked handlers, no Setup edge | Device scope | Unknown | Yes | No | No | No | New entry/load | Unknown | High | REJECT_NO_SETUP_CONTEXT |
| CarPlay Binder callbacks | App/service status APIs | No native key | Possibly app-status listeners only | Yes | No | No | App resources only | New app entry | APK/install likely | Medium | REJECT_TOO_LATE |
| Independent external process | No preserved bridge to native Setup | No | Could be project-local | No Honda entry | No | No | Own process resources only | Entry missing | Likely | Unknown | REJECT_NO_EVIDENCE |
| `LD_PRELOAD`/dependency wrapper | Generic API-17 linker support; no existing Honda launch slot | No paired key | No | No evidenced project load | Could only if hooks | No safe interposition | No paired Honda cleanup | Startup modification | Yes | High | REJECT_PERSISTENCE |

**Loader classification:** stock proxy `DT_NEEDED` is `SUPPORTED_EXISTING_LOAD_PATH` **for Honda's existing proxy only**, not ClarityLink. Adding/replacing a dependency is `BINARY_REPLACEMENT_REQUIRED`; modifying init/service environment is `PERSISTENT_CONFIG_CHANGE_REQUIRED`; a supported optional CarPlay plugin directory/property/constructor-loaded project library is `NO_EVIDENCE`; actual `jmcs` launch environment is `UNKNOWN` because its service stanza is absent ([startup audit](jmcs-startup-path.md)). No install procedure follows from this classification.

**Best remaining internal object:** `AirPlayReceiverSessionRef` is present at Honda Setup and finalization, but inaccessible as a non-replacement observer and has no established generation semantics. It is a diagnostic research lead, not `BEST_CANDIDATE` for implementation. Every candidate fails at least one model gate, so `DO_NOT_BUILD_MODEL`.

## Registration semantics cross-check

The strongest candidates were checked against all ten session-registration questions. In this table, “scope” answers whether lifetime is one session or global; “early” means before Setup response serialization; “process” means relevance to the native session owner.

| Candidate | Multiple consumers? | Additive? | Caller context stored? | Stable session ID? | Unregister/cleanup? | Scope | Type110 Honda-only? | Early? | Distinguish 110/111? | Correct process? |
|---|---|---|---|---|---|---|---|---|---|---|
| Proxy screen record | No | No | Six callbacks, no refcon | No | Whole global unregister | Global | No if replaced | No Setup context | No evidenced type dispatch | Yes, `jmcs` linked |
| Session delegate | One Honda record | No | Honda context | Raw pointer only, reuse unknown | Honda finalizer | One session | No if replaced | Honda internal only | Honda stock parser skips 111 | Yes |
| Global destroyed event | One slot | No | Interface callback record | No | Global setter/replacement | Global | No if replaced | No | No session/type | Yes, then app event |
| `ScreenRegister` | Multiple objects | Data append only | Screen object | No AirPlay ID | Object release only | Process-wide | Stock main selected | Before `/info`, not Setup response | Stock builder main-only | Yes |
| Binder app callback | Possibly multiple UI consumers (`UNKNOWN`) | `UNKNOWN` service semantics | Binder object | No native AirPlay ID | Unregister names exist | App/service scope | Yes for native stock if passive | No native pre-serializer edge | No Setup stream record | Different process boundary |
| Device-manager attach | Multiple ranked candidates | Registration is not simultaneous fan-out | Device context | No AirPlay ID | Device lifecycle only | Device/interface scope | Winner may change | Not Setup response | No recovered 111 dispatch | `jmcs`, wrong layer |
