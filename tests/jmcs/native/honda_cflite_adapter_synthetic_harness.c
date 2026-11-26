/* Synthetic CFLite fixture. It is intentionally not the Honda runtime. */
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "../../../src/claritylink-jmcs/native/honda_cflite_adapter.h"

enum { FAKE_DICTIONARY = 1, FAKE_ARRAY = 2, FAKE_INTEGER = 3 };
typedef struct FakeObject FakeObject;
struct FakeObject {
    CLHondaCFTypeID type_id;
    CLHondaCFObjectRef streams;
    CLHondaCFObjectRef item[8];
    size_t item_count;
    int64_t stream_type;
    int32_t read_error;
};

static CLHondaCFTypeID fake_type_id(CLHondaCFObjectRef object) {
    return object ? ((const FakeObject *)object)->type_id : 0;
}
static CLHondaCFTypeID fake_array_type_id(void) { return FAKE_ARRAY; }
static CLHondaCFTypeID fake_dictionary_type_id(void) { return FAKE_DICTIONARY; }
static CLHondaCFObjectRef fake_dictionary_get_value(
    CLHondaCFDictionaryRef dictionary, CLHondaCFObjectRef key) {
    (void)key;
    return ((const FakeObject *)dictionary)->streams;
}
static int64_t fake_dictionary_get_int64(
    CLHondaCFDictionaryRef dictionary, CLHondaCFObjectRef key,
    int32_t *out_error) {
    (void)key;
    *out_error = ((const FakeObject *)dictionary)->read_error;
    return ((const FakeObject *)dictionary)->stream_type;
}
static CLHondaCFIndex fake_array_get_count(CLHondaCFArrayRef array) {
    return (CLHondaCFIndex)((const FakeObject *)array)->item_count;
}
static CLHondaCFObjectRef fake_array_get_value_at_index(
    CLHondaCFArrayRef array, CLHondaCFIndex index) {
    const FakeObject *object = (const FakeObject *)array;
    return index >= 0 && (size_t)index < object->item_count
        ? object->item[index] : 0;
}

typedef struct FakeIdentity {
    int available;
    void *session;
    const void *capability;
} FakeIdentity;
static int32_t fake_resolve(void *context, void *session,
                            CLHondaCFDictionaryRef descriptor,
                            CLNativeSetupRequest *out) {
    FakeIdentity *identity = (FakeIdentity *)context;
    if (!identity->available || session != identity->session) return -1;
    out->stream_type = 111;
    out->parent_session = session;
    out->parent_generation = 4;
    out->stream_connection = (const void *)(uintptr_t)0x3300;
    out->stream_generation = 9;
    out->accepted_auxiliary_capability = identity->capability;
    out->opaque_request = descriptor;
    return 0;
}

static void setup_adapter(CLHondaCFLiteSetupAdapter *adapter,
                         FakeIdentity *identity) {
    memset(adapter, 0, sizeof(*adapter));
    adapter->cflite.get_type_id = fake_type_id;
    adapter->cflite.array_get_type_id = fake_array_type_id;
    adapter->cflite.dictionary_get_type_id = fake_dictionary_type_id;
    adapter->cflite.dictionary_get_value = fake_dictionary_get_value;
    adapter->cflite.dictionary_get_int64 = fake_dictionary_get_int64;
    adapter->cflite.array_get_count = fake_array_get_count;
    adapter->cflite.array_get_value_at_index = fake_array_get_value_at_index;
    adapter->provenance = CL_HONDA_CFLITE_BINDING_SYNTHETIC_TEST;
    adapter->identity_context = identity;
    adapter->resolve_accepted_stream = fake_resolve;
    adapter->streams_key = (const void *)(uintptr_t)0x111;
    adapter->type_key = (const void *)(uintptr_t)0x222;
    adapter->array_type_id = FAKE_ARRAY;
    adapter->dictionary_type_id = FAKE_DICTIONARY;
    adapter->type111_value = 111;
}

static int test_extract_and_authority_gate(void) {
    FakeIdentity identity = {1, (void *)(uintptr_t)0x4400,
                             (const void *)(uintptr_t)0x5500};
    CLHondaCFLiteSetupAdapter adapter;
    FakeObject descriptor = {.type_id = FAKE_DICTIONARY, .stream_type = 111};
    FakeObject array = {.type_id = FAKE_ARRAY, .item = {&descriptor},
                        .item_count = 1};
    FakeObject request = {.type_id = FAKE_DICTIONARY, .streams = &array};
    CLNativeSetupRequest extracted;
    size_t count = 0;
    setup_adapter(&adapter, &identity);
    if (cl_honda_cflite_extract_type111(
            &adapter, identity.session, &request, &extracted, &count) !=
            CL_HONDA_CFLITE_EXTRACT_ONE || count != 1 ||
        extracted.stream_type != 111 ||
        extracted.parent_session != identity.session ||
        extracted.accepted_auxiliary_capability != identity.capability ||
        extracted.opaque_request != &descriptor)
        return 1;
    identity.available = 0;
    if (cl_honda_cflite_extract_type111(
            &adapter, identity.session, &request, &extracted, &count) !=
            CL_HONDA_CFLITE_EXTRACT_AUTHORITY_UNAVAILABLE || count != 1 ||
        extracted.parent_session || extracted.accepted_auxiliary_capability)
        return 2;
    return 0;
}

static int test_none_and_malformed_inputs(void) {
    FakeIdentity identity = {1, (void *)(uintptr_t)0x4400,
                             (const void *)(uintptr_t)0x5500};
    CLHondaCFLiteSetupAdapter adapter;
    FakeObject descriptor = {.type_id = FAKE_DICTIONARY, .stream_type = 110};
    FakeObject array = {.type_id = FAKE_ARRAY, .item = {&descriptor},
                        .item_count = 1};
    FakeObject request = {.type_id = FAKE_DICTIONARY, .streams = &array};
    CLNativeSetupRequest extracted;
    size_t count = 0;
    setup_adapter(&adapter, &identity);
    if (cl_honda_cflite_extract_type111(
            &adapter, identity.session, &request, &extracted, &count) !=
            CL_HONDA_CFLITE_EXTRACT_NONE || count != 0)
        return 1;
    descriptor.stream_type = 111;
    descriptor.read_error = -1;
    if (cl_honda_cflite_extract_type111(
            &adapter, identity.session, &request, &extracted, &count) !=
            CL_HONDA_CFLITE_EXTRACT_ERROR)
        return 2;
    descriptor.read_error = 0;
    array.item[1] = &descriptor;
    array.item_count = 2;
    if (cl_honda_cflite_extract_type111(
            &adapter, identity.session, &request, &extracted, &count) !=
            CL_HONDA_CFLITE_EXTRACT_ERROR || count != 2)
        return 3;
    array.item_count = 9;
    if (cl_honda_cflite_extract_type111(
            &adapter, identity.session, &request, &extracted, &count) !=
            CL_HONDA_CFLITE_EXTRACT_ERROR)
        return 4;
    return 0;
}

static int test_unresolved_binding_fails_closed(void) {
    FakeIdentity identity = {1, (void *)(uintptr_t)0x4400,
                             (const void *)(uintptr_t)0x5500};
    CLHondaCFLiteSetupAdapter adapter;
    FakeObject request = {.type_id = FAKE_DICTIONARY};
    CLNativeSetupRequest extracted;
    size_t count = 0;
    setup_adapter(&adapter, &identity);
    adapter.provenance = CL_HONDA_CFLITE_BINDING_UNRESOLVED;
    if (cl_honda_cflite_extract_type111(
            &adapter, identity.session, &request, &extracted, &count) !=
        CL_HONDA_CFLITE_EXTRACT_BINDING_UNAVAILABLE)
        return 1;
    adapter.provenance = CL_HONDA_CFLITE_BINDING_SYNTHETIC_TEST;
    adapter.cflite.array_get_value_at_index = 0;
    if (cl_honda_cflite_extract_type111(
            &adapter, identity.session, &request, &extracted, &count) !=
        CL_HONDA_CFLITE_EXTRACT_BINDING_UNAVAILABLE)
        return 2;
    return 0;
}

int main(void) {
    if (test_extract_and_authority_gate()) return 10;
    if (test_none_and_malformed_inputs()) return 20;
    if (test_unresolved_binding_fails_closed()) return 30;
    puts("SYNTHETIC_CFLITE_ADAPTER_PASS type_scan=PASS authority_gate=PASS malformed=PASS");
    return 0;
}
