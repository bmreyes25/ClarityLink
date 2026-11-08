#ifndef CLARITYLINK_JMCS_INFO_AUGMENTATION_H
#define CLARITYLINK_JMCS_INFO_AUGMENTATION_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Opaque CoreFoundation/CFLite objects. These are project shim callbacks, not
 * direct function-pointer casts to Honda's wrappers. The eventual in-ELF
 * adapter must bind exact receiver signatures. Its verified-retaining probes
 * must accept only callback-table identities proven to retain children; a
 * generic boolean or non-null check is insufficient. This component does not
 * discover or hook jmcs. */
typedef const void *CLCFTypeRef;
typedef void *CLCFMutableDictionaryRef;
typedef long CLCFIndex;

typedef struct CLCFAPI {
    CLCFMutableDictionaryRef (*dictionary_create_mutable)(
        CLCFIndex capacity, const void *key_callbacks,
        const void *value_callbacks);
    void (*dictionary_set_value)(CLCFMutableDictionaryRef dictionary,
                                 CLCFTypeRef key, CLCFTypeRef value);
    CLCFTypeRef (*dictionary_get_value)(CLCFTypeRef dictionary,
                                        CLCFTypeRef key);
    int (*is_array)(CLCFTypeRef value);
    int (*is_dictionary)(CLCFTypeRef value);
    /* True only for a string UUID equal to canonical_uuid, ASCII case-folded;
     * non-string identifiers such as Honda's numeric primary UUID are false. */
    int (*uuid_equal)(CLCFTypeRef value, const char *canonical_uuid);
    CLCFIndex (*array_get_count)(CLCFTypeRef array);
    CLCFTypeRef (*array_get_value_at_index)(CLCFTypeRef array,
                                            CLCFIndex index);
    void *(*array_create_mutable)(CLCFIndex capacity,
                                  const void *array_callbacks);
    /* Returns nonzero on success. Failure must leave the array unchanged. */
    int (*array_append_value)(void *array, CLCFTypeRef value);
    CLCFTypeRef (*string_create_utf8)(const char *value);
    CLCFTypeRef (*number_create_i64)(int64_t value);
    int (*equal)(CLCFTypeRef left, CLCFTypeRef right);
    /* Recognizes canonical numeric 111 and the experimental string form "111". */
    int (*is_type111)(CLCFTypeRef value);
    int (*dictionary_callbacks_are_verified_retaining)(
        const void *key_callbacks, const void *value_callbacks);
    int (*array_callbacks_are_verified_retaining)(const void *array_callbacks);
    void (*release)(CLCFTypeRef value);
} CLCFAPI;

typedef struct CLDisplayProfile {
    const char *uuid;
    const void *dictionary_key_callbacks;
    const void *dictionary_value_callbacks;
    const void *array_callbacks;
} CLDisplayProfile;

#define CL_INFO_MAX_EXISTING_DISPLAYS 8L

typedef enum CLInfoAugmentResult {
    CL_INFO_AUGMENT_OK = 0,
    CL_INFO_AUGMENT_INVALID_ARGUMENT = 1,
    CL_INFO_AUGMENT_INVALID_UUID = 2,
    CL_INFO_AUGMENT_DUPLICATE_AUXILIARY = 3,
    CL_INFO_AUGMENT_ALLOCATION_FAILED = 4,
    CL_INFO_AUGMENT_APPEND_FAILED = 5,
    CL_INFO_AUGMENT_DICTIONARY_FAILED = 6
} CLInfoAugmentResult;

/* Creates an independent, caller-owned Type111 candidate dictionary.
 * The only wire fields are type=111 and a caller-provided canonical lowercase
 * UUID string. This external-prior-art profile remains unverified for Honda.
 * The caller must append only after all other prerequisites have succeeded,
 * and only into a container whose exact retaining callback table was verified.
 * The input array must remain immutable for the duration of this call. Counts
 * above CL_INFO_MAX_EXISTING_DISPLAYS (8) return INVALID_ARGUMENT. On failure,
 * *out_descriptor is NULL and no input object is modified. */
CLInfoAugmentResult cl_info_create_type111_candidate(
    const CLCFAPI *api, CLCFTypeRef existing_displays,
    const CLDisplayProfile *profile, CLCFMutableDictionaryRef *out_descriptor);

/* Creates a separate array that retains each original descriptor plus the
 * candidate. The factory array and descriptors remain untouched and available
 * for serialization fallback. The caller owns the returned array. Production
 * CFArrayAppendValue has no status return; its adapter reports success after
 * the call and cannot recover from process-level OOM. The input must remain
 * immutable throughout this call. */
CLInfoAugmentResult cl_info_create_augmented_displays(
    const CLCFAPI *api, CLCFTypeRef factory_displays,
    const CLDisplayProfile *profile, void **out_augmented_displays);

#ifdef __cplusplus
}
#endif

#endif
