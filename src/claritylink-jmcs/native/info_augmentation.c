#include "info_augmentation.h"

static int has_uuid_shape(const char *value) {
    size_t i;
    if (!value) return 0;
    for (i = 0; i < 36; ++i) {
        const char c = value[i];
        if (i == 8 || i == 13 || i == 18 || i == 23) {
            if (c != '-') return 0;
        } else if (!((c >= '0' && c <= '9') ||
                     (c >= 'a' && c <= 'f'))) {
            return 0;
        }
    }
    /* A valid version nibble is already nonzero; nil UUIDs fail this check. */
    return value[36] == '\0' && value[14] >= '1' && value[14] <= '8' &&
           (value[19] == '8' || value[19] == '9' ||
            value[19] == 'a' || value[19] == 'b');
}

static int api_is_complete(const CLCFAPI *api) {
    return api && api->dictionary_create_mutable &&
           api->dictionary_set_value && api->dictionary_get_value &&
           api->is_array && api->is_dictionary && api->uuid_equal &&
           api->array_get_count && api->array_get_value_at_index &&
           api->array_create_mutable &&
           api->array_append_value &&
           api->string_create_utf8 && api->number_create_i64 && api->equal &&
           api->is_type111 &&
           api->dictionary_callbacks_are_verified_retaining &&
           api->array_callbacks_are_verified_retaining && api->release;
}

static void release_if(const CLCFAPI *api, CLCFTypeRef value) {
    if (value) api->release(value);
}

static CLInfoAugmentResult create_candidate(
    const CLCFAPI *api, CLCFTypeRef existing_displays,
    const CLDisplayProfile *profile, CLInfoAugmentPolicy policy,
    CLCFIndex *out_count,
    CLCFMutableDictionaryRef *out_descriptor) {
    static const char type_key_text[] = "type";
    static const char uuid_key_text[] = "uuid";
    CLCFTypeRef type_key = 0, uuid_key = 0, uuid_value = 0, type_value = 0;
    CLCFMutableDictionaryRef candidate = 0;
    CLCFTypeRef inserted_type, inserted_uuid;
    CLCFIndex i, count;

    if (!out_descriptor) return CL_INFO_AUGMENT_INVALID_ARGUMENT;
    *out_descriptor = 0;
    if (!profile) return CL_INFO_AUGMENT_INVALID_ARGUMENT;
    if (policy == CL_INFO_AUGMENT_POLICY_DISABLED)
        return CL_INFO_AUGMENT_DISABLED;
    if (policy != CL_INFO_AUGMENT_POLICY_TYPE111)
        return CL_INFO_AUGMENT_INVALID_ARGUMENT;
    if (!api_is_complete(api) || !existing_displays ||
        !profile->dictionary_key_callbacks ||
        !profile->dictionary_value_callbacks ||
        !api->dictionary_callbacks_are_verified_retaining(
            profile->dictionary_key_callbacks, profile->dictionary_value_callbacks))
        return CL_INFO_AUGMENT_INVALID_ARGUMENT;
    if (!api->is_array(existing_displays))
        return CL_INFO_AUGMENT_INVALID_ARGUMENT;
    count = api->array_get_count(existing_displays);
    if (count < 0 || count > CL_INFO_MAX_EXISTING_DISPLAYS)
        return CL_INFO_AUGMENT_INVALID_ARGUMENT;
    if (!has_uuid_shape(profile->uuid)) return CL_INFO_AUGMENT_INVALID_UUID;

    type_key = api->string_create_utf8(type_key_text);
    uuid_key = api->string_create_utf8(uuid_key_text);
    uuid_value = api->string_create_utf8(profile->uuid);
    type_value = api->number_create_i64(111);
    if (!type_key || !uuid_key || !uuid_value || !type_value) {
        release_if(api, type_key);
        release_if(api, uuid_key);
        release_if(api, uuid_value);
        release_if(api, type_value);
        return CL_INFO_AUGMENT_ALLOCATION_FAILED;
    }

    for (i = 0; i < count; ++i) {
        CLCFTypeRef descriptor = api->array_get_value_at_index(existing_displays, i);
        CLCFTypeRef existing_uuid;
        CLCFTypeRef existing_type;
        if (!descriptor || !api->is_dictionary(descriptor)) {
            release_if(api, type_key);
            release_if(api, uuid_key);
            release_if(api, uuid_value);
            release_if(api, type_value);
            return CL_INFO_AUGMENT_INVALID_ARGUMENT;
        }
        existing_uuid = api->dictionary_get_value(descriptor, uuid_key);
        existing_type = api->dictionary_get_value(descriptor, type_key);
        if ((existing_uuid && api->uuid_equal(existing_uuid, profile->uuid)) ||
            (existing_type && api->is_type111(existing_type))) {
            release_if(api, type_key);
            release_if(api, uuid_key);
            release_if(api, uuid_value);
            release_if(api, type_value);
            return CL_INFO_AUGMENT_DUPLICATE_AUXILIARY;
        }
    }

    candidate = api->dictionary_create_mutable(
        2, profile->dictionary_key_callbacks,
        profile->dictionary_value_callbacks);
    if (!candidate) {
        release_if(api, type_key);
        release_if(api, uuid_key);
        release_if(api, uuid_value);
        release_if(api, type_value);
        return CL_INFO_AUGMENT_ALLOCATION_FAILED;
    }

    api->dictionary_set_value(candidate, type_key, type_value);
    api->dictionary_set_value(candidate, uuid_key, uuid_value);
    inserted_type = api->dictionary_get_value(candidate, type_key);
    inserted_uuid = api->dictionary_get_value(candidate, uuid_key);
    if (!inserted_type || !inserted_uuid ||
        !api->equal(inserted_type, type_value) ||
        !api->equal(inserted_uuid, uuid_value)) {
        api->release(candidate);
        release_if(api, type_key);
        release_if(api, uuid_key);
        release_if(api, uuid_value);
        release_if(api, type_value);
        return CL_INFO_AUGMENT_DICTIONARY_FAILED;
    }
    release_if(api, type_key);
    release_if(api, uuid_key);
    release_if(api, uuid_value);
    release_if(api, type_value);
    *out_descriptor = candidate;
    if (out_count) *out_count = count;
    return CL_INFO_AUGMENT_OK;
}

CLInfoAugmentResult cl_info_create_type111_candidate(
    const CLCFAPI *api, CLCFTypeRef existing_displays,
    const CLDisplayProfile *profile, CLInfoAugmentPolicy policy,
    CLCFMutableDictionaryRef *out_descriptor) {
    return create_candidate(api, existing_displays, profile, policy, 0,
                            out_descriptor);
}

CLInfoAugmentResult cl_info_create_augmented_displays(
    const CLCFAPI *api, CLCFTypeRef factory_displays,
    const CLDisplayProfile *profile, CLInfoAugmentPolicy policy,
    void **out_augmented_displays) {
    CLCFMutableDictionaryRef candidate = 0;
    void *augmented = 0;
    CLInfoAugmentResult result;
    CLCFIndex i, count;
    if (!out_augmented_displays) return CL_INFO_AUGMENT_INVALID_ARGUMENT;
    *out_augmented_displays = 0;
    if (!profile) return CL_INFO_AUGMENT_INVALID_ARGUMENT;
    if (policy == CL_INFO_AUGMENT_POLICY_DISABLED)
        return CL_INFO_AUGMENT_DISABLED;
    if (policy != CL_INFO_AUGMENT_POLICY_TYPE111)
        return CL_INFO_AUGMENT_INVALID_ARGUMENT;
    if (!api || !factory_displays || !profile->array_callbacks ||
        !api->array_callbacks_are_verified_retaining ||
        !api->array_callbacks_are_verified_retaining(profile->array_callbacks))
        return CL_INFO_AUGMENT_INVALID_ARGUMENT;
    result = create_candidate(api, factory_displays, profile, policy, &count,
                              &candidate);
    if (result != CL_INFO_AUGMENT_OK) return result;
    augmented = api->array_create_mutable(count + 1,
                                          profile->array_callbacks);
    if (!augmented) {
        api->release(candidate);
        return CL_INFO_AUGMENT_ALLOCATION_FAILED;
    }
    for (i = 0; i < count; ++i) {
        CLCFTypeRef descriptor = api->array_get_value_at_index(factory_displays, i);
        if (!api->array_append_value(augmented, descriptor)) {
            api->release(augmented);
            api->release(candidate);
            return CL_INFO_AUGMENT_APPEND_FAILED;
        }
    }
    if (!api->array_append_value(augmented, candidate)) {
        api->release(augmented);
        api->release(candidate);
        return CL_INFO_AUGMENT_APPEND_FAILED;
    }
    api->release(candidate);
    *out_augmented_displays = augmented;
    return CL_INFO_AUGMENT_OK;
}
