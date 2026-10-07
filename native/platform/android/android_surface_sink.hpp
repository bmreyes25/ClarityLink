#pragma once

#include "claritylink/receiver.hpp"

#include <android/native_window.h>
#include <atomic>
#include <mutex>

namespace claritylink::android {

// Owns exactly one ANativeWindow reference and one (generation, stream,
// surface-token) tuple. Callbacks never call back into Java.
class AndroidSurfaceSink final : public FrameSink {
 public:
  AndroidSurfaceSink(ANativeWindow* window, uint64_t generation,
                     StreamType stream, uint64_t surface_token);
  ~AndroidSurfaceSink() override;
  AndroidSurfaceSink(const AndroidSurfaceSink&) = delete;
  AndroidSurfaceSink& operator=(const AndroidSurfaceSink&) = delete;
  bool present(const Frame& frame) noexcept override;
  void clear(uint64_t generation) noexcept override;
  void invalidate() noexcept;
  bool valid() const noexcept;
  bool matches(uint64_t generation, StreamType stream) const noexcept;
 private:
  mutable std::mutex mutex_;
  ANativeWindow* window_;
  const uint64_t generation_;
  const StreamType stream_;
  const uint64_t surface_token_;
  bool valid_;
};
}  // namespace claritylink::android
