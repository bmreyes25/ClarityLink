CC ?= cc
CFLAGS ?= -O2 -Wall -Wextra -Werror -std=c11

.PHONY: all test armv7 clean safety
all: test-reader
jmcs-registry-reader: reader.c
	$(CC) $(CFLAGS) -o $@ $<
test: test-reader
	./test-reader
test-reader: test_reader.c reader.c
	$(CC) $(CFLAGS) -o $@ test_reader.c
armv7:
	@test -n "$(ARM_CC)" || { echo 'Set ARM_CC to a verified Android ARMv7 toolchain compiler'; exit 2; }
	$(ARM_CC) $(CFLAGS) -fPIE -pie -o jmcs-registry-reader-armv7 reader.c
safety: test-reader
	@if nm -u test-reader | grep -E 'process_vm_writev|ptrace|kill|tgkill|debuggerd|pwrite|writev'; then exit 1; else echo 'forbidden imports: none'; fi
clean:
	rm -f jmcs-registry-reader jmcs-registry-reader-armv7 test-reader
