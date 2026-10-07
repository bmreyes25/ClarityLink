#include "android_surface_sink.hpp"

#include <algorithm>
#include <cstring>
#include <limits>

namespace claritylink::android {
namespace {
constexpr uint32_t kMaxDimension = 8192;
constexpr size_t kMaxFrameBytes = 64u * 1024u * 1024u;
}

AndroidSurfaceSink::AndroidSurfaceSink(ANativeWindow* window, uint64_t generation,
                                       StreamType stream, uint64_t token)
    : window_(window), generation_(generation), stream_(stream),
      surface_token_(token), valid_(window != nullptr && generation != 0 && token != 0) {
  if (valid_) ANativeWindow_acquire(window_);
}
AndroidSurfaceSink::~AndroidSurfaceSink() { invalidate(); }

bool AndroidSurfaceSink::valid() const noexcept {
  std::lock_guard<std::mutex> lock(mutex_);
  return valid_ && window_ != nullptr;
}
bool AndroidSurfaceSink::matches(uint64_t generation, StreamType stream) const noexcept {
  std::lock_guard<std::mutex> lock(mutex_);
  return valid_ && window_ != nullptr && generation_ == generation && stream_ == stream;
}

bool AndroidSurfaceSink::present(const Frame& frame) noexcept {
  std::lock_guard<std::mutex> lock(mutex_);
  if (!valid_ || !window_ || frame.generation != generation_ || frame.stream != stream_ ||
      frame.width == 0 || frame.height == 0 || frame.width > kMaxDimension ||
      frame.height > kMaxDimension || frame.width > UINT32_MAX / 4u ||
      frame.stride < frame.width * 4u || frame.stride > kMaxFrameBytes ||
      frame.height > kMaxFrameBytes / frame.stride ||
      frame.rgba.size() != static_cast<size_t>(frame.stride) * frame.height) return false;

  ANativeWindow_Buffer buffer{};
  if (ANativeWindow_setBuffersGeometry(window_, static_cast<int32_t>(frame.width),
                                       static_cast<int32_t>(frame.height), WINDOW_FORMAT_RGBA_8888) != 0)
    return false;
  if (ANativeWindow_lock(window_, &buffer, nullptr) != 0) return false;
  bool ok = false;
  if (buffer.bits && buffer.width > 0 && buffer.height > 0 && buffer.stride >= buffer.width &&
      static_cast<uint32_t>(buffer.width) >= frame.width &&
      static_cast<uint32_t>(buffer.height) >= frame.height &&
      static_cast<size_t>(buffer.stride) <= kMaxFrameBytes / 4u &&
      static_cast<size_t>(buffer.height) <= kMaxFrameBytes / (static_cast<size_t>(buffer.stride) * 4u)) {
    auto* dst = static_cast<uint8_t*>(buffer.bits);
    const size_t dst_stride = static_cast<size_t>(buffer.stride) * 4u;
    const size_t row_bytes = static_cast<size_t>(frame.width) * 4u;
    for (uint32_t y = 0; y < frame.height; ++y)
      std::memcpy(dst + static_cast<size_t>(y) * dst_stride,
                  frame.rgba.data() + static_cast<size_t>(y) * frame.stride, row_bytes);
    ok = true;
  }
  const int32_t posted = ANativeWindow_unlockAndPost(window_);
  return ok && posted == 0;
}

void AndroidSurfaceSink::clear(uint64_t generation) noexcept {
  std::lock_guard<std::mutex> lock(mutex_);
  if (!valid_ || !window_ || generation != generation_) return;
  ANativeWindow_Buffer buffer{};
  if (ANativeWindow_lock(window_, &buffer, nullptr) != 0) return;
  if (buffer.bits && buffer.width > 0 && buffer.height > 0 && buffer.stride >= buffer.width &&
      static_cast<size_t>(buffer.stride) <= kMaxFrameBytes / 4u &&
      static_cast<size_t>(buffer.height) <= kMaxFrameBytes / (static_cast<size_t>(buffer.stride) * 4u)) {
    std::memset(buffer.bits, 0, static_cast<size_t>(buffer.stride) * buffer.height * 4u);
  }
  ANativeWindow_unlockAndPost(window_);
}

void AndroidSurfaceSink::invalidate() noexcept {
  std::lock_guard<std::mutex> lock(mutex_);
  if (!valid_ && !window_) return;
  valid_ = false;
  if (window_) ANativeWindow_release(window_);
  window_ = nullptr;
}
}  // namespace claritylink::android
