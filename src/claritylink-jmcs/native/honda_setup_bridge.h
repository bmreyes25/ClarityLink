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
typedef int32_t (*CLHondaOriginalSetupFn)(
    void *receiver_session, const void *request_dictionary,
    void **response_dictionary_out);

typedef enum CLHondaExtractStatus {
    CL_HONDA_EXTRACT_NONE = 0,
    CL_HONDA_EXTRACT_ONE_TYPE111 = 1,
    CL_HONDA_EXTRACT_INVALID = 2
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
    CL_HONDA_BRIDGE_INVALID_ARGUMENT = 10
} CLHondaBridgeCode;

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
    void *stock_response;       /* Owned result from stock until selected or released. */
    void *candidate_response;   /* Owned until complete/transfer. */
    void *selected_response;    /* Stock until commit succeeds. */
    CLNativeSetupResult child;
    int32_t pending;
    int32_t candidate_transferred;
} CLHondaSetupBridgeResult;

/* Calls the original whole-request SETUP exactly once. Disabled, non-SETUP
 * and stock-error paths preserve its status and response pointer. With the
 * extension enabled, any missing Honda binding is reported explicitly and
 * falls back to that untouched stock response. The caller owns and releases
 * selected_response after its existing response/serializer lifetime. */
CLHondaBridgeCode cl_honda_setup_bridge_call(
    const CLHondaSetupBridgeBindings *bindings, int32_t extension_enabled,
    void *receiver_session, const void *request_dictionary,
    CLHondaSetupBridgeResult *out_result);

/* Call after candidate serialization into a private, untransmitted buffer.
 * On failure the project child rolls back and selected_response remains the
 * original stock response. On success the candidate response ownership is
 * transferred to the caller. Caller must not expose candidate bytes earlier. */
CLHondaBridgeCode cl_honda_setup_bridge_complete(
    const CLHondaSetupBridgeBindings *bindings,
    CLHondaSetupBridgeResult *result, int32_t serialization_succeeded);

#ifdef __cplusplus
}
#endif

#endif
