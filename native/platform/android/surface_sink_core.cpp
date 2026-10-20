#include "surface_sink_core.hpp"

#include <cstring>
#include <limits>

namespace claritylink::android {
namespace {
constexpr uint32_t kMaxDimension = 8192;
constexpr size_t kMaxFrameBytes = 64u * 1024u * 1024u;

bool valid_buffer(const SurfaceBuffer& buffer) {
  return buffer.bits && buffer.width > 0 && buffer.height > 0 &&
         buffer.stride_pixels >= buffer.width &&
         static_cast<size_t>(buffer.stride_pixels) <= kMaxFrameBytes / 4u &&
         static_cast<size_t>(buffer.height) <=
             kMaxFrameBytes / (static_cast<size_t>(buffer.stride_pixels) * 4u);
}
}  // namespace

SurfaceSinkCore::SurfaceSinkCore(std::shared_ptr<SurfaceWindow> window,
                                 uint64_t generation, StreamType stream,
                                 uint64_t surface_token)
    : window_(std::move(window)), generation_(generation), stream_(stream),
      surface_token_(surface_token),
      valid_(window_ != nullptr && generation != 0 && surface_token != 0 &&
             (stream == StreamType::Type110 || stream == StreamType::Type111)) {}

SurfaceSinkCore::~SurfaceSinkCore() { invalidate(); }

bool SurfaceSinkCore::valid() const noexcept {
  std::lock_guard<std::mutex> lock(mutex_);
  return valid_ && window_ != nullptr;
}

bool SurfaceSinkCore::matches(uint64_t generation, StreamType stream) const noexcept {
  std::lock_guard<std::mutex> lock(mutex_);
  return valid_ && window_ != nullptr && generation_ == generation && stream_ == stream;
}

bool SurfaceSinkCore::present(const Frame& frame) noexcept {
  std::lock_guard<std::mutex> lock(mutex_);
  if (!valid_ || !window_ || frame_in_progress_ || frame.generation != generation_ ||
      frame.stream != stream_ || frame.width == 0 || frame.height == 0 ||
      frame.width > kMaxDimension || frame.height > kMaxDimension ||
      frame.width > std::numeric_limits<uint32_t>::max() / 4u ||
      frame.stride < frame.width * 4u || frame.stride > kMaxFrameBytes ||
      frame.height > kMaxFrameBytes / frame.stride ||
      frame.rgba.size() != static_cast<size_t>(frame.stride) * frame.height)
    return false;

  if (!window_->set_rgba_geometry(frame.width, frame.height)) return false;
  SurfaceBuffer buffer;
  if (!window_->lock(buffer)) return false;
  frame_in_progress_ = true;
  bool copied = false;
  if (valid_buffer(buffer) && static_cast<uint32_t>(buffer.width) >= frame.width &&
      static_cast<uint32_t>(buffer.height) >= frame.height) {
    const size_t dst_stride = static_cast<size_t>(buffer.stride_pixels) * 4u;
    const size_t row_bytes = static_cast<size_t>(frame.width) * 4u;
    for (uint32_t y = 0; y < frame.height; ++y) {
      std::memcpy(buffer.bits + static_cast<size_t>(y) * dst_stride,
                  frame.rgba.data() + static_cast<size_t>(y) * frame.stride,
                  row_bytes);
    }
    copied = true;
  }
  const bool posted = window_->unlock_and_post();
  frame_in_progress_ = false;
  if (copied && posted) {
    last_frame_width_ = frame.width;
    last_frame_height_ = frame.height;
  }
  return copied && posted;
}

void SurfaceSinkCore::clear(uint64_t generation) noexcept {
  std::lock_guard<std::mutex> lock(mutex_);
  if (!valid_ || !window_ || generation != generation_ || frame_in_progress_ ||
      last_frame_width_ == 0 || last_frame_height_ == 0) return;
  const uint32_t frame_width = last_frame_width_;
  const uint32_t frame_height = last_frame_height_;
  SurfaceBuffer buffer;
  if (!window_->lock(buffer)) return;
  frame_in_progress_ = true;
  bool cleared = false;
  if (frame_width != 0 && frame_height != 0 && valid_buffer(buffer)) {
    const size_t row_bytes = static_cast<size_t>(buffer.width) * 4u;
    const size_t dst_stride = static_cast<size_t>(buffer.stride_pixels) * 4u;
    for (int32_t y = 0; y < buffer.height; ++y)
      std::memset(buffer.bits + static_cast<size_t>(y) * dst_stride, 0, row_bytes);
    cleared = true;
  }
  const bool posted = window_->unlock_and_post();
  frame_in_progress_ = false;
  if (cleared && posted) {
    last_frame_width_ = 0;
    last_frame_height_ = 0;
  }
}

void SurfaceSinkCore::invalidate() noexcept {
  std::lock_guard<std::mutex> lock(mutex_);
  valid_ = false;
  last_frame_width_ = 0;
  last_frame_height_ = 0;
  window_.reset();
}

}  // namespace claritylink::android
