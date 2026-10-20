#pragma once

#include <cstdint>

namespace claritylink::android::r7c6test {

enum class Checkpoint : int {
  SetupPrimaryAllocated = 1,
  SetupSecondaryAllocated = 2,
  DecodePrimaryBeforePost = 3,
  DecodeSecondaryBeforePost = 4,
  SocketReadActive = 5,
  SocketWriteActive = 6,
};

bool arm(Checkpoint checkpoint, uint64_t generation, int stream, uint32_t timeout_ms) noexcept;
bool wait_reached(Checkpoint checkpoint, uint64_t generation, int stream,
                  uint32_t timeout_ms) noexcept;
bool pause_if_armed(Checkpoint checkpoint, uint64_t generation, int stream) noexcept;
bool release(Checkpoint checkpoint, uint64_t generation, int stream) noexcept;
void clear() noexcept;
bool reset_for_next_case(uint32_t timeout_ms) noexcept;
bool idle() noexcept;
bool wait_idle(uint32_t timeout_ms) noexcept;
unsigned active_waiters() noexcept;
void set_stream_context(int stream) noexcept;
int stream_context() noexcept;

}  // namespace claritylink::android::r7c6test
