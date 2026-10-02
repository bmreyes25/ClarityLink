#include "native_setup_txn.h"

#define CL_TXN_MAGIC UINT32_C(0x43545831)
#define CL_SERVICE_OK INT32_C(1)
#define CL_SERVICE_BUSY INT32_C(0)

static int32_t cl_services_valid(const ClSetupServices *services) {
    return services != NULL && services->gate_claim != NULL &&
           services->gate_release != NULL && services->generation_prepare != NULL &&
           services->listener_prepare != NULL && services->generation_commit != NULL &&
           services->generation_rollback != NULL && services->listener_rollback != NULL;
}

static int32_t cl_request_find_type111(const ClSyntheticRequest *request,
                                      uint32_t *index_out) {
    uint32_t i;
    uint32_t count111 = 0;
    uint32_t index = 0;
    if (request == NULL || request->magic != CL_REQUEST_MAGIC ||
        request->count > CL_MAX_STREAMS) {
        return CL_SETUP_REJECTED;
    }
    for (i = 0; i < request->count; ++i) {
        if (request->streams[i].type == 111u) {
            ++count111;
            index = i;
        }
    }
    if (count111 > 1u) {
        return CL_SETUP_REJECTED;
    }
    if (count111 == 0u) {
        return CL_SETUP_BYPASS;
    }

    for (i = 0; i < request->count; ++i) {
        const ClSyntheticRequestStream *current = &request->streams[i];
        uint32_t j;
        if (current->type != 100u && current->type != 101u &&
            current->type != 110u && current->type != 111u) {
            return CL_SETUP_REJECTED;
        }
        if (current->type == 110u || current->type == 111u) {
            if (current->stream_id_low == 0u && current->stream_id_high == 0u) {
                return CL_SETUP_REJECTED;
            }
            for (j = 0; j < i; ++j) {
                const ClSyntheticRequestStream *prior = &request->streams[j];
                if ((prior->type == 110u || prior->type == 111u) &&
                    prior->stream_id_low == current->stream_id_low &&
                    prior->stream_id_high == current->stream_id_high) {
                    return CL_SETUP_REJECTED;
                }
            }
        }
    }
    *index_out = index;
    return CL_SETUP_PREPARED;
}

static int32_t cl_response_validate(const ClSyntheticResponse *response) {
    uint32_t i;
    if (response == NULL || response->magic != CL_RESPONSE_MAGIC ||
        response->count > CL_MAX_STREAMS || response->count == CL_MAX_STREAMS) {
        return 0;
    }
    for (i = 0; i < response->count; ++i) {
        if (response->streams[i].type == 111u) {
            return 0;
        }
        if (response->streams[i].type == 110u &&
            response->streams[i].data_port == 0u) {
            return 0;
        }
    }
    return 1;
}

static void cl_restore_response(const ClSetupCall *call, ClPreparedTxn *txn) {
    ClSyntheticResponse *response;
    uint32_t index;
    if (call == NULL || txn == NULL || txn->response_appended == 0u ||
        call->response == NULL) {
        return;
    }
    response = call->response;
    index = txn->original_response_count;
    if (response->magic == CL_RESPONSE_MAGIC && response->count == index + 1u &&
        index < CL_MAX_STREAMS && response->streams[index].type == 111u &&
        response->streams[index].data_port == txn->data_port) {
        response->streams[index].type = 0u;
        response->streams[index].data_port = 0u;
        response->count = index;
    }
    txn->response_appended = 0u;
}

static int32_t cl_rollback(const ClSetupCall *call, ClPreparedTxn *txn,
                           const ClSetupServices *services) {
    int32_t cleanup_failed = 0;
    if (txn == NULL || txn->magic != CL_TXN_MAGIC || !cl_services_valid(services)) {
        return CL_SETUP_INTERNAL_ERROR;
    }
    cl_restore_response(call, txn);
    if (txn->listener_owned != 0u) {
        if (services->listener_rollback(services->userdata, txn->generation) != CL_SERVICE_OK) {
            cleanup_failed = 1;
        }
        txn->listener_owned = 0u;
    }
    if (txn->generation_owned != 0u) {
        if (services->generation_rollback(services->userdata, txn->generation) != CL_SERVICE_OK) {
            cleanup_failed = 1;
        }
        txn->generation_owned = 0u;
    }
    if (txn->gate_token != 0u) {
        if (services->gate_release(services->userdata, txn->gate_token) != CL_SERVICE_OK) {
            cleanup_failed = 1;
        }
        txn->gate_token = 0u;
    }
    txn->state = CL_TXN_ROLLED_BACK;
    return cleanup_failed != 0 ? CL_SETUP_INTERNAL_ERROR : CL_SETUP_REJECTED;
}

int32_t cl_setup_prepare(const ClSetupCall *call, ClPreparedTxn *txn,
                         const ClSetupServices *services) {
    uint32_t type111_index = 0u;
    uint32_t gate_token = 0u;
    uint32_t generation = 0u;
    uint32_t port = 0u;
    int32_t parsed;
    const ClSyntheticRequestStream *screen;
    if (txn == NULL) {
        return CL_SETUP_REJECTED;
    }
    txn->magic = CL_TXN_MAGIC;
    txn->state = CL_TXN_EMPTY;
    txn->gate_token = 0u;
    txn->generation = 0u;
    txn->stream_id_low = 0u;
    txn->stream_id_high = 0u;
    txn->data_port = 0u;
    txn->original_response_count = 0u;
    txn->response_appended = 0u;
    txn->listener_owned = 0u;
    txn->generation_owned = 0u;

    if (call == NULL || call->request == NULL) {
        return CL_SETUP_BYPASS;
    }
    parsed = cl_request_find_type111(call->request, &type111_index);
    if (parsed == CL_SETUP_BYPASS) {
        return CL_SETUP_BYPASS;
    }
    if (parsed != CL_SETUP_PREPARED || call->response == NULL || call->session == NULL ||
        call->status_out == NULL || (uintptr_t)call->status_out != call->expected_status_out ||
        !cl_response_validate(call->response) || !cl_services_valid(services)) {
        return CL_SETUP_REJECTED;
    }
    screen = &call->request->streams[type111_index];
    if (cl_response_validate(call->response) == 0) {
        return CL_SETUP_REJECTED;
    }

    /* Process-wide try-lock: no Honda session address is retained or keyed. */
    parsed = services->gate_claim(services->userdata, &gate_token);
    if (parsed == CL_SERVICE_BUSY) {
        return CL_SETUP_BUSY;
    }
    if (parsed != CL_SERVICE_OK || gate_token == 0u) {
        return CL_SETUP_INTERNAL_ERROR;
    }
    txn->gate_token = gate_token;
    txn->stream_id_low = screen->stream_id_low;
    txn->stream_id_high = screen->stream_id_high;

    if (services->generation_prepare(services->userdata, txn->stream_id_low,
                                     txn->stream_id_high, &generation) != CL_SERVICE_OK ||
        generation == 0u) {
        (void)cl_rollback(call, txn, services);
        return CL_SETUP_INTERNAL_ERROR;
    }
    txn->generation = generation;
    txn->generation_owned = 1u;

    if (services->listener_prepare(services->userdata, generation, &port) != CL_SERVICE_OK) {
        (void)cl_rollback(call, txn, services);
        return CL_SETUP_INTERNAL_ERROR;
    }
    txn->listener_owned = 1u;
    if (port == 0u || port > UINT16_MAX) {
        (void)cl_rollback(call, txn, services);
        return CL_SETUP_INTERNAL_ERROR;
    }
    txn->data_port = port;

    txn->original_response_count = call->response->count;
    call->response->streams[call->response->count].type = 111u;
    call->response->streams[call->response->count].data_port = port;
    ++call->response->count;
    txn->response_appended = 1u;
    txn->state = CL_TXN_PREPARED;
    return CL_SETUP_PREPARED;
}

int32_t cl_setup_finish(const ClSetupCall *call, ClPreparedTxn *txn,
                        int32_t serializer_r0, int32_t commit_allowed,
                        const ClSetupServices *services) {
    if (txn == NULL || txn->magic != CL_TXN_MAGIC || txn->state != CL_TXN_PREPARED ||
        !cl_services_valid(services)) {
        return CL_SETUP_BYPASS;
    }
    if (commit_allowed != 0 && serializer_r0 == CL_SERIALIZER_SUCCESS &&
        call != NULL && call->status_out != NULL &&
        (uintptr_t)call->status_out == call->expected_status_out && *call->status_out == 0 &&
        services->generation_commit(services->userdata, txn->generation) == CL_SERVICE_OK) {
        if (services->gate_release(services->userdata, txn->gate_token) != CL_SERVICE_OK) {
            (void)cl_rollback(call, txn, services);
            return CL_SETUP_INTERNAL_ERROR;
        }
        txn->gate_token = 0u;
        txn->listener_owned = 0u;
        txn->generation_owned = 0u;
        txn->response_appended = 0u;
        txn->state = CL_TXN_COMMITTED;
        return CL_SETUP_PREPARED;
    }
    return cl_rollback(call, txn, services);
}

/* Kept separate from cl_setup_* so the host mirror can supply native pointers. */
static ClSetupCall cl_call_from_wire(const ClShimCallContext *wire) {
    ClSetupCall call;
    call.request = (const ClSyntheticRequest *)(uintptr_t)wire->request;
    call.response = (ClSyntheticResponse *)(uintptr_t)wire->response;
    call.status_out = (const int32_t *)(uintptr_t)wire->status_out;
    call.session = (const void *)(uintptr_t)wire->session;
    call.expected_status_out = (uintptr_t)wire->expected_status_address;
    return call;
}

#ifndef CL_TEST_SERVICE_TABLE_ADDRESS
#define CL_TEST_SERVICE_TABLE_ADDRESS UINT32_C(0x20800)
#endif

int32_t project_prepare(ClShimCallContext *wire) {
    ClSetupCall call;
    ClPreparedTxn *txn;
    const ClSetupServices *services =
        (const ClSetupServices *)(uintptr_t)CL_TEST_SERVICE_TABLE_ADDRESS;
    if (wire == NULL || wire->transaction == 0u) {
        return CL_SETUP_REJECTED;
    }
    call = cl_call_from_wire(wire);
    txn = (ClPreparedTxn *)(uintptr_t)wire->transaction;
    return cl_setup_prepare(&call, txn, services);
}

int32_t project_finish(int32_t commit_allowed, ClShimCallContext *wire) {
    ClSetupCall call;
    ClPreparedTxn *txn;
    const ClSetupServices *services =
        (const ClSetupServices *)(uintptr_t)CL_TEST_SERVICE_TABLE_ADDRESS;
    if (wire == NULL || wire->transaction == 0u) {
        return CL_SETUP_REJECTED;
    }
    call = cl_call_from_wire(wire);
    txn = (ClPreparedTxn *)(uintptr_t)wire->transaction;
    wire->finish_result = (uint32_t)cl_setup_finish(
        &call, txn, (int32_t)wire->serializer_r0, commit_allowed, services);
    return (int32_t)wire->finish_result;
}
