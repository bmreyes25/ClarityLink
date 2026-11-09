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
and unknown types, in their original relative order. All stock callbacks run
before Type111 preparation. A stock failure suppresses Type111 preparation.
Type111 never reaches the factory callback. It is held unless a caller supplies
the accepted auxiliary capability plus project-owned stock delegation,
validation, preparation, commit, rollback, child-withdrawal, and
parent-withdrawal callbacks. Missing stock delegation or either teardown
callback disables the Type111 route. A prepared candidate remains hidden behind
the factory fallback until private response serialization succeeds and the
integration's commit callback reports success. The adapter requires that
callback to revalidate the parent, generations, authority, and transport, but
no such Honda callback currently exists.

The adapter does not define a Honda struct layout, wire field, dataPort,
listener, key, or authentication scheme. No in-repository callback currently
proves an accepted Honda control capability or authenticated media context.
The accepted-capability handle is opaque and must be checked against its
parent/generation by the readiness callback. A candidate response must be
serialized only to an untransmitted buffer; the caller may expose that buffer
only after finalization commits. Commit must retain or transfer the candidate's
lifetime beyond consumption of the transaction cookie. The callback contract
requires capturing immutable identity and retaining any needed object
references in its transaction before returning; delayed rollback receives
only the transaction and candidate, never the caller's borrowed
request/capability pointers. This ownership is not implemented or proven by
the mock callback. The caller must leave a prepared result unchanged and
finalize it exactly once; `serialization_succeeded=0` aborts it. The adapter
captures callback function pointers and context at prepare time.
The tests exercise Type111 disabled/not-ready, partial setup rollback,
serialization failure, commit failure, duplicate identity rejection, and
teardown forwarding. The readiness callback used to reach the partial-setup
failure test is a local fault-injection stub; it produces no response and is
not evidence of authentication. No successful Type111 commit is tested. A
Type111 batch with more than one Type111 entry, an unknown stream type, or a
shared Type110/Type111 connection identity is rejected before project-owned
Type111 resources are prepared. Commit failure is required to leave the
transaction rollback-able.

## Results

**Observation:** The native focused suite passed **5 tests, 0 skipped**:
dispatcher host execution, API17 ARMv7/Thumb ELF inspection and Unicorn
execution, plus the three inherited native advertisement checks. The specific
dispatcher test passed **2 tests, 0 skipped**. The standalone production ARM
object had no unresolved symbols. Unicorn confirmed the test entry returned
to its sentinel, restored SP, preserved r4-r11, and sampled SP alignment from
each exercised callback through the harness's nested alignment helper. The
harness checks alignment across every callback path it exercises; stack depth
was not measured.
The harness verified unchanged stock handling of 100/101/110 and unknown types,
including factory-relative order. Type111 bypassed the factory path and the
adapter kept its fallback entry on disabled, not-ready, duplicate/ambiguous,
stock-failure, partial-setup, serializer-failure and commit-failure cases. This
is a pointer-identity check for the fallback entry only; the adapter cannot
inspect an opaque candidate or prove that its serializer preserved stock
entries. Candidate composition and serialization preservation remain obligations
of a future integration callback and are not tested here. No successful Type111
commit was executed. The commit-failure path was the only path that exercised
callback/context capture by changing the original ops table before finalize.
Serializer rollback's identity values came from mock-side state; they do not
prove adapter-owned transaction identity. The harness also checked invalid
request/result arrays, null opaque requests, the eight-entry bound, and
untouched results when the request count exceeds that bound. Missing capability,
factory delegate, or required teardown callbacks kept Type111 disabled. Type110
still delegated to the factory callback.

The existing Python integration regressions passed **53 tests** for stream
dispatch, the Type111 setup contract, and stock delegation. `clang --analyze`
completed without diagnostics. AddressSanitizer and UndefinedBehaviorSanitizer
passed with `ASAN_OPTIONS=detect_leaks=0`; LeakSanitizer remains unavailable in
this environment. The dispatcher performs no dynamic allocation. A first
Claude exact-scope review found stock ordering, batch validation, request
lifetime and callback-ownership defects; these were corrected. A second review
found the test harness masked possible ARM runtime references and called for
more precise response-preservation claims. The dispatcher now keeps no delayed
request copy; transaction callbacks are required by contract to own
identity/lifetime, but this ownership is not implemented by the mock. The ARM
test checks the standalone production object for unresolved symbols. The final
exact-scope Claude review approved the diff without blocking findings. The
scoped public-safety scan and `git diff --check` passed. ECC review is not
available through the current Studio tool surface, so VERIFIED publication
remains gated. The branch is still WIP_UNVERIFIED; latest published SHA was
`44f659e78c351235487cbfb3f6ae4f57c36b7956`.

**Conclusion:** The compiled project-owned adapter has a verified offline
Type110-preserving dispatch and fail-closed Type111 contract. The caller must
hold candidate serialization privately until commit succeeds; the adapter
does not itself control transmission. It is not
connected to Honda `jmcs`; there is no validated Control SETUP capability
handle, receiver-owned Type111 authority, listener or transport callback in
this build. No iPhone negotiation or vehicle behavior is proved.

**Next action:** finish exact-scope independent review and required publication
checks. Keep Type111 disabled until the accepted Honda capability and
authenticated media context are established. This adapter remains an offline
project-owned executable, not a Honda `jmcs` patch or receiver integration.

## Closeout

No vehicle, startup configuration, receiver binary, or private firmware was
modified. CL-54B Control SETUP remains a separate WIP_UNVERIFIED dependency
because the required ECC review is outstanding; this task is based only on the
published native advertisement checkpoint PR #153.
