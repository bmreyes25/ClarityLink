/* Host regression for src/claritylink-negotiation/cl_type111_child.c.
 * Synthetic authority only: proves boundary logic, not Honda behavior. */
#include "cl_type111_child.h"

#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int failures;
#define CHECK(cond)                                                              \
    do {                                                                         \
        if (!(cond)) {                                                           \
            fprintf(stderr, "FAIL %s:%d %s\n", __FILE__, __LINE__, #cond);       \
            ++failures;                                                          \
        }                                                                        \
    } while (0)

typedef struct {
    uint32_t acquires, activates, releases, builds;
    uint32_t fail_acquire, zero_resource, fail_activate, fail_release, fail_build;
    uint32_t build_mode; /* 1 partial-write-then-fail, 2 oversize len, 3 zero len, 4 big ok */
    uint32_t next_resource;
    uint32_t live[1u << 16];
    ClT111Session *reenter;
    uint32_t reenter_gen;
    int32_t reenter_open, reenter_close, reenter_revoke, reenter_status;
    uint32_t reenter_status_untouched;
    uint32_t double_release;
} Auth;

static ClT111RequestView make_request(uint32_t id111) {
    ClT111RequestView r;
    memset(&r, 0, sizeof(r));
    r.magic = CL_T111_REQUEST_VIEW_MAGIC;
    r.count = 3u;
    r.streams[0].type = 100u;
    r.streams[1].type = 110u;
    r.streams[1].id_low = 0x110u;
    r.streams[1].id_high = 1u;
    r.streams[2].type = 111u;
    r.streams[2].id_low = id111;
    r.streams[2].id_high = 7u;
    return r;
}

static int32_t cb_acquire(void *u, uint32_t gen, uint32_t lo, uint32_t hi, uint32_t *out) {
    Auth *a = (Auth *)u;
    uint32_t res;
    (void)gen; (void)lo; (void)hi;
    __atomic_add_fetch(&a->acquires, 1u, __ATOMIC_SEQ_CST);
    if (a->fail_acquire) return 0;
    if (a->zero_resource) { *out = 0u; return CL_T111_CB_OK; }
    res = __atomic_add_fetch(&a->next_resource, 1u, __ATOMIC_SEQ_CST);
    a->live[res & 0xFFFFu] = 1u;
    *out = res;
    return CL_T111_CB_OK;
}

static int32_t cb_activate(void *u, uint32_t res) {
    Auth *a = (Auth *)u;
    ClT111ChildRef scratch;
    (void)res;
    ++a->activates;
    if (a->reenter) {
        ClT111RequestView req = make_request(0x999u);
        ClT111Session *s = a->reenter;
        a->reenter = NULL;
        a->reenter_open = cl_t111_child_open(s, a->reenter_gen, &req, &scratch);
        a->reenter_revoke = cl_t111_session_revoke(s, a->reenter_gen);
        {
            ClT111Status probe;
            memset(&probe, 0xA5, sizeof(probe));
            a->reenter_status = cl_t111_session_status(s, &probe);
            a->reenter_status_untouched = ((const unsigned char *)&probe)[0] == 0xA5u;
        }
        memset(&scratch, 0, sizeof(scratch));
        scratch.parent_generation = a->reenter_gen;
        scratch.serial = 1u;
        a->reenter_close = cl_t111_child_close(s, &scratch);
    }
    return a->fail_activate ? 0 : CL_T111_CB_OK;
}

static int32_t cb_release(void *u, uint32_t res) {
    Auth *a = (Auth *)u;
    __atomic_add_fetch(&a->releases, 1u, __ATOMIC_SEQ_CST);
    if (a->live[res & 0xFFFFu] == 0u) ++a->double_release;
    a->live[res & 0xFFFFu] = 0u;
    return a->fail_release ? 0 : CL_T111_CB_OK;
}

static int32_t cb_build(void *u, uint32_t res, void *out, size_t cap, size_t *len) {
    Auth *a = (Auth *)u;
    ++a->builds;
    if (a->build_mode == 1u) { memset(out, 0xCC, cap); return 0; }
    if (a->build_mode == 2u) { memset(out, 0xCC, cap); *len = cap + 1u; return CL_T111_CB_OK; }
    if (a->build_mode == 3u) { memset(out, 0xCC, cap); *len = 0u; return CL_T111_CB_OK; }
    if (a->build_mode == 4u) { memset(out, 0xDD, cap); *len = cap; return CL_T111_CB_OK; }
    if (a->fail_build || cap < 4u) return 0;
    memcpy(out, &res, 4u);
    *len = 4u;
    return CL_T111_CB_OK;
}

static ClT111Authority good(Auth *a, int with_response) {
    ClT111Authority t;
    memset(&t, 0, sizeof(t));
    t.abi_version = CL_T111_ABI_VERSION;
    t.struct_size = (uint32_t)sizeof(t);
    t.authority_token = 0xA11u;
    t.userdata = a;
    t.acquire = cb_acquire;
    t.activate = cb_activate;
    t.release = cb_release;
    if (with_response) { t.response_contract_id = 0x5E5u; t.response_build = cb_build; }
    return t;
}

static uint32_t callbacks(const Auth *a) { return a->acquires + a->activates + a->releases + a->builds; }

static Auth *new_auth(void) { return (Auth *)calloc(1u, sizeof(Auth)); }

static void test_disabled_by_default(void) {
    ClT111Session s; Auth *a = new_auth(); ClT111Status st; ClT111ChildRef ref;
    ClT111RequestView req = make_request(1u);
    ClT111RequestView before = req;
    uint8_t out[8]; size_t len = 99u;
    memset(out, 0xAB, sizeof(out));
    memset(&ref, 0, sizeof(ref));
    CHECK(cl_t111_session_create(&s, NULL, 1u) == CL_T111_DISABLED);
    CHECK(cl_t111_session_status(&s, &st) == CL_T111_OK);
    CHECK(st.state == CL_T111_STATE_DISABLED && st.disabled_reason == CL_T111_REASON_NO_AUTHORITY);
    CHECK(cl_t111_child_open(&s, 1u, &req, &ref) == CL_T111_DISABLED);
    CHECK(cl_t111_child_close(&s, &ref) == CL_T111_DISABLED);
    CHECK(cl_t111_session_revoke(&s, 1u) == CL_T111_DISABLED);
    CHECK(cl_t111_response_build(&s, &ref, out, sizeof(out), &len) == CL_T111_DISABLED);
    CHECK(len == 0u && out[0] == 0xAB);
    CHECK(memcmp(&req, &before, sizeof(req)) == 0);
    CHECK(callbacks(a) == 0u);
    CHECK(cl_t111_session_destroy(&s) == CL_T111_OK);
    free(a);
}

static void test_invalid_capability_tables(void) {
    Auth *a = new_auth(); ClT111Session s; ClT111Authority t; ClT111ChildRef ref;
    ClT111RequestView req = make_request(1u);
    ClT111Status st;
    uint32_t i;
    for (i = 0; i < 9u; ++i) {
        uint32_t gen = 1u;
        t = good(a, 0);
        switch (i) {
            case 0: t.abi_version = 2u; break;
            case 1: t.struct_size -= 4u; break;
            case 2: t.authority_token = 0u; break;
            case 3: t.acquire = NULL; break;
            case 4: t.activate = NULL; break;
            case 5: t.release = NULL; break;
            case 6: t.response_contract_id = 5u; break;   /* id without callback */
            case 7: t.response_build = cb_build; break;  /* callback without id */
            default: gen = 0u; break;                     /* zero generation */
        }
        CHECK(cl_t111_session_create(&s, &t, gen) == CL_T111_DISABLED);
        CHECK(cl_t111_session_status(&s, &st) == CL_T111_OK);
        CHECK(st.disabled_reason == CL_T111_REASON_INVALID_CAPABILITIES);
        CHECK(cl_t111_child_open(&s, gen, &req, &ref) == CL_T111_DISABLED);
    }
    CHECK(callbacks(a) == 0u);
    free(a);
}

static void test_open_close_and_request_immutable(void) {
    Auth *a = new_auth(); ClT111Session s; ClT111Authority t = good(a, 0); ClT111Status st;
    ClT111RequestView req = make_request(5u);
    ClT111RequestView before = req;
    ClT111ChildRef r1, r2;
    CHECK(cl_t111_session_create(&s, &t, 9u) == CL_T111_OK);
    CHECK(cl_t111_child_open(&s, 9u, &req, &r1) == CL_T111_OK);
    CHECK(memcmp(&req, &before, sizeof(req)) == 0);  /* Type110 stream untouched */
    CHECK(a->acquires == 1u && a->activates == 1u && a->releases == 0u);
    req = make_request(6u);
    CHECK(cl_t111_child_open(&s, 9u, &req, &r2) == CL_T111_OK);
    CHECK(r1.serial != r2.serial && r1.slot != r2.slot);
    CHECK(cl_t111_session_status(&s, &st) == CL_T111_OK && st.active_children == 2u);
    CHECK(st.integration_verified == 0u && st.safe_for_honda == 0u);
    CHECK(st.state == CL_T111_STATE_ENABLED_UNVERIFIED);
    CHECK(cl_t111_child_close(&s, &r1) == CL_T111_OK);          /* independent close */
    CHECK(a->releases == 1u);
    CHECK(cl_t111_session_status(&s, &st) == CL_T111_OK && st.active_children == 1u);
    CHECK(cl_t111_child_close(&s, &r1) == CL_T111_ALREADY_CLOSED);
    CHECK(a->releases == 1u);                                   /* no double release */
    CHECK(cl_t111_child_close(&s, &r2) == CL_T111_OK);
    CHECK(cl_t111_session_destroy(&s) == CL_T111_OK);
    CHECK(a->acquires == a->releases && a->double_release == 0u);
    free(a);
}

static void test_request_validation_fail_closed(void) {
    Auth *a = new_auth(); ClT111Session s; ClT111Authority t = good(a, 0); ClT111ChildRef ref;
    ClT111RequestView r;
    CHECK(cl_t111_session_create(&s, &t, 3u) == CL_T111_OK);

    r = make_request(1u); r.magic ^= 1u;
    CHECK(cl_t111_child_open(&s, 3u, &r, &ref) == CL_T111_MALFORMED);
    r = make_request(1u); r.count = CL_T111_REQUEST_VIEW_MAX_STREAMS + 1u;
    CHECK(cl_t111_child_open(&s, 3u, &r, &ref) == CL_T111_MALFORMED);
    r = make_request(0u); r.streams[2].id_high = 0u;      /* zero identity */
    CHECK(cl_t111_child_open(&s, 3u, &r, &ref) == CL_T111_MALFORMED);
    r = make_request(1u); r.streams[0].type = 112u;               /* unknown value */
    CHECK(cl_t111_child_open(&s, 3u, &r, &ref) == CL_T111_UNKNOWN_TYPE);
    r = make_request(1u); r.streams[0].type = 0xFFFFFFFFu;
    CHECK(cl_t111_child_open(&s, 3u, &r, &ref) == CL_T111_UNKNOWN_TYPE);
    r = make_request(1u); r.count = 4u;                           /* second Type111 */
    r.streams[3] = r.streams[2]; r.streams[3].id_low = 2u;
    CHECK(cl_t111_child_open(&s, 3u, &r, &ref) == CL_T111_DUPLICATE);
    r = make_request(1u);                                         /* 111 id == 110 id */
    r.streams[2].id_low = r.streams[1].id_low;
    r.streams[2].id_high = r.streams[1].id_high;
    CHECK(cl_t111_child_open(&s, 3u, &r, &ref) == CL_T111_DUPLICATE);
    r = make_request(1u); r.count = 2u;                           /* no Type111 */
    CHECK(cl_t111_child_open(&s, 3u, &r, &ref) == CL_T111_NOT_APPLICABLE);
    CHECK(cl_t111_child_open(&s, 3u, NULL, &ref) == CL_T111_INVALID_ARGUMENT);
    CHECK(cl_t111_child_open(&s, 3u, &r, NULL) == CL_T111_INVALID_ARGUMENT);
    CHECK(callbacks(a) == 0u);                                    /* nothing reached authority */

    r = make_request(1u);                                         /* duplicate active child */
    CHECK(cl_t111_child_open(&s, 3u, &r, &ref) == CL_T111_OK);
    CHECK(cl_t111_child_open(&s, 3u, &r, &ref) == CL_T111_DUPLICATE);
    CHECK(a->acquires == 1u);
    (void)cl_t111_session_destroy(&s);
    free(a);
}

static void test_request_not_retained(void) {
    Auth *a = new_auth(); ClT111Session s; ClT111Authority t = good(a, 0); ClT111ChildRef ref;
    ClT111RequestView *heap = (ClT111RequestView *)malloc(sizeof(*heap));
    ClT111Status st;
    *heap = make_request(11u);
    CHECK(cl_t111_session_create(&s, &t, 4u) == CL_T111_OK);
    CHECK(cl_t111_child_open(&s, 4u, heap, &ref) == CL_T111_OK);
    memset(heap, 0xEE, sizeof(*heap));
    free(heap);                                   /* ASan flags any retained use */
    CHECK(cl_t111_session_status(&s, &st) == CL_T111_OK && st.active_children == 1u);
    CHECK(cl_t111_child_close(&s, &ref) == CL_T111_OK);
    CHECK(sizeof(ClT111ChildRef) == 12u);         /* scalars only */
    (void)cl_t111_session_destroy(&s);
    free(a);
}

static void test_authority_failures_roll_back(void) {
    Auth *a = new_auth(); ClT111Session s; ClT111Authority t = good(a, 0); ClT111ChildRef ref;
    ClT111RequestView r = make_request(1u);
    ClT111Status st;
    CHECK(cl_t111_session_create(&s, &t, 3u) == CL_T111_OK);
    a->fail_acquire = 1u;
    CHECK(cl_t111_child_open(&s, 3u, &r, &ref) == CL_T111_AUTHORITY_FAILED);
    CHECK(a->releases == 0u);                      /* failure-atomic acquire */
    a->fail_acquire = 0u; a->zero_resource = 1u;
    CHECK(cl_t111_child_open(&s, 3u, &r, &ref) == CL_T111_AUTHORITY_FAILED);
    a->zero_resource = 0u; a->fail_activate = 1u;
    CHECK(cl_t111_child_open(&s, 3u, &r, &ref) == CL_T111_AUTHORITY_FAILED);
    CHECK(a->releases == 1u && a->double_release == 0u);   /* synchronous rollback */
    CHECK(cl_t111_session_status(&s, &st) == CL_T111_OK && st.active_children == 0u);
    a->fail_activate = 0u;
    CHECK(cl_t111_child_open(&s, 3u, &r, &ref) == CL_T111_OK);   /* recoverable */
    a->fail_release = 1u;
    CHECK(cl_t111_child_close(&s, &ref) == CL_T111_RELEASE_FAILED);
    CHECK(cl_t111_session_status(&s, &st) == CL_T111_OK);
    CHECK(st.active_children == 0u && st.release_failures == 1u);
    (void)cl_t111_session_destroy(&s);
    free(a);
}

static void test_exhaustion_and_slot_reuse(void) {
    Auth *a = new_auth(); ClT111Session s; ClT111Authority t = good(a, 0);
    ClT111ChildRef refs[CL_T111_MAX_CHILDREN], extra, reused;
    ClT111RequestView r;
    uint32_t i;
    CHECK(cl_t111_session_create(&s, &t, 3u) == CL_T111_OK);
    for (i = 0; i < CL_T111_MAX_CHILDREN; ++i) {
        r = make_request(100u + i);
        CHECK(cl_t111_child_open(&s, 3u, &r, &refs[i]) == CL_T111_OK);
    }
    r = make_request(500u);
    CHECK(cl_t111_child_open(&s, 3u, &r, &extra) == CL_T111_EXHAUSTED);
    CHECK(cl_t111_child_close(&s, &refs[1]) == CL_T111_OK);
    CHECK(cl_t111_child_open(&s, 3u, &r, &reused) == CL_T111_OK);
    CHECK(reused.slot == refs[1].slot && reused.serial != refs[1].serial);
    CHECK(cl_t111_child_close(&s, &refs[1]) == CL_T111_ALREADY_CLOSED); /* stale ref ignored */
    CHECK(cl_t111_child_close(&s, &reused) == CL_T111_OK);
    (void)cl_t111_session_destroy(&s);
    CHECK(a->acquires == a->releases && a->double_release == 0u);
    free(a);
}

static void test_generation_and_revoke(void) {
    Auth *a = new_auth(); ClT111Session s, other; ClT111Authority t = good(a, 1);
    ClT111ChildRef r1, r2, o1;
    ClT111RequestView r = make_request(1u);
    ClT111Status st;
    uint8_t out[8]; size_t len;
    CHECK(cl_t111_session_create(&s, &t, 10u) == CL_T111_OK);
    CHECK(cl_t111_session_create(&other, &t, 20u) == CL_T111_OK);
    CHECK(cl_t111_child_open(&s, 10u, &r, &r1) == CL_T111_OK);
    r = make_request(2u);
    CHECK(cl_t111_child_open(&s, 10u, &r, &r2) == CL_T111_OK);
    CHECK(cl_t111_child_open(&other, 20u, &r, &o1) == CL_T111_OK);
    CHECK(cl_t111_child_open(&s, 11u, &r, &r2) == CL_T111_STALE_GENERATION);
    CHECK(cl_t111_session_revoke(&s, 11u) == CL_T111_STALE_GENERATION);
    CHECK(a->releases == 0u);
    CHECK(cl_t111_session_revoke(&s, 10u) == CL_T111_OK);
    CHECK(a->releases == 2u);                                  /* all child resources revoked */
    CHECK(cl_t111_session_revoke(&s, 10u) == CL_T111_OK);      /* idempotent */
    CHECK(a->releases == 2u);
    CHECK(cl_t111_session_status(&s, &st) == CL_T111_OK);
    CHECK(st.state == CL_T111_STATE_REVOKED && st.active_children == 0u);
    CHECK(cl_t111_child_open(&s, 10u, &r, &r2) == CL_T111_REVOKED);
    CHECK(cl_t111_child_close(&s, &r1) == CL_T111_ALREADY_CLOSED);
    CHECK(cl_t111_response_build(&s, &r1, out, sizeof(out), &len) == CL_T111_REVOKED);
    CHECK(cl_t111_session_status(&other, &st) == CL_T111_OK && st.active_children == 1u);
    CHECK(cl_t111_child_close(&other, &r1) == CL_T111_STALE_GENERATION); /* ref from other gen */
    CHECK(cl_t111_child_close(&other, &o1) == CL_T111_OK);
    (void)cl_t111_session_destroy(&s);
    (void)cl_t111_session_destroy(&other);
    CHECK(a->acquires == a->releases && a->double_release == 0u);
    free(a);
}

static void test_revoke_release_failure_still_frees_all(void) {
    Auth *a = new_auth(); ClT111Session s; ClT111Authority t = good(a, 0);
    ClT111ChildRef r1, r2;
    ClT111RequestView r = make_request(1u);
    ClT111Status st;
    CHECK(cl_t111_session_create(&s, &t, 2u) == CL_T111_OK);
    CHECK(cl_t111_child_open(&s, 2u, &r, &r1) == CL_T111_OK);
    r = make_request(2u);
    CHECK(cl_t111_child_open(&s, 2u, &r, &r2) == CL_T111_OK);
    a->fail_release = 1u;
    CHECK(cl_t111_session_revoke(&s, 2u) == CL_T111_RELEASE_FAILED);
    CHECK(a->releases == 2u);                                  /* kept going after first failure */
    CHECK(cl_t111_session_status(&s, &st) == CL_T111_OK);
    CHECK(st.release_failures == 2u && st.active_children == 0u);
    (void)cl_t111_session_destroy(&s);
    free(a);
}

static void test_response_unavailable_without_contract(void) {
    Auth *a = new_auth(); ClT111Session s; ClT111Authority t = good(a, 0); ClT111ChildRef ref;
    ClT111RequestView r = make_request(1u);
    ClT111Status st;
    uint8_t out[16]; size_t len = 77u;
    CHECK(cl_t111_session_create(&s, &t, 2u) == CL_T111_OK);
    CHECK(cl_t111_child_open(&s, 2u, &r, &ref) == CL_T111_OK);
    memset(out, 0x5A, sizeof(out));
    CHECK(cl_t111_response_build(&s, &ref, out, sizeof(out), &len) == CL_T111_RESPONSE_UNAVAILABLE);
    CHECK(len == 0u && out[0] == 0x5A && out[15] == 0x5A);     /* stock bytes untouched */
    CHECK(a->builds == 0u);
    CHECK(cl_t111_session_status(&s, &st) == CL_T111_OK && st.response_contract_available == 0u);
    (void)cl_t111_session_destroy(&s);
    free(a);
}

static void test_response_with_contract(void) {
    Auth *a = new_auth(); ClT111Session s; ClT111Authority t = good(a, 1); ClT111ChildRef ref;
    ClT111RequestView r = make_request(1u);
    ClT111Status st;
    uint8_t out[8]; size_t len = 0u;
    CHECK(cl_t111_session_create(&s, &t, 2u) == CL_T111_OK);
    CHECK(cl_t111_child_open(&s, 2u, &r, &ref) == CL_T111_OK);
    CHECK(cl_t111_session_status(&s, &st) == CL_T111_OK && st.response_contract_available == 1u);
    CHECK(cl_t111_response_build(&s, &ref, out, sizeof(out), &len) == CL_T111_OK && len == 4u);
    CHECK(cl_t111_response_build(&s, &ref, out, 2u, &len) == CL_T111_AUTHORITY_FAILED && len == 0u);
    a->fail_build = 1u;
    CHECK(cl_t111_response_build(&s, &ref, out, sizeof(out), &len) == CL_T111_AUTHORITY_FAILED);
    CHECK(cl_t111_response_build(&s, &ref, NULL, sizeof(out), &len) == CL_T111_INVALID_ARGUMENT);
    CHECK(cl_t111_child_close(&s, &ref) == CL_T111_OK);
    CHECK(cl_t111_response_build(&s, &ref, out, sizeof(out), &len) == CL_T111_ALREADY_CLOSED);
    (void)cl_t111_session_destroy(&s);
    free(a);
}

static void test_reentrancy_fails_closed(void) {
    Auth *a = new_auth(); ClT111Session s; ClT111Authority t = good(a, 0); ClT111ChildRef ref;
    ClT111RequestView r = make_request(1u);
    ClT111Status st;
    CHECK(cl_t111_session_create(&s, &t, 6u) == CL_T111_OK);
    a->reenter = &s; a->reenter_gen = 6u;
    CHECK(cl_t111_child_open(&s, 6u, &r, &ref) == CL_T111_OK);
    CHECK(a->reenter_open == CL_T111_BUSY);
    CHECK(a->reenter_close == CL_T111_BUSY);
    CHECK(a->reenter_revoke == CL_T111_REVOKE_DEFERRED);
    CHECK(a->reenter_status == CL_T111_BUSY && a->reenter_status_untouched == 1u);
    /* the deferred revoke ran as soon as the outer call left the guard */
    CHECK(cl_t111_session_status(&s, &st) == CL_T111_OK);
    CHECK(st.state == CL_T111_STATE_REVOKED && st.active_children == 0u);
    CHECK(a->acquires == 1u && a->releases == 1u && a->double_release == 0u);
    CHECK(cl_t111_session_destroy(&s) == CL_T111_OK);
    free(a);
}

static void test_destroy_invalidates(void) {
    Auth *a = new_auth(); ClT111Session s; ClT111Authority t = good(a, 0); ClT111ChildRef ref;
    ClT111RequestView r = make_request(1u);
    ClT111Status st;
    CHECK(cl_t111_session_create(&s, &t, 6u) == CL_T111_OK);
    CHECK(cl_t111_child_open(&s, 6u, &r, &ref) == CL_T111_OK);
    CHECK(cl_t111_session_destroy(&s) == CL_T111_OK);
    CHECK(a->releases == 1u);
    CHECK(cl_t111_child_open(&s, 6u, &r, &ref) == CL_T111_INVALID_ARGUMENT);
    CHECK(cl_t111_session_status(&s, &st) == CL_T111_INVALID_ARGUMENT);
    CHECK(cl_t111_session_destroy(&s) == CL_T111_INVALID_ARGUMENT);
    CHECK(cl_t111_session_create(NULL, NULL, 1u) == CL_T111_INVALID_ARGUMENT);
    CHECK(cl_t111_safe_for_honda() == 0);
    free(a);
}

static void test_response_build_is_transactional(void) {
    Auth *a = new_auth(); ClT111Session s; ClT111Authority t = good(a, 1); ClT111ChildRef ref;
    ClT111RequestView r = make_request(1u);
    uint8_t out[16], before[16];
    size_t len;
    uint32_t mode;
    CHECK(cl_t111_session_create(&s, &t, 2u) == CL_T111_OK);
    CHECK(cl_t111_child_open(&s, 2u, &r, &ref) == CL_T111_OK);
    memset(out, 0x5A, sizeof(out));
    memcpy(before, out, sizeof(out));
    for (mode = 1u; mode <= 3u; ++mode) {  /* partial+fail, oversize, zero length */
        a->build_mode = mode;
        len = 77u;
        CHECK(cl_t111_response_build(&s, &ref, out, sizeof(out), &len) == CL_T111_AUTHORITY_FAILED);
        CHECK(len == 0u && memcmp(out, before, sizeof(out)) == 0);
    }
    a->build_mode = 0u;
    CHECK(cl_t111_response_build(&s, &ref, out, sizeof(out), &len) == CL_T111_OK && len == 4u);
    CHECK(memcmp(out + 4, before + 4, sizeof(out) - 4u) == 0);  /* only produced bytes written */
    {   /* capacity above the stage bound is clamped, never overrun */
        uint8_t *big = (uint8_t *)malloc(CL_T111_RESPONSE_STAGE_MAX + 64u);
        memset(big, 0x11, CL_T111_RESPONSE_STAGE_MAX + 64u);
        a->build_mode = 4u;
        CHECK(cl_t111_response_build(&s, &ref, big, CL_T111_RESPONSE_STAGE_MAX + 64u, &len) == CL_T111_OK);
        CHECK(len == CL_T111_RESPONSE_STAGE_MAX && big[CL_T111_RESPONSE_STAGE_MAX] == 0x11u);
        a->build_mode = 2u;
        CHECK(cl_t111_response_build(&s, &ref, big, CL_T111_RESPONSE_STAGE_MAX + 64u, &len) == CL_T111_AUTHORITY_FAILED);
        CHECK(len == 0u && big[0] == 0xDDu);  /* prior contents intact on failure */
        free(big);
    }
    (void)cl_t111_session_destroy(&s);
    free(a);
}

static void test_serial_never_wraps(void) {
    Auth *a = new_auth(); ClT111Session s; ClT111Authority t = good(a, 0);
    ClT111ChildRef old, extra, fresh;
    ClT111RequestView r = make_request(1u);
    ClT111Status st;
    CHECK(cl_t111_session_create(&s, &t, 2u) == CL_T111_OK);
    s.next_serial = UINT32_MAX - 2u;                       /* white-box: near the limit */
    CHECK(cl_t111_child_open(&s, 2u, &r, &old) == CL_T111_OK && old.serial == UINT32_MAX - 2u);
    r = make_request(2u);
    CHECK(cl_t111_child_open(&s, 2u, &r, &fresh) == CL_T111_OK && fresh.serial == UINT32_MAX - 1u);
    CHECK(cl_t111_child_close(&s, &fresh) == CL_T111_OK);
    r = make_request(3u);
    CHECK(cl_t111_child_open(&s, 2u, &r, &extra) == CL_T111_EXHAUSTED);   /* no wrap to 0/1 */
    CHECK(extra.serial == 0u);
    s.next_serial = 0u;                                    /* even a wrapped counter fails closed */
    CHECK(cl_t111_child_open(&s, 2u, &r, &extra) == CL_T111_EXHAUSTED);
    CHECK(cl_t111_child_close(&s, &old) == CL_T111_OK);   /* existing handles still close once */
    CHECK(cl_t111_child_close(&s, &old) != CL_T111_OK);
    CHECK(cl_t111_session_status(&s, &st) == CL_T111_OK && st.active_children == 0u);
    CHECK(a->acquires == a->releases && a->double_release == 0u);
    (void)cl_t111_session_destroy(&s);
    free(a);
}

typedef struct { ClT111Session *s; uint32_t gen; uint32_t base; } Worker;


static void *worker(void *p) {
    Worker *w = (Worker *)p;
    uint32_t i;
    for (i = 0; i < 4000u; ++i) {
        ClT111RequestView r = make_request(w->base + (i % 3u));
        ClT111ChildRef ref;
        if (cl_t111_child_open(w->s, w->gen, &r, &ref) == CL_T111_OK) {
            (void)cl_t111_child_close(w->s, &ref);
        }
    }
    return NULL;
}

static void test_status_snapshot_is_coherent(void) {
    Auth *a = new_auth(); ClT111Session s; ClT111Authority t = good(a, 0);
    ClT111ChildRef ref;
    ClT111RequestView r = make_request(1u);
    ClT111Status st;
    CHECK(cl_t111_session_create(&s, &t, 5u) == CL_T111_OK);
    CHECK(cl_t111_child_open(&s, 5u, &r, &ref) == CL_T111_OK);
    CHECK(cl_t111_session_status(&s, &st) == CL_T111_OK);
    CHECK(st.state == CL_T111_STATE_ENABLED_UNVERIFIED && st.parent_generation == 5u);
    CHECK(st.active_children == 1u && st.opened_total == 1u && st.closed_total == 0u);
    CHECK(st.integration_verified == 0u && st.safe_for_honda == 0u);
    CHECK(cl_t111_child_close(&s, &ref) == CL_T111_OK);
    CHECK(cl_t111_session_status(&s, &st) == CL_T111_OK);
    CHECK(st.active_children == 0u && st.opened_total == 1u && st.closed_total == 1u);
    CHECK(s.busy == 0u);                       /* status leaves the guard released */
    (void)cl_t111_session_destroy(&s);
    free(a);
}

typedef struct { ClT111Session *s; uint32_t incoherent; uint32_t stop; } Poller;

static void *status_poller(void *p) {
    Poller *q = (Poller *)p;
    while (!__atomic_load_n(&q->stop, __ATOMIC_SEQ_CST)) {
        ClT111Status st;
        if (cl_t111_session_status(q->s, &st) == CL_T111_OK &&
            st.opened_total - st.closed_total != st.active_children) {
            ++q->incoherent;
        }
    }
    return NULL;
}

static void test_status_races_open_close(void) {
    Auth *a = new_auth(); ClT111Session s; ClT111Authority t = good(a, 0);
    pthread_t th[2]; pthread_t poll; Worker w[2]; Poller q;
    uint32_t i;
    CHECK(cl_t111_session_create(&s, &t, 9u) == CL_T111_OK);
    q.s = &s; q.incoherent = 0u; q.stop = 0u;
    pthread_create(&poll, NULL, status_poller, &q);
    for (i = 0; i < 2u; ++i) {
        w[i].s = &s; w[i].gen = 9u; w[i].base = 5000u * (i + 1u);
        pthread_create(&th[i], NULL, worker, &w[i]);
    }
    for (i = 0; i < 2u; ++i) pthread_join(th[i], NULL);
    __atomic_store_n(&q.stop, 1u, __ATOMIC_SEQ_CST);
    pthread_join(poll, NULL);
    CHECK(q.incoherent == 0u);
    (void)cl_t111_session_revoke(&s, 9u);
    (void)cl_t111_session_destroy(&s);
    free(a);
}

static void test_concurrent_open_close_then_revoke(void) {
    Auth *a = new_auth(); ClT111Session s; ClT111Authority t = good(a, 0);
    pthread_t th[4]; Worker w[4];
    uint32_t i;
    CHECK(cl_t111_session_create(&s, &t, 8u) == CL_T111_OK);
    for (i = 0; i < 4u; ++i) {
        w[i].s = &s; w[i].gen = 8u; w[i].base = 1000u * (i + 1u);
        pthread_create(&th[i], NULL, worker, &w[i]);
    }
    for (i = 0; i < 100u; ++i) (void)cl_t111_session_revoke(&s, 8u); /* races workers */
    for (i = 0; i < 4u; ++i) pthread_join(th[i], NULL);
    CHECK(cl_t111_session_revoke(&s, 8u) == CL_T111_OK);       /* settle any deferred revoke */
    CHECK(cl_t111_session_destroy(&s) == CL_T111_OK);
    CHECK(a->acquires == a->releases);                         /* nothing leaked or doubled */
    CHECK(a->double_release == 0u);
    free(a);
}

int main(void) {
    test_disabled_by_default();
    test_invalid_capability_tables();
    test_open_close_and_request_immutable();
    test_request_validation_fail_closed();
    test_request_not_retained();
    test_authority_failures_roll_back();
    test_exhaustion_and_slot_reuse();
    test_generation_and_revoke();
    test_revoke_release_failure_still_frees_all();
    test_response_unavailable_without_contract();
    test_response_with_contract();
    test_response_build_is_transactional();
    test_serial_never_wraps();
    test_reentrancy_fails_closed();
    test_destroy_invalidates();
    test_concurrent_open_close_then_revoke();
    test_status_snapshot_is_coherent();
    test_status_races_open_close();
    if (failures != 0) {
        fprintf(stderr, "%d failure(s)\n", failures);
        return 1;
    }
    puts("type111 child boundary tests passed (host synthetic; not Honda evidence)");
    return 0;
}
