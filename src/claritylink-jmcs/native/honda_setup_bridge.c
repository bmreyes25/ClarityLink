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
    result->callback_context = 0;
    result->type111_callback_context = 0;
    result->captured_release_response = 0;
    result->captured_withdraw_type111 = 0;
    result->captured_withdraw_parent_type111 = 0;
    result->parent_generation = 0;
    result->stream_generation = 0;
    result->pending = 0;
    result->awaiting_delivery = 0;
    result->delivery_confirmed = 0;
    result->parent_ended = 0;
    result->withdrawal_attempted = 0;
    result->withdrawal_status = 0;
    result->resources_may_remain = 0;
}

static void rollback_child(CLHondaSetupBridgeResult *result) {
    if (result->child.code == CL_NATIVE_SETUP_TYPE111_PREPARED)
        (void)cl_native_setup_finalize_type111(&result->child, 0);
    result->pending = 0;
}

static void release_response(CLHondaSetupBridgeResult *result, void *response) {
    if (response && result->captured_release_response)
        result->captured_release_response(result->callback_context, response);
}

static void release_candidate(CLHondaSetupBridgeResult *result) {
    release_response(result, result->candidate_response);
    result->candidate_response = 0;
}

static int32_t withdraw_child(CLHondaSetupBridgeResult *result) {
    if (!result->captured_withdraw_type111 ||
        result->parent_generation == 0 || result->stream_generation == 0)
        return -1;
    return result->captured_withdraw_type111(
        result->type111_callback_context, result->parent_generation,
        result->stream_generation);
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
    if (out_result->stock_status != 0 || !out_result->stock_response) {
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
    out_result->callback_context = bindings->context;
    out_result->type111_callback_context = bindings->type111_ops.context;
    out_result->captured_release_response = bindings->release_response;
    out_result->captured_withdraw_type111 =
        bindings->type111_ops.withdraw_type111;
    out_result->captured_withdraw_parent_type111 =
        bindings->type111_ops.withdraw_parent_type111;

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
    if (extracted == CL_HONDA_EXTRACT_AUTHORITY_UNAVAILABLE ||
        extracted == CL_HONDA_EXTRACT_BINDING_UNAVAILABLE) {
        out_result->code = CL_HONDA_BRIDGE_BINDING_UNAVAILABLE;
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
    out_result->parent_generation = child_request.parent_generation;
    out_result->stream_generation = child_request.stream_generation;

    if (bindings->build_response_candidate(
            bindings->context, out_result->stock_response,
            out_result->child.candidate_entry, &candidate_response) != 0 ||
        !candidate_response || candidate_response == out_result->stock_response) {
        if (candidate_response && candidate_response != out_result->stock_response)
            release_response(out_result, candidate_response);
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
    CLHondaSetupBridgeResult *result, int32_t serialization_succeeded) {
    CLNativeSetupCode finalized;
    if (!result || !result->pending ||
        result->code != CL_HONDA_BRIDGE_TYPE111_PENDING ||
        (serialization_succeeded != 0 && serialization_succeeded != 1))
        return CL_HONDA_BRIDGE_INVALID_ARGUMENT;
    if (!serialization_succeeded) {
        rollback_child(result);
        release_candidate(result);
        result->selected_response = result->stock_response;
        result->code = CL_HONDA_BRIDGE_SERIALIZATION_FAILED;
        return result->code;
    }
    finalized = cl_native_setup_finalize_type111(&result->child, 1);
    result->pending = 0;
    if (finalized != CL_NATIVE_SETUP_TYPE111_COMMITTED) {
        release_candidate(result);
        result->selected_response = result->stock_response;
        result->code = CL_HONDA_BRIDGE_COMMIT_FAILED;
        return result->code;
    }
    result->awaiting_delivery = 1;
    result->selected_response = result->candidate_response;
    result->code = CL_HONDA_BRIDGE_PENDING_DELIVERY;
    return result->code;
}

CLHondaBridgeCode cl_honda_setup_bridge_delivery(
    CLHondaSetupBridgeResult *result, CLHondaDeliveryOutcome outcome) {
    if (!result || !result->awaiting_delivery || result->parent_ended ||
        result->code != CL_HONDA_BRIDGE_PENDING_DELIVERY ||
        outcome < CL_HONDA_DELIVERY_SENT ||
        outcome > CL_HONDA_DELIVERY_PARTIAL_OR_UNKNOWN)
        return CL_HONDA_BRIDGE_INVALID_ARGUMENT;
    result->awaiting_delivery = 0;
    if (outcome == CL_HONDA_DELIVERY_SENT) {
        release_response(result, result->stock_response);
        result->stock_response = 0;
        release_candidate(result);
        result->selected_response = 0;
        result->delivery_confirmed = 1;
        result->code = CL_HONDA_BRIDGE_TYPE111_COMMITTED;
        return result->code;
    }

    result->withdrawal_attempted = 1;
    result->withdrawal_status = withdraw_child(result);
    result->resources_may_remain = result->withdrawal_status != 0;
    release_candidate(result);
    result->code = result->resources_may_remain
        ? CL_HONDA_BRIDGE_CLEANUP_FAILED
        : CL_HONDA_BRIDGE_DELIVERY_FAILED;
    if (outcome == CL_HONDA_DELIVERY_NOT_PUBLISHED) {
        if (result->resources_may_remain) {
            release_response(result, result->stock_response);
            result->stock_response = 0;
            result->selected_response = 0;
        } else {
            result->selected_response = result->stock_response;
            result->stock_response = 0; /* Transfer stock +1 for fallback. */
        }
        return result->code;
    }
    release_response(result, result->stock_response);
    result->stock_response = 0;
    result->selected_response = 0;
    return result->code;
}

CLHondaBridgeCode cl_honda_setup_bridge_parent_ended(
    CLHondaSetupBridgeResult *result) {
    if (!result) return CL_HONDA_BRIDGE_INVALID_ARGUMENT;
    if (result->parent_ended)
        return result->resources_may_remain
            ? CL_HONDA_BRIDGE_CLEANUP_FAILED
            : CL_HONDA_BRIDGE_PARENT_ENDED;
    if (result->pending) rollback_child(result);
    else if (result->awaiting_delivery || result->delivery_confirmed) {
        result->withdrawal_attempted = 1;
        result->withdrawal_status =
            (result->captured_withdraw_parent_type111 &&
             result->parent_generation != 0)
                ? result->captured_withdraw_parent_type111(
                      result->type111_callback_context,
                      result->parent_generation)
                : -1;
        result->resources_may_remain = result->withdrawal_status != 0;
    }
    result->awaiting_delivery = 0;
    result->delivery_confirmed = 0;
    release_candidate(result);
    if (result->stock_response) {
        release_response(result, result->stock_response);
        result->stock_response = 0;
    }
    result->selected_response = 0;
    result->parent_ended = 1;
    result->code = result->resources_may_remain
        ? CL_HONDA_BRIDGE_CLEANUP_FAILED
        : CL_HONDA_BRIDGE_PARENT_ENDED;
    return result->code;
}
