#ifndef CLARITYLINK_NATIVE_SETUP_TXN_H
#define CLARITYLINK_NATIVE_SETUP_TXN_H

#include <stddef.h>
#include <stdint.h>

#define CL_REQUEST_MAGIC UINT32_C(0x43525131)
#define CL_RESPONSE_MAGIC UINT32_C(0x43525331)
#define CL_MAX_STREAMS 8u
#define CL_SERIALIZER_SUCCESS INT32_C(0xc8)

typedef enum {
    CL_SETUP_BYPASS = 0,
    CL_SETUP_PREPARED = 1,
    CL_SETUP_REJECTED = 2,
    CL_SETUP_BUSY = 3,
    CL_SETUP_INTERNAL_ERROR = 4
} ClSetupResult;

typedef enum {
    CL_TXN_EMPTY = 0,
    CL_TXN_PREPARED = 1,
    CL_TXN_COMMITTED = 2,
    CL_TXN_ROLLED_BACK = 3
} ClTransactionState;

typedef struct {
    uint32_t type;
    uint32_t stream_id_low;
    uint32_t stream_id_high;
} ClSyntheticRequestStream;

typedef struct {
    uint32_t magic;
    uint32_t count;
    ClSyntheticRequestStream streams[CL_MAX_STREAMS];
} ClSyntheticRequest;

typedef struct {
    uint32_t type;
    uint32_t data_port;
} ClSyntheticResponseStream;

typedef struct {
    uint32_t magic;
    uint32_t count;
    ClSyntheticResponseStream streams[CL_MAX_STREAMS];
} ClSyntheticResponse;

/* Borrowed call data. None of these pointers may be copied into ClPreparedTxn. */
typedef struct {
    const ClSyntheticRequest *request;
    ClSyntheticResponse *response;
    const int32_t *status_out;
    const void *session;
    uintptr_t expected_status_out;
} ClSetupCall;

/* Project-owned scalar state only; intentionally contains no pointer fields. */
typedef struct {
    uint32_t magic;
    uint32_t state;
    uint32_t gate_token;
    uint32_t generation;
    uint32_t stream_id_low;
    uint32_t stream_id_high;
    uint32_t data_port;
    uint32_t original_response_count;
    uint32_t response_appended;
    uint32_t listener_owned;
    uint32_t generation_owned;
} ClPreparedTxn;

typedef int32_t (*ClGateClaim)(void *userdata, uint32_t *token_out);
typedef int32_t (*ClGateRelease)(void *userdata, uint32_t token);
typedef int32_t (*ClGenerationPrepare)(void *userdata, uint32_t id_low,
                                       uint32_t id_high, uint32_t *generation_out);
typedef int32_t (*ClListenerPrepare)(void *userdata, uint32_t generation,
                                     uint32_t *port_out);
typedef int32_t (*ClGenerationAction)(void *userdata, uint32_t generation);
typedef int32_t (*ClListenerAction)(void *userdata, uint32_t generation);

typedef struct {
    void *userdata;
    ClGateClaim gate_claim;
    ClGateRelease gate_release;
    ClGenerationPrepare generation_prepare;
    ClListenerPrepare listener_prepare;
    ClGenerationAction generation_commit;
    ClGenerationAction generation_rollback;
    ClListenerAction listener_rollback;
} ClSetupServices;

/*
 * Service contract: callbacks are synchronous, non-throwing C operations.
 * A callback that reports failure must leave no newly acquired ownership;
 * successful prepare callbacks return a generation/token that is later
 * addressed by exact value. Implementations must serialize shared state.
 */

int32_t cl_setup_prepare(const ClSetupCall *call, ClPreparedTxn *txn,
                         const ClSetupServices *services);
int32_t cl_setup_finish(const ClSetupCall *call, ClPreparedTxn *txn,
                        int32_t serializer_r0, int32_t commit_allowed,
                        const ClSetupServices *services);

/* 32-bit call frame shared with the standalone Thumb trampoline. */
typedef struct {
    uint32_t original_sp;
    uint32_t request;
    uint32_t response;
    uint32_t status_out;
    uint32_t session;
    uint32_t serializer_args[4];
    uint32_t prepare_result;
    uint32_t serializer_r0;
    uint32_t expected_status_address;
    uint32_t transaction;
    uint32_t finish_result;
} ClShimCallContext;

_Static_assert(sizeof(ClPreparedTxn) == 44u, "transaction wire size changed");
_Static_assert(sizeof(ClShimCallContext) == 56u, "shim context wire size changed");
_Static_assert(offsetof(ClShimCallContext, transaction) == 48u,
               "shim transaction offset changed");

/* Emulator-only wrappers use the service table at a fixed test address. */
int32_t project_prepare(ClShimCallContext *wire);
int32_t project_finish(int32_t commit_allowed, ClShimCallContext *wire);

#endif
