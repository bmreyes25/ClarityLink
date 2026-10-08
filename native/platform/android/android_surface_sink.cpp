#include "android_surface_sink.hpp"

#include <limits>
#include <utility>

namespace claritylink::android {
namespace {
class AndroidNativeWindow final : public SurfaceWindow {
 public:
  explicit AndroidNativeWindow(ANativeWindow* window) : window_(window) {
    if (window_) ANativeWindow_acquire(window_);
  }
  ~AndroidNativeWindow() override {
    if (window_) ANativeWindow_release(window_);
  }

  bool set_rgba_geometry(uint32_t width, uint32_t height) noexcept override {
    if (!window_ || width > static_cast<uint32_t>(std::numeric_limits<int32_t>::max()) ||
        height > static_cast<uint32_t>(std::numeric_limits<int32_t>::max())) return false;
    return ANativeWindow_setBuffersGeometry(window_, static_cast<int32_t>(width),
        static_cast<int32_t>(height), WINDOW_FORMAT_RGBA_8888) == 0;
  }

  bool lock(SurfaceBuffer& result) noexcept override {
    if (!window_) return false;
    ANativeWindow_Buffer buffer{};
    if (ANativeWindow_lock(window_, &buffer, nullptr) != 0) return false;
    result.bits = static_cast<uint8_t*>(buffer.bits);
    result.width = buffer.width;
    result.height = buffer.height;
    result.stride_pixels = buffer.stride;
    return true;
  }

  bool unlock_and_post() noexcept override {
    return window_ && ANativeWindow_unlockAndPost(window_) == 0;
  }

 private:
  ANativeWindow* window_;
};
}  // namespace

AndroidSurfaceSink::AndroidSurfaceSink(ANativeWindow* window, uint64_t generation,
                                       StreamType stream, uint64_t surface_token) {
  std::shared_ptr<SurfaceWindow> backend;
  if (window) backend = std::make_shared<AndroidNativeWindow>(window);
  core_ = std::make_shared<SurfaceSinkCore>(std::move(backend), generation, stream,
                                            surface_token);
}

AndroidSurfaceSink::~AndroidSurfaceSink() { invalidate(); }
bool AndroidSurfaceSink::present(const Frame& frame) noexcept {
  return core_ && core_->present(frame);
}
void AndroidSurfaceSink::clear(uint64_t generation) noexcept {
  if (core_) core_->clear(generation);
}
void AndroidSurfaceSink::invalidate() noexcept {
  if (core_) core_->invalidate();
}
bool AndroidSurfaceSink::valid() const noexcept {
  return core_ && core_->valid();
}
bool AndroidSurfaceSink::matches(uint64_t generation, StreamType stream) const noexcept {
  return core_ && core_->matches(generation, stream);
}

}  // namespace claritylink::android
