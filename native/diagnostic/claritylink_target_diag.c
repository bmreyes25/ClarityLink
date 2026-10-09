#define _POSIX_C_SOURCE 200809L

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#ifndef CLARITYLINK_BUILD_SHA
#define CLARITYLINK_BUILD_SHA "UNRECORDED"
#endif

#define DIAG_VERSION "1.0.0"
#define SELF_TEST_ALLOCATION_SIZE 64U

static void print_identity(void) {
    (void)printf("CLARITYLINK_DIAG_VERSION=%s\n", DIAG_VERSION);
    (void)printf("BUILD_SHA=%s\n", CLARITYLINK_BUILD_SHA);
    (void)printf("API_TARGET=17\nABI=armeabi-v7a\n");
}

static void print_usage(void) {
    (void)puts("ClarityLink target diagnostic (offline-built; no persistent actions)");
    (void)puts("Usage: claritylink-target-diag [--help|--version|--status|--self-test]");
}

static int run_self_test(void) {
    struct timespec before;
    struct timespec after;
    unsigned char* const scratch = (unsigned char*)malloc(SELF_TEST_ALLOCATION_SIZE);
    unsigned int resources = 0U;
    size_t index;
    unsigned int checksum = 0U;
    int result = 1;

    (void)puts("SELF_TEST_BEGIN");
    (void)puts("RESOURCE_COUNTS allocated=0");
    if (scratch == NULL) {
        (void)puts("SELF_TEST_FAIL reason=bounded_allocation");
        goto cleanup;
    }
    resources = 1U;
    for (index = 0U; index < SELF_TEST_ALLOCATION_SIZE; ++index) {
        scratch[index] = (unsigned char)(index ^ 0x5aU);
        checksum += (unsigned int)scratch[index];
    }
    if (clock_gettime(CLOCK_MONOTONIC, &before) != 0 ||
        clock_gettime(CLOCK_MONOTONIC, &after) != 0 ||
        after.tv_sec < before.tv_sec ||
        (after.tv_sec == before.tv_sec && after.tv_nsec < before.tv_nsec)) {
        (void)puts("SELF_TEST_FAIL reason=monotonic_clock");
        goto cleanup;
    }
    if (checksum == 0U) {
        (void)puts("SELF_TEST_FAIL reason=local_memory_check");
        goto cleanup;
    }
    result = 0;

cleanup:
    if (scratch != NULL) {
        free(scratch);
        resources = 0U;
    }
    (void)printf("RESOURCE_COUNTS final=%u\n", resources);
    if (result == 0 && resources == 0U) {
        (void)puts("SELF_TEST_PASS");
        return 0;
    }
    (void)puts("SELF_TEST_FAIL reason=cleanup");
    return 1;
}

int main(int argc, char** argv) {
    if (argc == 1) {
        print_identity();
        print_usage();
        return 0;
    }
    if (argc != 2 || argv == NULL || argv[1] == NULL) {
        (void)fputs("UNSUPPORTED_ARGUMENTS\n", stderr);
        return 2;
    }
    if (strcmp(argv[1], "--help") == 0) {
        print_identity();
        print_usage();
        return 0;
    }
    if (strcmp(argv[1], "--version") == 0) {
        print_identity();
        return 0;
    }
    if (strcmp(argv[1], "--status") == 0) {
        print_identity();
        (void)puts("MODE=STATUS PERSISTENCE=NONE LISTENERS=0 DISPLAY=NONE RECEIVER=NONE");
        return 0;
    }
    if (strcmp(argv[1], "--self-test") == 0) {
        print_identity();
        return run_self_test();
    }
    (void)fputs("UNSUPPORTED_MODE\n", stderr);
    return 2;
}
