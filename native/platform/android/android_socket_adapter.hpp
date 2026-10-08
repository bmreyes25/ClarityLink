#pragma once
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <memory>
#include <mutex>
#include <string>

namespace claritylink::android {
struct SocketEndpoint {
  std::string ipv4;  // remote numeric IPv4 only; wildcard is rejected
  std::string bind_ipv4;  // explicit local interface; wildcard is rejected
  uint16_t port = 0;
  uint32_t timeout_ms = 1000;
  uint64_t generation = 0;
};

class AndroidSocketAdapter final {
 public:
  AndroidSocketAdapter() = default;
  ~AndroidSocketAdapter();
  AndroidSocketAdapter(const AndroidSocketAdapter&) = delete;
  AndroidSocketAdapter& operator=(const AndroidSocketAdapter&) = delete;
  bool connect(const SocketEndpoint& endpoint);
  int read(uint8_t* buffer, size_t capacity, uint64_t generation);
  int write(const uint8_t* buffer, size_t length, uint64_t generation);
  void shutdown();
  void close();
  int error() const { return error_.load(); }

 private:
  struct SocketState;
  std::shared_ptr<SocketState> snapshot() const;
  mutable std::mutex mutex_;
  std::shared_ptr<SocketState> state_;
  uint64_t revision_ = 0;
  std::atomic<int> error_{0};
};
}  // namespace claritylink::android
