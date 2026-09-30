#include <unistd.h>

__attribute__((constructor)) static void claritylink_probe_constructor(void) {
  static const char marker[] = "CLARITYLINK_PROBE_CONSTRUCTOR_RAN\n";
  (void)write(STDERR_FILENO, marker, sizeof(marker) - 1);
}
