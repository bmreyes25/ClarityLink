#ifndef CLARITYLINK_HONDA_SETUP_BRIDGE_H
#define CLARITYLINK_HONDA_SETUP_BRIDGE_H

#include "setup_dispatch.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Android API17 ARMv7 AAPCS32 contract at Honda's Setup callsite:
 * r0=session, r1=request dictionary, r2=response-out pointer; r0 returns the
 * 32-bit OSStatus. No stack arguments. The function pointer must already
 * carry the correct Thumb state from a validated resolver; this bridge does
 * not derive addresses or alter code. A production adapter must compile a
 * typed thunk against the recovered Honda typedefs; it must not cast an
 * untyped address to this normalized opaque-pointer signature. */
#if defined(CL_HONDA_ARM32_ABI)
_Static_assert(sizeof(void *) == 4, "Honda bridge requires 32-bit pointers");
#endif
typedef int32_t (*CLHondaAirPlayReceiverSessionSetupFn)(
    void *receiver_session, const void *request_dictionary,
    void **response_dictionary_out);
typedef CLHondaAirPlayReceiverSessionSetupFn CLHondaOriginalSetupFn;

typedef enum CLHondaExtractStatus {
    CL_HONDA_EXTRACT_NONE = 0,
    CL_HONDA_EXTRACT_ONE_TYPE111 = 1,
    CL_HONDA_EXTRACT_INVALID = 2,
    CL_HONDA_EXTRACT_AUTHORITY_UNAVAILABLE = 3,
    CL_HONDA_EXTRACT_BINDING_UNAVAILABLE = 4
} CLHondaExtractStatus;

typedef CLHondaExtractStatus (*CLHondaExtractType111Fn)(
    void *context, void *receiver_session, const void *request_dictionary,
    CLNativeSetupRequest *out_request, size_t *out_type111_count);

/* Must return a separately owned response candidate, preserving every stock
 * response field/entry and appending exactly one independently owned child
 * entry. It may not mutate stock_response. */
typedef int32_t (*CLHondaBuildResponseCandidateFn)(
    void *context, const void *stock_response,
    const void *type111_response_entry, void **out_candidate_response);
typedef void (*CLHondaReleaseResponseFn)(void *context, void *response);

typedef enum CLHondaBridgeCode {
    CL_HONDA_BRIDGE_STOCK_ONLY = 0,
    CL_HONDA_BRIDGE_TYPE111_PENDING = 1,
    CL_HONDA_BRIDGE_TYPE111_COMMITTED = 2,
    CL_HONDA_BRIDGE_STOCK_ERROR = 3,
    CL_HONDA_BRIDGE_BINDING_UNAVAILABLE = 4,
    CL_HONDA_BRIDGE_EXTRACT_FAILED = 5,
    CL_HONDA_BRIDGE_CHILD_REJECTED = 6,
    CL_HONDA_BRIDGE_RESPONSE_BUILD_FAILED = 7,
    CL_HONDA_BRIDGE_SERIALIZATION_FAILED = 8,
    CL_HONDA_BRIDGE_COMMIT_FAILED = 9,
    CL_HONDA_BRIDGE_INVALID_ARGUMENT = 10,
    CL_HONDA_BRIDGE_PENDING_DELIVERY = 11,
    CL_HONDA_BRIDGE_DELIVERY_FAILED = 12,
    CL_HONDA_BRIDGE_PARENT_ENDED = 13,
    CL_HONDA_BRIDGE_CLEANUP_FAILED = 14
} CLHondaBridgeCode;

typedef enum CLHondaDeliveryOutcome {
    CL_HONDA_DELIVERY_SENT = 0,
    CL_HONDA_DELIVERY_NOT_PUBLISHED = 1,
    CL_HONDA_DELIVERY_PARTIAL_OR_UNKNOWN = 2
} CLHondaDeliveryOutcome;

typedef struct CLHondaSetupBridgeBindings {
    void *context;
    CLHondaOriginalSetupFn original_setup;
    CLHondaExtractType111Fn extract_type111;
    CLHondaBuildResponseCandidateFn build_response_candidate;
    CLHondaReleaseResponseFn release_response;
    CLNativeSetupOps type111_ops;
} CLHondaSetupBridgeBindings;

typedef struct CLHondaSetupBridgeResult {
    CLHondaBridgeCode code;
    int32_t stock_status;
    void *stock_response;
    void *candidate_response;
    void *selected_response;
    CLNativeSetupResult child;
    void *callback_context;
    CLHondaReleaseResponseFn captured_release_response;
    int32_t (*captured_withdraw_type111)(
        void *context, const void *parent_session, uint64_t parent_generation,
        const void *stream_connection, uint64_t stream_generation);
    int32_t (*captured_withdraw_parent_type111)(
        void *context, const void *parent_session, uint64_t parent_generation);
    const void *parent_session;
    uint64_t parent_generation;
    const void *stream_connection;
    uint64_t stream_generation;
    int32_t pending;
    int32_t awaiting_delivery;
    int32_t delivery_confirmed;
    int32_t parent_ended;
    int32_t withdrawal_attempted;
    int32_t withdrawal_status;
    int32_t resources_may_remain;
} CLHondaSetupBridgeResult;

/* Calls the original whole-request SETUP exactly once. Disabled, non-SETUP
 * and stock-error paths preserve its status and response pointer. When
 * enabled, missing Honda bindings are explicit and the stock response stays
 * selected. The caller owns selected_response unless the bridge explicitly
 * retains it through the delivery transaction. */
CLHondaBridgeCode cl_honda_setup_bridge_call(
    const CLHondaSetupBridgeBindings *bindings, int32_t extension_enabled,
    void *receiver_session, const void *request_dictionary,
    CLHondaSetupBridgeResult *out_result);

/* Call after candidate serialization into a private, untransmitted buffer.
 * Callback context and cleanup functions were captured during preparation.
 * A committed child remains pending until a delivery outcome is reported. */
CLHondaBridgeCode cl_honda_setup_bridge_complete(
    CLHondaSetupBridgeResult *result, int32_t serialization_succeeded);

/* SENT means the full response passed the transport's completed-write edge.
 * NOT_PUBLISHED transfers untouched stock response ownership for fallback.
 * PARTIAL_OR_UNKNOWN withdraws the child and releases both response graphs. */
CLHondaBridgeCode cl_honda_setup_bridge_delivery(
    CLHondaSetupBridgeResult *result, CLHondaDeliveryOutcome outcome);

/* Session teardown rolls back pending state or withdraws committed state using
 * the captured callback context. Repeated calls are idempotent. */
CLHondaBridgeCode cl_honda_setup_bridge_parent_ended(
    CLHondaSetupBridgeResult *result);

#ifdef __cplusplus
}
#endif

#endif
