#include <stdint.h>
#include "../../../src/claritylink-jmcs/native/info_augmentation.h"

enum { OBJ_ARRAY = 1, OBJ_DICTIONARY = 2, OBJ_STRING = 3, OBJ_NUMBER = 4 };
typedef struct TestObject TestObject;
struct TestObject {
    uint32_t kind;
    int32_t refs;
    int32_t alive;
    int64_t number;
    char string[40];
    uint32_t count;
    TestObject *keys[4];
    TestObject *values[4];
};

static TestObject pool[256];
static uint32_t pool_used;
static int32_t live_objects;
static int32_t ownership_errors;
static int32_t allocation_number;
static int32_t fail_allocation_number;
static int32_t fail_append;
static int32_t dictionary_callbacks_enabled = 1;
static int32_t array_callbacks_enabled = 1;
static int32_t force_negative_count;
static int32_t append_calls;
static int32_t fail_append_at;
static int32_t fail_dictionary_set_at;
static int32_t dictionary_set_calls;
static TestObject primary;
static TestObject displays;
static TestObject *augmented;
static void *augmented_raw;
static TestObject factory_only;
static TestObject type_key;
static TestObject uuid_key;
static TestObject primary_uuid;
static TestObject *candidate_number;
static TestObject *candidate;
static void *candidate_raw;
static const char candidate_uuid[] = "abcdefab-cdef-4abc-8def-abcdefabcdef";

static void retain_object(TestObject *object) {
    if (object && object->alive) ++object->refs;
    else if (object) ++ownership_errors;
}

static void release_object(TestObject *object) {
    uint32_t i;
    if (!object) return;
    if (!object->alive || object->refs <= 0) { ++ownership_errors; return; }
    if (--object->refs != 0) return;
    object->alive = 0;
    --live_objects;
    if (object->kind == OBJ_DICTIONARY) {
        for (i = 0; i < object->count && i < 4u; ++i) {
            release_object(object->keys[i]);
            release_object(object->values[i]);
        }
    } else if (object->kind == OBJ_ARRAY) {
        for (i = 0; i < object->count && i < 4u; ++i)
            release_object(object->values[i]);
    }
}

static TestObject *allocate_object(uint32_t kind) {
    TestObject *object;
    ++allocation_number;
    if (fail_allocation_number == allocation_number || pool_used >= 256u)
        return 0;
    object = &pool[pool_used++];
    object->kind = kind;
    object->refs = 1;
    object->alive = 1;
    ++live_objects;
    object->count = 0;
    object->number = 0;
    object->string[0] = '\0';
    return object;
}

static void *api_dictionary_create(long capacity, const void *keys,
                                   const void *values) {
    (void)capacity; (void)keys; (void)values;
    return allocate_object(OBJ_DICTIONARY);
}

static void api_dictionary_set(void *opaque, const void *key,
                               const void *value) {
    TestObject *dictionary = (TestObject *)opaque;
    uint32_t slot;
    ++dictionary_set_calls;
    if (dictionary_set_calls == fail_dictionary_set_at) return;
    slot = dictionary->count++;
    if (slot >= 4u) return;
    dictionary->keys[slot] = (TestObject *)key;
    dictionary->values[slot] = (TestObject *)value;
    retain_object(dictionary->keys[slot]);
    retain_object(dictionary->values[slot]);
}

static const void *api_dictionary_get(const void *opaque, const void *key) {
    const TestObject *dictionary = (const TestObject *)opaque;
    uint32_t i;
    if (!dictionary || !dictionary->alive || !key) { ++ownership_errors; return 0; }
    for (i = 0; i < dictionary->count && i < 4u; ++i) {
        const TestObject *stored_key = dictionary->keys[i];
        if (stored_key->kind == OBJ_STRING && ((const TestObject *)key)->kind == OBJ_STRING) {
            uint32_t j = 0;
            while (stored_key->string[j] == ((const TestObject *)key)->string[j] &&
                   stored_key->string[j] != '\0') ++j;
            if (stored_key->string[j] == ((const TestObject *)key)->string[j])
                return dictionary->values[i];
        }
    }
    return 0;
}

static int api_is_array(const void *value) {
    return ((const TestObject *)value)->kind == OBJ_ARRAY;
}

static int api_is_dictionary(const void *value) {
    return ((const TestObject *)value)->kind == OBJ_DICTIONARY;
}

static int api_uuid_equal(const void *value, const char *canonical_uuid) {
    const TestObject *object = (const TestObject *)value;
    uint32_t i;
    if (!object || !object->alive || object->kind != OBJ_STRING) return 0;
    for (i = 0; i < 40u; ++i) {
        char a = object->string[i], b = canonical_uuid[i];
        if (a >= 'A' && a <= 'F') a = (char)(a - 'A' + 'a');
        if (b >= 'A' && b <= 'F') b = (char)(b - 'A' + 'a');
        if (a != b) return 0;
        if (!a) return 1;
    }
    return 0;
}

static long api_array_count(const void *value) {
    const TestObject *array = (const TestObject *)value;
    if (!array || !array->alive) { ++ownership_errors; return -1; }
    if (force_negative_count) return -1;
    return (long)array->count;
}

static void *api_array_create(long capacity, const void *callbacks) {
    (void)capacity; (void)callbacks;
    return allocate_object(OBJ_ARRAY);
}

static const void *api_array_value(const void *value, long index) {
    const TestObject *array = (const TestObject *)value;
    if (!array || !array->alive) { ++ownership_errors; return 0; }
    return index < 0 || (uint32_t)index >= array->count
        ? 0 : array->values[index];
}

static int api_array_append(void *opaque, const void *value) {
    TestObject *array = (TestObject *)opaque;
    ++append_calls;
    if (fail_append || append_calls == fail_append_at || array->count >= 4u)
        return 0;
    array->values[array->count++] = (TestObject *)value;
    retain_object(array->values[array->count - 1u]);
    return 1;
}

static const void *api_string(const char *value) {
    TestObject *object = allocate_object(OBJ_STRING);
    uint32_t i;
    if (!object || !value) return 0;
    for (i = 0; i < 39u; ++i) {
        object->string[i] = value[i];
        if (!value[i]) return object;
    }
    object->string[39] = '\0';
    return object;
}

static const void *api_number(int64_t value) {
    TestObject *object = allocate_object(OBJ_NUMBER);
    if (!object) return 0;
    object->number = value;
    return object;
}

static int api_is_type111(const void *value) {
    const TestObject *object = (const TestObject *)value;
    if (!object || !object->alive) { ++ownership_errors; return 0; }
    if (object->kind == OBJ_NUMBER) return object->number == 111;
    return object->kind == OBJ_STRING && object->string[0] == '1' &&
           object->string[1] == '1' && object->string[2] == '1' &&
           object->string[3] == '\0';
}

static int api_equal(const void *left, const void *right) {
    const TestObject *a = (const TestObject *)left;
    const TestObject *b = (const TestObject *)right;
    uint32_t i;
    if (!a || !b || !a->alive || !b->alive) { ++ownership_errors; return 0; }
    if (a->kind != b->kind) return 0;
    if (a->kind == OBJ_NUMBER) return a->number == b->number;
    if (a->kind == OBJ_STRING) {
        for (i = 0; i < 40u; ++i) {
            if (a->string[i] != b->string[i]) return 0;
            if (!a->string[i]) return 1;
        }
    }
    return a == b;
}

static int api_dictionary_callbacks_retain(const void *keys, const void *values) {
    return dictionary_callbacks_enabled && keys == (const void *)1 && values == (const void *)1;
}

static int api_array_callbacks_retain(const void *callbacks) {
    return array_callbacks_enabled && callbacks == (const void *)1;
}

static void api_release(const void *value) {
    release_object((TestObject *)value);
}

static const CLCFAPI api = {
    api_dictionary_create, api_dictionary_set, api_dictionary_get,
    api_is_array, api_is_dictionary, api_uuid_equal,
    api_array_count, api_array_value,
    api_array_create, api_array_append, api_string, api_number, api_equal,
    api_is_type111,
    api_dictionary_callbacks_retain, api_array_callbacks_retain, api_release
};

static int32_t run_append_success(void) {
    CLDisplayProfile profile = { candidate_uuid, (const void *)1,
                                 (const void *)1, (const void *)1 };
    CLInfoAugmentResult result;
    allocation_number = 0;
    fail_allocation_number = 0;
    fail_append = 0;
    append_calls = 0;
    fail_append_at = 0;
    fail_dictionary_set_at = 0;
    dictionary_set_calls = 0;
    pool_used = 0;
    live_objects = 0;
    ownership_errors = 0;
    primary.kind = OBJ_DICTIONARY;
    primary.refs = 1; primary.alive = 1;
    primary.count = 1;
    type_key.kind = OBJ_STRING; type_key.refs = 1; type_key.alive = 1;
    type_key.string[0] = 't'; type_key.string[1] = 'y';
    type_key.string[2] = 'p'; type_key.string[3] = 'e';
    type_key.string[4] = '\0';
    uuid_key.kind = OBJ_STRING; uuid_key.refs = 1; uuid_key.alive = 1;
    uuid_key.string[0] = 'u'; uuid_key.string[1] = 'u';
    uuid_key.string[2] = 'i'; uuid_key.string[3] = 'd';
    uuid_key.string[4] = '\0';
    primary_uuid.kind = OBJ_NUMBER; primary_uuid.refs = 1; primary_uuid.alive = 1;
    primary_uuid.number = 7331;
    primary.keys[0] = &uuid_key;
    primary.values[0] = &primary_uuid;
    displays.kind = OBJ_ARRAY; displays.refs = 1; displays.alive = 1;
    displays.count = 1;
    retain_object(&primary);
    retain_object(&uuid_key);
    retain_object(&primary_uuid);
    displays.values[0] = &primary;
    augmented_raw = 0;
    result = cl_info_create_augmented_displays(&api, &displays, &profile,
                                                &augmented_raw);
    augmented = (TestObject *)augmented_raw;
    if (result != CL_INFO_AUGMENT_OK || !augmented || augmented->count != 2u)
        return 1;
    if (displays.count != 1u || augmented->values[0] != &primary ||
        primary_uuid.number != 7331 ||
        primary_uuid.kind != OBJ_NUMBER) return 2;
    candidate = augmented->values[1];
    if (!candidate || candidate->kind != OBJ_DICTIONARY || candidate->count != 2u)
        return 3;
    candidate_number = (TestObject *)api_dictionary_get(candidate, (const void *)&type_key);
    if (!candidate_number || !candidate_number->alive ||
        candidate_number->kind != OBJ_NUMBER ||
        candidate_number->number != 111)
        return 4;
    return 0;
}

int32_t cl_native_info_test_entry(void) {
    CLDisplayProfile profile = { candidate_uuid, (const void *)1,
                                 (const void *)1, (const void *)1 };
    CLInfoAugmentResult result;
    int32_t failure_at;
    int32_t baseline_live;
    int32_t status = run_append_success();
    if (status) return status;

    baseline_live = live_objects;
    allocation_number = 0;
    {
        TestObject *existing_uuid = (TestObject *)api_dictionary_get(
            augmented->values[1], &uuid_key);
        uint32_t i;
        if (!existing_uuid || !existing_uuid->alive) return 5;
        for (i = 0; i < 36u; ++i) {
            if (existing_uuid->string[i] >= 'a' && existing_uuid->string[i] <= 'f')
                existing_uuid->string[i] = (char)(existing_uuid->string[i] - 'a' + 'A');
        }
    }
    result = cl_info_create_type111_candidate(&api, augmented, &profile,
                                               &candidate_raw);
    if (result != CL_INFO_AUGMENT_DUPLICATE_AUXILIARY || candidate_raw) return 6;
    release_object(augmented);
    augmented = 0;
    displays.count = 1;
    if (live_objects != 0) return 7;

    dictionary_callbacks_enabled = 0;
    result = cl_info_create_type111_candidate(&api, &displays, &profile,
                                               &candidate_raw);
    if (result != CL_INFO_AUGMENT_INVALID_ARGUMENT || candidate_raw) return 15;
    dictionary_callbacks_enabled = 1;
    array_callbacks_enabled = 0;
    augmented_raw = 0;
    result = cl_info_create_augmented_displays(&api, &displays, &profile,
                                                &augmented_raw);
    if (result != CL_INFO_AUGMENT_INVALID_ARGUMENT || augmented_raw) return 18;
    array_callbacks_enabled = 1;
    if (cl_info_create_type111_candidate(0, &displays, &profile,
                                         &candidate_raw) != CL_INFO_AUGMENT_INVALID_ARGUMENT ||
        candidate_raw) return 19;
    if (cl_info_create_type111_candidate(&api, &displays, 0,
                                         &candidate_raw) != CL_INFO_AUGMENT_INVALID_ARGUMENT ||
        candidate_raw) return 20;
    force_negative_count = 1;
    result = cl_info_create_type111_candidate(&api, &displays, &profile,
                                               &candidate_raw);
    force_negative_count = 0;
    if (result != CL_INFO_AUGMENT_INVALID_ARGUMENT || candidate_raw) return 21;
    {
        TestObject malformed, malformed_array;
        malformed.kind = OBJ_NUMBER; malformed.alive = 1; malformed.refs = 1;
        malformed.number = 55; malformed_array.kind = OBJ_ARRAY;
        malformed_array.alive = 1; malformed_array.refs = 1;
        malformed_array.count = 1; malformed_array.values[0] = &malformed;
        result = cl_info_create_type111_candidate(&api, &malformed_array,
                                                   &profile, &candidate_raw);
        if (result != CL_INFO_AUGMENT_INVALID_ARGUMENT || candidate_raw) return 22;
    }
    profile.uuid = "invalid";
    result = cl_info_create_type111_candidate(&api, &displays, &profile,
                                               &candidate_raw);
    if (result != CL_INFO_AUGMENT_INVALID_UUID || candidate_raw) return 16;
    profile.uuid = candidate_uuid;
    factory_only.kind = OBJ_ARRAY; factory_only.refs = 1; factory_only.alive = 1;
    factory_only.count = 1;
    retain_object(&primary);
    factory_only.values[0] = &primary;
    baseline_live = live_objects;
    {
        TestObject over_limit;
        over_limit.kind = OBJ_ARRAY; over_limit.count = 9u;
        over_limit.alive = 1; over_limit.refs = 1;
        result = cl_info_create_type111_candidate(&api, &over_limit, &profile,
                                                   &candidate_raw);
        if (result != CL_INFO_AUGMENT_INVALID_ARGUMENT || candidate_raw) return 17;
    }
    {
        TestObject type_string, other_uuid, typed_descriptor, typed_array;
        type_string.kind = OBJ_STRING; type_string.refs = 1; type_string.alive = 1;
        type_string.string[0] = '1'; type_string.string[1] = '1';
        type_string.string[2] = '1'; type_string.string[3] = '\0';
        other_uuid.kind = OBJ_STRING; other_uuid.refs = 1; other_uuid.alive = 1;
        {
            const char value[] = "12345678-1234-4234-8234-123456789abc";
            uint32_t i;
            for (i = 0; i < sizeof(value); ++i) other_uuid.string[i] = value[i];
        }
        typed_descriptor.kind = OBJ_DICTIONARY; typed_descriptor.refs = 1;
        typed_descriptor.alive = 1; typed_descriptor.count = 2;
        typed_descriptor.keys[0] = &uuid_key; typed_descriptor.values[0] = &other_uuid;
        typed_descriptor.keys[1] = &type_key; typed_descriptor.values[1] = &type_string;
        typed_array.kind = OBJ_ARRAY; typed_array.refs = 1; typed_array.alive = 1;
        typed_array.count = 1; typed_array.values[0] = &typed_descriptor;
        result = cl_info_create_type111_candidate(&api, &typed_array, &profile,
                                                   &candidate_raw);
        if (result != CL_INFO_AUGMENT_DUPLICATE_AUXILIARY || candidate_raw) return 23;
    }
    for (failure_at = 1; failure_at <= 6; ++failure_at) {
        allocation_number = 0;
        fail_allocation_number = failure_at;
        augmented_raw = 0;
        result = cl_info_create_augmented_displays(&api, &factory_only,
                                                    &profile, &augmented_raw);
        if (result != CL_INFO_AUGMENT_ALLOCATION_FAILED) return 100 + failure_at;
        if (augmented_raw) return 110 + failure_at;
        if (factory_only.count != 1u) return 120 + failure_at;
        if (live_objects != baseline_live) return 130 + failure_at;
    }

    allocation_number = 0;
    fail_allocation_number = 0;
    dictionary_set_calls = 0;
    fail_dictionary_set_at = 1;
    result = cl_info_create_type111_candidate(&api, &factory_only, &profile,
                                               &candidate_raw);
    if (result != CL_INFO_AUGMENT_DICTIONARY_FAILED || candidate_raw ||
        factory_only.count != 1u || live_objects != baseline_live) return 9;
    dictionary_set_calls = 0;
    fail_dictionary_set_at = 2;
    result = cl_info_create_type111_candidate(&api, &factory_only, &profile,
                                               &candidate_raw);
    fail_dictionary_set_at = 0;
    if (result != CL_INFO_AUGMENT_DICTIONARY_FAILED || candidate_raw ||
        factory_only.count != 1u || live_objects != baseline_live) return 10;

    append_calls = 0;
    fail_append = 1;
    augmented_raw = 0;
    result = cl_info_create_augmented_displays(&api, &factory_only, &profile,
                                                &augmented_raw);
    fail_append = 0;
    if (result != CL_INFO_AUGMENT_APPEND_FAILED || augmented_raw ||
        factory_only.count != 1u || live_objects != baseline_live) return 24;

    append_calls = 0;
    fail_append_at = 2;
    augmented_raw = 0;
    result = cl_info_create_augmented_displays(&api, &factory_only, &profile,
                                                &augmented_raw);
    fail_append_at = 0;
    if (result != CL_INFO_AUGMENT_APPEND_FAILED || augmented_raw ||
        factory_only.count != 1u || live_objects != baseline_live) return 11;

    append_calls = 0;
    augmented_raw = 0;
    result = cl_info_create_augmented_displays(&api, &factory_only, &profile,
                                                &augmented_raw);
    augmented = (TestObject *)augmented_raw;
    if (result != CL_INFO_AUGMENT_OK || !augmented || augmented->count != 2u)
        return 12;
    release_object(augmented);
    augmented = 0;
    if (live_objects != baseline_live || factory_only.count != 1u) return 13;
    if (ownership_errors != 0) return 14;
    return 0;
}
