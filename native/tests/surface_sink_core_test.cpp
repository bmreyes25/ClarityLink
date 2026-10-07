#include "../platform/android/surface_sink_core.hpp"

#include <atomic>
#include <condition_variable>
#include <cstring>
#include <iostream>
#include <mutex>
#include <stdexcept>
#include <thread>
#include <vector>

using namespace claritylink;
using namespace claritylink::android;

namespace {
void require(bool ok, const char* why) { if (!ok) throw std::runtime_error(why); }

class FakeSurfaceWindow final : public SurfaceWindow {
 public:
  explicit FakeSurfaceWindow(int32_t width = 8, int32_t height = 4, int32_t stride = 10)
      : pixels_(static_cast<size_t>(stride) * static_cast<size_t>(height) * 4u, 0xA5),
        width_(width), height_(height), stride_(stride) {}
  bool set_rgba_geometry(uint32_t width, uint32_t height) noexcept override {
    if (!geometry_ok) return false;
    width_ = static_cast<int32_t>(width); height_ = static_cast<int32_t>(height);
    if (stride_ < width_) stride_ = width_;
    pixels_.assign(static_cast<size_t>(stride_) * static_cast<size_t>(height_) * 4u, 0xA5);
    return true;
  }
  bool lock(SurfaceBuffer& out) noexcept override {
    std::unique_lock<std::mutex> lock(mutex_);
    if (!lock_ok) return false;
    entered_ = true; cv_.notify_all();
    if (block_lock_) cv_.wait(lock, [&] { return release_lock_; });
    out = {pixels_.data(), width_, height_, stride_};
    ++locks; return true;
  }
  bool unlock_and_post() noexcept override {
    ++posts;
    return post_ok;
  }
  void wait_for_lock() { std::unique_lock<std::mutex> l(mutex_); cv_.wait(l, [&] { return entered_; }); }
  void unblock() { std::lock_guard<std::mutex> l(mutex_); release_lock_ = true; cv_.notify_all(); }
  bool geometry_ok = true, lock_ok = true, post_ok = true;
  int locks = 0, posts = 0;
  const std::vector<uint8_t>& pixels() const { return pixels_; }
  void block_next_lock() { std::lock_guard<std::mutex> l(mutex_); block_lock_ = true; }
 private:
  std::vector<uint8_t> pixels_;
  int32_t width_, height_, stride_;
  std::mutex mutex_; std::condition_variable cv_;
  bool block_lock_ = false, entered_ = false, release_lock_ = false;
};

Frame frame(uint64_t gen = 7, StreamType stream = StreamType::Type110,
            uint32_t width = 2, uint32_t height = 2, uint32_t stride = 8) {
  Frame f{stream, gen, 1, width, height, stride, std::vector<uint8_t>(stride * height, 0x3C)};
  return f;
}
}

int main() {
  try {
    auto window = std::make_shared<FakeSurfaceWindow>();
    SurfaceSinkCore sink(window, 7, StreamType::Type110, 101);
    require(sink.valid() && sink.matches(7, StreamType::Type110), "attached surface identity");
    require(!sink.matches(8, StreamType::Type110) && !sink.matches(7, StreamType::Type111), "generation/stream mismatch");
    require(sink.present(frame()), "RGBA frame present");
    require(window->posts == 1 && window->pixels()[0] == 0x3C, "copy and post");
    require(window->pixels()[8] == 0xA5, "row copy respects destination pixel stride");
    sink.clear(6); require(window->pixels()[0] == 0x3C, "wrong generation cannot clear");
    sink.clear(7); require(window->pixels()[0] == 0, "matching generation clears");

    auto bad_stride = frame(); bad_stride.stride = 4; bad_stride.rgba.resize(8);
    require(!sink.present(bad_stride), "undersized source stride rejected");
    auto wrong_gen = frame(8); require(!sink.present(wrong_gen), "stale frame rejected");
    auto wrong_stream = frame(7, StreamType::Type111); require(!sink.present(wrong_stream), "wrong stream rejected");
    auto zero = frame(7, StreamType::Type110, 0, 2, 0); require(!sink.present(zero), "zero dimensions rejected");
    auto huge = frame(7, StreamType::Type110, 9000, 1, 36000); require(!sink.present(huge), "oversized dimensions rejected");

    window->geometry_ok = false; require(!sink.present(frame()), "geometry failure surfaced"); window->geometry_ok = true;
    window->lock_ok = false; require(!sink.present(frame()), "lock failure surfaced"); window->lock_ok = true;
    window->post_ok = false; require(!sink.present(frame()), "post failure surfaced"); window->post_ok = true;

    auto replacement_window = std::make_shared<FakeSurfaceWindow>();
    SurfaceSinkCore replacement(replacement_window, 7, StreamType::Type110, 102);
    sink.invalidate(); sink.invalidate();
    require(!sink.valid() && !sink.present(frame()), "invalidated old surface rejects frames idempotently");
    require(replacement.valid() && replacement.surface_token() != sink.surface_token(), "surface replacement has new token");
    require(replacement.present(frame()), "replacement receives frame");

    auto race_window = std::make_shared<FakeSurfaceWindow>(); race_window->block_next_lock();
    SurfaceSinkCore racing(race_window, 9, StreamType::Type111, 201);
    bool delivered = false;
    std::thread render([&] { delivered = racing.present(frame(9, StreamType::Type111)); });
    race_window->wait_for_lock();
    std::thread remove([&] { racing.invalidate(); });
    race_window->unblock(); render.join(); remove.join();
    require(delivered && !racing.valid(), "invalidation serializes after an in-flight frame");
    require(!racing.present(frame(9, StreamType::Type111)), "frame after invalidation rejected");
    std::cout << "R7C1_SURFACE_CORE_PASS environment=HOST_SIMULATED_ANDROID_RUNTIME replacement=PASS invalidation=PASS bounds=PASS\n";
  } catch (const std::exception& e) {
    std::cerr << "R7C1_SURFACE_CORE_FAIL " << e.what() << "\n"; return 1;
  }
  return 0;
}
