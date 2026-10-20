#pragma once

#include "claritylink/receiver.hpp"

#include <cstdint>
#include <memory>
#include <mutex>

namespace claritylink::android {

struct SurfaceBuffer {
  uint8_t* bits = nullptr;
  int32_t width = 0;
  int32_t height = 0;
  int32_t stride_pixels = 0;
};

// Host-testable boundary around the Android window lock/post primitives.
// The Android production adapter implements this with ANativeWindow calls.
class SurfaceWindow {
 public:
  virtual ~SurfaceWindow() = default;
  virtual bool set_rgba_geometry(uint32_t width, uint32_t height) noexcept = 0;
  virtual bool lock(SurfaceBuffer& buffer) noexcept = 0;
  virtual bool unlock_and_post() noexcept = 0;
};

class SurfaceSinkCore final : public FrameSink {
 public:
  SurfaceSinkCore(std::shared_ptr<SurfaceWindow> window, uint64_t generation,
                  StreamType stream, uint64_t surface_token);
  ~SurfaceSinkCore() override;
  SurfaceSinkCore(const SurfaceSinkCore&) = delete;
  SurfaceSinkCore& operator=(const SurfaceSinkCore&) = delete;

  bool present(const Frame& frame) noexcept override;
  void clear(uint64_t generation) noexcept override;
  void invalidate() noexcept;
  bool valid() const noexcept;
  bool matches(uint64_t generation, StreamType stream) const noexcept;
  uint64_t surface_token() const noexcept { return surface_token_; }

 private:
  mutable std::mutex mutex_;
  std::shared_ptr<SurfaceWindow> window_;
  const uint64_t generation_;
  const StreamType stream_;
  const uint64_t surface_token_;
  bool valid_;
  bool frame_in_progress_ = false;
  uint32_t last_frame_width_ = 0;
  uint32_t last_frame_height_ = 0;
};

}  // namespace claritylink::android
