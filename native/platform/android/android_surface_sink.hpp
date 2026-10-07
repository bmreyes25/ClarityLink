#pragma once

#include "surface_sink_core.hpp"

#include <android/native_window.h>
#include <memory>

namespace claritylink::android {

// API17 production bridge to the host-testable surface ownership core.
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
  std::shared_ptr<SurfaceSinkCore> core_;
};
}  // namespace claritylink::android
