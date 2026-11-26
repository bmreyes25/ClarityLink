#include "honda_cflite_adapter.h"

#define CL_HONDA_CFLITE_MAX_STREAMS 8

static int bindings_complete(const CLHondaCFLiteSetupAdapter *adapter) {
    const CLHondaCFLiteGetterBindings *api = &adapter->cflite;
    return api->get_type_id && api->array_get_type_id &&
           api->dictionary_get_type_id && api->dictionary_get_value &&
           api->dictionary_get_int64 && api->array_get_count &&
           api->array_get_value_at_index && adapter->resolve_accepted_stream &&
           adapter->streams_key && adapter->type_key &&
           adapter->array_type_id && adapter->dictionary_type_id;
}

CLHondaCFLiteExtractResult cl_honda_cflite_extract_type111(
    void *adapter_context, void *receiver_session,
    CLHondaCFDictionaryRef request_dictionary,
    CLNativeSetupRequest *out_request, size_t *out_type111_count) {
    CLHondaCFLiteSetupAdapter *adapter =
        (CLHondaCFLiteSetupAdapter *)adapter_context;
    CLHondaCFObjectRef streams_object;
    CLHondaCFArrayRef streams;
    CLHondaCFIndex count;
    CLHondaCFIndex index;
    size_t found = 0;
    CLHondaCFDictionaryRef selected = 0;
    int32_t authority_unavailable = 0;

    if (out_type111_count) *out_type111_count = 0;
    if (out_request) {
        out_request->stream_type = 0;
        out_request->parent_session = 0;
        out_request->parent_generation = 0;
        out_request->stream_connection = 0;
        out_request->stream_generation = 0;
        out_request->accepted_auxiliary_capability = 0;
        out_request->opaque_request = 0;
    }
    if (!adapter || !receiver_session || !request_dictionary || !out_request ||
        !out_type111_count)
        return CL_HONDA_CFLITE_EXTRACT_ERROR;
    if (adapter->provenance == CL_HONDA_CFLITE_BINDING_UNRESOLVED ||
        !bindings_complete(adapter))
        return CL_HONDA_CFLITE_EXTRACT_BINDING_UNAVAILABLE;
    if (adapter->provenance != CL_HONDA_CFLITE_BINDING_RUNTIME_VERIFIED &&
        adapter->provenance != CL_HONDA_CFLITE_BINDING_SYNTHETIC_TEST)
        return CL_HONDA_CFLITE_EXTRACT_BINDING_UNAVAILABLE;
    if (adapter->cflite.array_get_type_id() != adapter->array_type_id ||
        adapter->cflite.dictionary_get_type_id() !=
            adapter->dictionary_type_id)
        return CL_HONDA_CFLITE_EXTRACT_ERROR;
    if (adapter->cflite.get_type_id(request_dictionary) !=
        adapter->dictionary_type_id)
        return CL_HONDA_CFLITE_EXTRACT_ERROR;

    streams_object = adapter->cflite.dictionary_get_value(
        request_dictionary, adapter->streams_key);
    if (!streams_object) return CL_HONDA_CFLITE_EXTRACT_NONE;
    if (adapter->cflite.get_type_id(streams_object) !=
        adapter->array_type_id)
        return CL_HONDA_CFLITE_EXTRACT_ERROR;
    streams = (CLHondaCFArrayRef)streams_object;
    count = adapter->cflite.array_get_count(streams);
    if (count < 0 || count > CL_HONDA_CFLITE_MAX_STREAMS)
        return CL_HONDA_CFLITE_EXTRACT_ERROR;

    for (index = 0; index < count; ++index) {
        CLHondaCFObjectRef item = adapter->cflite.array_get_value_at_index(
            streams, index);
        CLHondaCFDictionaryRef descriptor;
        int32_t read_error = 0;
        int64_t stream_type;
        if (!item || adapter->cflite.get_type_id(item) !=
                         adapter->dictionary_type_id)
            return CL_HONDA_CFLITE_EXTRACT_ERROR;
        descriptor = (CLHondaCFDictionaryRef)item;
        stream_type = adapter->cflite.dictionary_get_int64(
            descriptor, adapter->type_key, &read_error);
        if (read_error != 0 || stream_type < 0 || stream_type > INT32_MAX)
            return CL_HONDA_CFLITE_EXTRACT_ERROR;
        if (stream_type != adapter->type111_value) continue;
        ++found;
        selected = descriptor;
    }
    *out_type111_count = found;
    if (found == 0) return CL_HONDA_CFLITE_EXTRACT_NONE;
    if (found != 1 || !selected)
        return CL_HONDA_CFLITE_EXTRACT_ERROR;

    if (adapter->resolve_accepted_stream(adapter->identity_context,
                                         receiver_session, selected,
                                         out_request) != 0) {
        authority_unavailable = 1;
    } else if (out_request->stream_type != adapter->type111_value ||
               out_request->opaque_request != selected ||
               !out_request->parent_session ||
               !out_request->parent_generation ||
               !out_request->stream_connection ||
               !out_request->stream_generation ||
               !out_request->accepted_auxiliary_capability) {
        authority_unavailable = 1;
    }
    if (authority_unavailable) {
        out_request->stream_type = 0;
        out_request->parent_session = 0;
        out_request->parent_generation = 0;
        out_request->stream_connection = 0;
        out_request->stream_generation = 0;
        out_request->accepted_auxiliary_capability = 0;
        out_request->opaque_request = 0;
        return CL_HONDA_CFLITE_EXTRACT_AUTHORITY_UNAVAILABLE;
    }
    return CL_HONDA_CFLITE_EXTRACT_ONE;
}

CLHondaExtractStatus cl_honda_cflite_extract_bridge_callback(
    void *adapter_context, void *receiver_session,
    const void *request_dictionary, CLNativeSetupRequest *out_request,
    size_t *out_type111_count) {
    return (CLHondaExtractStatus)cl_honda_cflite_extract_type111(
        adapter_context, receiver_session,
        (CLHondaCFDictionaryRef)request_dictionary, out_request,
        out_type111_count);
}
