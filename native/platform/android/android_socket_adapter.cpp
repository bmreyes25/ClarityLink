#include "android_socket_adapter.hpp"
#include "r7c6_race_controller.hpp"

#include <arpa/inet.h>
#include <cerrno>
#include <fcntl.h>
#include <poll.h>
#include <sys/socket.h>
#include <unistd.h>

namespace claritylink::android {
namespace {
constexpr size_t kMaxTransfer = 1024u * 1024u;
void close_fd(int fd) { if (fd >= 0) ::close(fd); }
}

struct AndroidSocketAdapter::SocketState {
  SocketState(int descriptor, uint64_t owner_generation, uint32_t owner_timeout_ms)
      : fd(descriptor), generation(owner_generation), timeout_ms(owner_timeout_ms) {}
  ~SocketState() { close_fd(fd); }
  void shutdown() noexcept {
    if (!shutdown_started.exchange(true)) ::shutdown(fd, SHUT_RDWR);
  }
  const int fd;
  const uint64_t generation;
  const uint32_t timeout_ms;
  std::atomic<bool> shutdown_started{false};
};

AndroidSocketAdapter::~AndroidSocketAdapter() { close(); }

std::shared_ptr<AndroidSocketAdapter::SocketState> AndroidSocketAdapter::snapshot() const {
  std::lock_guard<std::mutex> lock(mutex_);
  return state_;
}

bool AndroidSocketAdapter::connect(const SocketEndpoint& ep) {
  std::shared_ptr<SocketState> old;
  uint64_t revision;
  {
    std::lock_guard<std::mutex> lock(mutex_);
    revision = ++revision_;
    old.swap(state_);
  }
  if (old) old->shutdown();
  error_.store(0);
  if (ep.ipv4.empty() || ep.ipv4 == "0.0.0.0" || ep.bind_ipv4.empty() ||
      ep.bind_ipv4 == "0.0.0.0" || ep.port == 0 || ep.timeout_ms == 0 ||
      ep.timeout_ms > 30000 || ep.generation == 0) {
    error_.store(EINVAL);
    return false;
  }
  sockaddr_in addr{};
  addr.sin_family = AF_INET;
  addr.sin_port = htons(ep.port);
  if (inet_pton(AF_INET, ep.ipv4.c_str(), &addr.sin_addr) != 1 ||
      addr.sin_addr.s_addr == htonl(INADDR_ANY)) {
    error_.store(EINVAL);
    return false;
  }
  sockaddr_in local{};
  local.sin_family = AF_INET;
  if (inet_pton(AF_INET, ep.bind_ipv4.c_str(), &local.sin_addr) != 1 ||
      local.sin_addr.s_addr == htonl(INADDR_ANY)) {
    error_.store(EINVAL);
    return false;
  }
  const int fd = socket(AF_INET, SOCK_STREAM, 0);
  if (fd < 0) { error_.store(errno); return false; }
  if (::bind(fd, reinterpret_cast<sockaddr*>(&local), sizeof(local)) < 0) {
    error_.store(errno); close_fd(fd); return false;
  }
  const int flags = fcntl(fd, F_GETFL, 0);
  if (flags < 0 || fcntl(fd, F_SETFL, flags | O_NONBLOCK) < 0) {
    error_.store(errno); close_fd(fd); return false;
  }
  int result = ::connect(fd, reinterpret_cast<sockaddr*>(&addr), sizeof(addr));
  if (result < 0 && errno != EINPROGRESS) {
    error_.store(errno); close_fd(fd); return false;
  }
  if (result < 0) {
    pollfd p{fd, POLLOUT, 0};
    result = poll(&p, 1, static_cast<int>(ep.timeout_ms));
    if (result <= 0) {
      error_.store(result == 0 ? ETIMEDOUT : errno); close_fd(fd); return false;
    }
    int socket_error = 0;
    socklen_t n = sizeof(socket_error);
    if (getsockopt(fd, SOL_SOCKET, SO_ERROR, &socket_error, &n) < 0 || socket_error != 0) {
      error_.store(socket_error == 0 ? errno : socket_error); close_fd(fd); return false;
    }
  }
  auto connected = std::make_shared<SocketState>(fd, ep.generation, ep.timeout_ms);
  {
    std::lock_guard<std::mutex> lock(mutex_);
    if (revision != revision_) {
      connected->shutdown();
      error_.store(ECANCELED);
      return false;
    }
    state_ = std::move(connected);
  }
  return true;
}

int AndroidSocketAdapter::read(uint8_t* buffer, size_t cap, uint64_t gen) {
  const auto state = snapshot();
  if (!state || state->generation != gen || state->shutdown_started.load() ||
      !buffer || cap == 0 || cap > kMaxTransfer) {
    error_.store(!state || (state && state->generation != gen) || !buffer || cap == 0 || cap > kMaxTransfer
        ? EINVAL : ECANCELED);
    return -1;
  }
#if defined(CLARITYLINK_TEST_DIAGNOSTICS)
  if (!r7c6test::pause_if_armed(r7c6test::Checkpoint::SocketReadActive, gen,
                                 r7c6test::stream_context())) {
    error_.store(ETIMEDOUT); return -1;
  }
#endif
  pollfd p{state->fd, POLLIN, 0};
  const int r = poll(&p, 1, static_cast<int>(state->timeout_ms));
  if (r <= 0) { error_.store(r == 0 ? ETIMEDOUT : errno); return -1; }
  if (state->shutdown_started.load()) { error_.store(ECANCELED); return -1; }
  const ssize_t n = recv(state->fd, buffer, cap, 0);
  if (n < 0) error_.store(errno);
  else if (n == 0) { error_.store(ECONNRESET); return -1; }
  return static_cast<int>(n);
}

int AndroidSocketAdapter::write(const uint8_t* data, size_t length, uint64_t gen) {
  const auto state = snapshot();
  if (!state || state->generation != gen || state->shutdown_started.load() ||
      !data || length == 0 || length > kMaxTransfer) {
    error_.store(!state || (state && state->generation != gen) || !data || length == 0 || length > kMaxTransfer
        ? EINVAL : ECANCELED);
    return -1;
  }
#if defined(CLARITYLINK_TEST_DIAGNOSTICS)
  if (!r7c6test::pause_if_armed(r7c6test::Checkpoint::SocketWriteActive, gen,
                                 r7c6test::stream_context())) {
    error_.store(ETIMEDOUT); return -1;
  }
#endif
  pollfd p{state->fd, POLLOUT, 0};
  const int r = poll(&p, 1, 1000);
  if (r <= 0) { error_.store(r == 0 ? ETIMEDOUT : errno); return -1; }
  if (state->shutdown_started.load()) { error_.store(ECANCELED); return -1; }
  const ssize_t n = send(state->fd, data, length, MSG_NOSIGNAL);
  if (n < 0) error_.store(errno);
  return static_cast<int>(n);  // Partial writes are reported to the caller.
}

void AndroidSocketAdapter::shutdown() {
  const auto state = snapshot();
  if (state) state->shutdown();
}

void AndroidSocketAdapter::close() {
  std::shared_ptr<SocketState> old;
  {
    std::lock_guard<std::mutex> lock(mutex_);
    ++revision_;
    old.swap(state_);
  }
  if (old) old->shutdown();
}

}  // namespace claritylink::android
