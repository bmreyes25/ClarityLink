#include "native_setup_txn.h"

#include <pthread.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    pthread_mutex_t mutex;
    uint32_t gate_held;
    uint32_t next_token;
    uint32_t next_generation;
    uint32_t next_port;
    uint32_t fail_generation;
    uint32_t fail_listener;
    uint32_t fail_commit;
    uint32_t fail_release_once;
    uint32_t claims;
    uint32_t releases;
    uint32_t generations_prepared;
    uint32_t generations_committed;
    uint32_t generations_rolled_back;
    uint32_t listeners_prepared;
    uint32_t listeners_rolled_back;
    uint32_t busy_count;
} TestServiceState;

_Static_assert(sizeof(ClPreparedTxn) == 44, "transaction retains only scalar project state");
_Static_assert(sizeof(((ClPreparedTxn *)0)->gate_token) == sizeof(uint32_t), "fixed-width token");

static int32_t service_claim(void *opaque, uint32_t *out) {
    TestServiceState *state = (TestServiceState *)opaque;
    int32_t result = 1;
    if (out == NULL) return -1;
    pthread_mutex_lock(&state->mutex);
    if (state->gate_held != 0u) {
        ++state->busy_count;
        result = 0;
    } else {
        state->gate_held = 1u;
        *out = ++state->next_token;
        ++state->claims;
    }
    pthread_mutex_unlock(&state->mutex);
    return result;
}

static int32_t service_release(void *opaque, uint32_t token) {
    TestServiceState *state = (TestServiceState *)opaque;
    pthread_mutex_lock(&state->mutex);
    if (state->fail_release_once != 0u) {
        state->fail_release_once = 0u;
        pthread_mutex_unlock(&state->mutex);
        return -1;
    }
    if (state->gate_held == 0u || token == 0u) {
        pthread_mutex_unlock(&state->mutex);
        return -1;
    }
    state->gate_held = 0u;
    ++state->releases;
    pthread_mutex_unlock(&state->mutex);
    return 1;
}

static int32_t service_generation_prepare(void *opaque, uint32_t low, uint32_t high,
                                          uint32_t *out) {
    TestServiceState *state = (TestServiceState *)opaque;
    (void)low;
    (void)high;
    pthread_mutex_lock(&state->mutex);
    if (state->fail_generation != 0u || out == NULL) {
        pthread_mutex_unlock(&state->mutex);
        return -1;
    }
    *out = ++state->next_generation;
    ++state->generations_prepared;
    pthread_mutex_unlock(&state->mutex);
    return 1;
}

static int32_t service_listener_prepare(void *opaque, uint32_t generation, uint32_t *out) {
    TestServiceState *state = (TestServiceState *)opaque;
    if (generation == 0u || out == NULL) return -1;
    pthread_mutex_lock(&state->mutex);
    if (state->fail_listener != 0u) {
        pthread_mutex_unlock(&state->mutex);
        return -1;
    }
    *out = ++state->next_port;
    ++state->listeners_prepared;
    pthread_mutex_unlock(&state->mutex);
    return 1;
}

static int32_t service_generation_commit(void *opaque, uint32_t generation) {
    TestServiceState *state = (TestServiceState *)opaque;
    pthread_mutex_lock(&state->mutex);
    if (generation == 0u || state->fail_commit != 0u) {
        pthread_mutex_unlock(&state->mutex);
        return -1;
    }
    ++state->generations_committed;
    pthread_mutex_unlock(&state->mutex);
    return 1;
}

static int32_t service_generation_rollback(void *opaque, uint32_t generation) {
    TestServiceState *state = (TestServiceState *)opaque;
    if (generation == 0u) return -1;
    pthread_mutex_lock(&state->mutex);
    ++state->generations_rolled_back;
    pthread_mutex_unlock(&state->mutex);
    return 1;
}

static int32_t service_listener_rollback(void *opaque, uint32_t generation) {
    TestServiceState *state = (TestServiceState *)opaque;
    if (generation == 0u) return -1;
    pthread_mutex_lock(&state->mutex);
    ++state->listeners_rolled_back;
    pthread_mutex_unlock(&state->mutex);
    return 1;
}

static ClSetupServices services_for(TestServiceState *state) {
    ClSetupServices ops = {state, service_claim, service_release,
                           service_generation_prepare, service_listener_prepare,
                           service_generation_commit, service_generation_rollback,
                           service_listener_rollback};
    return ops;
}

static void service_state_init(TestServiceState *state) {
    memset(state, 0, sizeof(*state));
    state->next_port = 42000u;
    pthread_mutex_init(&state->mutex, NULL);
}

static void service_state_destroy(TestServiceState *state) {
    pthread_mutex_destroy(&state->mutex);
}

static ClSetupCall make_call(ClSyntheticRequest *request,
                             ClSyntheticResponse *response,
                             int32_t *status, const void *session) {
    ClSetupCall call = {request, response, status, session, (uintptr_t)status};
    return call;
}

static void init_type111(ClSyntheticRequest *request, ClSyntheticResponse *response,
                         int type111_first) {
    memset(request, 0, sizeof(*request));
    memset(response, 0, sizeof(*response));
    request->magic = CL_REQUEST_MAGIC;
    request->count = 2u;
    if (type111_first != 0) {
        request->streams[0] = (ClSyntheticRequestStream){111u, 0x55667788u, 1u};
        request->streams[1] = (ClSyntheticRequestStream){110u, 0x11223344u, 1u};
    } else {
        request->streams[0] = (ClSyntheticRequestStream){110u, 0x11223344u, 1u};
        request->streams[1] = (ClSyntheticRequestStream){111u, 0x55667788u, 1u};
    }
    response->magic = CL_RESPONSE_MAGIC;
    response->count = 1u;
    response->streams[0] = (ClSyntheticResponseStream){110u, 4000u};
}

#define CHECK(expr) do { if (!(expr)) { \
    fprintf(stderr, "native txn assertion failed at %s:%d: %s\n", __FILE__, __LINE__, #expr); \
    return 1; } } while (0)

static int test_bypass_and_success(void) {
    TestServiceState state;
    ClSetupServices ops;
    ClSyntheticRequest request;
    ClSyntheticResponse response;
    ClSyntheticResponse original;
    ClPreparedTxn txn;
    ClSetupCall call;
    int32_t status = 0;
    int marker = 7;
    service_state_init(&state);
    ops = services_for(&state);
    init_type111(&request, &response, 0);
    request.streams[1].type = 110u;
    original = response;
    call = make_call(&request, &response, &status, &marker);
    memset(&txn, 0, sizeof(txn));
    CHECK(cl_setup_prepare(&call, &txn, &ops) == CL_SETUP_BYPASS);
    CHECK(memcmp(&response, &original, sizeof(response)) == 0);
    CHECK(state.claims == 0u);
    CHECK(cl_setup_finish(&call, &txn, CL_SERIALIZER_SUCCESS, 1, &ops) == CL_SETUP_BYPASS);

    init_type111(&request, &response, 1);
    original = response;
    call = make_call(&request, &response, &status, &marker);
    CHECK(cl_setup_prepare(&call, &txn, &ops) == CL_SETUP_PREPARED);
    CHECK(response.count == 2u && response.streams[0].type == original.streams[0].type);
    CHECK(response.streams[0].data_port == original.streams[0].data_port);
    CHECK(response.streams[1].type == 111u && response.streams[1].data_port == 42001u);
    CHECK(txn.state == CL_TXN_PREPARED && txn.generation != 0u);
    CHECK(cl_setup_finish(&call, &txn, CL_SERIALIZER_SUCCESS, 1, &ops) == CL_SETUP_PREPARED);
    CHECK(txn.state == CL_TXN_COMMITTED && state.generations_committed == 1u);
    CHECK(state.gate_held == 0u && state.releases == 1u);
    service_state_destroy(&state);
    return 0;
}

static int test_rejections_and_rollback(void) {
    TestServiceState state;
    ClSetupServices ops;
    ClSyntheticRequest request;
    ClSyntheticResponse response;
    ClSyntheticResponse original;
    ClPreparedTxn txn;
    ClSetupCall call;
    int32_t status = 0;
    int marker = 9;
    service_state_init(&state);
    ops = services_for(&state);
    init_type111(&request, &response, 0);
    original = response;
    call = make_call(&request, &response, &status, &marker);
    memset(&txn, 0, sizeof(txn));
    request.count = CL_MAX_STREAMS + 1u;
    CHECK(cl_setup_prepare(&call, &txn, &ops) == CL_SETUP_REJECTED);
    CHECK(memcmp(&response, &original, sizeof(response)) == 0 && state.claims == 0u);
    init_type111(&request, &response, 0);
    request.streams[0].stream_id_low = request.streams[1].stream_id_low;
    request.streams[0].stream_id_high = request.streams[1].stream_id_high;
    CHECK(cl_setup_prepare(&call, &txn, &ops) == CL_SETUP_REJECTED);
    init_type111(&request, &response, 0);
    request.streams[0].type = 111u;
    CHECK(cl_setup_prepare(&call, &txn, &ops) == CL_SETUP_REJECTED);
    init_type111(&request, &response, 0);
    request.magic = 0u;
    CHECK(cl_setup_prepare(&call, &txn, &ops) == CL_SETUP_REJECTED);

    init_type111(&request, &response, 0);
    original = response;
    call = make_call(&request, &response, &status, &marker);
    state.fail_listener = 1u;
    CHECK(cl_setup_prepare(&call, &txn, &ops) == CL_SETUP_INTERNAL_ERROR);
    CHECK(state.generations_rolled_back == 1u && state.gate_held == 0u);
    CHECK(memcmp(&response, &original, sizeof(response)) == 0);
    state.fail_listener = 0u;
    CHECK(cl_setup_prepare(&call, &txn, &ops) == CL_SETUP_PREPARED);
    CHECK(cl_setup_finish(&call, &txn, 500, 0, &ops) == CL_SETUP_REJECTED);
    CHECK(txn.state == CL_TXN_ROLLED_BACK && state.listeners_rolled_back == 1u);
    CHECK(state.gate_held == 0u && memcmp(&response, &original, sizeof(response)) == 0);

    CHECK(cl_setup_prepare(&call, &txn, &ops) == CL_SETUP_PREPARED);
    state.fail_commit = 1u;
    CHECK(cl_setup_finish(&call, &txn, CL_SERIALIZER_SUCCESS, 1, &ops) == CL_SETUP_REJECTED);
    CHECK(state.listeners_rolled_back == 2u && state.gate_held == 0u);
    state.fail_commit = 0u;

    CHECK(cl_setup_prepare(&call, &txn, &ops) == CL_SETUP_PREPARED);
    state.fail_release_once = 1u;
    CHECK(cl_setup_finish(&call, &txn, CL_SERIALIZER_SUCCESS, 1, &ops) == CL_SETUP_INTERNAL_ERROR);
    CHECK(state.listeners_rolled_back == 3u && state.gate_held == 0u);
    service_state_destroy(&state);
    return 0;
}

static int test_borrowed_pointer_non_retention_and_busy_policy(void) {
    TestServiceState state;
    ClSetupServices ops;
    ClSyntheticRequest request_a, request_b;
    ClSyntheticResponse response_a, response_b;
    ClPreparedTxn txn_a, txn_b;
    ClSetupCall call_a, call_b;
    int32_t status_a = 0, status_b = 0;
    int session_a = 1, session_b = 2;
    unsigned char txn_bytes[sizeof(ClPreparedTxn)];
    size_t i;
    service_state_init(&state);
    ops = services_for(&state);
    init_type111(&request_a, &response_a, 0);
    init_type111(&request_b, &response_b, 1);
    call_a = make_call(&request_a, &response_a, &status_a, &session_a);
    call_b = make_call(&request_b, &response_b, &status_b, &session_a);
    memset(&txn_a, 0, sizeof(txn_a));
    memset(&txn_b, 0, sizeof(txn_b));
    CHECK(cl_setup_prepare(&call_a, &txn_a, &ops) == CL_SETUP_PREPARED);
    CHECK(cl_setup_prepare(&call_b, &txn_b, &ops) == CL_SETUP_BUSY);
    CHECK(cl_setup_finish(&call_b, &txn_b, CL_SERIALIZER_SUCCESS, 0, &ops) == CL_SETUP_BYPASS);
    call_b.session = &session_b;
    CHECK(cl_setup_prepare(&call_b, &txn_b, &ops) == CL_SETUP_BUSY);
    CHECK(response_b.count == 1u && response_b.streams[0].type == 110u);
    CHECK(cl_setup_finish(&call_b, &txn_b, CL_SERIALIZER_SUCCESS, 0, &ops) == CL_SETUP_BYPASS);
    CHECK(cl_setup_finish(&call_a, &txn_a, CL_SERIALIZER_SUCCESS, 1, &ops) == CL_SETUP_PREPARED);

    CHECK(cl_setup_prepare(&call_b, &txn_b, &ops) == CL_SETUP_PREPARED);
    memcpy(txn_bytes, &txn_b, sizeof(txn_b));
    {
        const uintptr_t borrowed[] = {(uintptr_t)call_b.request, (uintptr_t)call_b.response,
                                      (uintptr_t)call_b.status_out, (uintptr_t)call_b.session,
                                      (uintptr_t)&call_b};
        for (i = 0; i + sizeof(uintptr_t) <= sizeof(txn_bytes); ++i) {
            size_t j;
            for (j = 0; j < sizeof(borrowed) / sizeof(borrowed[0]); ++j) {
                if (memcmp(txn_bytes + i, &borrowed[j], sizeof(uintptr_t)) == 0) return 1;
            }
        }
    }
    CHECK(cl_setup_finish(&call_b, &txn_b, CL_SERIALIZER_SUCCESS, 1, &ops) == CL_SETUP_PREPARED);
    service_state_destroy(&state);
    return 0;
}

typedef struct {
    TestServiceState *services;
    uint32_t thread_id;
    uint32_t prepared;
    uint32_t busy;
} ThreadInput;

static void *overlap_worker(void *opaque) {
    ThreadInput *input = (ThreadInput *)opaque;
    ClSetupServices ops = services_for(input->services);
    ClSyntheticRequest request;
    ClSyntheticResponse response;
    ClPreparedTxn txn;
    ClSetupCall call;
    int32_t status = 0;
    int session_marker = (int)input->thread_id;
    uint32_t i;
    for (i = 0; i < 250u; ++i) {
        int32_t result;
        init_type111(&request, &response, (int)(i & 1u));
        request.streams[0].stream_id_low += input->thread_id * 1000u;
        request.streams[1].stream_id_low += input->thread_id * 1000u;
        call = make_call(&request, &response, &status, &session_marker);
        memset(&txn, 0, sizeof(txn));
        result = cl_setup_prepare(&call, &txn, &ops);
        if (result == CL_SETUP_PREPARED) {
            ++input->prepared;
            (void)sched_yield();
            (void)cl_setup_finish(&call, &txn, CL_SERIALIZER_SUCCESS, 1, &ops);
        } else if (result == CL_SETUP_BUSY) {
            ++input->busy;
        } else {
            return (void *)1;
        }
    }
    return NULL;
}

static int test_concurrent_calls_are_serialized_without_session_pointers(void) {
    TestServiceState state;
    enum { THREADS = 6 };
    pthread_t threads[THREADS];
    ThreadInput inputs[THREADS];
    size_t i;
    uint32_t prepared = 0;
    uint32_t busy = 0;
    service_state_init(&state);
    for (i = 0; i < THREADS; ++i) {
        inputs[i] = (ThreadInput){&state, (uint32_t)i + 1u, 0u, 0u};
        CHECK(pthread_create(&threads[i], NULL, overlap_worker, &inputs[i]) == 0);
    }
    for (i = 0; i < THREADS; ++i) {
        void *result = NULL;
        CHECK(pthread_join(threads[i], &result) == 0 && result == NULL);
        prepared += inputs[i].prepared;
        busy += inputs[i].busy;
    }
    CHECK(prepared > 0u && busy > 0u);
    CHECK(prepared + busy == THREADS * 250u);
    CHECK(state.gate_held == 0u && state.claims == state.releases);
    service_state_destroy(&state);
    return 0;
}

static int test_deterministic_malformed_input_sweep(void) {
    TestServiceState state;
    ClSetupServices ops;
    uint32_t value = 0x12345678u;
    unsigned int i;
    service_state_init(&state);
    ops = services_for(&state);
    for (i = 0; i < 10000u; ++i) {
        ClSyntheticRequest request;
        ClSyntheticResponse response;
        ClPreparedTxn txn;
        ClSetupCall call;
        int32_t status = 0;
        int marker = 3;
        value = value * 1664525u + 1013904223u;
        memset(&request, 0, sizeof(request));
        memset(&response, 0, sizeof(response));
        request.magic = (value & 1u) ? CL_REQUEST_MAGIC : value;
        request.count = (value >> 1) % (CL_MAX_STREAMS + 3u);
        request.streams[0].type = (value >> 4) & 0xffu;
        request.streams[0].stream_id_low = value;
        request.streams[0].stream_id_high = value ^ 0xa5a5a5a5u;
        response.magic = CL_RESPONSE_MAGIC;
        response.count = value % (CL_MAX_STREAMS + 2u);
        call = make_call(&request, &response, &status, &marker);
        memset(&txn, 0, sizeof(txn));
        (void)cl_setup_prepare(&call, &txn, &ops);
        if (txn.state == CL_TXN_PREPARED) {
            (void)cl_setup_finish(&call, &txn, 500, 0, &ops);
        }
        CHECK(state.gate_held == 0u);
    }
    service_state_destroy(&state);
    return 0;
}

int main(void) {
    if (test_bypass_and_success() || test_rejections_and_rollback() ||
        test_borrowed_pointer_non_retention_and_busy_policy() ||
        test_concurrent_calls_are_serialized_without_session_pointers() ||
        test_deterministic_malformed_input_sweep()) {
        return 1;
    }
    puts("native setup transaction: core, rollback, borrowed pointers, BUSY policy, concurrency, malformed sweep passed");
    return 0;
}
