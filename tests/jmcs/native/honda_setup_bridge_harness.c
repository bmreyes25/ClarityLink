#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "../../../src/claritylink-jmcs/native/honda_setup_bridge.h"

typedef struct MockResponse {
    int stock_marker;
    const void *type110_entry;
    const void *type111_entry;
} MockResponse;

typedef struct MockState {
    int stock_calls;
    int extract_calls;
    int build_calls;
    int release_calls;
    int stock_release_calls;
    int validate_calls;
    int prepare_calls;
    int commit_calls;
    int rollback_calls;
    int withdraw_calls;
    int withdraw_parent_calls;
    int stock_status;
    int extract_count;
    int extract_result;
    int build_status;
    int validate_ready;
    int authority_unavailable;
    int commit_status;
    int withdraw_status;
    int withdraw_parent_status;
    void *session;
    const void *request;
    const void *stream_descriptor;
    MockResponse stock_response;
    MockResponse candidate_response;
    int child_resource;
    int child_entry;
} MockState;

static MockState *g_stock_mock;

static int32_t stock_setup(void *session, const void *request, void **response) {
    MockState *mock = g_stock_mock;
    /* The synthetic test uses fixed sentinel identity values. */
    if (session != (void *)(uintptr_t)0x1110 ||
        request != (const void *)(uintptr_t)0x2220 || !response)
        return -99;
    if (!mock) return -99;
    ++mock->stock_calls;
    mock->stock_response.stock_marker = 42;
    mock->stock_response.type110_entry = (const void *)(uintptr_t)0x4440;
    *response = &mock->stock_response;
    return mock->stock_status;
}

static CLHondaExtractStatus extract_type111(
    void *context, void *session, const void *request,
    CLNativeSetupRequest *out_request, size_t *out_count) {
    MockState *mock = (MockState *)context;
    ++mock->extract_calls;
    if (session != mock->session || request != mock->request || !out_request ||
        !out_count)
        return CL_HONDA_EXTRACT_INVALID;
    *out_count = (size_t)mock->extract_count;
    if (mock->extract_result != CL_HONDA_EXTRACT_ONE_TYPE111)
        return (CLHondaExtractStatus)mock->extract_result;
    memset(out_request, 0, sizeof(*out_request));
    out_request->stream_type = 111;
    out_request->parent_session = mock->session;
    out_request->parent_generation = 3;
    out_request->stream_connection = (const void *)(uintptr_t)0x5550;
    out_request->stream_generation = 8;
    out_request->accepted_auxiliary_capability = (const void *)(uintptr_t)0x6660;
    out_request->opaque_request = mock->stream_descriptor;
    return CL_HONDA_EXTRACT_ONE_TYPE111;
}

static int32_t build_candidate(void *context, const void *stock_response,
                               const void *entry, void **out_candidate) {
    MockState *mock = (MockState *)context;
    ++mock->build_calls;
    if (!stock_response || stock_response != &mock->stock_response || !entry ||
        !out_candidate)
        return -1;
    mock->candidate_response = mock->stock_response;
    mock->candidate_response.type111_entry = entry;
    *out_candidate = &mock->candidate_response;
    if (mock->build_status != 0) return mock->build_status;
    return 0;
}

static void release_candidate(void *context, void *response) {
    MockState *mock = (MockState *)context;
    if (response == &mock->candidate_response) ++mock->release_calls;
    else if (response == &mock->stock_response) ++mock->stock_release_calls;
}

static CLNativeReadiness validate_child(void *context,
                                        const CLNativeSetupRequest *request) {
    MockState *mock = (MockState *)context;
    ++mock->validate_calls;
    if (request->accepted_auxiliary_capability != (const void *)(uintptr_t)0x6660)
        return CL_NATIVE_READINESS_AUTHORITY_UNAVAILABLE;
    if (mock->authority_unavailable)
        return CL_NATIVE_READINESS_AUTHORITY_UNAVAILABLE;
    return mock->validate_ready ? CL_NATIVE_READINESS_READY
                                : CL_NATIVE_READINESS_TRANSPORT_UNREADY;
}

static CLNativePrepareStatus prepare_child(void *context,
                                           const CLNativeSetupRequest *request,
                                           void **transaction,
                                           const void **entry) {
    MockState *mock = (MockState *)context;
    ++mock->prepare_calls;
    if (request->parent_session != mock->session || !transaction || !entry)
        return CL_NATIVE_PREPARE_ERROR;
    *transaction = &mock->child_resource;
    *entry = &mock->child_entry;
    return CL_NATIVE_PREPARE_READY;
}

static int32_t commit_child(void *context, void *transaction) {
    MockState *mock = (MockState *)context;
    ++mock->commit_calls;
    if (transaction != &mock->child_resource) return -1;
    return mock->commit_status;
}

static void rollback_child(void *context, void *transaction,
                           const void *entry) {
    MockState *mock = (MockState *)context;
    if (transaction == &mock->child_resource || entry == &mock->child_entry)
        ++mock->rollback_calls;
}

static int32_t withdraw_child(void *context, const void *parent,
                              uint64_t parent_generation,
                              const void *connection,
                              uint64_t stream_generation) {
    MockState *mock = (MockState *)context;
    if (parent != mock->session || parent_generation != 3 ||
        connection != (const void *)(uintptr_t)0x5550 || stream_generation != 8)
        return -1;
    ++mock->withdraw_calls;
    return mock->withdraw_status;
}

static int32_t withdraw_parent(void *context, const void *parent,
                               uint64_t parent_generation) {
    MockState *mock = (MockState *)context;
    if (parent != mock->session || parent_generation != 3) return -1;
    ++mock->withdraw_parent_calls;
    return mock->withdraw_parent_status;
}

static void configure(MockState *mock, CLHondaSetupBridgeBindings *bindings) {
    memset(mock, 0, sizeof(*mock));
    mock->session = (void *)(uintptr_t)0x1110;
    mock->request = (const void *)(uintptr_t)0x2220;
    g_stock_mock = mock;
    mock->stream_descriptor = (const void *)(uintptr_t)0x7770;
    mock->extract_count = 1;
    mock->extract_result = CL_HONDA_EXTRACT_ONE_TYPE111;
    mock->validate_ready = 1;
    memset(bindings, 0, sizeof(*bindings));
    bindings->context = mock;
    /* The stock callback has the target ABI signature but routes to the
       synthetic fixture through its test-only sentinel context. */
    bindings->original_setup = stock_setup;
    bindings->extract_type111 = extract_type111;
    bindings->build_response_candidate = build_candidate;
    bindings->release_response = release_candidate;
    bindings->type111_ops.context = mock;
    bindings->type111_ops.validate_type111 = validate_child;
    bindings->type111_ops.prepare_type111 = prepare_child;
    bindings->type111_ops.commit_type111 = commit_child;
    bindings->type111_ops.rollback_type111 = rollback_child;
    bindings->type111_ops.withdraw_type111 = withdraw_child;
    bindings->type111_ops.withdraw_parent_type111 = withdraw_parent;
}

static int test_stock_passthrough_and_failure(void) {
    MockState mock;
    CLHondaSetupBridgeBindings bindings;
    CLHondaSetupBridgeResult result;
    configure(&mock, &bindings);
    if (cl_honda_setup_bridge_call(&bindings, 0, mock.session, mock.request,
                                   &result) != CL_HONDA_BRIDGE_STOCK_ONLY ||
        mock.stock_calls != 1 || mock.extract_calls != 0 ||
        result.selected_response != &mock.stock_response ||
        result.stock_status != 0)
        return 1;
    mock.stock_calls = 0;
    mock.stock_status = -77;
    if (cl_honda_setup_bridge_call(&bindings, 1, mock.session, mock.request,
                                   &result) != CL_HONDA_BRIDGE_STOCK_ERROR ||
        mock.stock_calls != 1 || mock.extract_calls != 0 ||
        result.stock_status != -77 || result.selected_response != &mock.stock_response)
        return 2;
    return 0;
}

static int test_child_pending_commit_and_original_preservation(void) {
    MockState mock;
    CLHondaSetupBridgeBindings bindings;
    CLHondaSetupBridgeResult result;
    configure(&mock, &bindings);
    if (cl_honda_setup_bridge_call(&bindings, 1, mock.session, mock.request,
                                   &result) != CL_HONDA_BRIDGE_TYPE111_PENDING ||
        mock.stock_calls != 1 || mock.extract_calls != 1 ||
        mock.prepare_calls != 1 || mock.build_calls != 1 ||
        result.selected_response != &mock.stock_response ||
        result.candidate_response != &mock.candidate_response ||
        mock.stock_response.type110_entry != (const void *)(uintptr_t)0x4440 ||
        mock.stock_response.type111_entry != 0 ||
        mock.candidate_response.type110_entry != mock.stock_response.type110_entry ||
        mock.candidate_response.type111_entry != &mock.child_entry)
        return 1;
    if (cl_honda_setup_bridge_complete(&result, 1) !=
            CL_HONDA_BRIDGE_PENDING_DELIVERY ||
        mock.commit_calls != 1 || mock.rollback_calls != 0 ||
        !result.awaiting_delivery || result.pending ||
        result.selected_response != &mock.candidate_response)
        return 2;
    /* Replacing the caller's binding table after prepare cannot redirect
       delivery cleanup to another callback context. */
    bindings.context = 0;
    bindings.type111_ops.withdraw_type111 = 0;
    if (cl_honda_setup_bridge_delivery(&result, CL_HONDA_DELIVERY_SENT) !=
            CL_HONDA_BRIDGE_TYPE111_COMMITTED ||
        mock.stock_release_calls != 1 || mock.release_calls != 1 ||
        !result.delivery_confirmed || result.stock_response ||
        result.candidate_response)
        return 3;
    if (cl_honda_setup_bridge_parent_ended(&result) !=
            CL_HONDA_BRIDGE_PARENT_ENDED || mock.withdraw_parent_calls != 1 ||
        cl_honda_setup_bridge_parent_ended(&result) !=
            CL_HONDA_BRIDGE_PARENT_ENDED || mock.withdraw_parent_calls != 1)
        return 4;
    return 0;
}

static int test_missing_binding_and_no_capability_fall_back(void) {
    MockState mock;
    CLHondaSetupBridgeBindings bindings;
    CLHondaSetupBridgeResult result;
    configure(&mock, &bindings);
    bindings.extract_type111 = 0;
    if (cl_honda_setup_bridge_call(&bindings, 1, mock.session, mock.request,
                                   &result) != CL_HONDA_BRIDGE_BINDING_UNAVAILABLE ||
        mock.stock_calls != 1 || result.selected_response != &mock.stock_response)
        return 1;
    configure(&mock, &bindings);
    mock.extract_result = CL_HONDA_EXTRACT_NONE;
    mock.extract_count = 0;
    if (cl_honda_setup_bridge_call(&bindings, 1, mock.session, mock.request,
                                   &result) != CL_HONDA_BRIDGE_STOCK_ONLY ||
        mock.stock_calls != 1 || mock.prepare_calls != 0 ||
        result.selected_response != &mock.stock_response)
        return 2;
    return 0;
}

static int test_invalid_readiness_build_and_serialize_rollback(void) {
    MockState mock;
    CLHondaSetupBridgeBindings bindings;
    CLHondaSetupBridgeResult result;
    configure(&mock, &bindings);
    mock.validate_ready = 0;
    if (cl_honda_setup_bridge_call(&bindings, 1, mock.session, mock.request,
                                   &result) != CL_HONDA_BRIDGE_CHILD_REJECTED ||
        mock.stock_calls != 1 || mock.prepare_calls != 0 ||
        result.selected_response != &mock.stock_response)
        return 1;
    configure(&mock, &bindings);
    mock.authority_unavailable = 1;
    if (cl_honda_setup_bridge_call(&bindings, 1, mock.session, mock.request,
                                   &result) != CL_HONDA_BRIDGE_BINDING_UNAVAILABLE ||
        mock.stock_calls != 1 || mock.prepare_calls != 0 ||
        result.selected_response != &mock.stock_response)
        return 2;
    configure(&mock, &bindings);
    mock.build_status = -1;
    if (cl_honda_setup_bridge_call(&bindings, 1, mock.session, mock.request,
                                   &result) != CL_HONDA_BRIDGE_RESPONSE_BUILD_FAILED ||
        mock.rollback_calls != 1 || mock.release_calls != 1 ||
        result.selected_response != &mock.stock_response)
        return 3;
    configure(&mock, &bindings);
    if (cl_honda_setup_bridge_call(&bindings, 1, mock.session, mock.request,
                                   &result) != CL_HONDA_BRIDGE_TYPE111_PENDING)
        return 4;
    if (cl_honda_setup_bridge_complete(&result, 0) !=
            CL_HONDA_BRIDGE_SERIALIZATION_FAILED ||
        mock.rollback_calls != 1 || mock.release_calls != 1 ||
        result.selected_response != &mock.stock_response || result.pending)
        return 5;
    return 0;
}

static int test_commit_failure_and_duplicate_reject(void) {
    MockState mock;
    CLHondaSetupBridgeBindings bindings;
    CLHondaSetupBridgeResult result;
    configure(&mock, &bindings);
    if (cl_honda_setup_bridge_call(&bindings, 1, mock.session, mock.request,
                                   &result) != CL_HONDA_BRIDGE_TYPE111_PENDING)
        return 1;
    mock.commit_status = -1;
    if (cl_honda_setup_bridge_complete(&result, 1) !=
            CL_HONDA_BRIDGE_COMMIT_FAILED ||
        mock.rollback_calls != 1 || mock.release_calls != 1 ||
        result.selected_response != &mock.stock_response)
        return 2;
    configure(&mock, &bindings);
    mock.extract_count = 2;
    if (cl_honda_setup_bridge_call(&bindings, 1, mock.session, mock.request,
                                   &result) != CL_HONDA_BRIDGE_EXTRACT_FAILED ||
        mock.stock_calls != 1 || mock.prepare_calls != 0 ||
        result.selected_response != &mock.stock_response)
        return 3;
    return 0;
}

static int test_delivery_failure_and_parent_loss_cleanup(void) {
    MockState mock;
    CLHondaSetupBridgeBindings bindings;
    CLHondaSetupBridgeResult result;
    configure(&mock, &bindings);
    if (cl_honda_setup_bridge_call(&bindings, 1, mock.session, mock.request,
                                   &result) != CL_HONDA_BRIDGE_TYPE111_PENDING ||
        cl_honda_setup_bridge_complete(&result, 1) !=
            CL_HONDA_BRIDGE_PENDING_DELIVERY)
        return 1;
    if (cl_honda_setup_bridge_delivery(
            &result, CL_HONDA_DELIVERY_NOT_PUBLISHED) !=
            CL_HONDA_BRIDGE_DELIVERY_FAILED ||
        mock.withdraw_calls != 1 || mock.release_calls != 1 ||
        result.selected_response != &mock.stock_response ||
        result.stock_response != 0 || mock.stock_release_calls != 0)
        return 2;
    if (cl_honda_setup_bridge_parent_ended(&result) !=
            CL_HONDA_BRIDGE_PARENT_ENDED || mock.withdraw_parent_calls != 0)
        return 3;

    configure(&mock, &bindings);
    if (cl_honda_setup_bridge_call(&bindings, 1, mock.session, mock.request,
                                   &result) != CL_HONDA_BRIDGE_TYPE111_PENDING ||
        cl_honda_setup_bridge_complete(&result, 1) !=
            CL_HONDA_BRIDGE_PENDING_DELIVERY)
        return 4;
    if (cl_honda_setup_bridge_parent_ended(&result) !=
            CL_HONDA_BRIDGE_PARENT_ENDED || mock.withdraw_parent_calls != 1 ||
        mock.release_calls != 1 || mock.stock_release_calls != 1 ||
        result.candidate_response || result.stock_response ||
        cl_honda_setup_bridge_delivery(&result, CL_HONDA_DELIVERY_SENT) !=
            CL_HONDA_BRIDGE_INVALID_ARGUMENT)
        return 5;
    return 0;
}

static int test_failed_withdrawal_is_not_reported_as_clean(void) {
    MockState mock;
    CLHondaSetupBridgeBindings bindings;
    CLHondaSetupBridgeResult result;
    configure(&mock, &bindings);
    mock.withdraw_status = -41;
    if (cl_honda_setup_bridge_call(&bindings, 1, mock.session, mock.request,
                                   &result) != CL_HONDA_BRIDGE_TYPE111_PENDING ||
        cl_honda_setup_bridge_complete(&result, 1) !=
            CL_HONDA_BRIDGE_PENDING_DELIVERY)
        return 1;
    if (cl_honda_setup_bridge_delivery(
            &result, CL_HONDA_DELIVERY_NOT_PUBLISHED) !=
            CL_HONDA_BRIDGE_CLEANUP_FAILED ||
        !result.withdrawal_attempted || result.withdrawal_status != -41 ||
        !result.resources_may_remain || mock.withdraw_calls != 1 ||
        mock.release_calls != 1 || mock.stock_release_calls != 1 ||
        result.stock_response || result.selected_response ||
        cl_honda_setup_bridge_delivery(
            &result, CL_HONDA_DELIVERY_PARTIAL_OR_UNKNOWN) !=
            CL_HONDA_BRIDGE_INVALID_ARGUMENT)
        return 2;

    configure(&mock, &bindings);
    mock.withdraw_parent_status = -42;
    if (cl_honda_setup_bridge_call(&bindings, 1, mock.session, mock.request,
                                   &result) != CL_HONDA_BRIDGE_TYPE111_PENDING ||
        cl_honda_setup_bridge_complete(&result, 1) !=
            CL_HONDA_BRIDGE_PENDING_DELIVERY ||
        cl_honda_setup_bridge_parent_ended(&result) !=
            CL_HONDA_BRIDGE_CLEANUP_FAILED ||
        result.withdrawal_status != -42 || !result.resources_may_remain ||
        cl_honda_setup_bridge_parent_ended(&result) !=
            CL_HONDA_BRIDGE_CLEANUP_FAILED || mock.withdraw_parent_calls != 1)
        return 3;
    return 0;
}

int main(void) {
    int result = test_stock_passthrough_and_failure();
    if (result) return 10 + result;
    result = test_child_pending_commit_and_original_preservation();
    if (result) return 20 + result;
    result = test_missing_binding_and_no_capability_fall_back();
    if (result) return 30 + result;
    result = test_invalid_readiness_build_and_serialize_rollback();
    if (result) return 40 + result;
    result = test_commit_failure_and_duplicate_reject();
    if (result) return 50 + result;
    result = test_delivery_failure_and_parent_loss_cleanup();
    if (result) return 60 + result;
    result = test_failed_withdrawal_is_not_reported_as_clean();
    if (result) return 70 + result;
    puts("HONDA_SETUP_BRIDGE_PASS stock_once=PASS type111_gate=PASS rollback=PASS");
    return 0;
}
