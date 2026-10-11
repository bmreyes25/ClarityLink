#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#ifndef CLARITYLINK_BUILD_SHA
#define CLARITYLINK_BUILD_SHA "UNRECORDED"
#endif

#ifndef CLARITYLINK_DIAG_ABI
#define CLARITYLINK_DIAG_ABI "armeabi-v7a"
#endif

#define DIAG_VERSION "1.0.0"
#define SELF_TEST_ALLOCATION_SIZE 64U
#define CHILD_WATCHDOG_EXIT_CODE 124
#define PARENT_WATCHDOG_EXIT_CODE 125
#define CHILD_CRASH_EXIT_CODE 126
#define SUPERVISOR_ERROR_EXIT_CODE 127
#define PARENT_POLL_NANOSECONDS 10000000L

#ifdef CLARITYLINK_TEST_FAULTS
#define CHILD_DEADLINE_SECONDS 1U
#define PARENT_DEADLINE_SECONDS 3U
#define TEST_PARENT_DEADLINE_SECONDS 1U
#else
#define CHILD_DEADLINE_SECONDS 2U
#define PARENT_DEADLINE_SECONDS 4U
#endif

static volatile sig_atomic_t supervised_child_pid = -1;

enum diagnostic_mode {
    MODE_INVALID = 0,
    MODE_VERSION,
    MODE_SELF_TEST,
#ifdef CLARITYLINK_TEST_FAULTS
    MODE_TEST_CHILD_LOOP,
    MODE_TEST_CHILD_SLEEP,
    MODE_TEST_CHILD_CRASH,
    MODE_TEST_PARENT_TIMEOUT,
    MODE_TEST_SIGCHLD_IGNORED,
    MODE_TEST_FORK_FAILURE,
    MODE_TEST_WAITPID_ERROR,
#endif
};

_Static_assert(sizeof(pid_t) <= sizeof(sig_atomic_t),
               "sig_atomic_t must be able to hold an exact child PID");

#ifdef CLARITYLINK_TEST_FAULTS
static int inject_fork_failure = 0;
static int inject_waitpid_error = 0;
#endif

static void print_identity(void) {
    (void)printf("CLARITYLINK_DIAG_VERSION=%s\n", DIAG_VERSION);
    (void)printf("BUILD_SHA=%s\n", CLARITYLINK_BUILD_SHA);
    (void)printf("API_TARGET=17\nABI=%s\n", CLARITYLINK_DIAG_ABI);
}

static void print_usage(void) {
    (void)puts("ClarityLink target diagnostic (offline-built; no persistent actions)");
    (void)puts("Usage: claritylink-target-diag [--help|--version|--status|--self-test]");
}

static void child_watchdog_handler(int signal_number) {
    (void)signal_number;
    _exit(CHILD_WATCHDOG_EXIT_CODE);
}

static void parent_watchdog_handler(int signal_number) {
    const pid_t child_pid = (pid_t)supervised_child_pid;
    (void)signal_number;

    if (child_pid > 0) {
        int status = 0;
        pid_t waited;
        if (kill(child_pid, SIGKILL) < 0 && errno != ESRCH) {
            _exit(SUPERVISOR_ERROR_EXIT_CODE);
        }
        do {
            waited = waitpid(child_pid, &status, 0);
        } while (waited < 0 && errno == EINTR);
        if (waited != child_pid) {
            _exit(SUPERVISOR_ERROR_EXIT_CODE);
        }
    }
    _exit(PARENT_WATCHDOG_EXIT_CODE);
}

static int run_self_test(void) {
    struct timespec before;
    struct timespec after;
    unsigned char* const scratch = (unsigned char*)malloc(SELF_TEST_ALLOCATION_SIZE);
    size_t index;
    unsigned int checksum = 0U;
    int result = 1;
    unsigned int resources = 0U;

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

static int run_requested_operation(enum diagnostic_mode mode) {
    print_identity();
    if (mode == MODE_VERSION) {
        return 0;
    }
    if (mode == MODE_SELF_TEST) {
        return run_self_test();
    }
#ifdef CLARITYLINK_TEST_FAULTS
    if (mode == MODE_TEST_CHILD_LOOP || mode == MODE_TEST_PARENT_TIMEOUT) {
        if (mode == MODE_TEST_PARENT_TIMEOUT) {
            struct sigaction ignore_alarm;
            (void)memset(&ignore_alarm, 0, sizeof(ignore_alarm));
            ignore_alarm.sa_handler = SIG_IGN;
            (void)sigemptyset(&ignore_alarm.sa_mask);
            if (sigaction(SIGALRM, &ignore_alarm, NULL) != 0) {
                return SUPERVISOR_ERROR_EXIT_CODE;
            }
        }
        for (;;) {
        }
    }
    if (mode == MODE_TEST_CHILD_SLEEP) {
        const struct timespec delay = {20, 0};
        (void)nanosleep(&delay, NULL);
        return 0;
    }
    if (mode == MODE_TEST_CHILD_CRASH) {
        (void)raise(SIGSEGV);
        return SUPERVISOR_ERROR_EXIT_CODE;
    }
    if (mode == MODE_TEST_WAITPID_ERROR) {
        for (;;) {
        }
    }
#endif
    return SUPERVISOR_ERROR_EXIT_CODE;
}

static int disarm_parent_watchdog_and_reap_pending(pid_t child_pid,
                                                    int* child_status,
                                                    int wait_error) {
    sigset_t alarm_set;
    sigset_t pending_set;
    sigset_t previous_mask;
    int pending_signal = 0;
    int mask_changed = 0;

    if (sigemptyset(&alarm_set) != 0 || sigaddset(&alarm_set, SIGALRM) != 0 ||
        sigprocmask(SIG_BLOCK, &alarm_set, &previous_mask) != 0) {
        return -1;
    }
    mask_changed = 1;

    if (wait_error != 0) {
        pid_t waited;
        if (kill(child_pid, SIGKILL) < 0 && errno != ESRCH) {
            (void)alarm(0U);
            supervised_child_pid = -1;
            (void)sigprocmask(SIG_SETMASK, &previous_mask, NULL);
            return -1;
        }
        do {
            waited = waitpid(child_pid, child_status, 0);
        } while (waited < 0 && errno == EINTR);
        if (waited != child_pid) {
            (void)alarm(0U);
            supervised_child_pid = -1;
            (void)sigprocmask(SIG_SETMASK, &previous_mask, NULL);
            return -1;
        }
    }

    (void)alarm(0U);
    if (sigpending(&pending_set) == 0 && sigismember(&pending_set, SIGALRM) == 1) {
        if (sigwait(&alarm_set, &pending_signal) != 0) {
            supervised_child_pid = -1;
            (void)sigprocmask(SIG_SETMASK, &previous_mask, NULL);
            return -1;
        }
    }
    supervised_child_pid = -1;
    if (mask_changed && sigprocmask(SIG_SETMASK, &previous_mask, NULL) != 0) {
        return -1;
    }
    return 0;
}

static int supervise(enum diagnostic_mode mode) {
    struct sigaction parent_action;
    struct sigaction child_status_action;
    sigset_t alarm_set;
    sigset_t original_mask;
    pid_t child_pid;
    int child_status = 0;
    int wait_error = 0;

    (void)memset(&parent_action, 0, sizeof(parent_action));
    parent_action.sa_handler = parent_watchdog_handler;
    if (sigemptyset(&parent_action.sa_mask) != 0 ||
        sigaction(SIGALRM, &parent_action, NULL) != 0) {
        return SUPERVISOR_ERROR_EXIT_CODE;
    }
    /* SIG_IGN survives exec and can auto-reap children; this supervisor
     * needs exclusive waitpid ownership of its direct child. */
    (void)memset(&child_status_action, 0, sizeof(child_status_action));
    child_status_action.sa_handler = SIG_DFL;
    if (sigemptyset(&child_status_action.sa_mask) != 0 ||
        sigaction(SIGCHLD, &child_status_action, NULL) != 0) {
        return SUPERVISOR_ERROR_EXIT_CODE;
    }
    if (sigemptyset(&alarm_set) != 0 || sigaddset(&alarm_set, SIGALRM) != 0 ||
        sigprocmask(SIG_BLOCK, &alarm_set, &original_mask) != 0) {
        return SUPERVISOR_ERROR_EXIT_CODE;
    }
    if (sigismember(&original_mask, SIGALRM) != 0) {
        (void)sigprocmask(SIG_SETMASK, &original_mask, NULL);
        return SUPERVISOR_ERROR_EXIT_CODE;
    }
#ifdef CLARITYLINK_TEST_FAULTS
    (void)alarm(mode == MODE_TEST_PARENT_TIMEOUT
                    ? TEST_PARENT_DEADLINE_SECONDS
                    : PARENT_DEADLINE_SECONDS);
#else
    (void)alarm(PARENT_DEADLINE_SECONDS);
#endif

#ifdef CLARITYLINK_TEST_FAULTS
    if (inject_fork_failure != 0) {
        child_pid = -1;
        errno = EAGAIN;
    } else
#endif
    {
        child_pid = fork();
    }
    if (child_pid < 0) {
        (void)alarm(0U);
        (void)sigprocmask(SIG_SETMASK, &original_mask, NULL);
        return SUPERVISOR_ERROR_EXIT_CODE;
    }
    if (child_pid == 0) {
        struct sigaction child_action;
        int operation_status;

        (void)alarm(0U);
        (void)memset(&child_action, 0, sizeof(child_action));
        child_action.sa_handler = child_watchdog_handler;
        if (sigemptyset(&child_action.sa_mask) != 0 ||
            sigaction(SIGALRM, &child_action, NULL) != 0) {
            _exit(SUPERVISOR_ERROR_EXIT_CODE);
        }
#ifdef CLARITYLINK_TEST_FAULTS
        if (mode == MODE_TEST_PARENT_TIMEOUT) {
            (void)alarm(PARENT_DEADLINE_SECONDS + 1U);
            if (sigprocmask(SIG_UNBLOCK, &alarm_set, NULL) != 0) {
                _exit(SUPERVISOR_ERROR_EXIT_CODE);
            }
            operation_status = run_requested_operation(mode);
            (void)fflush(NULL);
            _exit(operation_status);
        }
#endif
        (void)alarm(CHILD_DEADLINE_SECONDS);
        if (sigprocmask(SIG_UNBLOCK, &alarm_set, NULL) != 0) {
            _exit(SUPERVISOR_ERROR_EXIT_CODE);
        }
        operation_status = run_requested_operation(mode);
        if (fflush(NULL) != 0) {
            operation_status = SUPERVISOR_ERROR_EXIT_CODE;
        }
        (void)alarm(0U);
        _exit(operation_status);
    }

    supervised_child_pid = (sig_atomic_t)child_pid;
    if (sigprocmask(SIG_SETMASK, &original_mask, NULL) != 0) {
        (void)kill(child_pid, SIGKILL);
        while (waitpid(child_pid, &child_status, 0) < 0 && errno == EINTR) {
        }
        supervised_child_pid = -1;
        (void)alarm(0U);
        _exit(SUPERVISOR_ERROR_EXIT_CODE);
    }
    for (;;) {
        sigset_t previous_mask;
        pid_t waited;

        if (sigprocmask(SIG_BLOCK, &alarm_set, &previous_mask) != 0) {
            for (;;) {
                (void)pause();
            }
        }
#ifdef CLARITYLINK_TEST_FAULTS
        if (inject_waitpid_error != 0) {
            inject_waitpid_error = 0;
            waited = -1;
            errno = EIO;
        } else
#endif
        {
            waited = waitpid(child_pid, &child_status, WNOHANG);
        }
        if (waited == child_pid) {
            if (disarm_parent_watchdog_and_reap_pending(child_pid, &child_status, 0) != 0) {
                _exit(PARENT_WATCHDOG_EXIT_CODE);
            }
            break;
        }
        if (waited < 0 && errno != EINTR) {
            wait_error = errno;
            if (disarm_parent_watchdog_and_reap_pending(child_pid, &child_status,
                                                        wait_error) != 0) {
                _exit(PARENT_WATCHDOG_EXIT_CODE);
            }
            if (printf("SUPERVISOR_CHILD_REAPED pid=%ld recovery=kill_waitpid\n",
                       (long)child_pid) < 0 || fflush(stdout) != 0) {
                return SUPERVISOR_ERROR_EXIT_CODE;
            }
            return SUPERVISOR_ERROR_EXIT_CODE;
        }
        if (sigprocmask(SIG_SETMASK, &previous_mask, NULL) != 0) {
            (void)kill(child_pid, SIGKILL);
            while (waitpid(child_pid, &child_status, 0) < 0 && errno == EINTR) {
            }
            supervised_child_pid = -1;
            (void)alarm(0U);
            _exit(SUPERVISOR_ERROR_EXIT_CODE);
        }
        if (waited == 0) {
            const struct timespec pause_time = {0, PARENT_POLL_NANOSECONDS};
            (void)nanosleep(&pause_time, NULL);
        }
    }

    if (sigprocmask(SIG_SETMASK, &original_mask, NULL) != 0) {
        return SUPERVISOR_ERROR_EXIT_CODE;
    }

    if (printf("SUPERVISOR_CHILD_REAPED pid=%ld\n", (long)child_pid) < 0 ||
        fflush(stdout) != 0) {
        return SUPERVISOR_ERROR_EXIT_CODE;
    }

    if (WIFEXITED(child_status)) {
        return WEXITSTATUS(child_status);
    }
    if (WIFSIGNALED(child_status)) {
        return CHILD_CRASH_EXIT_CODE;
    }
    return SUPERVISOR_ERROR_EXIT_CODE;
}

static enum diagnostic_mode parse_mode(int argc, char** argv) {
    if (argc != 2 || argv == NULL || argv[1] == NULL) {
        return MODE_INVALID;
    }
    if (strcmp(argv[1], "--version") == 0) {
        return MODE_VERSION;
    }
    if (strcmp(argv[1], "--self-test") == 0) {
        return MODE_SELF_TEST;
    }
#ifdef CLARITYLINK_TEST_FAULTS
    if (strcmp(argv[1], "--test-child-loop") == 0) {
        return MODE_TEST_CHILD_LOOP;
    }
    if (strcmp(argv[1], "--test-child-sleep") == 0) {
        return MODE_TEST_CHILD_SLEEP;
    }
    if (strcmp(argv[1], "--test-child-crash") == 0) {
        return MODE_TEST_CHILD_CRASH;
    }
    if (strcmp(argv[1], "--test-parent-timeout") == 0) {
        return MODE_TEST_PARENT_TIMEOUT;
    }
    if (strcmp(argv[1], "--test-sigchld-ignored") == 0) {
        return MODE_TEST_SIGCHLD_IGNORED;
    }
    if (strcmp(argv[1], "--test-fork-failure") == 0) {
        return MODE_TEST_FORK_FAILURE;
    }
    if (strcmp(argv[1], "--test-waitpid-error") == 0) {
        return MODE_TEST_WAITPID_ERROR;
    }
#endif
    return MODE_INVALID;
}

int main(int argc, char** argv) {
    enum diagnostic_mode mode;
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
    if (strcmp(argv[1], "--status") == 0) {
        print_identity();
        (void)puts("MODE=STATUS PERSISTENCE=NONE LISTENERS=0 DISPLAY=NONE RECEIVER=NONE");
        return 0;
    }

    mode = parse_mode(argc, argv);
    if (mode == MODE_INVALID) {
        (void)fputs("UNSUPPORTED_MODE\n", stderr);
        return 2;
    }
#ifdef CLARITYLINK_TEST_FAULTS
    if (mode == MODE_TEST_SIGCHLD_IGNORED) {
        struct sigaction ignore_child;
        (void)memset(&ignore_child, 0, sizeof(ignore_child));
        ignore_child.sa_handler = SIG_IGN;
        if (sigemptyset(&ignore_child.sa_mask) != 0 ||
            sigaction(SIGCHLD, &ignore_child, NULL) != 0) {
            return SUPERVISOR_ERROR_EXIT_CODE;
        }
        return supervise(MODE_VERSION);
    }
    if (mode == MODE_TEST_FORK_FAILURE) {
        inject_fork_failure = 1;
        return supervise(MODE_VERSION);
    }
    if (mode == MODE_TEST_WAITPID_ERROR) {
        inject_waitpid_error = 1;
    }
#endif
    return supervise(mode);
}
