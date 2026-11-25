#include "honda_setup_bridge.h"

static void initialize_bridge_result(CLHondaSetupBridgeResult *result) {
    result->code = CL_HONDA_BRIDGE_INVALID_ARGUMENT;
    result->stock_status = 0;
    result->stock_response = 0;
    result->candidate_response = 0;
    result->selected_response = 0;
    result->child.code = CL_NATIVE_SETUP_INVALID_ARGUMENT;
    result->child.factory_result = 0;
    result->child.response_entry = 0;
    result->child.candidate_entry = 0;
    result->child.transaction = 0;
    result->child.transaction_context = 0;
    result->child.commit_callback = 0;
    result->child.rollback_callback = 0;
    result->child.readiness_result = CL_NATIVE_READINESS_ERROR;
    result->child.prepare_result = CL_NATIVE_PREPARE_ERROR;
    result->pending = 0;
    result->candidate_transferred = 0;
}

static void rollback_child(CLHondaSetupBridgeResult *result) {
    if (result->child.code == CL_NATIVE_SETUP_TYPE111_PREPARED)
        (void)cl_native_setup_finalize_type111(&result->child, 0);
    result->pending = 0;
}

static void release_candidate(const CLHondaSetupBridgeBindings *bindings,
                              CLHondaSetupBridgeResult *result) {
    if (result->candidate_response && bindings && bindings->release_response)
        bindings->release_response(bindings->context,
                                   result->candidate_response);
    result->candidate_response = 0;
}

CLHondaBridgeCode cl_honda_setup_bridge_call(
    const CLHondaSetupBridgeBindings *bindings, int32_t extension_enabled,
    void *receiver_session, const void *request_dictionary,
    CLHondaSetupBridgeResult *out_result) {
    CLNativeSetupRequest child_request;
    CLHondaExtractStatus extracted;
    size_t type111_count = 0;
    void *candidate_response = 0;

    if (!out_result) return CL_HONDA_BRIDGE_INVALID_ARGUMENT;
    initialize_bridge_result(out_result);
    if ((extension_enabled != 0 && extension_enabled != 1) ||
        !receiver_session || !request_dictionary || !bindings ||
        !bindings->original_setup) {
        out_result->code = (bindings && bindings->original_setup)
            ? CL_HONDA_BRIDGE_INVALID_ARGUMENT
            : CL_HONDA_BRIDGE_BINDING_UNAVAILABLE;
        return out_result->code;
    }

    /* The only call through the stock boundary in this bridge invocation. */
    out_result->stock_status = bindings->original_setup(
        receiver_session, request_dictionary, &out_result->stock_response);
    out_result->selected_response = out_result->stock_response;
    if (out_result->stock_status != 0) {
        out_result->code = CL_HONDA_BRIDGE_STOCK_ERROR;
        return out_result->code;
    }
    if (!out_result->stock_response) {
        out_result->code = CL_HONDA_BRIDGE_STOCK_ERROR;
        return out_result->code;
    }
    if (!extension_enabled) {
        out_result->code = CL_HONDA_BRIDGE_STOCK_ONLY;
        return out_result->code;
    }

    if (!bindings->extract_type111 || !bindings->build_response_candidate ||
        !bindings->release_response ||
        !bindings->type111_ops.validate_type111 ||
        !bindings->type111_ops.prepare_type111 ||
        !bindings->type111_ops.commit_type111 ||
        !bindings->type111_ops.rollback_type111 ||
        !bindings->type111_ops.withdraw_type111 ||
        !bindings->type111_ops.withdraw_parent_type111) {
        out_result->code = CL_HONDA_BRIDGE_BINDING_UNAVAILABLE;
        return out_result->code;
    }

    child_request.stream_type = 0;
    child_request.parent_session = 0;
    child_request.parent_generation = 0;
    child_request.stream_connection = 0;
    child_request.stream_generation = 0;
    child_request.accepted_auxiliary_capability = 0;
    child_request.opaque_request = 0;
    extracted = bindings->extract_type111(
        bindings->context, receiver_session, request_dictionary,
        &child_request, &type111_count);
    if (extracted == CL_HONDA_EXTRACT_NONE && type111_count == 0) {
        out_result->code = CL_HONDA_BRIDGE_STOCK_ONLY;
        return out_result->code;
    }
    if (extracted != CL_HONDA_EXTRACT_ONE_TYPE111 || type111_count != 1 ||
        child_request.stream_type != 111 || !child_request.opaque_request) {
        out_result->code = CL_HONDA_BRIDGE_EXTRACT_FAILED;
        return out_result->code;
    }

    if (cl_native_setup_prepare_type111(
            &child_request, 0, &bindings->type111_ops, &out_result->child) !=
        CL_NATIVE_SETUP_TYPE111_PREPARED) {
        out_result->code =
            out_result->child.readiness_result ==
                    CL_NATIVE_READINESS_AUTHORITY_UNAVAILABLE
                ? CL_HONDA_BRIDGE_BINDING_UNAVAILABLE
                : CL_HONDA_BRIDGE_CHILD_REJECTED;
        return out_result->code;
    }

    if (bindings->build_response_candidate(
            bindings->context, out_result->stock_response,
            out_result->child.candidate_entry, &candidate_response) != 0 ||
        !candidate_response || candidate_response == out_result->stock_response) {
        if (candidate_response && candidate_response != out_result->stock_response)
            bindings->release_response(bindings->context, candidate_response);
        rollback_child(out_result);
        out_result->code = CL_HONDA_BRIDGE_RESPONSE_BUILD_FAILED;
        return out_result->code;
    }

    out_result->candidate_response = candidate_response;
    out_result->pending = 1;
    out_result->code = CL_HONDA_BRIDGE_TYPE111_PENDING;
    return out_result->code;
}

CLHondaBridgeCode cl_honda_setup_bridge_complete(
    const CLHondaSetupBridgeBindings *bindings,
    CLHondaSetupBridgeResult *result, int32_t serialization_succeeded) {
    CLNativeSetupCode finalized;
    if (!bindings || !result || !result->pending ||
        result->code != CL_HONDA_BRIDGE_TYPE111_PENDING ||
        (serialization_succeeded != 0 && serialization_succeeded != 1))
        return CL_HONDA_BRIDGE_INVALID_ARGUMENT;
    if (!serialization_succeeded) {
        rollback_child(result);
        release_candidate(bindings, result);
        result->selected_response = result->stock_response;
        result->code = CL_HONDA_BRIDGE_SERIALIZATION_FAILED;
        return result->code;
    }
    finalized = cl_native_setup_finalize_type111(&result->child, 1);
    result->pending = 0;
    if (finalized != CL_NATIVE_SETUP_TYPE111_COMMITTED) {
        release_candidate(bindings, result);
        result->selected_response = result->stock_response;
        result->code = CL_HONDA_BRIDGE_COMMIT_FAILED;
        return result->code;
    }
    bindings->release_response(bindings->context, result->stock_response);
    result->stock_response = 0;
    result->selected_response = result->candidate_response;
    result->candidate_response = 0;
    result->candidate_transferred = 1;
    result->code = CL_HONDA_BRIDGE_TYPE111_COMMITTED;
    return result->code;
}
