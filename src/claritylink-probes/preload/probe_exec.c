#include <unistd.h>

int main(void) {
  static const char marker[] = "CLARITYLINK_PROBE_MAIN_RAN\n";
  (void)write(STDOUT_FILENO, marker, sizeof(marker) - 1);
  return 42;
}
