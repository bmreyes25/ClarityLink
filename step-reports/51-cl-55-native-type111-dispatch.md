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
project-owned validation, preparation, commit, and rollback callbacks. A
prepared candidate remains hidden behind the factory fallback until the
enclosing response serializer succeeds and the project commit callback
revalidates the parent, generations, authority, and transport.

The adapter does not define a Honda struct layout, wire field, dataPort,
listener, key, or authentication scheme. No in-repository callback currently
proves an accepted Honda control capability or authenticated media context.
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
was executed.

The existing Python integration regressions passed **53 tests** for stream
dispatch, the Type111 setup contract, and stock delegation. `clang --analyze`
completed without diagnostics. AddressSanitizer and UndefinedBehaviorSanitizer
completed with `ASAN_OPTIONS=detect_leaks=0`; LeakSanitizer reported that leak
detection is unsupported on this platform. The dispatcher itself performs no
dynamic allocation. Public-safety scan, exact-scope independent review, and
Studio publication preflight remain pending.

**Conclusion:** The compiled project-owned adapter has a verified offline
Type110-preserving dispatch and fail-closed Type111 contract. It is not
connected to Honda `jmcs`; there is no validated Control SETUP capability
handle, receiver-owned Type111 authority, listener or transport callback in
this build. No iPhone negotiation or vehicle behavior is proved.

**Next action:** complete the scoped review and public-safety checks, then
publish only as an honestly labeled checkpoint. Keep Type111 disabled until
the capability and authenticated media context are established.

## Closeout

No vehicle, startup configuration, receiver binary, or private firmware was
modified. The CL-54B Control SETUP branch remains separate and unreviewed; this
task is based only on the published native advertisement checkpoint PR #153.
