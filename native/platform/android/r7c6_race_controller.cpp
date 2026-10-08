#include "r7c6_race_controller.hpp"

#include <chrono>
#include <condition_variable>
#include <mutex>

namespace claritylink::android::r7c6test {
namespace {
struct Controller {
  std::mutex mutex;
  std::condition_variable changed;
  bool armed = false;
  bool reached = false;
  bool released = false;
  bool timed_out = false;
  Checkpoint checkpoint = Checkpoint::SetupPrimaryAllocated;
  uint64_t generation = 0;
  int stream = 0;
  uint32_t timeout_ms = 0;
  unsigned active_waiters = 0;
};
Controller controller;
thread_local int current_stream = 0;

bool matches(Checkpoint checkpoint, uint64_t generation, int stream) {
  return controller.armed && controller.checkpoint == checkpoint &&
      controller.generation == generation && controller.stream == stream;
}
void reset_locked() {
  controller.armed = false;
  controller.reached = false;
  controller.released = false;
  controller.timed_out = false;
  controller.generation = 0;
  controller.stream = 0;
  controller.timeout_ms = 0;
}
}  // namespace

bool arm(Checkpoint checkpoint, uint64_t generation, int stream, uint32_t timeout_ms) noexcept {
  if (generation == 0 || (stream != 110 && stream != 111) || timeout_ms == 0 || timeout_ms > 30000) return false;
  std::lock_guard<std::mutex> lock(controller.mutex);
  if (controller.armed) return false;
  controller.armed = true;
  controller.reached = false;
  controller.released = false;
  controller.timed_out = false;
  controller.checkpoint = checkpoint;
  controller.generation = generation;
  controller.stream = stream;
  controller.timeout_ms = timeout_ms;
  return true;
}

bool wait_reached(Checkpoint checkpoint, uint64_t generation, int stream,
                  uint32_t timeout_ms) noexcept {
  std::unique_lock<std::mutex> lock(controller.mutex);
  const auto deadline = std::chrono::steady_clock::now() + std::chrono::milliseconds(timeout_ms);
  const bool reached = controller.changed.wait_until(lock, deadline, [&] {
    return !controller.armed || (matches(checkpoint, generation, stream) && controller.reached);
  });
  return reached && matches(checkpoint, generation, stream) && controller.reached;
}

bool pause_if_armed(Checkpoint checkpoint, uint64_t generation, int stream) noexcept {
  std::unique_lock<std::mutex> lock(controller.mutex);
  if (!matches(checkpoint, generation, stream)) return true;
  ++controller.active_waiters;
  controller.reached = true;
  controller.changed.notify_all();
  const uint32_t timeout_ms = controller.timeout_ms;
  const bool released = controller.changed.wait_for(lock, std::chrono::milliseconds(timeout_ms), [] {
    return controller.released || !controller.armed;
  });
  if (!released) controller.timed_out = true;
  const bool ok = released && controller.released;
  reset_locked();
  --controller.active_waiters;
  controller.changed.notify_all();
  return ok;
}

bool release(Checkpoint checkpoint, uint64_t generation, int stream) noexcept {
  std::lock_guard<std::mutex> lock(controller.mutex);
  if (!matches(checkpoint, generation, stream) || !controller.reached) return false;
  controller.released = true;
  controller.changed.notify_all();
  return true;
}

void clear() noexcept {
  std::lock_guard<std::mutex> lock(controller.mutex);
  controller.released = true;
  controller.changed.notify_all();
  reset_locked();
  controller.changed.notify_all();
}

bool reset_for_next_case(uint32_t timeout_ms) noexcept {
  if (timeout_ms == 0 || timeout_ms > 30000) return false;
  std::unique_lock<std::mutex> lock(controller.mutex);
  controller.released = true;
  controller.armed = false;
  controller.changed.notify_all();
  const auto deadline = std::chrono::steady_clock::now() + std::chrono::milliseconds(timeout_ms);
  return controller.changed.wait_until(lock, deadline, [] {
    return !controller.armed && controller.active_waiters == 0;
  });
}

bool idle() noexcept {
  std::lock_guard<std::mutex> lock(controller.mutex);
  return !controller.armed && controller.active_waiters == 0;
}

bool wait_idle(uint32_t timeout_ms) noexcept {
  if (timeout_ms == 0 || timeout_ms > 30000) return false;
  std::unique_lock<std::mutex> lock(controller.mutex);
  const auto deadline = std::chrono::steady_clock::now() + std::chrono::milliseconds(timeout_ms);
  return controller.changed.wait_until(lock, deadline, [] {
    return !controller.armed && controller.active_waiters == 0;
  });
}

unsigned active_waiters() noexcept {
  std::lock_guard<std::mutex> lock(controller.mutex);
  return controller.active_waiters;
}

void set_stream_context(int stream) noexcept { current_stream = stream; }
int stream_context() noexcept { return current_stream; }

}  // namespace claritylink::android::r7c6test
