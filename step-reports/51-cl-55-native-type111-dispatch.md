# CL-55 Native Type111 Dispatcher — Offline Prototype

Date: 2026-11-08
Task: `CL-55-NATIVE-TYPE111-DISPATCH`
Branch: `codex/cl-55-native-type111-dispatch`
Base: PR #153, `a945ead50a4cd36db935b7865a15bb88f6a1f56f`

## Question and method

**Question:** Can a target-compiled project-owned dispatcher preserve the
factory 100/101/110 and unknown-stream handler route while keeping Type111 on
a separate, disabled-by-default transaction path?

**Method:** Add a small C adapter with opaque request/session/connection
handles, a bounded ordered request batch, readiness and resource callbacks,
two-phase response commit, rollback, and child/parent teardown forwarding.
Exercise it through a host harness and the existing NDK/Unicorn ARMv7 path.

## Evidence and implementation boundary

The factory callback is passed the original request view for 100, 101, 110,
and unknown types, in input order. Type111 never reaches that callback. It is
held unless a caller supplies the accepted auxiliary capability plus
project-owned stock delegation, validation, preparation, commit, rollback,
child-withdrawal, and parent-withdrawal callbacks. Missing stock delegation or
either teardown callback disables the Type111 route. A prepared candidate
remains hidden behind the factory
fallback until private response serialization succeeds and the project commit
callback revalidates the parent, generations, authority, and transport.

The adapter does not define a Honda struct layout, wire field, dataPort,
listener, key, or authentication scheme. No in-repository callback currently
proves an accepted Honda control capability or authenticated media context.
The accepted-capability handle is opaque and must be checked against its
parent/generation by the readiness callback. A candidate response must be
serialized only to an untransmitted buffer; the caller may expose that buffer
only after finalization commits. Commit must retain or transfer the candidate's
lifetime beyond consumption of the transaction cookie. Rollback clears all
borrowed request/resource handles held by the adapter.
The tests exercise Type111 disabled/not-ready, partial setup rollback,
serialization failure, commit failure, duplicate identity rejection, and
teardown forwarding. The readiness callback used to reach the partial-setup
failure test is a local fault-injection stub; it produces no response and is
not evidence of authentication. No successful Type111 commit is tested.

## Results

**Observation:** The new host and required ARMv7 suite passed **5 tests, 0
skipped**: dispatcher host execution, API17 ARMv7/Thumb ELF inspection and
Unicorn execution, plus the three inherited native advertisement checks.
Unicorn confirmed the test entry returned to its sentinel, restored SP,
preserved r4-r11, and called the readiness/factory callbacks with aligned
stacks. The harness verified factory callback order for 100/101/110 and an
unknown type; Type111 bypassed the factory path and preserved the fallback
response on missing authority, unready transport, duplicate identity, partial
setup, serializer failure, and commit failure. No successful Type111 commit
was executed. Serializer and commit failures cleared the candidate, transaction,
and borrowed request handle before returning. A missing capability handle,
factory delegate, or either required teardown callback kept Type111 disabled;
Type110 still delegated to the stock callback.

The existing Python integration regressions passed **53 tests** for stream
dispatch, the Type111 setup contract, and stock delegation. `clang --analyze`
completed without diagnostics. AddressSanitizer and UndefinedBehaviorSanitizer
completed with `ASAN_OPTIONS=detect_leaks=0`; LeakSanitizer reported that leak
detection is unsupported on this platform. The dispatcher itself performs no
dynamic allocation. Scoped public-safety and whitespace checks passed. Five
WIP checkpoints were published through the Studio publisher and their remote
SHAs verified; the latest at report preparation is
`fa3dcc869f70e7292bf91b00970e3f7453fa6978`. Exact-scope independent review and
a VERIFIED PR preflight remain pending.

**Conclusion:** The compiled project-owned adapter has a verified offline
Type110-preserving dispatch and fail-closed Type111 contract. The caller must
hold candidate serialization privately until commit succeeds; the adapter
does not itself control transmission. It is not
connected to Honda `jmcs`; there is no validated Control SETUP capability
handle, receiver-owned Type111 authority, listener or transport callback in
this build. No iPhone negotiation or vehicle behavior is proved.

**Next action:** complete exact-scope engineering/security review, then use the
VERIFIED publisher and create a stacked PR against the reviewed dependency
branch if review passes. Keep Type111 disabled until the capability and
authenticated media context are established.

## Closeout

No vehicle, startup configuration, receiver binary, or private firmware was
modified. The CL-54B Control SETUP branch remains separate and unreviewed; this
task is based only on the published native advertisement checkpoint PR #153.
