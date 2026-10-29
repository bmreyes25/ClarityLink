#ifndef CLARITYLINK_CL_TYPE111_CHILD_H
#define CLARITYLINK_CL_TYPE111_CHILD_H

/*
 * Receiver-side Type111 child-control boundary (option C: project-owned
 * receiver behind an explicit, disabled-by-default authority boundary).
 *
 * This module is OFFLINE and UNVERIFIED. It does not hook, patch, load into,
 * or call anything in Honda's jmcs. The 43T1 records evidence no additive
 * Setup+cleanup entry, no supported loader entry, and no lifetime-paired
 * Honda session authority; nothing here claims such a boundary exists.
 *
 * Properties enforced here:
 *  - A session is DISABLED unless an authority supplies a complete, valid
 *    capability table at creation. Disabled sessions invoke no callback.
 *  - No Honda session, CoreFoundation, request or response pointer is ever
 *    retained. Requests are borrowed const for one synchronous call. Child
 *    identity is scalar only.
 *  - Type111 children own independent state/resources; Type110 state is never
 *    referenced or modified.
 *  - Type111 response construction is unavailable unless the authority
 *    supplied an established response contract. This module never invents
 *    response fields, authentication, or security values.
 *  - Children close independently; parent-generation revoke releases all.
 *  - Callbacks are synchronous. Reentrant or concurrent calls on a session
 *    fail closed with BUSY (revoke is deferred, never lost).
 *
 * safeForHonda() is, and must remain, false.
 */

#include <stddef.h>
#include <stdint.h>

#define CL_T111_ABI_VERSION UINT32_C(1)
#define CL_T111_MAX_CHILDREN 4u
#define CL_T111_CB_OK INT32_C(1)
#define CL_T111_REQUEST_VIEW_MAGIC UINT32_C(0x43543156)
#define CL_T111_REQUEST_VIEW_MAX_STREAMS 8u
/* Upper bound on one staged response; larger output is a failure, not truncated. */
#define CL_T111_RESPONSE_STAGE_MAX 512u

typedef enum {
    CL_T111_OK = 0,
    CL_T111_NOT_APPLICABLE = 1,    /* request carries no Type111 stream */
    CL_T111_DISABLED = 2,
    CL_T111_INVALID_ARGUMENT = 3,
    CL_T111_MALFORMED = 4,
    CL_T111_UNKNOWN_TYPE = 5,
    CL_T111_DUPLICATE = 6,
    CL_T111_STALE_GENERATION = 7,
    CL_T111_REVOKED = 8,
    CL_T111_BUSY = 9,
    CL_T111_EXHAUSTED = 10,
    CL_T111_AUTHORITY_FAILED = 11, /* acquire/activate failed; rolled back */
    CL_T111_RELEASE_FAILED = 12,   /* release outcome is uncertain and retained */
    CL_T111_UNKNOWN_CHILD = 13,
    CL_T111_ALREADY_CLOSED = 14,
    CL_T111_RESPONSE_UNAVAILABLE = 15,
    CL_T111_REVOKE_DEFERRED = 16,
    CL_T111_UNCERTAIN_RESOURCE = 17
} ClT111Result;

typedef enum {
    CL_T111_STATE_DISABLED = 0,
    CL_T111_STATE_ENABLED_UNVERIFIED = 1,
    CL_T111_STATE_REVOKED = 2,
    CL_T111_STATE_RELEASE_UNCERTAIN = 3
} ClT111SessionState;

typedef enum {
    CL_T111_REASON_NONE = 0,
    CL_T111_REASON_NO_AUTHORITY = 1,
    CL_T111_REASON_INVALID_CAPABILITIES = 2,
    CL_T111_REASON_REVOKED = 3
} ClT111DisabledReason;

/*
 * Authority-supplied capabilities. Every callback is synchronous and
 * non-throwing. A failing acquire/activate must leave no newly held resource.
 * A failed release has an UNKNOWN outcome and may have partially completed:
 * the module retains the resource as UNCERTAIN and never retries it. There is
 * currently no callback that can reconcile an uncertain release, so storage
 * cannot be destroyed while one remains. `userdata` is authority-owned and
 * must never be a Honda session or CoreFoundation pointer. The table is
 * copied by value, but `userdata` and the callbacks must remain valid for the
 * whole life of the session (until destroy completes). Callbacks are
 * serialized within one session, yet distinct sessions may invoke them
 * concurrently, so an authority shared across sessions must be thread-safe.
 *
 * Response contract: either both response_contract_id and response_build are
 * zero/NULL (response unavailable) or both are set. `response_build` fills an
 * authority-defined buffer; this module adds no fields of its own.
 */
typedef int32_t (*ClT111Acquire)(void *userdata, uint32_t parent_generation,
                                 uint32_t id_low, uint32_t id_high,
                                 uint32_t *resource_out);
typedef int32_t (*ClT111Activate)(void *userdata, uint32_t resource);
typedef int32_t (*ClT111Release)(void *userdata, uint32_t resource);
typedef int32_t (*ClT111ResponseBuild)(void *userdata, uint32_t resource,
                                       void *out, size_t out_capacity,
                                       size_t *out_length);

typedef struct {
    uint32_t abi_version;
    uint32_t struct_size;
    uint32_t authority_token; /* nonzero, authority-defined */
    void *userdata;
    ClT111Acquire acquire;
    ClT111Activate activate;
    ClT111Release release;
    uint32_t response_contract_id;
    ClT111ResponseBuild response_build;
} ClT111Authority;

/*
 * Normalized scalar request view, owned by this module. A future authority
 * adapter would copy the stream count and each stream's type and identity
 * values into this struct synchronously; no Honda adapter exists or is
 * claimed. It holds scalars only (no pointers) and is borrowed const for one
 * call. `magic` must be CL_T111_REQUEST_VIEW_MAGIC; `count` is bounded by
 * CL_T111_REQUEST_VIEW_MAX_STREAMS and entries past `count` are ignored.
 * Type110 values are validated for identity uniqueness and never modified.
 */
typedef struct {
    uint32_t type;
    uint32_t id_low;
    uint32_t id_high;
} ClT111StreamView;

typedef struct {
    uint32_t magic;
    uint32_t count;
    ClT111StreamView streams[CL_T111_REQUEST_VIEW_MAX_STREAMS];
} ClT111RequestView;

/* Scalar child handle; no pointers, so stale use is detectable. */
typedef struct {
    uint32_t parent_generation;
    uint32_t slot;
    uint32_t serial;
} ClT111ChildRef;

typedef struct {
    uint32_t state; /* ClT111SessionState */
    uint32_t disabled_reason;
    uint32_t parent_generation;
    uint32_t active_children;
    uint32_t uncertain_children;
    uint32_t response_contract_available;
    uint32_t opened_total;
    uint32_t closed_total;
    uint32_t release_failures;
    uint32_t integration_verified; /* always 0 */
    uint32_t safe_for_honda;       /* always 0 */
} ClT111Status;

typedef struct {
    uint32_t state;
    uint32_t serial;
    uint32_t id_low;
    uint32_t id_high;
    uint32_t resource;
} ClT111ChildSlot;

/* Caller-provided storage; treat as opaque. */
typedef struct {
    uint32_t magic;
    uint32_t state;
    uint32_t disabled_reason;
    uint32_t parent_generation;
    uint32_t next_serial;
    uint32_t opened_total;
    uint32_t closed_total;
    uint32_t release_failures;
    uint32_t uncertain_children;
    uint32_t busy;
    uint32_t revoke_pending;
    ClT111Authority authority;
    ClT111ChildSlot children[CL_T111_MAX_CHILDREN];
} ClT111Session;

/* Always false; exposed so tests and callers cannot assume otherwise. */
int32_t cl_t111_safe_for_honda(void);

/*
 * Initialise `session`. `authority` may be NULL or invalid, in which case the
 * session is DISABLED (returns CL_T111_DISABLED, no callback ever runs).
 * `parent_generation` must be nonzero and is supplied by the authority; it is
 * not derived from any Honda pointer.
 *
 * `session` must be fresh or inactive caller storage: create does not
 * synchronise with, or tear down, a session already live in that memory.
 */
int32_t cl_t111_session_create(ClT111Session *session,
                               const ClT111Authority *authority,
                               uint32_t parent_generation);

/* Open the independent Type111 child described by `request` (borrowed const). */
/*
 * Serials are issued from 1 to UINT32_MAX-1 and never reused; once exhausted,
 * opens fail with CL_T111_EXHAUSTED rather than wrap and revive old handles.
 */
int32_t cl_t111_child_open(ClT111Session *session, uint32_t parent_generation,
                           const ClT111RequestView *request,
                           ClT111ChildRef *child_out);

int32_t cl_t111_child_close(ClT111Session *session, const ClT111ChildRef *child);

/* Revoke every child for this parent generation; idempotent. */
int32_t cl_t111_session_revoke(ClT111Session *session, uint32_t parent_generation);

/*
 * Build an authority-defined Type111 response. Returns
 * CL_T111_RESPONSE_UNAVAILABLE, leaving `out` untouched, unless a response
 * contract was established at creation.
 *
 * Transactional: the authority writes into an internal stage of
 * min(out_capacity, CL_T111_RESPONSE_STAGE_MAX) bytes and the result is
 * copied to `out` only on success. Any callback error, zero or oversized
 * reported length, leaves `out` bytes unchanged and *out_length == 0
 * (CL_T111_AUTHORITY_FAILED). Responses above the stage maximum cannot be
 * produced. A callback must not write past the capacity it is given.
 */
int32_t cl_t111_response_build(ClT111Session *session, const ClT111ChildRef *child,
                               void *out, size_t out_capacity, size_t *out_length);

/*
 * Coherent snapshot taken under the session guard. Returns CL_T111_BUSY,
 * leaving `status_out` untouched, if another call (including a callback of
 * this session) holds the guard.
 */
int32_t cl_t111_session_status(const ClT111Session *session, ClT111Status *status_out);

/*
 * Revokes (if needed) then invalidates the storage's magic. The module cannot
 * free caller-owned memory or stop new entrants, so the caller must stop and
 * join all concurrent API calls on `session` before invalidating or reusing
 * its storage. Returns CL_T111_BUSY if a call is still in flight, or
 * CL_T111_RELEASE_FAILED without invalidating storage while any release
 * outcome remains uncertain. No automatic retry or resolution is provided.
 */
int32_t cl_t111_session_destroy(ClT111Session *session);

#endif
