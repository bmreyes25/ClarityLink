CC ?= cc
CFLAGS ?= -O2 -Wall -Wextra -Werror -std=c11
NDK_ROOT ?= /Volumes/Android\ NDK\ r23c/AndroidNDK8568313.app/Contents/NDK
HOST_TAG ?= darwin-x86_64
CLANG = $(NDK_ROOT)/toolchains/llvm/prebuilt/$(HOST_TAG)/bin/clang
SYSROOT = $(NDK_ROOT)/toolchains/llvm/prebuilt/$(HOST_TAG)/sysroot

.PHONY: test armv7 clean
test: test-reader
	./test-reader

test-reader: test_reader.c reader.c
	$(CC) $(CFLAGS) -o $@ test_reader.c

armv7: reader.c
	"$(CLANG)" --target=armv7a-linux-androideabi17 --sysroot="$(SYSROOT)" $(CFLAGS) -march=armv7-a -mfloat-abi=softfp -fPIE -pie -Wl,-z,relro,-z,now -o jmcs_ptrace_registry_reader reader.c

clean:
	rm -f test-reader jmcs_ptrace_registry_reader
