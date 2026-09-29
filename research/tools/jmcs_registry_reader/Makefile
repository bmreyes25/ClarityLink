CC ?= cc
CFLAGS ?= -O2 -Wall -Wextra -Werror -std=c11
NDK_ROOT ?=
ANDROID_TRIPLE ?= armv7a-linux-androideabi17
ANDROID_SYSROOT ?= $(NDK_ROOT)/toolchains/llvm/prebuilt/darwin-x86_64/sysroot
ANDROID_CLANG ?= $(NDK_ROOT)/toolchains/llvm/prebuilt/darwin-x86_64/bin/clang

.PHONY: all test armv7 clean safety
all: test-reader
jmcs-registry-reader: reader.c
	$(CC) $(CFLAGS) -o $@ $<
test: test-reader
	./test-reader
test-reader: test_reader.c reader.c
	$(CC) $(CFLAGS) -o $@ test_reader.c
armv7:
	@test -x "$(ANDROID_CLANG)" || { echo 'Set NDK_ROOT to Android NDK r23c'; exit 2; }
	"$(ANDROID_CLANG)" --target=$(ANDROID_TRIPLE) --sysroot="$(ANDROID_SYSROOT)" $(CFLAGS) -march=armv7-a -mfloat-abi=softfp -fPIE -pie -Wl,-z,relro,-z,now -o jmcs_registry_reader reader.c
safety: test-reader
	@if nm -u test-reader | grep -E 'process_vm_writev|ptrace|kill|tgkill|debuggerd|pwrite|writev'; then exit 1; else echo 'forbidden imports: none'; fi
clean:
	rm -f jmcs-registry-reader jmcs_registry_reader jmcs-registry-reader-armv7 test-reader
