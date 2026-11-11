#include <CoreFoundation/CoreFoundation.h>
#include <assert.h>
#include <stdio.h>
#include <limits.h>

#include "../../../src/claritylink-jmcs/native/info_augmentation.h"

static int fail_string_at;
static int string_calls;
static int fail_number_create;
static int fail_dictionary_create;
static int fail_dictionary_set_at;
static int dictionary_set_calls;
static int fail_array_create;
static int array_append_calls;
static int fail_array_append_at;
static int callbacks_retain = 1;
static int fail_negative_count;
static int api_created;
static int api_released;
static int insertion_retains_children = 1;
static int dictionary_retention_observed;
static int array_retention_observed;

static CLCFMutableDictionaryRef create_dictionary(
    CLCFIndex capacity, const void *key_callbacks,
    const void *value_callbacks) {
    CLCFMutableDictionaryRef result;
    if (fail_dictionary_create) return NULL;
    result = CFDictionaryCreateMutable(
        kCFAllocatorDefault, capacity,
        (const CFDictionaryKeyCallBacks *)key_callbacks,
        (const CFDictionaryValueCallBacks *)value_callbacks);
    if (result) ++api_created;
    return result;
}

static void set_value(CLCFMutableDictionaryRef dictionary,
                      CLCFTypeRef key, CLCFTypeRef value) {
    ++dictionary_set_calls;
    if (dictionary_set_calls == fail_dictionary_set_at) return;
    {
        CFIndex before = CFGetRetainCount(value);
        CFDictionarySetValue((CFMutableDictionaryRef)dictionary, key, value);
        if (before != LONG_MAX) {
            if (CFGetRetainCount(value) <= before) insertion_retains_children = 0;
            else dictionary_retention_observed = 1;
        }
    }
}

static CLCFTypeRef get_value(CLCFTypeRef dictionary, CLCFTypeRef key) {
    return CFDictionaryGetValue((CFDictionaryRef)dictionary, key);
}

static int is_array(CLCFTypeRef value) {
    return CFGetTypeID(value) == CFArrayGetTypeID();
}

static int is_dictionary(CLCFTypeRef value) {
    return CFGetTypeID(value) == CFDictionaryGetTypeID();
}

static int uuid_equal(CLCFTypeRef value, const char *canonical_uuid) {
    char existing[37];
    size_t i;
    if (CFGetTypeID(value) != CFStringGetTypeID() ||
        !CFStringGetCString((CFStringRef)value, existing, sizeof(existing),
                            kCFStringEncodingUTF8))
        return 0;
    for (i = 0; i < sizeof(existing); ++i) {
        char a = existing[i], b = canonical_uuid[i];
        if (a >= 'A' && a <= 'F') a = (char)(a - 'A' + 'a');
        if (b >= 'A' && b <= 'F') b = (char)(b - 'A' + 'a');
        if (a != b) return 0;
        if (!a) return 1;
    }
    return 0;
}

static CLCFIndex array_count(CLCFTypeRef array) {
    if (fail_negative_count) return -1;
    return (CLCFIndex)CFArrayGetCount((CFArrayRef)array);
}

static CLCFTypeRef array_value(CLCFTypeRef array, CLCFIndex index) {
    return CFArrayGetValueAtIndex((CFArrayRef)array, (CFIndex)index);
}

static void *create_array(CLCFIndex capacity, const void *callbacks) {
    CFMutableArrayRef result;
    if (fail_array_create) return NULL;
    result = CFArrayCreateMutable(kCFAllocatorDefault, capacity,
                                  (const CFArrayCallBacks *)callbacks);
    if (result) ++api_created;
    return result;
}

static int append_value(void *array, CLCFTypeRef value) {
    ++array_append_calls;
    if (array_append_calls == fail_array_append_at) return 0;
    {
        CFIndex before = CFGetRetainCount(value);
        CFArrayAppendValue((CFMutableArrayRef)array, value);
        if (before != LONG_MAX) {
            if (CFGetRetainCount(value) <= before) insertion_retains_children = 0;
            else array_retention_observed = 1;
        }
    }
    return 1;
}

static CLCFTypeRef create_string(const char *value) {
    CLCFTypeRef result;
    ++string_calls;
    if (fail_string_at == string_calls) return NULL;
    result = CFStringCreateWithCString(kCFAllocatorDefault, value,
                                       kCFStringEncodingUTF8);
    if (result) ++api_created;
    return result;
}

static CLCFTypeRef create_number(int64_t value) {
    CLCFTypeRef result;
    if (fail_number_create) return NULL;
    result = CFNumberCreate(kCFAllocatorDefault, kCFNumberSInt64Type, &value);
    if (result) ++api_created;
    return result;
}

static int is_type111(CLCFTypeRef value) {
    if (CFGetTypeID(value) == CFNumberGetTypeID()) {
        int64_t number = 0;
        return CFNumberGetValue((CFNumberRef)value, kCFNumberSInt64Type,
                                &number) && number == 111;
    }
    return CFGetTypeID(value) == CFStringGetTypeID() &&
           CFStringCompare((CFStringRef)value, CFSTR("111"), 0) == kCFCompareEqualTo;
}

static int values_equal(CLCFTypeRef left, CLCFTypeRef right) {
    return CFEqual(left, right) ? 1 : 0;
}

static int dictionary_callbacks_retain(const void *keys, const void *values) {
    return callbacks_retain && keys == &kCFTypeDictionaryKeyCallBacks &&
           values == &kCFTypeDictionaryValueCallBacks;
}

static int array_callbacks_retain(const void *callbacks) {
    return callbacks_retain && callbacks == &kCFTypeArrayCallBacks;
}

static void release_value(CLCFTypeRef value) {
    ++api_released;
    CFRelease(value);
}

static const CLCFAPI api = {
    create_dictionary, set_value, get_value, is_array, is_dictionary, uuid_equal,
    array_count, array_value, create_array, append_value,
    create_string, create_number, values_equal, is_type111,
    dictionary_callbacks_retain,
    array_callbacks_retain, release_value
};

static CFDataRef serialize(CFTypeRef value) {
    CFErrorRef error = NULL;
    CFDataRef data = CFPropertyListCreateData(
        kCFAllocatorDefault, value, kCFPropertyListBinaryFormat_v1_0, 0, &error);
    if (error) CFRelease(error);
    return data;
}

static void assert_primary_unchanged(CFDictionaryRef primary,
                                     CFNumberRef expected_uuid) {
    CFStringRef uuid_key = CFSTR("uuid");
    const void *uuid = CFDictionaryGetValue(primary, uuid_key);
    int64_t number = 0;
    assert(uuid && CFGetTypeID(uuid) == CFNumberGetTypeID());
    assert(CFEqual(uuid, expected_uuid));
    assert(CFNumberGetValue((CFNumberRef)uuid, kCFNumberSInt64Type, &number));
    assert(number == 7331);
}

static void assert_api_balanced(int created_before, int released_before) {
    assert(api_created - created_before == api_released - released_before);
}

int main(void) {
    const char *candidate_uuid = "abcdefab-cdef-4abc-8def-abcdefabcdef";
    CFMutableDictionaryRef primary = CFDictionaryCreateMutable(
        kCFAllocatorDefault, 0, &kCFTypeDictionaryKeyCallBacks,
        &kCFTypeDictionaryValueCallBacks);
    CFMutableArrayRef displays = CFArrayCreateMutable(
        kCFAllocatorDefault, 0, &kCFTypeArrayCallBacks);
    CFMutableArrayRef factory_only = CFArrayCreateMutable(
        kCFAllocatorDefault, 0, &kCFTypeArrayCallBacks);
    CFStringRef uuid_key = CFSTR("uuid");
    CFStringRef pixels_key = CFSTR("widthPixels");
    CFNumberRef primary_uuid = CFNumberCreate(
        kCFAllocatorDefault, kCFNumberSInt64Type, &(int64_t){7331});
    CFNumberRef width = CFNumberCreate(
        kCFAllocatorDefault, kCFNumberSInt64Type, &(int64_t){1280});
    CFDataRef factory_before, augmented_data, factory_after;
    CFErrorRef error = NULL;
    CFPropertyListRef roundtrip;
    CLDisplayProfile profile = {
        candidate_uuid, &kCFTypeDictionaryKeyCallBacks,
        &kCFTypeDictionaryValueCallBacks, &kCFTypeArrayCallBacks
    };
    void *augmented = NULL, *failed_augmented = NULL;
    CLCFMutableDictionaryRef candidate = NULL;
    CFStringRef type_key = CFSTR("type");
    CFStringRef candidate_uuid_value;
    CFNumberRef type_value;
    int64_t type_number = 0;
    int status, i, created_before, released_before;
    int api_start_created, api_start_released;

    assert(primary && displays && factory_only && primary_uuid && width);
    CFDictionarySetValue(primary, uuid_key, primary_uuid);
    CFDictionarySetValue(primary, pixels_key, width);
    CFArrayAppendValue(displays, primary);
    CFArrayAppendValue(factory_only, primary);
    factory_before = serialize(displays);
    assert(factory_before);
    api_start_created = api_created; api_start_released = api_released;

    {
        int strings_before = string_calls;
        int sets_before = dictionary_set_calls;
        int appends_before = array_append_calls;
        int allocations_before = api_created;
        CFDataRef disabled_after;
        candidate = (CLCFMutableDictionaryRef)(uintptr_t)1;
        status = cl_info_create_type111_candidate(
            &api, displays, &profile, CL_INFO_AUGMENT_POLICY_DISABLED, &candidate);
        assert(status == CL_INFO_AUGMENT_DISABLED && !candidate);
        augmented = (void *)(uintptr_t)1;
        status = cl_info_create_augmented_displays(
            &api, displays, &profile, CL_INFO_AUGMENT_POLICY_DISABLED, &augmented);
        assert(status == CL_INFO_AUGMENT_DISABLED && !augmented);
        candidate = (CLCFMutableDictionaryRef)(uintptr_t)1;
        status = cl_info_create_type111_candidate(
            &api, displays, &profile, (CLInfoAugmentPolicy)99, &candidate);
        assert(status == CL_INFO_AUGMENT_INVALID_ARGUMENT && !candidate);
        augmented = (void *)(uintptr_t)1;
        status = cl_info_create_augmented_displays(
            &api, displays, &profile, (CLInfoAugmentPolicy)99, &augmented);
        assert(status == CL_INFO_AUGMENT_INVALID_ARGUMENT && !augmented);
        assert(string_calls == strings_before &&
               dictionary_set_calls == sets_before &&
               array_append_calls == appends_before &&
               api_created == allocations_before);
        disabled_after = serialize(displays);
        assert(disabled_after && CFArrayGetCount(displays) == 1 &&
               CFEqual(factory_before, disabled_after));
        CFRelease(disabled_after);
    }

    created_before = api_created; released_before = api_released;
    status = cl_info_create_augmented_displays(&api, displays, &profile, CL_INFO_AUGMENT_POLICY_TYPE111,
                                                &augmented);
    assert(status == CL_INFO_AUGMENT_OK && augmented);
    assert(api_created - created_before == api_released - released_before + 1);
    assert(CFArrayGetCount(displays) == 1);
    assert(CFArrayGetCount((CFArrayRef)augmented) == 2);
    assert_primary_unchanged(primary, primary_uuid);

    candidate = (CLCFMutableDictionaryRef)CFArrayGetValueAtIndex(
        (CFArrayRef)augmented, 1);
    type_value = CFDictionaryGetValue(candidate, type_key);
    assert(type_value && CFNumberGetValue(type_value, kCFNumberSInt64Type,
                                           &type_number));
    assert(type_number == 111);
    candidate_uuid_value = CFStringCreateWithCString(
        kCFAllocatorDefault, candidate_uuid, kCFStringEncodingUTF8);
    assert(candidate_uuid_value);
    assert(CFEqual(CFDictionaryGetValue(candidate, uuid_key),
                   candidate_uuid_value));
    CFRelease(candidate_uuid_value);

    augmented_data = serialize((CFTypeRef)augmented);
    assert(augmented_data);
    roundtrip = CFPropertyListCreateWithData(
        kCFAllocatorDefault, augmented_data, kCFPropertyListImmutable, NULL, &error);
    assert(roundtrip && !error);
    assert(CFGetTypeID(roundtrip) == CFArrayGetTypeID());
    assert(CFArrayGetCount((CFArrayRef)roundtrip) == 2);
    assert_primary_unchanged(CFArrayGetValueAtIndex((CFArrayRef)roundtrip, 0),
                             primary_uuid);
    assert(CFEqual(CFArrayGetValueAtIndex((CFArrayRef)roundtrip, 0), primary));

    created_before = api_created; released_before = api_released;
    status = cl_info_create_type111_candidate(
        &api, augmented, &profile, CL_INFO_AUGMENT_POLICY_TYPE111, &candidate);
    assert(status == CL_INFO_AUGMENT_DUPLICATE_AUXILIARY && !candidate);
    assert_api_balanced(created_before, released_before);

    {
        CFMutableDictionaryRef uppercase_descriptor = CFDictionaryCreateMutable(
            kCFAllocatorDefault, 1, &kCFTypeDictionaryKeyCallBacks,
            &kCFTypeDictionaryValueCallBacks);
        CFMutableArrayRef uppercase_displays = CFArrayCreateMutable(
            kCFAllocatorDefault, 0, &kCFTypeArrayCallBacks);
        CFStringRef uppercase_uuid = CFSTR("ABCDEFAB-CDEF-4ABC-8DEF-ABCDEFABCDEF");
        assert(uppercase_descriptor && uppercase_displays);
        CFDictionarySetValue(uppercase_descriptor, uuid_key, uppercase_uuid);
        CFArrayAppendValue(uppercase_displays, uppercase_descriptor);
        status = cl_info_create_type111_candidate(
            &api, uppercase_displays, &profile, CL_INFO_AUGMENT_POLICY_TYPE111, &candidate);
        assert(status == CL_INFO_AUGMENT_DUPLICATE_AUXILIARY && !candidate);
        CFRelease(uppercase_displays);
        CFRelease(uppercase_descriptor);
    }

    callbacks_retain = 0;
    status = cl_info_create_type111_candidate(&api, displays, &profile, CL_INFO_AUGMENT_POLICY_TYPE111,
                                               &candidate);
    assert(status == CL_INFO_AUGMENT_INVALID_ARGUMENT && !candidate);
    status = cl_info_create_augmented_displays(&api, displays, &profile, CL_INFO_AUGMENT_POLICY_TYPE111,
                                                &failed_augmented);
    assert(status == CL_INFO_AUGMENT_INVALID_ARGUMENT && !failed_augmented);
    callbacks_retain = 1;

    profile.uuid = "invalid";
    created_before = api_created; released_before = api_released;
    status = cl_info_create_type111_candidate(&api, displays, &profile, CL_INFO_AUGMENT_POLICY_TYPE111,
                                               &candidate);
    assert(status == CL_INFO_AUGMENT_INVALID_UUID && !candidate);
    assert_api_balanced(created_before, released_before);
    profile.uuid = "00000000-0000-0000-0000-000000000000";
    status = cl_info_create_type111_candidate(&api, displays, &profile, CL_INFO_AUGMENT_POLICY_TYPE111,
                                               &candidate);
    assert(status == CL_INFO_AUGMENT_INVALID_UUID && !candidate);
    profile.uuid = "abcdefab-cdef-0abc-8def-abcdefabcdef";
    status = cl_info_create_type111_candidate(&api, displays, &profile, CL_INFO_AUGMENT_POLICY_TYPE111,
                                               &candidate);
    assert(status == CL_INFO_AUGMENT_INVALID_UUID && !candidate);
    profile.uuid = "abcdefab-cdef-4abc-7def-abcdefabcdef";
    status = cl_info_create_type111_candidate(&api, displays, &profile, CL_INFO_AUGMENT_POLICY_TYPE111,
                                               &candidate);
    assert(status == CL_INFO_AUGMENT_INVALID_UUID && !candidate);
    profile.uuid = "ABCDEFAB-CDEF-4ABC-8DEF-ABCDEFABCDEF";
    status = cl_info_create_type111_candidate(&api, displays, &profile, CL_INFO_AUGMENT_POLICY_TYPE111,
                                               &candidate);
    assert(status == CL_INFO_AUGMENT_INVALID_UUID && !candidate);
    profile.uuid = candidate_uuid;

    {
        CLCFAPI incomplete = api;
        incomplete.string_create_utf8 = NULL;
        status = cl_info_create_type111_candidate(&incomplete, displays,
                                                   &profile, CL_INFO_AUGMENT_POLICY_TYPE111, &candidate);
        assert(status == CL_INFO_AUGMENT_INVALID_ARGUMENT && !candidate);
    }
    status = cl_info_create_type111_candidate(&api, primary, &profile, CL_INFO_AUGMENT_POLICY_TYPE111,
                                               &candidate);
    assert(status == CL_INFO_AUGMENT_INVALID_ARGUMENT && !candidate);

    for (i = 1; i <= 3; ++i) {
        string_calls = 0;
        fail_string_at = i;
        candidate = NULL;
        created_before = api_created; released_before = api_released;
        status = cl_info_create_type111_candidate(&api, factory_only, &profile, CL_INFO_AUGMENT_POLICY_TYPE111,
                                                   &candidate);
        assert(status == CL_INFO_AUGMENT_ALLOCATION_FAILED && !candidate);
        assert_api_balanced(created_before, released_before);
        assert(CFArrayGetCount(factory_only) == 1);
    }
    fail_string_at = 0;
    string_calls = 0;
    fail_number_create = 1;
    created_before = api_created; released_before = api_released;
    status = cl_info_create_type111_candidate(&api, factory_only, &profile, CL_INFO_AUGMENT_POLICY_TYPE111,
                                               &candidate);
    assert(status == CL_INFO_AUGMENT_ALLOCATION_FAILED && !candidate);
    assert_api_balanced(created_before, released_before);
    fail_number_create = 0;

    fail_dictionary_create = 1;
    created_before = api_created; released_before = api_released;
    status = cl_info_create_type111_candidate(&api, factory_only, &profile, CL_INFO_AUGMENT_POLICY_TYPE111,
                                               &candidate);
    assert(status == CL_INFO_AUGMENT_ALLOCATION_FAILED && !candidate);
    assert_api_balanced(created_before, released_before);
    fail_dictionary_create = 0;

    for (i = 1; i <= 2; ++i) {
        dictionary_set_calls = 0;
        fail_dictionary_set_at = i;
        created_before = api_created; released_before = api_released;
        status = cl_info_create_type111_candidate(&api, factory_only, &profile, CL_INFO_AUGMENT_POLICY_TYPE111,
                                                   &candidate);
        assert(status == CL_INFO_AUGMENT_DICTIONARY_FAILED && !candidate);
        assert_api_balanced(created_before, released_before);
        fail_dictionary_set_at = 0;
    }

    fail_array_create = 1;
    created_before = api_created; released_before = api_released;
    status = cl_info_create_augmented_displays(&api, factory_only, &profile, CL_INFO_AUGMENT_POLICY_TYPE111,
                                                &failed_augmented);
    assert(status == CL_INFO_AUGMENT_ALLOCATION_FAILED && !failed_augmented);
    assert_api_balanced(created_before, released_before);
    fail_array_create = 0;

    array_append_calls = 0;
    fail_array_append_at = 1;
    created_before = api_created; released_before = api_released;
    status = cl_info_create_augmented_displays(&api, factory_only, &profile, CL_INFO_AUGMENT_POLICY_TYPE111,
                                                &failed_augmented);
    assert(status == CL_INFO_AUGMENT_APPEND_FAILED && !failed_augmented);
    assert_api_balanced(created_before, released_before);
    array_append_calls = 0;
    fail_array_append_at = 2;
    created_before = api_created; released_before = api_released;
    status = cl_info_create_augmented_displays(&api, factory_only, &profile, CL_INFO_AUGMENT_POLICY_TYPE111,
                                                &failed_augmented);
    assert(status == CL_INFO_AUGMENT_APPEND_FAILED && !failed_augmented);
    assert_api_balanced(created_before, released_before);
    assert(CFArrayGetCount(factory_only) == 1);
    fail_array_append_at = 0;

    fail_negative_count = 1;
    created_before = api_created; released_before = api_released;
    status = cl_info_create_augmented_displays(&api, factory_only, &profile, CL_INFO_AUGMENT_POLICY_TYPE111,
                                                &failed_augmented);
    assert(status == CL_INFO_AUGMENT_INVALID_ARGUMENT && !failed_augmented);
    assert_api_balanced(created_before, released_before);
    status = cl_info_create_type111_candidate(&api, factory_only, &profile, CL_INFO_AUGMENT_POLICY_TYPE111,
                                               &candidate);
    assert(status == CL_INFO_AUGMENT_INVALID_ARGUMENT && !candidate);
    fail_negative_count = 0;
    status = cl_info_create_type111_candidate(NULL, factory_only, &profile, CL_INFO_AUGMENT_POLICY_TYPE111,
                                               &candidate);
    assert(status == CL_INFO_AUGMENT_INVALID_ARGUMENT && !candidate);
    status = cl_info_create_type111_candidate(&api, NULL, &profile, CL_INFO_AUGMENT_POLICY_TYPE111, &candidate);
    assert(status == CL_INFO_AUGMENT_INVALID_ARGUMENT && !candidate);
    status = cl_info_create_type111_candidate(&api, factory_only, NULL, CL_INFO_AUGMENT_POLICY_TYPE111,
                                               &candidate);
    assert(status == CL_INFO_AUGMENT_INVALID_ARGUMENT && !candidate);
    status = cl_info_create_type111_candidate(&api, factory_only, &profile, CL_INFO_AUGMENT_POLICY_TYPE111, NULL);
    assert(status == CL_INFO_AUGMENT_INVALID_ARGUMENT);

    {
        CFMutableDictionaryRef existing_aux = CFDictionaryCreateMutable(
            kCFAllocatorDefault, 2, &kCFTypeDictionaryKeyCallBacks,
            &kCFTypeDictionaryValueCallBacks);
        CFMutableArrayRef existing_aux_array = CFArrayCreateMutable(
            kCFAllocatorDefault, 0, &kCFTypeArrayCallBacks);
        CFStringRef other_uuid = CFSTR("12345678-1234-4234-8234-123456789abc");
        CFNumberRef type111 = CFNumberCreate(
            kCFAllocatorDefault, kCFNumberSInt64Type, &(int64_t){111});
        assert(existing_aux && existing_aux_array && type111);
        CFDictionarySetValue(existing_aux, uuid_key, other_uuid);
        CFDictionarySetValue(existing_aux, type_key, type111);
        CFArrayAppendValue(existing_aux_array, existing_aux);
        status = cl_info_create_type111_candidate(
            &api, existing_aux_array, &profile, CL_INFO_AUGMENT_POLICY_TYPE111, &candidate);
        assert(status == CL_INFO_AUGMENT_DUPLICATE_AUXILIARY && !candidate);
        CFRelease(existing_aux_array);
        CFRelease(existing_aux);
        CFRelease(type111);
    }
    {
        CFMutableDictionaryRef string_type_aux = CFDictionaryCreateMutable(
            kCFAllocatorDefault, 2, &kCFTypeDictionaryKeyCallBacks,
            &kCFTypeDictionaryValueCallBacks);
        CFMutableArrayRef string_type_array = CFArrayCreateMutable(
            kCFAllocatorDefault, 0, &kCFTypeArrayCallBacks);
        CFStringRef other_uuid = CFSTR("12345678-1234-4234-8234-123456789abc");
        CFStringRef string_type = CFSTR("111");
        assert(string_type_aux && string_type_array);
        CFDictionarySetValue(string_type_aux, uuid_key, other_uuid);
        CFDictionarySetValue(string_type_aux, type_key, string_type);
        CFArrayAppendValue(string_type_array, string_type_aux);
        status = cl_info_create_type111_candidate(
            &api, string_type_array, &profile, CL_INFO_AUGMENT_POLICY_TYPE111, &candidate);
        assert(status == CL_INFO_AUGMENT_DUPLICATE_AUXILIARY && !candidate);
        CFRelease(string_type_array);
        CFRelease(string_type_aux);
    }

    {
        /* Mutable CFData has a measurable retain count on this host. */
        CFMutableDictionaryRef probe = CFDictionaryCreateMutable(
            kCFAllocatorDefault, 1, &kCFTypeDictionaryKeyCallBacks,
            &kCFTypeDictionaryValueCallBacks);
        UInt8 byte = 0x5a;
        CFMutableDataRef child = CFDataCreateMutable(kCFAllocatorDefault, 1);
        CFIndex before;
        assert(probe && child);
        CFDataAppendBytes(child, &byte, 1);
        before = CFGetRetainCount(child);
        api.dictionary_set_value(probe, type_key, child);
        assert(CFGetRetainCount(child) > before);
        assert(dictionary_retention_observed);
        CFRelease(child);
        CFRelease(probe);
    }

    {
        CFNumberRef malformed = CFNumberCreate(
            kCFAllocatorDefault, kCFNumberSInt64Type, &(int64_t){7});
        CFMutableArrayRef malformed_displays = CFArrayCreateMutable(
            kCFAllocatorDefault, 0, &kCFTypeArrayCallBacks);
        assert(malformed && malformed_displays);
        CFArrayAppendValue(malformed_displays, malformed);
        status = cl_info_create_type111_candidate(
            &api, malformed_displays, &profile, CL_INFO_AUGMENT_POLICY_TYPE111, &candidate);
        assert(status == CL_INFO_AUGMENT_INVALID_ARGUMENT && !candidate);
        CFRelease(malformed_displays);
        CFRelease(malformed);
    }

    {
        CFMutableArrayRef too_many = CFArrayCreateMutable(
            kCFAllocatorDefault, 0, &kCFTypeArrayCallBacks);
        int i;
        assert(too_many);
        for (i = 0; i < 9; ++i) CFArrayAppendValue(too_many, primary);
        created_before = api_created; released_before = api_released;
        status = cl_info_create_type111_candidate(&api, too_many, &profile, CL_INFO_AUGMENT_POLICY_TYPE111,
                                                   &candidate);
        assert(status == CL_INFO_AUGMENT_INVALID_ARGUMENT && !candidate);
        assert_api_balanced(created_before, released_before);
        CFRelease(too_many);
    }

    factory_after = serialize(displays);
    assert(factory_after && CFEqual(factory_before, factory_after));
    assert_primary_unchanged(primary, primary_uuid);
    CFRelease(roundtrip);
    CFRelease(factory_after);
    CFRelease(augmented_data);
    CFRelease(factory_before);
    api.release(augmented);
    assert_api_balanced(api_start_created, api_start_released);
    assert(insertion_retains_children && dictionary_retention_observed &&
           array_retention_observed);
    printf("NATIVE_INFO_AUGMENT_HOST_CF_PASS primary_preserved=PASS binary_plist=PASS duplicate_casefold=PASS ownership_ledger=PASS failure_rollback=PASS target_runtime=NOT_RUN\n");
    CFRelease(width);
    CFRelease(primary_uuid);
    CFRelease(factory_only);
    CFRelease(displays);
    CFRelease(primary);
    return 0;
}
