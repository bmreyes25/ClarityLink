#pragma once

#include <cstdint>
#include <cstddef>
#include <memory>
#include <string>

namespace claritylink::platform {
// Platform ports intentionally do not bind to Honda hardware or guessed APIs.
class PlatformClock { public: virtual ~PlatformClock() = default; virtual uint64_t monotonic_ms() = 0; };
class PlatformThread { public: virtual ~PlatformThread() = default; virtual bool start(void (*entry)(void*), void* context) = 0; virtual void join() = 0; };
class PlatformSocket { public: virtual ~PlatformSocket() = default; virtual int native_handle() const = 0; virtual void close() = 0; };
class PlatformDisplay { public: virtual ~PlatformDisplay() = default; virtual bool present(const uint8_t* rgba, uint32_t width, uint32_t height, uint32_t stride) = 0; virtual void clear() = 0; };
class PlatformAudio { public: virtual ~PlatformAudio() = default; virtual bool submit(const uint8_t*, size_t) = 0; };
class PlatformInput { public: virtual ~PlatformInput() = default; virtual bool poll(uint32_t& event) = 0; };
class PlatformUsb { public: virtual ~PlatformUsb() = default; virtual bool open_claimed_interface(uint16_t, uint16_t) = 0; };
class PlatformAuthentication { public: virtual ~PlatformAuthentication() = default; virtual bool authenticated() const = 0; };
class PlatformProcessLifecycle { public: virtual ~PlatformProcessLifecycle() = default; virtual void request_shutdown() = 0; };

}  // namespace claritylink::platform
