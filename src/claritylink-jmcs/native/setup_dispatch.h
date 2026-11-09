#ifndef CLARITYLINK_JMCS_SETUP_DISPATCH_H
#define CLARITYLINK_JMCS_SETUP_DISPATCH_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define CL_NATIVE_SETUP_MAX_REQUESTS 8u

/* Project-owned request view. All object handles are borrowed and opaque;
 * this interface does not describe a Honda private struct layout. */
typedef struct CLNativeSetupRequest {
    int32_t stream_type;
    const void *parent_session;
    uint64_t parent_generation;
    const void *stream_connection;
    uint64_t stream_generation;
    /* Opaque borrowed handle only. validate_type111 must confirm this is the
     * currently accepted capability for this parent and generation. */
    const void *accepted_auxiliary_capability;
    const void *opaque_request;
} CLNativeSetupRequest;

typedef enum CLNativeReadiness {
    CL_NATIVE_READINESS_READY = 0,
    CL_NATIVE_READINESS_FEATURE_DISABLED = 1,
    CL_NATIVE_READINESS_AUTHORITY_UNAVAILABLE = 2,
    CL_NATIVE_READINESS_TRANSPORT_UNREADY = 3,
    CL_NATIVE_READINESS_STALE_PARENT = 4,
    CL_NATIVE_READINESS_INVALID_IDENTITY = 5,
    CL_NATIVE_READINESS_DUPLICATE_IDENTITY = 6,
    CL_NATIVE_READINESS_ERROR = 7
} CLNativeReadiness;

typedef enum CLNativePrepareStatus {
    CL_NATIVE_PREPARE_READY = 0,
    CL_NATIVE_PREPARE_NOT_READY = 1,
    CL_NATIVE_PREPARE_ALLOCATION_FAILED = 2,
    CL_NATIVE_PREPARE_ERROR = 3
} CLNativePrepareStatus;

typedef enum CLNativeSetupCode {
    CL_NATIVE_SETUP_STOCK_HANDLED = 0,
    CL_NATIVE_SETUP_STOCK_FAILED = 1,
    CL_NATIVE_SETUP_TYPE111_DISABLED = 2,
    CL_NATIVE_SETUP_TYPE111_INVALID_IDENTITY = 3,
    CL_NATIVE_SETUP_TYPE111_DUPLICATE = 4,
    CL_NATIVE_SETUP_TYPE111_NOT_READY = 5,
    CL_NATIVE_SETUP_TYPE111_PREPARE_FAILED = 6,
    CL_NATIVE_SETUP_TYPE111_PREPARED = 7,
    CL_NATIVE_SETUP_TYPE111_COMMITTED = 8,
    CL_NATIVE_SETUP_TYPE111_SERIALIZER_FAILED = 9,
    CL_NATIVE_SETUP_TYPE111_COMMIT_FAILED = 10,
    CL_NATIVE_SETUP_INVALID_ARGUMENT = 11,
    CL_NATIVE_SETUP_TOO_MANY_REQUESTS = 12,
    CL_NATIVE_SETUP_NOT_PENDING = 13,
    CL_NATIVE_SETUP_BATCH_COMPLETED = 14,
    CL_NATIVE_SETUP_TYPE111_UNSUPPORTED_BATCH = 15
} CLNativeSetupCode;

typedef struct CLNativeSetupOps {
    void *context;
    /* Called unchanged for 100/101/110 and unknown types. Return 0 on stock
     * success; response_entry is borrowed from the factory owner. */
    int32_t (*factory_setup)(void *context,
                             const CLNativeSetupRequest *request,
                             const void **response_entry);
    /* Must verify accepted auxiliary capability, current parent association,
     * unique/current stream identity, receiver-owned authority, and a separate
     * media-ready transport. The project currently provides no Honda binding. */
    CLNativeReadiness (*validate_type111)(
        void *context, const CLNativeSetupRequest *request);
    /* Stages only project-owned resources. The candidate is provisional. The
     * callback/caller must build from an immutable factory response snapshot,
     * preserve every stock entry, and serialize only to a private,
     * untransmitted buffer. Keep the factory fallback available until
     * finalize commits; this adapter cannot inspect opaque serialized data. */
    CLNativePrepareStatus (*prepare_type111)(
        void *context, const CLNativeSetupRequest *request,
        void **transaction, const void **candidate_entry);
    /* Return 0 only if parent/generations/resources are still current and the
     * candidate remains valid after this cookie is consumed. Failure must be
     * atomic: leave transaction/candidate rollback-able. Transfer/pin its
     * lifetime in project-owned state through response completion/withdrawal. */
    int32_t (*commit_type111)(void *context, void *transaction);
    /* Releases every partial output, including a candidate returned without a
     * transaction cookie after a faulty or partial prepare. The prepare
     * callback must make transaction/candidate sufficient to release every
     * partial resource. Delayed rollback must not dereference caller request
     * storage or its borrowed capability handle. */
    void (*rollback_type111)(void *context, void *transaction,
                             const void *candidate_entry);
    int32_t (*withdraw_type111)(void *context, const void *parent_session,
                                uint64_t parent_generation,
                                const void *stream_connection,
                                uint64_t stream_generation);
    int32_t (*withdraw_parent_type111)(void *context,
                                       const void *parent_session,
                                       uint64_t parent_generation);
} CLNativeSetupOps;

typedef int32_t (*CLNativeSetupCommitFn)(void *context, void *transaction);
typedef void (*CLNativeSetupRollbackFn)(void *context, void *transaction,
                                        const void *candidate_entry);

typedef struct CLNativeSetupResult {
    CLNativeSetupCode code;
    int32_t factory_result;
    const void *response_entry;
    const void *candidate_entry;
    void *transaction;
    void *transaction_context;
    CLNativeSetupCommitFn commit_callback;
    CLNativeSetupRollbackFn rollback_callback;
    CLNativeReadiness readiness_result;
    CLNativePrepareStatus prepare_result;
} CLNativeSetupResult;

/* Calls all factory stream handlers in original relative order before any
 * Type111 preparation. A failed stock call suppresses Type111 preparation.
 * Type111 is disabled unless the factory delegate, readiness/transaction
 * callbacks, child/parent-withdrawal callbacks, and a non-null
 * accepted-capability handle are supplied.
 * Batches with multiple Type111 entries, an unknown type alongside Type111,
 * or a Type110 connection identity collision fail closed for Type111.
 * Failure preserves factory_fallback_entry by pointer identity. A missing
 * request array with a valid result array initializes each result as invalid;
 * too-many-request and missing-result-array errors leave outputs untouched.
 * A null opaque_request in any element invalidates every result before any
 * factory callback is invoked.
 * The prepare callback must retain or encode its immutable identity and
 * required handle lifetimes in the transaction before returning. A prepared
 * result is transaction state: the caller must not modify, drop, or reuse it
 * and must finalize it exactly once. Passing serialization_succeeded=0 is the
 * abort/rollback path. The adapter allocates no memory and bounds processing
 * to eight entries. */
CLNativeSetupCode cl_native_setup_dispatch_batch(
    const CLNativeSetupRequest *requests, size_t request_count,
    const void *factory_fallback_entry, const CLNativeSetupOps *ops,
    CLNativeSetupResult *results);

/* Call exactly once for each PREPARED result, after serialization into a
 * private, untransmitted buffer (or with 0 to abort). The caller
 * may expose that buffer only if this returns TYPE111_COMMITTED; otherwise it
 * must send/use the original factory response. On failure, rollback runs and
 * the factory fallback is retained. Commit/rollback callbacks and context are
 * captured at prepare time, so a different ops table cannot redirect cleanup.
 * This adapter creates no listener, dataPort, or wire fields. */
CLNativeSetupCode cl_native_setup_finalize_type111(
    CLNativeSetupResult *result, int32_t serialization_succeeded);

/* Independent stream and parent teardown are delegated to project-owned
 * lifecycle callbacks. No Type110 callback or state is reachable here. */
int32_t cl_native_setup_withdraw_type111(
    const CLNativeSetupOps *ops, const void *parent_session,
    uint64_t parent_generation, const void *stream_connection,
    uint64_t stream_generation);
int32_t cl_native_setup_withdraw_parent_type111(
    const CLNativeSetupOps *ops, const void *parent_session,
    uint64_t parent_generation);

#ifdef __cplusplus
}
#endif

#endif
