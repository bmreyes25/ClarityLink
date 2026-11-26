#ifndef CLARITYLINK_HONDA_CFLITE_ADAPTER_H
#define CLARITYLINK_HONDA_CFLITE_ADAPTER_H

#include "setup_dispatch.h"
#include "honda_setup_bridge.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Opaque Honda CFLite handles. These do not import Apple's CF ABI. Function
 * pointer prototypes below are the ARM32 wrapper contracts recovered from
 * the hash-matched jmcs call path. A runtime resolver must populate them with
 * correctly relocated/Thumb-adjusted addresses; ELF VAs are never callable. */
typedef const void *CLHondaCFObjectRef;
typedef const void *CLHondaCFDictionaryRef;
typedef const void *CLHondaCFArrayRef;
typedef int32_t CLHondaCFIndex;
typedef uint32_t CLHondaCFTypeID;

typedef CLHondaCFTypeID (*CLHondaCFGetTypeIDFn)(CLHondaCFObjectRef object);
typedef CLHondaCFTypeID (*CLHondaCFGetContainerTypeIDFn)(void);
typedef CLHondaCFObjectRef (*CLHondaCFDictionaryGetValueFn)(
    CLHondaCFDictionaryRef dictionary, CLHondaCFObjectRef key);
typedef int64_t (*CLHondaCFDictionaryGetInt64Fn)(
    CLHondaCFDictionaryRef dictionary, CLHondaCFObjectRef key,
    int32_t *out_error);
typedef CLHondaCFIndex (*CLHondaCFArrayGetCountFn)(CLHondaCFArrayRef array);
typedef CLHondaCFObjectRef (*CLHondaCFArrayGetValueAtIndexFn)(
    CLHondaCFArrayRef array, CLHondaCFIndex index);

typedef struct CLHondaCFLiteGetterBindings {
    CLHondaCFGetTypeIDFn get_type_id;
    CLHondaCFGetContainerTypeIDFn array_get_type_id;
    CLHondaCFGetContainerTypeIDFn dictionary_get_type_id;
    CLHondaCFDictionaryGetValueFn dictionary_get_value;
    CLHondaCFDictionaryGetInt64Fn dictionary_get_int64;
    CLHondaCFArrayGetCountFn array_get_count;
    CLHondaCFArrayGetValueAtIndexFn array_get_value_at_index;
} CLHondaCFLiteGetterBindings;

typedef enum CLHondaCFLiteBindingProvenance {
    CL_HONDA_CFLITE_BINDING_UNRESOLVED = 0,
    CL_HONDA_CFLITE_BINDING_RUNTIME_VERIFIED = 1,
    CL_HONDA_CFLITE_BINDING_SYNTHETIC_TEST = 2
} CLHondaCFLiteBindingProvenance;

/* This resolver must map a real Honda descriptor to already-established
 * authenticated parent/stream identities and accepted authority. This
 * adapter validates the returned handles but cannot create that authority. */
typedef int32_t (*CLHondaResolveAcceptedStreamFn)(
    void *context, void *receiver_session,
    CLHondaCFDictionaryRef stream_descriptor,
    CLNativeSetupRequest *out_request);

typedef struct CLHondaCFLiteSetupAdapter {
    CLHondaCFLiteGetterBindings cflite;
    CLHondaCFLiteBindingProvenance provenance;
    void *identity_context;
    CLHondaResolveAcceptedStreamFn resolve_accepted_stream;
    CLHondaCFObjectRef streams_key;
    CLHondaCFObjectRef type_key;
    CLHondaCFTypeID array_type_id;
    CLHondaCFTypeID dictionary_type_id;
    int32_t type111_value;
} CLHondaCFLiteSetupAdapter;

typedef enum CLHondaCFLiteExtractResult {
    CL_HONDA_CFLITE_EXTRACT_ERROR = CL_HONDA_EXTRACT_INVALID,
    CL_HONDA_CFLITE_EXTRACT_NONE = CL_HONDA_EXTRACT_NONE,
    CL_HONDA_CFLITE_EXTRACT_ONE = CL_HONDA_EXTRACT_ONE_TYPE111,
    CL_HONDA_CFLITE_EXTRACT_AUTHORITY_UNAVAILABLE =
        CL_HONDA_EXTRACT_AUTHORITY_UNAVAILABLE,
    CL_HONDA_CFLITE_EXTRACT_BINDING_UNAVAILABLE =
        CL_HONDA_EXTRACT_BINDING_UNAVAILABLE
} CLHondaCFLiteExtractResult;

/* Reads only the SETUP request's streams/type fields. Getters return borrowed
 * references for the observed Honda wrappers. At most eight descriptors are
 * examined. Missing authenticated identity/capability is a hard refusal. */
CLHondaCFLiteExtractResult cl_honda_cflite_extract_type111(
    void *adapter_context, void *receiver_session,
    CLHondaCFDictionaryRef request_dictionary,
    CLNativeSetupRequest *out_request, size_t *out_type111_count);

/* Directly usable as CLHondaExtractType111Fn. */
CLHondaExtractStatus cl_honda_cflite_extract_bridge_callback(
    void *adapter_context, void *receiver_session,
    const void *request_dictionary, CLNativeSetupRequest *out_request,
    size_t *out_type111_count);

#ifdef __cplusplus
}
#endif

#endif
