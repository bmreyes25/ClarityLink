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
    CL_NATIVE_SETUP_BATCH_COMPLETED = 14
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
    /* Stages only project-owned resources. The candidate is provisional. A
     * caller may serialize it into a private, untransmitted buffer; it must
     * keep the factory fallback response available until finalize commits. */
    CLNativePrepareStatus (*prepare_type111)(
        void *context, const CLNativeSetupRequest *request,
        void **transaction, const void **candidate_entry);
    /* Return 0 only if parent/generations/resources are still current and the
     * candidate remains valid after this cookie is consumed. Transfer/pin its
     * lifetime in project-owned state through response completion/withdrawal. */
    int32_t (*commit_type111)(void *context, void *transaction);
    /* Releases every partial output, including a candidate returned without
     * a transaction cookie after a faulty or partial prepare. */
    void (*rollback_type111)(void *context,
                             const CLNativeSetupRequest *request,
                             void *transaction,
                             const void *candidate_entry);
    int32_t (*withdraw_type111)(void *context, const void *parent_session,
                                uint64_t parent_generation,
                                const void *stream_connection,
                                uint64_t stream_generation);
    int32_t (*withdraw_parent_type111)(void *context,
                                       const void *parent_session,
                                       uint64_t parent_generation);
} CLNativeSetupOps;

typedef struct CLNativeSetupResult {
    CLNativeSetupCode code;
    int32_t factory_result;
    const void *response_entry;
    const void *candidate_entry;
    void *transaction;
    const CLNativeSetupRequest *request;
    CLNativeReadiness readiness_result;
    CLNativePrepareStatus prepare_result;
} CLNativeSetupResult;

/* Routes the input array in order. Type111 is disabled unless the factory
 * delegate, readiness/transaction callbacks, child/parent-withdrawal callbacks,
 * and a non-null accepted-capability handle are supplied.
 * Failure preserves factory_fallback_entry by pointer identity. Input request
 * storage must remain valid until every prepared result is finalized. The
 * function allocates no memory and bounds request processing to eight entries. */
CLNativeSetupCode cl_native_setup_dispatch_batch(
    const CLNativeSetupRequest *requests, size_t request_count,
    const void *factory_fallback_entry, const CLNativeSetupOps *ops,
    CLNativeSetupResult *results);

/* Call after serialization into a private, untransmitted buffer. The caller
 * may expose that buffer only if this returns TYPE111_COMMITTED; otherwise it
 * must send/use the original factory response. On failure, rollback runs and
 * the factory fallback is retained. This adapter creates no listener,
 * dataPort, or wire fields. */
CLNativeSetupCode cl_native_setup_finalize_type111(
    CLNativeSetupResult *result, const CLNativeSetupOps *ops,
    int32_t serialization_succeeded);

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
