#include "setup_dispatch.h"

static void initialize_result(CLNativeSetupResult *result,
                              const void *factory_fallback_entry) {
    result->code = CL_NATIVE_SETUP_INVALID_ARGUMENT;
    result->factory_result = 0;
    result->response_entry = factory_fallback_entry;
    result->candidate_entry = 0;
    result->transaction = 0;
    result->transaction_context = 0;
    result->commit_callback = 0;
    result->rollback_callback = 0;
    result->readiness_result = CL_NATIVE_READINESS_ERROR;
    result->prepare_result = CL_NATIVE_PREPARE_ERROR;
}

static int has_valid_identity(const CLNativeSetupRequest *request) {
    return request && request->parent_session && request->parent_generation > 0 &&
           request->stream_connection && request->stream_generation > 0;
}

/* Returns 1 for duplicate identities and 2 for unsupported mixed batches. */
static int type111_batch_problem(const CLNativeSetupRequest *requests,
                                 size_t request_count) {
    size_t prior;
    size_t type111_count = 0;
    const CLNativeSetupRequest *type111 = 0;
    int32_t unsupported_type_present = 0;
    for (prior = 0; prior < request_count; ++prior) {
        const CLNativeSetupRequest *candidate = &requests[prior];
        if (candidate->stream_type == 111) {
            ++type111_count;
            type111 = candidate;
        } else if (candidate->stream_type != 100 &&
                   candidate->stream_type != 101 &&
                   candidate->stream_type != 110) {
            unsupported_type_present = 1;
        }
    }
    if (type111_count > 1) return 1;
    if (unsupported_type_present) return 2;
    if (!type111) return 0;
    for (prior = 0; prior < request_count; ++prior) {
        const CLNativeSetupRequest *candidate = &requests[prior];
        if (candidate->stream_type == 110 &&
            candidate->stream_connection && type111->stream_connection &&
            candidate->stream_connection == type111->stream_connection)
            return 1;
    }
    return 0;
}

static void rollback_pending(CLNativeSetupResult *result) {
    if ((result->transaction || result->candidate_entry) &&
        result->rollback_callback)
        result->rollback_callback(result->transaction_context,
                                  result->transaction, result->candidate_entry);
    result->transaction = 0;
    result->candidate_entry = 0;
    result->transaction_context = 0;
    result->commit_callback = 0;
    result->rollback_callback = 0;
}

static void prepare_type111(const CLNativeSetupRequest *request,
                            const void *factory_fallback_entry,
                            const CLNativeSetupOps *ops,
                            CLNativeSetupResult *result) {
    CLNativeReadiness readiness;
    CLNativePrepareStatus prepared;
    void *transaction = 0;
    const void *candidate = 0;

    if (!ops || !ops->factory_setup ||
        !request->accepted_auxiliary_capability ||
        !ops->validate_type111 || !ops->prepare_type111 ||
        !ops->commit_type111 || !ops->rollback_type111 ||
        !ops->withdraw_type111 || !ops->withdraw_parent_type111) {
        result->code = CL_NATIVE_SETUP_TYPE111_DISABLED;
        return;
    }
    if (!has_valid_identity(request)) {
        result->code = CL_NATIVE_SETUP_TYPE111_INVALID_IDENTITY;
        return;
    }
    readiness = ops->validate_type111(ops->context, request);
    result->readiness_result = readiness;
    if (readiness != CL_NATIVE_READINESS_READY) {
        result->code = (readiness == CL_NATIVE_READINESS_INVALID_IDENTITY)
            ? CL_NATIVE_SETUP_TYPE111_INVALID_IDENTITY
            : (readiness == CL_NATIVE_READINESS_DUPLICATE_IDENTITY)
                ? CL_NATIVE_SETUP_TYPE111_DUPLICATE
                : CL_NATIVE_SETUP_TYPE111_NOT_READY;
        return;
    }
    prepared = ops->prepare_type111(ops->context, request,
                                    &transaction, &candidate);
    result->prepare_result = prepared;
    if (prepared != CL_NATIVE_PREPARE_READY || !transaction || !candidate) {
        if (transaction || candidate)
            ops->rollback_type111(ops->context, transaction, candidate);
        result->code = CL_NATIVE_SETUP_TYPE111_PREPARE_FAILED;
        result->response_entry = factory_fallback_entry;
        return;
    }
    result->code = CL_NATIVE_SETUP_TYPE111_PREPARED;
    result->response_entry = factory_fallback_entry;
    result->candidate_entry = candidate;
    result->transaction = transaction;
    result->transaction_context = ops->context;
    result->commit_callback = ops->commit_type111;
    result->rollback_callback = ops->rollback_type111;
}

CLNativeSetupCode cl_native_setup_dispatch_batch(
    const CLNativeSetupRequest *requests, size_t request_count,
    const void *factory_fallback_entry, const CLNativeSetupOps *ops,
    CLNativeSetupResult *results) {
    size_t index;
    int32_t stock_failed = 0;
    if (request_count > CL_NATIVE_SETUP_MAX_REQUESTS)
        return CL_NATIVE_SETUP_TOO_MANY_REQUESTS;
    if (request_count != 0 && !results)
        return CL_NATIVE_SETUP_INVALID_ARGUMENT;
    for (index = 0; index < request_count; ++index)
        initialize_result(&results[index], factory_fallback_entry);
    if (request_count != 0 && !requests) {
        for (index = 0; index < request_count; ++index)
            results[index].code = CL_NATIVE_SETUP_INVALID_ARGUMENT;
        return CL_NATIVE_SETUP_INVALID_ARGUMENT;
    }
    for (index = 0; index < request_count; ++index) {
        if (!requests[index].opaque_request) {
            size_t reset_index;
            for (reset_index = 0; reset_index < request_count; ++reset_index)
                results[reset_index].code = CL_NATIVE_SETUP_INVALID_ARGUMENT;
            return CL_NATIVE_SETUP_INVALID_ARGUMENT;
        }
    }

    /* Preserve factory ordering and ensure no auxiliary resource is prepared
     * if any stock request in this batch fails. */
    for (index = 0; index < request_count; ++index) {
        const CLNativeSetupRequest *request = &requests[index];
        CLNativeSetupResult *result = &results[index];
        if (request->stream_type == 111) continue;
        if (!ops || !ops->factory_setup) {
            result->code = CL_NATIVE_SETUP_STOCK_FAILED;
            stock_failed = 1;
            continue;
        }
        {
            const void *stock_entry = factory_fallback_entry;
            int32_t stock_status = ops->factory_setup(
                ops->context, request, &stock_entry);
            result->factory_result = stock_status;
            if (stock_status == 0 && stock_entry) {
                result->code = CL_NATIVE_SETUP_STOCK_HANDLED;
                result->response_entry = stock_entry;
            } else {
                result->code = CL_NATIVE_SETUP_STOCK_FAILED;
                result->response_entry = factory_fallback_entry;
                stock_failed = 1;
            }
        }
    }
    {
        int32_t batch_problem = type111_batch_problem(requests, request_count);
        for (index = 0; index < request_count; ++index) {
            const CLNativeSetupRequest *request = &requests[index];
            CLNativeSetupResult *result = &results[index];
            if (request->stream_type != 111) continue;
            if (batch_problem == 1) {
                result->code = CL_NATIVE_SETUP_TYPE111_DUPLICATE;
            } else if (batch_problem == 2) {
                result->code = CL_NATIVE_SETUP_TYPE111_UNSUPPORTED_BATCH;
            } else if (stock_failed) {
                result->code = CL_NATIVE_SETUP_STOCK_FAILED;
            } else {
                prepare_type111(request, factory_fallback_entry, ops, result);
            }
        }
    }
    return CL_NATIVE_SETUP_BATCH_COMPLETED;
}

CLNativeSetupCode cl_native_setup_finalize_type111(
    CLNativeSetupResult *result, int32_t serialization_succeeded) {
    if (!result || (serialization_succeeded != 0 &&
                            serialization_succeeded != 1))
        return CL_NATIVE_SETUP_INVALID_ARGUMENT;
    if (result->code != CL_NATIVE_SETUP_TYPE111_PREPARED ||
        !result->transaction || !result->candidate_entry)
        return CL_NATIVE_SETUP_NOT_PENDING;
    if (!serialization_succeeded) {
        rollback_pending(result);
        result->code = CL_NATIVE_SETUP_TYPE111_SERIALIZER_FAILED;
        return result->code;
    }
    if (!result->commit_callback || !result->rollback_callback ||
        result->commit_callback(result->transaction_context,
                                result->transaction) != 0) {
        rollback_pending(result);
        result->code = CL_NATIVE_SETUP_TYPE111_COMMIT_FAILED;
        return result->code;
    }
    result->response_entry = result->candidate_entry;
    result->transaction = 0;
    result->candidate_entry = 0;
    result->transaction_context = 0;
    result->commit_callback = 0;
    result->rollback_callback = 0;
    result->code = CL_NATIVE_SETUP_TYPE111_COMMITTED;
    return result->code;
}

int32_t cl_native_setup_withdraw_type111(
    const CLNativeSetupOps *ops, const void *parent_session,
    uint64_t parent_generation, const void *stream_connection,
    uint64_t stream_generation) {
    if (!ops || !ops->withdraw_type111 || !parent_session ||
        parent_generation == 0 || !stream_connection || stream_generation == 0)
        return -1;
    return ops->withdraw_type111(ops->context, parent_session,
                                 parent_generation, stream_connection,
                                 stream_generation);
}

int32_t cl_native_setup_withdraw_parent_type111(
    const CLNativeSetupOps *ops, const void *parent_session,
    uint64_t parent_generation) {
    if (!ops || !ops->withdraw_parent_type111 || !parent_session ||
        parent_generation == 0)
        return -1;
    return ops->withdraw_parent_type111(ops->context, parent_session,
                                       parent_generation);
}
