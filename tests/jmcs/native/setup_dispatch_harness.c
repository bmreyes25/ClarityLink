#include <stdint.h>
#include <stddef.h>
#ifndef CL_NATIVE_ARM
#include <stdio.h>
#endif

#include "../../../src/claritylink-jmcs/native/setup_dispatch.h"

#ifdef CL_NATIVE_ARM
/* Minimal test-only ARM EABI helper for compiler-lowered aggregate clears.
 * Volatile stores keep freestanding compilation from folding this back into
 * the same unresolved runtime call. Production dispatcher code does not use it. */
__attribute__((optnone, noinline))
void __aeabi_memclr8(void *destination, size_t length) {
    volatile unsigned char *bytes = (volatile unsigned char *)destination;
    while (length != 0) {
        *bytes++ = 0;
        --length;
    }
}
#endif

typedef struct Mock {
    const void *fallback;
    CLNativeReadiness readiness;
    CLNativePrepareStatus prepare_status;
    int32_t commit_status;
    int32_t stock_calls;
    int32_t readiness_calls;
    int32_t prepare_calls;
    int32_t commit_calls;
    int32_t rollback_calls;
    int32_t withdraw_calls;
    int32_t withdraw_parent_calls;
    int32_t callback_order_count;
    int32_t callback_order_kind[16];
    int32_t callback_order_type[16];
    int32_t stack_alignment_failures;
    const void *last_parent;
    const void *last_connection;
    uint64_t last_parent_generation;
    uint64_t last_stream_generation;
    const void *last_rollback_transaction;
} Mock;

static int32_t event(Mock *mock, int32_t kind, int32_t stream_type) {
    int32_t index = mock->callback_order_count++;
    if (index >= 16) return 1;
    mock->callback_order_kind[index] = kind;
    mock->callback_order_type[index] = stream_type;
    return 0;
}

#if defined(__arm__) && !defined(__aarch64__)
__attribute__((naked)) static uint32_t current_sp_alignment(void) {
    __asm__ volatile("mov r0, sp\n"
                     "and r0, r0, #7\n"
                     "bx lr\n");
}
#else
static uint32_t current_sp_alignment(void) { return 0; }
#endif

static void check_stack(Mock *mock) {
    if (current_sp_alignment() != 0) ++mock->stack_alignment_failures;
}

static int32_t factory_setup(void *opaque,
                             const CLNativeSetupRequest *request,
                             const void **response_entry) {
    Mock *mock = (Mock *)opaque;
    check_stack(mock);
    ++mock->stock_calls;
    if (event(mock, 1, request->stream_type)) return -1;
    *response_entry = request->opaque_request;
    return 0;
}

static CLNativeReadiness validate_type111(
    void *opaque, const CLNativeSetupRequest *request) {
    Mock *mock = (Mock *)opaque;
    check_stack(mock);
    ++mock->readiness_calls;
    (void)event(mock, 2, request->stream_type);
    mock->last_parent = request->parent_session;
    mock->last_connection = request->stream_connection;
    mock->last_parent_generation = request->parent_generation;
    mock->last_stream_generation = request->stream_generation;
    return mock->readiness;
}

static CLNativePrepareStatus prepare_type111(
    void *opaque, const CLNativeSetupRequest *request,
    void **transaction, const void **candidate_entry) {
    static int32_t transaction_sentinel;
    static int32_t candidate_sentinel;
    Mock *mock = (Mock *)opaque;
    check_stack(mock);
    ++mock->prepare_calls;
    (void)event(mock, 3, request->stream_type);
    /* A failing preparation may return a transaction to be rolled back. No
     * test callback represents successful authenticated media readiness. */
    *transaction = &transaction_sentinel;
    *candidate_entry = mock->prepare_status == CL_NATIVE_PREPARE_READY
        ? &candidate_sentinel : 0;
    return mock->prepare_status;
}

static int32_t commit_type111(void *opaque, void *transaction) {
    Mock *mock = (Mock *)opaque;
    check_stack(mock);
    ++mock->commit_calls;
    (void)transaction;
    return mock->commit_status;
}

static void rollback_type111(void *opaque,
                            const CLNativeSetupRequest *request,
                            void *transaction, const void *candidate_entry) {
    Mock *mock = (Mock *)opaque;
    check_stack(mock);
    ++mock->rollback_calls;
    mock->last_rollback_transaction = transaction ? transaction : candidate_entry;
    (void)request;
}

static int32_t withdraw_type111(void *opaque, const void *parent_session,
                                uint64_t parent_generation,
                                const void *stream_connection,
                                uint64_t stream_generation) {
    Mock *mock = (Mock *)opaque;
    ++mock->withdraw_calls;
    mock->last_parent = parent_session;
    mock->last_connection = stream_connection;
    mock->last_parent_generation = parent_generation;
    mock->last_stream_generation = stream_generation;
    return 0;
}

static int32_t withdraw_parent_type111(void *opaque,
                                       const void *parent_session,
                                       uint64_t parent_generation) {
    Mock *mock = (Mock *)opaque;
    ++mock->withdraw_parent_calls;
    mock->last_parent = parent_session;
    mock->last_parent_generation = parent_generation;
    return 0;
}

static CLNativeSetupOps make_ops(Mock *mock, int include_type111) {
    CLNativeSetupOps ops = {0};
    ops.context = mock;
    ops.factory_setup = factory_setup;
    if (include_type111) {
        ops.validate_type111 = validate_type111;
        ops.prepare_type111 = prepare_type111;
        ops.commit_type111 = commit_type111;
        ops.rollback_type111 = rollback_type111;
        ops.withdraw_type111 = withdraw_type111;
        ops.withdraw_parent_type111 = withdraw_parent_type111;
    }
    return ops;
}

static CLNativeSetupRequest make_request(int32_t stream_type,
                                         const void *opaque_request) {
    CLNativeSetupRequest request = {0};
    request.stream_type = stream_type;
    request.parent_session = (const void *)(uintptr_t)0x1100;
    request.parent_generation = 8;
    request.stream_connection = (const void *)(uintptr_t)0x2200;
    request.stream_generation = 13;
    request.accepted_auxiliary_capability =
        (const void *)(uintptr_t)0x3300;
    request.opaque_request = opaque_request;
    return request;
}

static int test_factory_order_and_type110_passthrough(void) {
    Mock mock = {0};
    int32_t request_tokens[5] = {1, 2, 3, 4, 5};
    const int32_t types[5] = {100, 111, 110, 101, 79};
    CLNativeSetupRequest requests[5];
    CLNativeSetupResult results[5];
    CLNativeSetupOps ops = make_ops(&mock, 1);
    const void *fallback = &mock.fallback;
    size_t index;
    mock.readiness = CL_NATIVE_READINESS_AUTHORITY_UNAVAILABLE;
    mock.fallback = fallback;
    for (index = 0; index < 5; ++index) {
        requests[index] = make_request(types[index], &request_tokens[index]);
    }
    if (cl_native_setup_dispatch_batch(requests, 5, fallback, &ops, results) !=
        CL_NATIVE_SETUP_BATCH_COMPLETED) return 1;
    if (mock.callback_order_count != 5 || mock.stock_calls != 4 ||
        mock.readiness_calls != 1 || mock.prepare_calls != 0) return 2;
    if (mock.callback_order_kind[0] != 1 || mock.callback_order_type[0] != 100 ||
        mock.callback_order_kind[1] != 2 || mock.callback_order_type[1] != 111 ||
        mock.callback_order_kind[2] != 1 || mock.callback_order_type[2] != 110 ||
        mock.callback_order_kind[3] != 1 || mock.callback_order_type[3] != 101 ||
        mock.callback_order_kind[4] != 1 || mock.callback_order_type[4] != 79)
        return 3;
    if (results[0].response_entry != requests[0].opaque_request) return 40;
    if (results[2].response_entry != requests[2].opaque_request) return 41;
    if (results[2].code != CL_NATIVE_SETUP_STOCK_HANDLED) return 42;
    if (results[1].response_entry != fallback) return 43;
    if (results[1].code != CL_NATIVE_SETUP_TYPE111_NOT_READY) return 44;
    if (mock.stack_alignment_failures != 0) return 5;
    return 0;
}

static int test_disabled_missing_identity_and_repeat_setup(void) {
    Mock mock = {0};
    int32_t token = 9;
    CLNativeSetupRequest request = make_request(111, &token);
    CLNativeSetupResult result;
    CLNativeSetupOps ops = make_ops(&mock, 0);
    const void *fallback = &mock.fallback;
    if (cl_native_setup_dispatch_batch(&request, 1, fallback, &ops, &result) !=
        CL_NATIVE_SETUP_BATCH_COMPLETED ||
        result.code != CL_NATIVE_SETUP_TYPE111_DISABLED ||
        result.response_entry != fallback || mock.stock_calls != 0)
        return 1;
    ops = make_ops(&mock, 1);
    request.accepted_auxiliary_capability = 0;
    if (cl_native_setup_dispatch_batch(&request, 1, fallback, &ops, &result) !=
        CL_NATIVE_SETUP_BATCH_COMPLETED ||
        result.code != CL_NATIVE_SETUP_TYPE111_DISABLED ||
        result.response_entry != fallback || mock.readiness_calls != 0)
        return 2;
    request = make_request(111, &token);
    ops.factory_setup = 0;
    if (cl_native_setup_dispatch_batch(&request, 1, fallback, &ops, &result) !=
        CL_NATIVE_SETUP_BATCH_COMPLETED ||
        result.code != CL_NATIVE_SETUP_TYPE111_DISABLED ||
        result.response_entry != fallback || mock.prepare_calls != 0)
        return 3;
    ops = make_ops(&mock, 1);
    ops.withdraw_type111 = 0;
    if (cl_native_setup_dispatch_batch(&request, 1, fallback, &ops, &result) !=
        CL_NATIVE_SETUP_BATCH_COMPLETED ||
        result.code != CL_NATIVE_SETUP_TYPE111_DISABLED ||
        result.response_entry != fallback || mock.prepare_calls != 0)
        return 4;
    ops = make_ops(&mock, 1);
    request.stream_connection = 0;
    if (cl_native_setup_dispatch_batch(&request, 1, fallback, &ops, &result) !=
        CL_NATIVE_SETUP_BATCH_COMPLETED ||
        result.code != CL_NATIVE_SETUP_TYPE111_INVALID_IDENTITY ||
        result.response_entry != fallback || mock.readiness_calls != 0)
        return 5;
    request = make_request(110, &token);
    if (cl_native_setup_dispatch_batch(&request, 1, fallback, &ops, &result) !=
        CL_NATIVE_SETUP_BATCH_COMPLETED ||
        result.code != CL_NATIVE_SETUP_STOCK_HANDLED ||
        result.response_entry != request.opaque_request)
        return 6;
    if (cl_native_setup_dispatch_batch(&request, 1, fallback, &ops, &result) !=
        CL_NATIVE_SETUP_BATCH_COMPLETED || mock.stock_calls != 2)
        return 7;
    return mock.stack_alignment_failures == 0 ? 0 : 8;
}

static int test_duplicate_and_readiness_fail_closed(void) {
    Mock mock = {0};
    int32_t tokens[2] = {10, 11};
    CLNativeSetupRequest requests[2];
    CLNativeSetupResult results[2];
    CLNativeSetupOps ops = make_ops(&mock, 1);
    const void *fallback = &mock.fallback;
    mock.readiness = CL_NATIVE_READINESS_TRANSPORT_UNREADY;
    requests[0] = make_request(111, &tokens[0]);
    requests[1] = make_request(111, &tokens[1]);
    if (cl_native_setup_dispatch_batch(requests, 2, fallback, &ops, results) !=
        CL_NATIVE_SETUP_BATCH_COMPLETED ||
        results[0].code != CL_NATIVE_SETUP_TYPE111_NOT_READY ||
        results[1].code != CL_NATIVE_SETUP_TYPE111_DUPLICATE ||
        results[0].response_entry != fallback || results[1].response_entry != fallback ||
        mock.readiness_calls != 1 || mock.prepare_calls != 0 ||
        mock.commit_calls != 0 || mock.rollback_calls != 0)
        return 1;
    if (mock.stack_alignment_failures != 0) return 2;
    {
        Mock stale = {0};
        CLNativeSetupRequest stale_request = make_request(111, &tokens[0]);
        CLNativeSetupResult stale_result;
        CLNativeSetupOps stale_ops = make_ops(&stale, 1);
        stale.readiness = CL_NATIVE_READINESS_STALE_PARENT;
        if (cl_native_setup_dispatch_batch(&stale_request, 1, fallback,
                                           &stale_ops, &stale_result) !=
                CL_NATIVE_SETUP_BATCH_COMPLETED ||
            stale_result.code != CL_NATIVE_SETUP_TYPE111_NOT_READY ||
            stale_result.readiness_result != CL_NATIVE_READINESS_STALE_PARENT ||
            stale.prepare_calls != 0 || stale_result.response_entry != fallback)
            return 3;
    }
    return 0;
}

static int test_partial_setup_rollback_and_serializer_failure(void) {
    Mock mock = {0};
    int32_t token = 12;
    CLNativeSetupRequest request = make_request(111, &token);
    CLNativeSetupResult result;
    CLNativeSetupOps ops = make_ops(&mock, 1);
    const void *fallback = &mock.fallback;
    mock.readiness = CL_NATIVE_READINESS_READY;
    mock.prepare_status = CL_NATIVE_PREPARE_ALLOCATION_FAILED;
    if (cl_native_setup_dispatch_batch(&request, 1, fallback, &ops, &result) !=
        CL_NATIVE_SETUP_BATCH_COMPLETED ||
        result.code != CL_NATIVE_SETUP_TYPE111_PREPARE_FAILED ||
        result.response_entry != fallback || mock.prepare_calls != 1 ||
        mock.rollback_calls != 1 || mock.commit_calls != 0 ||
        mock.last_rollback_transaction == 0)
        return 1;

    /* Drive the finalize failure branch with an opaque pending transaction;
     * this does not model authentication or a valid Type111 response. */
    {
        static int32_t pending_transaction;
        static int32_t uncommitted_candidate;
        result.code = CL_NATIVE_SETUP_TYPE111_PREPARED;
        result.response_entry = fallback;
        result.candidate_entry = &uncommitted_candidate;
        result.transaction = &pending_transaction;
        if (cl_native_setup_finalize_type111(&result, &ops, 0) !=
                CL_NATIVE_SETUP_TYPE111_SERIALIZER_FAILED ||
            result.response_entry != fallback || result.candidate_entry != 0 ||
            result.transaction != 0 || result.request != 0 ||
            mock.commit_calls != 0 ||
            mock.rollback_calls != 2)
            return 2;
    }
    return mock.stack_alignment_failures == 0 ? 0 : 3;
}

static int test_commit_failure_and_teardown_forwarding(void) {
    Mock mock = {0};
    CLNativeSetupOps ops = make_ops(&mock, 1);
    CLNativeSetupResult result = {0};
    static int32_t transaction;
    static int32_t candidate;
    const void *fallback = &mock.fallback;
    const void *parent = (const void *)(uintptr_t)0x4400;
    const void *connection = (const void *)(uintptr_t)0x5500;
    mock.commit_status = -1;
    result.code = CL_NATIVE_SETUP_TYPE111_PREPARED;
    result.response_entry = fallback;
    result.candidate_entry = &candidate;
    result.transaction = &transaction;
    if (cl_native_setup_finalize_type111(&result, &ops, 1) !=
            CL_NATIVE_SETUP_TYPE111_COMMIT_FAILED ||
        result.response_entry != fallback || result.candidate_entry != 0 ||
        result.transaction != 0 || result.request != 0 ||
        mock.commit_calls != 1 ||
        mock.rollback_calls != 1)
        return 1;
    if (cl_native_setup_withdraw_type111(&ops, parent, 17, connection, 23) != 0 ||
        mock.withdraw_calls != 1 || mock.last_parent != parent ||
        mock.last_connection != connection || mock.last_parent_generation != 17 ||
        mock.last_stream_generation != 23)
        return 2;
    if (cl_native_setup_withdraw_parent_type111(&ops, parent, 17) != 0 ||
        mock.withdraw_parent_calls != 1 || mock.last_parent != parent ||
        mock.last_parent_generation != 17)
        return 3;
    if (cl_native_setup_withdraw_type111(&ops, 0, 17, connection, 23) != -1 ||
        cl_native_setup_withdraw_parent_type111(&ops, parent, 0) != -1)
        return 4;
    return mock.stack_alignment_failures == 0 ? 0 : 5;
}

static int test_batch_bounds_and_no_partial_writes(void) {
    CLNativeSetupRequest requests[CL_NATIVE_SETUP_MAX_REQUESTS + 1u] = {{0}};
    CLNativeSetupResult results[CL_NATIVE_SETUP_MAX_REQUESTS + 1u];
    size_t index;
    for (index = 0; index < CL_NATIVE_SETUP_MAX_REQUESTS + 1u; ++index) {
        requests[index].opaque_request = (const void *)(uintptr_t)(index + 1u);
        results[index].code = CL_NATIVE_SETUP_TYPE111_COMMITTED;
        results[index].response_entry = (const void *)(uintptr_t)0xdead;
    }
    if (cl_native_setup_dispatch_batch(requests,
            CL_NATIVE_SETUP_MAX_REQUESTS + 1u, 0, 0, results) !=
        CL_NATIVE_SETUP_TOO_MANY_REQUESTS)
        return 1;
    if (results[0].code != CL_NATIVE_SETUP_TYPE111_COMMITTED ||
        results[0].response_entry != (const void *)(uintptr_t)0xdead)
        return 2;
    if (cl_native_setup_dispatch_batch(0, 1, 0, 0, results) !=
        CL_NATIVE_SETUP_INVALID_ARGUMENT)
        return 3;
    return 0;
}

static int run_all(void) {
    int result = test_factory_order_and_type110_passthrough();
    if (result) return 100 + result;
    result = test_disabled_missing_identity_and_repeat_setup();
    if (result) return 200 + result;
    result = test_duplicate_and_readiness_fail_closed();
    if (result) return 300 + result;
    result = test_partial_setup_rollback_and_serializer_failure();
    if (result) return 400 + result;
    result = test_commit_failure_and_teardown_forwarding();
    if (result) return 500 + result;
    result = test_batch_bounds_and_no_partial_writes();
    if (result) return 600 + result;
    return 0;
}

int32_t cl_native_setup_dispatch_test_entry(void) { return run_all(); }

#ifndef CL_NATIVE_ARM
int main(void) {
    const int result = run_all();
    if (result != 0) {
        (void)fprintf(stderr, "setup dispatch harness failure: %d\n", result);
        return result;
    }
    (void)puts("NATIVE_SETUP_DISPATCH_PASS type110_preserved=PASS type111_fail_closed=PASS rollback=PASS");
    return 0;
}
#endif
