#pragma once

#include <cstdint>
#include <atomic>
#include <cstddef>
#include <memory>
#include <mutex>
#include <string>
#include <vector>

namespace claritylink {

enum class StreamType : uint8_t { Type110 = 110, Type111 = 111 };
enum class SessionState : uint8_t { Idle, Authenticated, InfoExchanged, Active, Closing, Closed };
enum class StreamState : uint8_t { Configuring, Active, Closing, Closed, Failed };

struct Frame {
  StreamType stream;
  uint64_t generation;
  uint64_t timestamp;
  uint32_t width;
  uint32_t height;
  uint32_t stride;
  std::vector<uint8_t> rgba;
};

class FrameSink {
 public:
  virtual ~FrameSink() = default;
  // Both callbacks run under the generation lock; they must not re-enter the
  // owner and must not throw. Implementations should return false on failure.
  virtual bool present(const Frame& frame) noexcept = 0;
  virtual void clear(uint64_t generation) noexcept = 0;
};

class MediaTransport {
 public:
  virtual ~MediaTransport() = default;
  virtual bool submit_test_packet(const std::vector<uint8_t>& packet) = 0;
  virtual bool read_packet(std::vector<uint8_t>& packet) = 0;
  virtual void close() = 0;
};

class MediaFramer final {
 public:
  bool parse(const std::vector<uint8_t>& bytes, uint64_t& generation,
             StreamType& type, uint16_t& connection_id,
             std::vector<uint8_t>& payload) const;
};

class SecurityProvider {
 public:
  virtual ~SecurityProvider() = default;
  virtual bool open_test_media(const std::vector<uint8_t>& input,
                               std::vector<uint8_t>& clear) = 0;
  virtual bool production_ready() const = 0;
};

class AuthenticationAuthority {
 public:
  virtual ~AuthenticationAuthority() = default;
  virtual bool authenticate(uint64_t generation) = 0;
  virtual bool synthetic_test_authority() const = 0;
};
class SyntheticTestAuthenticationAuthority final : public AuthenticationAuthority {
 public:
  bool authenticate(uint64_t generation) override { return generation != 0; }
  bool synthetic_test_authority() const override { return true; }
};
class UnavailableAuthenticationAuthority final : public AuthenticationAuthority {
 public:
  bool authenticate(uint64_t) override { return false; }
  bool synthetic_test_authority() const override { return false; }
};

class PrimaryMediaSecurityProvider : public SecurityProvider {};
class SecondaryMediaSecurityProvider : public SecurityProvider {};
class TestPrimarySecurityProvider final : public PrimaryMediaSecurityProvider {
 public:
  bool open_test_media(const std::vector<uint8_t>& input,
                       std::vector<uint8_t>& clear) override;
  bool production_ready() const override { return false; }
};
class TestSecondarySecurityProvider final : public SecondaryMediaSecurityProvider {
 public:
  bool open_test_media(const std::vector<uint8_t>& input,
                       std::vector<uint8_t>& clear) override;
  bool production_ready() const override { return false; }
};
class FailClosedPrimarySecurityProvider final : public PrimaryMediaSecurityProvider {
 public:
  bool open_test_media(const std::vector<uint8_t>&, std::vector<uint8_t>&) override;
  bool production_ready() const override { return false; }
};
class FailClosedSecondarySecurityProvider final : public SecondaryMediaSecurityProvider {
 public:
  bool open_test_media(const std::vector<uint8_t>&, std::vector<uint8_t>&) override;
  bool production_ready() const override { return false; }
};

struct StreamConfig {
  StreamType type;
  uint16_t connection_id;
  bool fail_setup = false;
};

struct ResourceCounts {
  std::size_t sessions = 0;
  std::size_t listeners = 0;
  std::size_t security_contexts = 0;
  std::size_t decoders = 0;
  std::size_t retained_frames = 0;
  std::size_t display_ownership = 0;
  std::size_t streams = 0;
};

class ReceiverGeneration final {
 public:
  ReceiverGeneration(uint64_t generation, std::shared_ptr<FrameSink> display0,
                     std::shared_ptr<FrameSink> display1,
                     const std::shared_ptr<AuthenticationAuthority>& authority);
  ~ReceiverGeneration();
  ReceiverGeneration(const ReceiverGeneration&) = delete;
  ReceiverGeneration& operator=(const ReceiverGeneration&) = delete;

  bool exchange_info(uint64_t generation);
  bool setup(uint64_t generation, const std::vector<StreamConfig>& streams);
  bool ingest(uint64_t generation, uint16_t connection_id,
              const std::vector<uint8_t>& packet, uint64_t timestamp);
  void close_stream(StreamType type);
  void request_close() noexcept;
  void request_close_stream(StreamType type) noexcept;
  void close();
  SessionState state() const;
  ResourceCounts resources() const;
  uint64_t generation() const { return generation_; }
  std::vector<std::string> events() const;

 private:
  struct Stream;
  bool decode_and_present(Stream& stream, const std::vector<uint8_t>& payload,
                          uint64_t timestamp);
  void sync_state();
  mutable std::mutex mutex_;
  uint64_t generation_;
  SessionState state_ = SessionState::Authenticated;
  std::shared_ptr<FrameSink> display0_;
  std::shared_ptr<FrameSink> display1_;
  bool test_mode_;
  std::unique_ptr<Stream> primary_;
  std::unique_ptr<Stream> secondary_;
  std::vector<std::string> events_;
  std::atomic<bool> cancellation_requested_{false};
  std::atomic<bool> cancel_secondary_setup_{false};
};

// Wire packet: big-endian generation(8), stream type(1), connection id(2),
// payload length(4), then H.264 Annex-B bytes. Maximum payload is 2 MiB.
bool parse_media_packet(const std::vector<uint8_t>& bytes, uint64_t& generation,
                        StreamType& type, uint16_t& connection_id,
                        std::vector<uint8_t>& payload);

class MemoryFrameSink final : public FrameSink {
 public:
  bool available = true;
  bool present(const Frame& frame) noexcept override;
  void clear(uint64_t generation) noexcept override;
  const std::vector<Frame>& frames() const { return frames_; }
  bool cleared() const { return cleared_; }
 private:
  std::vector<Frame> frames_;
  bool cleared_ = true;
};

}  // namespace claritylink
