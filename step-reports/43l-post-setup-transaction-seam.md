# Step 43L — Honda post-Setup child transaction seam

**Base:** `6f6c9f25a3ef51f3653c266ab12aba836406dd21`; clean `main`. **Binary:** `extracted/system/system/bin/jmcs`, SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232` (MATCH). **Scope:** offline static analysis and synthetic model only.

## Findings

The Setup call at `0x28af72` receives session `[r10+0xf4]`, parsed request `[sp+0x1c]`, and response output `[sp+0x54]`. Return is saved at `0x28af76`, status stored at `[sp+0x50]`, compared at `0x28af7a`, and nonzero branches to `0x28b040`. Success executes Honda session metadata writes through `CFObjectSetProperty` at `0x28afae`. The exact Setup response is staged at `0x28afb6` and passed to `_requestSendPlistResponse` at `0x28afba`. The call returns at `0x28afbe`; caller releases parsed request at `0x28b048` and response at `0x28b052`. The outer handler later calls `HTTPConnectionSendResponse` at `0x28b790`.

| Address | Instruction/call | Values and failure edge | Transaction implication |
|---|---|---|---|
| `0x28af6a–0x28af72` | stage args; Setup BL | session/request/responseOut; status returned in `r0` | no project work before stock success |
| `0x28af76–0x28af7c` | save and branch | nonzero → stock error path `0x28b040` | gate prepare on zero status |
| `0x28af7e–0x28afae` | stock success context | updates session fields and calls `CFObjectSetProperty` | response still live; preserve stock order |
| `0x28afb2–0x28afba` | stage serializer inputs; BL | same response object; status-out pointer | narrow structural pre-serialization interval |
| `0x28afbe–0x28b052` | save result/common cleanup | response and request released | graph lifetime ends after sync helper |
| `0x28b790` | HTTP response commit | later state-machine action | network failure is later than graph lifetime |

Serializer `_requestSendPlistResponse` at `0x289f60` synchronously calls `CFPropertyListCreateData(format=0xc8)`. Null data and header-init errors go to HTTP 500; successful data yields byte pointer/length and is passed to `HTTPMessageSetBody` (`0x29d01c`). That helper performs a visible `memmove` when needed and sets headers. Body setter status maps to 200/500, is written through the response status pointer, and temporary CFData is released before return. The same response object is read, not consumed or mutated. `HTTPConnectionSendResponse` occurs later. Exact serializer return/body semantics are PROVEN; successful return is local body readiness, not peer receipt.

The response and streams array are built with mutable Honda CF-style objects; Type110 entry/container ownership is in 43G ledger. Public array wrappers include count, indexed get, create-copy, create-mutable, append; no public single-item array remove/set wrapper was found. Dictionary Get/Set/Remove wrappers exist. Best static design candidate: prepare everything first and make append the last graph mutation; never assume selective remove rollback. Request scanning by `streams[*].type == 111` is read-only and position-independent. Search by type for stock Type110; no fixed index contract.

The narrowest prepare candidate is after the successful status branch and stock metadata update, before `0x28afba`. It is not PROVEN safe to call arbitrary helper code there: no proof of callout, concurrency, or race behavior exists. Listener ordering is a project contract only: bind/listen succeeds → read assigned port → write `dataPort`; synthetic listener only.

| Failure | Response graph | Project response/resources | Required model action | Type110 |
|---|---|---|---|---|
| Stock Setup nonzero | Honda stock error path | no prepare | no project action | untouched by project |
| No Type111 request | unmodified stock object | none | no project action | preserved |
| Read/descriptor validation failure | unmodified stock object | none/temporary only | abort project and continue stock | preserved |
| Prepare/listener/port failure | unmodified stock object | partial resources possible | rollback project only | preserved |
| Entry construction failure | unmodified stock object | project temporaries | rollback project only | preserved |
| Append uncertainty/failure | append wrapper has no visible status; array mutation can be partial | project entry may be attached | UNKNOWN; therefore append last and avoid risky writes | stock untouched except potential extra entry |
| Plist serialization failure | augmented graph remains local until caller release | project resource cleanup linkage not tied to serializer | rollback project only; Honda HTTP error path | Type110 remains in graph, delivery not guaranteed |
| Body installation failure | HTTP message may be partially updated; CF graph is not consumed | project state cleanup follows same gap | rollback project only; Honda error path | graph retained until caller release |
| HTTP commit/write failure after serializer success | response graph already released | later project cleanup via PlatformFinalize model | parent-session cleanup if integration linkage exists | Honda path handles send failure |

Pre-serializer augmentation failures can fail open to stock by never touching stock graph until all project resources and entry objects are ready. If serializer itself fails, stock response cannot be assumed delivered; fail-open is therefore conditional. Preserve the exact response object and append only a project-owned entry; replacing the whole response is unproven and unnecessary. Response-ready candidate is successful serializer return at `0x28afbe`; commit candidate is immediately after it, once local body installation succeeds. This is earlier than HTTP send scheduling and does not claim phone receipt. Parent cleanup is statically present through connection close/session finalize, and project PlatformFinalize is implemented offline, but direct Honda subscription of the project child is not yet proven. Thus ACTIVE commit remains CANDIDATE.

## Decision gate

| Gate | Result |
|---|---|
| Mutation window | PROVEN structurally; callout safety PARTIAL |
| Prepare point | CANDIDATE |
| Type111 detection | READY (generic read-only rule only) |
| DataPort ordering | READY as project contract, not Honda behavior |
| Response mutation | PARTIAL (construction APIs proven; caller-side callout safety not proven) |
| Rollback | LAST_MUTATION |
| Serialization | PROVEN |
| Response-ready | PARTIAL (`0x28afbe`, local only) |
| Child commit | CANDIDATE (`0x28afbe` after status success) |
| Failure policy | CONDITIONAL fail-open before serializer |
| Identity | PRESERVE_SAME_OBJECT |
| Type110 | SEARCH_BY_TYPE |
| Transaction model | PARTIAL |
| Project lifecycle | OFFLINE_IMPLEMENTATION_READY |
| JMCS integration design | NOT READY |
| JMCS implementation/live/Type111/ExternalDisplay | NOT READY |
| LD_PRELOAD | PARKED |

The synthetic 43K lifecycle tests cover prepare/ready/commit/rollback, stale generations, duplicate cleanup, and finalization. Negotiation tests cover stock Setup failure, optional no-Type111 path, prepare/merge failure, request immutability, Type110/audio preservation, and stock status preservation. They do not establish Honda runtime callout safety or serializer-failure-to-project-cleanup wiring. Full requested test suite: 266 passed, 4 skipped; locator smoke 3 passed; simulator JS checks passed; capture-backed scripts skipped for unavailable private fixtures. `git diff --check` is recorded in final verification.

## Neutral static function inventory

Addresses below are ELF VAs. All six disassemble as Thumb; entries are unambiguous ELF function symbols. `llvm-nm -D` found none in `.dynsym`; ordinary direct calls are internal BLs, not PLT calls. Direct call counts exclude callback-table/indirect callers. First 16 bytes are recorded as instruction fingerprints (objdump display order).

| Function | VA / symbol | Direct callers found | First 16 bytes/instructions | Notes |
|---|---|---:|---|---|
| `_connectionHandleMessage` | `0x28a30c`, local `.symtab` `t` | indirect server callback; no direct BL caller in scan | `f8df 248c; e92d 4ff0; 4604; f8df 0488; f5ad 7d2d` | broad handler; callback entry and boundary are named |
| `AirPlayReceiverSessionSetup` | `0x2854e0`, global `.symtab` `T` | 1 (`0x28af72`) | `e92d 4ff0; b08b; 4605; 4688` | local, not dynamically exported |
| `_requestSendPlistResponse` | `0x289f60`, local `.symtab` `t` | 4 (`0x28a19c`, `0x28afba`, `0x28b42a`, `0x28b54e`) | `b5f7; 461e; f8d0 50c8; 4614` | not dynamically exported |
| `HTTPConnectionSendResponse` | `0x29dbe4`, global `.symtab` `T` | 1 (`0x28b790`) | `e92d 43f7; f500 5a02; 4605; 460e` | not dynamically exported |
| `AirPlayReceiverSessionPlatformControl` | `0x28cd88`, global `.symtab` `T` | 4 (`0x285364`, `0x28624a`, `0x286ab2`, `0x2875be`) | `e92d 4ff0; b08b; 4605; 4688` | indirect callback use not counted |
| `AirPlayReceiverSessionPlatformFinalize` | `0x28cd60`, global `.symtab` `T` | 1 (`0x284d3e`) | `b570; 4604; 460d; b08c` | finalizer call site |

Inventory limitations: no runtime addresses, loaded image bases, hookability, callout safety, or deployment conclusions are inferred. The caller count for `_connectionHandleMessage` is intentionally reported as indirect/unknown rather than treating callback registration as a direct BL.

**Biggest blocker:** the earliest serializer-success commit event is visible, but no Honda-safe project callout or direct project-child cleanup subscription to Honda finalization is proven.

**Next action:** Step 43M — inventory neutral static facts for the six candidate Honda functions, then design the smallest integration surface without implementing it.
