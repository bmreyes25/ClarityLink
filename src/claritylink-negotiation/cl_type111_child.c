#include "cl_type111_child.h"

/* Compiler builtin keeps the unit free of libc headers (freestanding ARMv7 check). */
#define memset __builtin_memset
#define memcpy __builtin_memcpy

#define CL_T111_SESSION_MAGIC UINT32_C(0x43543131)
#define CL_T111_STREAM_TYPE UINT32_C(111)
#define CL_T111_STREAM_TYPE_110 UINT32_C(110)

enum { CHILD_FREE = 0, CHILD_ACTIVE = 1 };

/* try-lock; seq_cst so a deferred revoke is never lost (see guard_exit). */
static int guard_try_enter(ClT111Session *s) {
    uint32_t expected = 0u;
    return __atomic_compare_exchange_n(&s->busy, &expected, 1u, 0,
                                       __ATOMIC_SEQ_CST, __ATOMIC_SEQ_CST);
}

static int32_t revoke_locked(ClT111Session *s) {
    uint32_t i;
    int32_t result = CL_T111_OK;
    __atomic_store_n(&s->state, (uint32_t)CL_T111_STATE_REVOKED, __ATOMIC_SEQ_CST);
    s->disabled_reason = CL_T111_REASON_REVOKED;
    for (i = 0; i < CL_T111_MAX_CHILDREN; ++i) {
        ClT111ChildSlot *slot = &s->children[i];
        uint32_t resource;
        if (slot->state != CHILD_ACTIVE) {
            continue;
        }
        resource = slot->resource;
        memset(slot, 0, sizeof(*slot)); /* slot is free before the callback */
        ++s->closed_total;
        if (s->authority.release(s->authority.userdata, resource) != CL_T111_CB_OK) {
            ++s->release_failures;
            result = CL_T111_RELEASE_FAILED;
        }
    }
    return result;
}

/* Release the guard, then run any revoke that was requested while it was held. */
static void guard_exit(ClT111Session *s) {
    __atomic_store_n(&s->busy, 0u, __ATOMIC_SEQ_CST);
    while (__atomic_load_n(&s->revoke_pending, __ATOMIC_SEQ_CST) != 0u &&
           guard_try_enter(s)) {
        __atomic_store_n(&s->revoke_pending, 0u, __ATOMIC_SEQ_CST);
        (void)revoke_locked(s);
        __atomic_store_n(&s->busy, 0u, __ATOMIC_SEQ_CST);
    }
}

static int authority_valid(const ClT111Authority *a) {
    int contract_id = a->response_contract_id != 0u;
    int contract_cb = a->response_build != NULL;
    return a->abi_version == CL_T111_ABI_VERSION &&
           a->struct_size == (uint32_t)sizeof(ClT111Authority) &&
           a->authority_token != 0u && a->acquire != NULL && a->activate != NULL &&
           a->release != NULL && contract_id == contract_cb;
}

static int session_live(const ClT111Session *s) {
    return s != NULL && s->magic == CL_T111_SESSION_MAGIC;
}

int32_t cl_t111_safe_for_honda(void) { return 0; }

int32_t cl_t111_session_create(ClT111Session *session,
                               const ClT111Authority *authority,
                               uint32_t parent_generation) {
    if (session == NULL) {
        return CL_T111_INVALID_ARGUMENT;
    }
    memset(session, 0, sizeof(*session));
    session->magic = CL_T111_SESSION_MAGIC;
    session->state = CL_T111_STATE_DISABLED;
    session->next_serial = 1u;
    if (authority == NULL) {
        session->disabled_reason = CL_T111_REASON_NO_AUTHORITY;
        return CL_T111_DISABLED;
    }
    if (!authority_valid(authority) || parent_generation == 0u) {
        session->disabled_reason = CL_T111_REASON_INVALID_CAPABILITIES;
        return CL_T111_DISABLED;
    }
    session->authority = *authority;
    session->parent_generation = parent_generation;
    session->state = CL_T111_STATE_ENABLED_UNVERIFIED;
    return CL_T111_OK;
}

/*
 * Independent Type111 validation: exactly zero or one Type111 stream, only
 * known types, nonzero unique identities across Type110/Type111, bounded count.
 */
static int32_t request_scan(const ClT111RequestView *request, uint32_t *id_low,
                            uint32_t *id_high) {
    uint32_t i;
    uint32_t j;
    uint32_t found = 0u;
    if (request->magic != CL_T111_REQUEST_VIEW_MAGIC ||
        request->count > CL_T111_REQUEST_VIEW_MAX_STREAMS) {
        return CL_T111_MALFORMED;
    }
    for (i = 0; i < request->count; ++i) {
        const ClT111StreamView *cur = &request->streams[i];
        if (cur->type != 100u && cur->type != 101u &&
            cur->type != CL_T111_STREAM_TYPE_110 && cur->type != CL_T111_STREAM_TYPE) {
            return CL_T111_UNKNOWN_TYPE;
        }
        if (cur->type != CL_T111_STREAM_TYPE_110 && cur->type != CL_T111_STREAM_TYPE) {
            continue;
        }
        if (cur->id_low == 0u && cur->id_high == 0u) {
            return CL_T111_MALFORMED;
        }
        for (j = 0; j < i; ++j) {
            const ClT111StreamView *prior = &request->streams[j];
            if ((prior->type == CL_T111_STREAM_TYPE_110 ||
                 prior->type == CL_T111_STREAM_TYPE) &&
                prior->id_low == cur->id_low &&
                prior->id_high == cur->id_high) {
                return CL_T111_DUPLICATE;
            }
        }
        if (cur->type == CL_T111_STREAM_TYPE) {
            if (++found > 1u) {
                return CL_T111_DUPLICATE;
            }
            *id_low = cur->id_low;
            *id_high = cur->id_high;
        }
    }
    return found == 0u ? CL_T111_NOT_APPLICABLE : CL_T111_OK;
}

/* Common gate for state-changing calls; caller must guard_exit on OK. */
static int32_t enter_live(ClT111Session *s, uint32_t generation) {
    if (!session_live(s)) {
        return CL_T111_INVALID_ARGUMENT;
    }
    if (!guard_try_enter(s)) {
        return CL_T111_BUSY;
    }
    if (s->state == CL_T111_STATE_DISABLED) {
        guard_exit(s);
        return CL_T111_DISABLED;
    }
    if (generation != s->parent_generation) {
        guard_exit(s);
        return CL_T111_STALE_GENERATION;
    }
    if (s->state == CL_T111_STATE_REVOKED) {
        guard_exit(s);
        return CL_T111_REVOKED;
    }
    return CL_T111_OK;
}

static int duplicate_active(const ClT111Session *s, uint32_t low, uint32_t high) {
    uint32_t i;
    for (i = 0; i < CL_T111_MAX_CHILDREN; ++i) {
        if (s->children[i].state == CHILD_ACTIVE && s->children[i].id_low == low &&
            s->children[i].id_high == high) {
            return 1;
        }
    }
    return 0;
}

int32_t cl_t111_child_open(ClT111Session *session, uint32_t parent_generation,
                           const ClT111RequestView *request,
                           ClT111ChildRef *child_out) {
    uint32_t id_low = 0u;
    uint32_t id_high = 0u;
    uint32_t resource = 0u;
    uint32_t slot_index = CL_T111_MAX_CHILDREN;
    uint32_t i;
    int32_t result;
    ClT111ChildSlot *slot;
    if (child_out != NULL) {
        memset(child_out, 0, sizeof(*child_out));
    }
    if (session == NULL || request == NULL || child_out == NULL) {
        return CL_T111_INVALID_ARGUMENT;
    }
    result = enter_live(session, parent_generation);
    if (result != CL_T111_OK) {
        return result;
    }
    result = request_scan(request, &id_low, &id_high);
    if (result != CL_T111_OK) {
        guard_exit(session);
        return result;
    }
    if (duplicate_active(session, id_low, id_high)) {
        guard_exit(session);
        return CL_T111_DUPLICATE;
    }
    if (session->next_serial == 0u || session->next_serial == UINT32_MAX) {
        guard_exit(session); /* serials never wrap, so no handle is ever reused */
        return CL_T111_EXHAUSTED;
    }
    for (i = 0; i < CL_T111_MAX_CHILDREN; ++i) {
        if (session->children[i].state == CHILD_FREE) {
            slot_index = i;
            break;
        }
    }
    if (slot_index == CL_T111_MAX_CHILDREN) {
        guard_exit(session);
        return CL_T111_EXHAUSTED;
    }
    if (session->authority.acquire(session->authority.userdata, session->parent_generation,
                                   id_low, id_high, &resource) != CL_T111_CB_OK ||
        resource == 0u) {
        guard_exit(session); /* failure-atomic contract: nothing to undo */
        return CL_T111_AUTHORITY_FAILED;
    }
    if (session->authority.activate(session->authority.userdata, resource) !=
        CL_T111_CB_OK) {
        if (session->authority.release(session->authority.userdata, resource) !=
            CL_T111_CB_OK) {
            ++session->release_failures;
        }
        guard_exit(session);
        return CL_T111_AUTHORITY_FAILED;
    }
    slot = &session->children[slot_index];
    slot->state = CHILD_ACTIVE;
    slot->serial = session->next_serial++;
    slot->id_low = id_low;
    slot->id_high = id_high;
    slot->resource = resource;
    ++session->opened_total;
    child_out->parent_generation = session->parent_generation;
    child_out->slot = slot_index;
    child_out->serial = slot->serial;
    guard_exit(session);
    return CL_T111_OK;
}

/* Resolve a ref to its active slot, or report why not. Guard must be held. */
static int32_t slot_for(ClT111Session *s, const ClT111ChildRef *child,
                        ClT111ChildSlot **slot_out) {
    ClT111ChildSlot *slot;
    if (child->slot >= CL_T111_MAX_CHILDREN || child->serial == 0u) {
        return CL_T111_UNKNOWN_CHILD;
    }
    slot = &s->children[child->slot];
    if (slot->state != CHILD_ACTIVE) {
        return child->serial < s->next_serial ? CL_T111_ALREADY_CLOSED
                                              : CL_T111_UNKNOWN_CHILD;
    }
    if (slot->serial != child->serial) {
        return CL_T111_ALREADY_CLOSED; /* slot reused: ref is stale */
    }
    *slot_out = slot;
    return CL_T111_OK;
}

int32_t cl_t111_child_close(ClT111Session *session, const ClT111ChildRef *child) {
    ClT111ChildSlot *slot = NULL;
    uint32_t resource;
    int32_t result;
    if (session == NULL || child == NULL) {
        return CL_T111_INVALID_ARGUMENT;
    }
    if (!session_live(session)) {
        return CL_T111_INVALID_ARGUMENT;
    }
    if (!guard_try_enter(session)) {
        return CL_T111_BUSY;
    }
    if (session->state == CL_T111_STATE_DISABLED) {
        guard_exit(session);
        return CL_T111_DISABLED;
    }
    if (child->parent_generation != session->parent_generation) {
        guard_exit(session);
        return CL_T111_STALE_GENERATION;
    }
    result = slot_for(session, child, &slot);
    if (result != CL_T111_OK) {
        /* After revoke every former child is simply closed. */
        guard_exit(session);
        return result;
    }
    resource = slot->resource;
    memset(slot, 0, sizeof(*slot));
    ++session->closed_total;
    result = CL_T111_OK;
    if (session->authority.release(session->authority.userdata, resource) !=
        CL_T111_CB_OK) {
        ++session->release_failures;
        result = CL_T111_RELEASE_FAILED;
    }
    guard_exit(session);
    return result;
}

int32_t cl_t111_session_revoke(ClT111Session *session, uint32_t parent_generation) {
    int32_t result;
    if (!session_live(session)) {
        return CL_T111_INVALID_ARGUMENT;
    }
    if (__atomic_load_n(&session->state, __ATOMIC_SEQ_CST) == CL_T111_STATE_DISABLED) {
        return CL_T111_DISABLED;
    }
    if (parent_generation != session->parent_generation) {
        return CL_T111_STALE_GENERATION;
    }
    /* Publish intent first; exactly one of us or the holder will run it. */
    __atomic_store_n(&session->revoke_pending, 1u, __ATOMIC_SEQ_CST);
    if (!guard_try_enter(session)) {
        return CL_T111_REVOKE_DEFERRED;
    }
    __atomic_store_n(&session->revoke_pending, 0u, __ATOMIC_SEQ_CST);
    result = revoke_locked(session);
    guard_exit(session);
    return result;
}

int32_t cl_t111_response_build(ClT111Session *session, const ClT111ChildRef *child,
                               void *out, size_t out_capacity, size_t *out_length) {
    ClT111ChildSlot *slot = NULL;
    int32_t result;
    size_t produced = 0u;
    size_t stage_capacity;
    uint8_t stage[CL_T111_RESPONSE_STAGE_MAX];
    if (out_length != NULL) {
        *out_length = 0u;
    }
    if (session == NULL || child == NULL || out == NULL || out_length == NULL ||
        out_capacity == 0u) {
        return CL_T111_INVALID_ARGUMENT;
    }
    result = enter_live(session, child->parent_generation);
    if (result != CL_T111_OK) {
        return result;
    }
    if (session->authority.response_contract_id == 0u ||
        session->authority.response_build == NULL) {
        guard_exit(session);
        return CL_T111_RESPONSE_UNAVAILABLE; /* `out` untouched */
    }
    result = slot_for(session, child, &slot);
    if (result != CL_T111_OK) {
        guard_exit(session);
        return result;
    }
    stage_capacity = out_capacity < CL_T111_RESPONSE_STAGE_MAX
                         ? out_capacity
                         : (size_t)CL_T111_RESPONSE_STAGE_MAX;
    memset(stage, 0, sizeof(stage));
    if (session->authority.response_build(session->authority.userdata, slot->resource,
                                          stage, stage_capacity, &produced) !=
            CL_T111_CB_OK ||
        produced == 0u || produced > stage_capacity) {
        memset(stage, 0, sizeof(stage)); /* `out` and *out_length stay untouched */
        guard_exit(session);
        return CL_T111_AUTHORITY_FAILED;
    }
    memcpy(out, stage, produced);
    memset(stage, 0, sizeof(stage));
    *out_length = produced;
    guard_exit(session);
    return CL_T111_OK;
}

int32_t cl_t111_session_status(const ClT111Session *session, ClT111Status *status_out) {
    /* The guard word is synchronisation state, not logical session state; the
     * snapshot below only reads, so the const cast is internal and benign. */
    ClT111Session *guarded = (ClT111Session *)(uintptr_t)session;
    ClT111Status snapshot;
    uint32_t i;
    if (!session_live(session) || status_out == NULL) {
        return CL_T111_INVALID_ARGUMENT;
    }
    if (!guard_try_enter(guarded)) {
        return CL_T111_BUSY; /* `status_out` untouched */
    }
    memset(&snapshot, 0, sizeof(snapshot));
    snapshot.state = session->state;
    snapshot.disabled_reason = session->disabled_reason;
    snapshot.parent_generation = session->parent_generation;
    for (i = 0; i < CL_T111_MAX_CHILDREN; ++i) {
        if (session->children[i].state == CHILD_ACTIVE) {
            ++snapshot.active_children;
        }
    }
    snapshot.response_contract_available =
        session->state == CL_T111_STATE_ENABLED_UNVERIFIED &&
        session->authority.response_contract_id != 0u &&
        session->authority.response_build != NULL;
    snapshot.opened_total = session->opened_total;
    snapshot.closed_total = session->closed_total;
    snapshot.release_failures = session->release_failures;
    snapshot.integration_verified = 0u;
    snapshot.safe_for_honda = 0u;
    guard_exit(guarded); /* may run a deferred revoke; snapshot is already copied */
    *status_out = snapshot;
    return CL_T111_OK;
}

int32_t cl_t111_session_destroy(ClT111Session *session) {
    int32_t result = CL_T111_OK;
    if (!session_live(session)) {
        return CL_T111_INVALID_ARGUMENT;
    }
    if (__atomic_load_n(&session->state, __ATOMIC_SEQ_CST) ==
        CL_T111_STATE_ENABLED_UNVERIFIED) {
        result = cl_t111_session_revoke(session, session->parent_generation);
        if (result == CL_T111_REVOKE_DEFERRED ||
            __atomic_load_n(&session->busy, __ATOMIC_SEQ_CST) != 0u) {
            return CL_T111_BUSY; /* storage must outlive in-flight callers */
        }
    }
    session->magic = 0u;
    return result;
}
