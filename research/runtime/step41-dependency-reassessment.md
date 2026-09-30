# Step 41A — dependency reassessment

Scope: offline against commit `28b9bd4` and the existing verified Honda acquisition. No vehicle, ADB, `su`, process access, execution of archived binaries, or patching.

| Runtime fact Step 41 requested | Classification | Evidence / consequence |
|---|---|---|
| `jmcs` mapping base and current ASLR layout | SELF-OBSERVABLE IN JMCS | A library running in jmcs can try `dladdr` on a known jmcs code pointer or parse `/proc/self/maps`. AOSP API-17 exact support remains to be verified against the pinned source. No external maps prerequisite follows. |
| Hook target runtime address | SELF-OBSERVABLE IN JMCS | Derive from load bias + verified ELF VA after proving module identity and mapping. Existing static call-site plan is internal Thumb call interception, not symbol lookup. |
| ELF segment/file-offset relation | STATICALLY RECOVERABLE | `research/carplay/honda-runtime-addressing.md` gives the ET_DYN formula and checked mapping requirements. |
| Exact current page size / mapping protections | SELF-OBSERVABLE IN JMCS; otherwise EXTERNALLY PRIVILEGED ONLY | `sysconf`/self maps may suffice in-process; historical external captures do not establish current values. Not needed for descriptor-only offline model. |
| Other process's maps/smaps/fd | NO LONGER REQUIRED for self-location; EXTERNALLY PRIVILEGED ONLY for external diagnostics | Step 40E4 documents denial to UID 2000 and no justifiable root path. |
| Thread rendezvous / patch safety | NO LONGER REQUIRED for this milestone | Call-site interception still has live concurrency and executable-memory requirements; self-location does not solve them. |
| How to load ClarityLink in jmcs | UNKNOWN | Separate deployment question; no proven stock plugin/JNI/preload seam yet. |
| Active proxy callback contents/session state | UNKNOWN | Module presence and static callback table do not prove runtime callback ownership. |

Conclusion: external privileged maps are not an architectural prerequisite if code is already loaded in jmcs. This does not establish a Honda load seam or live hook readiness. Step 40F is obsolete as a prerequisite and may remain an optional diagnostic only.
