# CL-R4B laboratory session authority and replay scope

ClarityLink's API17 receiver has a synthetic, same-application-UID laboratory
authority. It is not MFi authentication and it does not authorize a Honda or an
iPhone session.

The Type111 View process first asks the compositor to bind a live Type110 sink
Binder as the parent authority. The compositor checks the caller's Android
process identity, sink identity, and sink liveness, then assigns an in-memory
owner epoch and links a Binder death recipient. Type111 capability and setup
are allowed only inside that authorized session. Type111-first setup is still
supported: the parent authority is established first, then the child stream may
register before Type110 video activation. Its provisional authority is bounded
to 30 seconds and is revoked on Type110 owner loss or teardown.

The compositor keeps at most eight active parent sessions, a 256-ID exact recent
window, and a persistent 32 KiB Bloom replay fence. Replay IDs are reserved
durably before a stream registration is published. A persistence error, corrupt
fence, replay match, or lifetime limit rejects the request. The recent exact
window can evict old entries, but Bloom bits do not: the filter has no false
negatives for IDs recorded since that filter was initialized, with a possible
false positive that rejects a new ID.

The filter is capped at 4,096 issued session IDs per installed app-data set.
That cap keeps the bounded filter's expected false-positive rate low and makes
the limit explicit. Once reached, new sessions fail closed. There is no
transparent reset because resetting the replay state would also remove its
historical replay guarantee. Reinitializing app data is outside the guarantee;
it must only be done for an isolated synthetic lab environment, and old IDs
must not then be represented as protected. The implementation makes no claim
of global replay resistance across app-data deletion, device replacement,
factory reset, or a different legitimate authority.

An owner epoch is process-local and fences callbacks, frames, and stream
teardown while the compositor instance is alive. After compositor death, a new
process invalidates old attachments and identities and requires a fresh
authorized laboratory owner. Session IDs alone do not prove ownership.
