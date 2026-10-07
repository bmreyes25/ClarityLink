#include "claritylink/receiver.hpp"
#include "claritylink/platform.hpp"

#include <algorithm>
#include <limits>
#include <new>
#include <stdexcept>
#include <utility>

extern "C" {
#include <libavcodec/avcodec.h>
#include <libavutil/imgutils.h>
#include <libswscale/swscale.h>
}

namespace claritylink {
namespace {
constexpr size_t kMaxPayload = 2U * 1024U * 1024U;
struct CodecDeleter { void operator()(AVCodecContext* p) const { if (p) avcodec_free_context(&p); } };
struct FrameDeleter { void operator()(AVFrame* p) const { if (p) av_frame_free(&p); } };
struct PacketDeleter { void operator()(AVPacket* p) const { if (p) av_packet_free(&p); } };
struct ScaleDeleter { void operator()(SwsContext* p) const { if (p) sws_freeContext(p); } };
uint64_t read_u64(const uint8_t* p) {
  uint64_t v = 0;
  for (size_t i = 0; i < 8; ++i) v = (v << 8U) | p[i];
  return v;
}
uint32_t read_u32(const uint8_t* p) {
  return (static_cast<uint32_t>(p[0]) << 24U) |
         (static_cast<uint32_t>(p[1]) << 16U) |
         (static_cast<uint32_t>(p[2]) << 8U) | p[3];
}
class VectorMediaTransport final : public MediaTransport {
 public:
  bool submit_test_packet(const std::vector<uint8_t>& packet) override {
    if (closed_ || queued_ || packet.size() > kMaxPayload + 15U) return false;
    packet_ = packet;
    queued_ = true;
    return true;
  }
  bool read_packet(std::vector<uint8_t>& packet) override {
    if (closed_ || !queued_) return false;
    packet.swap(packet_);
    queued_ = false;
    return true;
  }
  void close() override { closed_ = true; queued_ = false; packet_.clear(); }
 private:
  bool closed_ = false;
  bool queued_ = false;
  std::vector<uint8_t> packet_;
};
}

struct ReceiverGeneration::Stream {
  StreamType type;
  uint16_t id;
  StreamState state = StreamState::Configuring;
  bool listener = true;
  std::unique_ptr<MediaTransport> transport;
  std::unique_ptr<SecurityProvider> security;
  std::unique_ptr<AVCodecContext, CodecDeleter> codec;
  std::unique_ptr<AVFrame, FrameDeleter> decoded;
  std::unique_ptr<AVPacket, PacketDeleter> packet;
  std::unique_ptr<SwsContext, ScaleDeleter> scaler;
  std::shared_ptr<FrameSink> sink;
  size_t retained_frames = 0;
  Stream(StreamType t, uint16_t connection_id, std::shared_ptr<FrameSink> output,
         bool test_mode) : type(t), id(connection_id), sink(std::move(output)) {
    transport = std::make_unique<VectorMediaTransport>();
    if (type == StreamType::Type110) {
      security = test_mode ? std::unique_ptr<SecurityProvider>(std::make_unique<TestPrimarySecurityProvider>())
                           : std::unique_ptr<SecurityProvider>(std::make_unique<FailClosedPrimarySecurityProvider>());
    } else {
      security = test_mode ? std::unique_ptr<SecurityProvider>(std::make_unique<TestSecondarySecurityProvider>())
                           : std::unique_ptr<SecurityProvider>(std::make_unique<FailClosedSecondarySecurityProvider>());
    }
    const AVCodec* decoder = avcodec_find_decoder(AV_CODEC_ID_H264);
    if (!decoder) throw std::runtime_error("h264 decoder unavailable");
    codec.reset(avcodec_alloc_context3(decoder));
    if (!codec) throw std::bad_alloc();
    codec->max_pixels = 4096LL * 4096LL;
    codec->thread_count = 1;
    if (avcodec_open2(codec.get(), decoder, nullptr) < 0) throw std::runtime_error("decoder open failed");
    decoded.reset(av_frame_alloc());
    packet.reset(av_packet_alloc());
    if (!decoded || !packet) throw std::bad_alloc();
    state = StreamState::Active;
  }
  ~Stream() {
    state = StreamState::Closing;
    if (sink) sink->clear(0);
    scaler.reset();
    packet.reset();
    decoded.reset();
    codec.reset();
    security.reset();
    if (transport) transport->close();
    transport.reset();
    listener = false;
    state = StreamState::Closed;
  }
};

bool TestPrimarySecurityProvider::open_test_media(const std::vector<uint8_t>& input,
                                                   std::vector<uint8_t>& clear) {
  if (input.empty() || input.size() > kMaxPayload) return false;
  clear = input;
  return true;
}
bool TestSecondarySecurityProvider::open_test_media(const std::vector<uint8_t>& input,
                                                     std::vector<uint8_t>& clear) {
  if (input.empty() || input.size() > kMaxPayload) return false;
  clear = input;
  return true;
}
bool FailClosedPrimarySecurityProvider::open_test_media(const std::vector<uint8_t>&,
                                                         std::vector<uint8_t>&) { return false; }
bool FailClosedSecondarySecurityProvider::open_test_media(const std::vector<uint8_t>&,
                                                           std::vector<uint8_t>&) { return false; }

ReceiverGeneration::ReceiverGeneration(uint64_t generation,
    std::shared_ptr<FrameSink> display0, std::shared_ptr<FrameSink> display1,
    const std::shared_ptr<AuthenticationAuthority>& authority) : generation_(generation), display0_(std::move(display0)),
    display1_(std::move(display1)), test_mode_(false) {
  if (!generation_ || !display0_ || !display1_)
    throw std::invalid_argument("invalid generation/output");
  const bool authenticated = authority && authority->authenticate(generation_);
  test_mode_ = authenticated && authority->synthetic_test_authority();
  state_ = authenticated ? SessionState::Authenticated : SessionState::Idle;
  events_.push_back(test_mode_ ? "SESSION_AUTHENTICATED_MODEL_ONLY" :
      (authenticated ? "SESSION_AUTHORITY_ACCEPTED" : "AUTHORITY_UNAVAILABLE_FAIL_CLOSED"));
}
ReceiverGeneration::~ReceiverGeneration() { close(); }

bool ReceiverGeneration::exchange_info(uint64_t generation) {
  std::lock_guard<std::mutex> lock(mutex_);
  if (generation != generation_ || state_ != SessionState::Authenticated) return false;
  state_ = SessionState::InfoExchanged;
  events_.push_back("INFO_EXCHANGED_MODEL_ONLY");
  return true;
}

bool ReceiverGeneration::setup(uint64_t generation, const std::vector<StreamConfig>& configs) {
  std::lock_guard<std::mutex> lock(mutex_);
  if (generation != generation_ ||
      (state_ != SessionState::InfoExchanged && state_ != SessionState::Active) || configs.empty()) return false;
  std::vector<uint16_t> ids;
  for (const auto& config : configs) {
    if (config.type != StreamType::Type110 && config.type != StreamType::Type111) return false;
    if (!config.connection_id || std::find(ids.begin(), ids.end(), config.connection_id) != ids.end()) return false;
    ids.push_back(config.connection_id);
    if ((primary_ && primary_->id == config.connection_id) ||
        (secondary_ && secondary_->id == config.connection_id)) return false;
    if ((config.type == StreamType::Type110 && primary_) ||
        (config.type == StreamType::Type111 && secondary_)) return false;
  }
  // Per-stream transaction: a failed secondary creation leaves a committed primary intact.
  for (const auto& config : configs) {
    if (config.fail_setup) {
      events_.push_back(config.type == StreamType::Type111 ? "TYPE111_SETUP_FAILED_ISOLATED" : "TYPE110_SETUP_FAILED");
      sync_state();
      return false;
    }
    try {
      auto stream = std::make_unique<Stream>(config.type, config.connection_id,
          config.type == StreamType::Type110 ? display0_ : display1_, test_mode_);
      if (config.type == StreamType::Type110) primary_ = std::move(stream);
      else secondary_ = std::move(stream);
    } catch (...) {
      events_.push_back("SETUP_ROLLED_BACK");
      sync_state();
      return false;
    }
  }
  sync_state();
  events_.push_back("SETUP_COMMITTED");
  return true;
}

bool ReceiverGeneration::decode_and_present(Stream& stream,
    const std::vector<uint8_t>& encrypted, uint64_t timestamp) {
  std::vector<uint8_t> clear;
  if (!stream.security || !stream.security->open_test_media(encrypted, clear) || clear.empty()) return false;
  if (clear.size() > static_cast<size_t>(std::numeric_limits<int>::max()) ||
      av_new_packet(stream.packet.get(), static_cast<int>(clear.size())) < 0) return false;
  std::copy(clear.begin(), clear.end(), stream.packet->data);
  stream.packet->pts = static_cast<int64_t>(timestamp);
  if (avcodec_send_packet(stream.codec.get(), stream.packet.get()) < 0) { av_packet_unref(stream.packet.get()); return false; }
  av_packet_unref(stream.packet.get());
  bool presented = false;
  while (avcodec_receive_frame(stream.codec.get(), stream.decoded.get()) == 0) {
        const int width = stream.decoded->width, height = stream.decoded->height;
        if (width < 1 || height < 1 || width > 4096 || height > 4096 ||
            static_cast<uint64_t>(width) * static_cast<uint64_t>(height) > 4096ULL * 4096ULL) return false;
        stream.scaler.reset(sws_getCachedContext(stream.scaler.release(), width, height,
            static_cast<AVPixelFormat>(stream.decoded->format), width, height, AV_PIX_FMT_RGBA,
            SWS_BILINEAR, nullptr, nullptr, nullptr));
        if (!stream.scaler) return false;
        Frame frame{stream.type, generation_, timestamp, static_cast<uint32_t>(width),
                    static_cast<uint32_t>(height), static_cast<uint32_t>(width * 4), {}};
        const uint64_t bytes = static_cast<uint64_t>(frame.stride) * frame.height;
        if (bytes > 64ULL * 1024ULL * 1024ULL) return false;
        frame.rgba.resize(static_cast<size_t>(bytes));
        uint8_t* planes[4] = {frame.rgba.data(), nullptr, nullptr, nullptr};
        int strides[4] = {static_cast<int>(frame.stride), 0, 0, 0};
        const int converted_lines = sws_scale(stream.scaler.get(), stream.decoded->data,
            stream.decoded->linesize, 0, height, planes, strides);
        if (converted_lines != height) return false;
        if (stream.state != StreamState::Active || !stream.sink || !stream.sink->present(frame)) return false;
        presented = true;
    av_frame_unref(stream.decoded.get());
  }
  return presented;
}

bool ReceiverGeneration::ingest(uint64_t generation, uint16_t id,
    const std::vector<uint8_t>& packet, uint64_t timestamp) {
  std::lock_guard<std::mutex> lock(mutex_);
  if (generation != generation_ || (state_ != SessionState::Active)) return false;
  uint64_t packet_generation = 0;
  StreamType type{};
  uint16_t packet_id = 0;
  std::vector<uint8_t> payload;
  MediaFramer framer;
  Stream* stream = nullptr;
  if (primary_ && primary_->id == id) stream = primary_.get();
  if (secondary_ && secondary_->id == id) stream = secondary_.get();
  if (!stream || !stream->transport || !stream->transport->submit_test_packet(packet)) return false;
  std::vector<uint8_t> received;
  if (!stream->transport->read_packet(received) || !framer.parse(received, packet_generation, type, packet_id, payload) ||
      packet_generation != generation_ || packet_id != id) return false;
  if ((type != StreamType::Type110 && type != StreamType::Type111) ||
      (type == StreamType::Type110 && stream != primary_.get()) ||
      (type == StreamType::Type111 && stream != secondary_.get())) return false;
  return stream->state == StreamState::Active && stream->id == id &&
      decode_and_present(*stream, payload, timestamp);
}

void ReceiverGeneration::close_stream(StreamType type) {
  std::lock_guard<std::mutex> lock(mutex_);
  if (type == StreamType::Type110) primary_.reset(); else if (type == StreamType::Type111) secondary_.reset();
  sync_state();
}
void ReceiverGeneration::close() {
  std::lock_guard<std::mutex> lock(mutex_);
  if (state_ == SessionState::Closed) return;
  state_ = SessionState::Closing;
  secondary_.reset();
  primary_.reset();
  display0_->clear(generation_);
  display1_->clear(generation_);
  state_ = SessionState::Closed;
  events_.push_back("SESSION_CLOSED");
}
void ReceiverGeneration::sync_state() {
  state_ = primary_ || secondary_ ? SessionState::Active : SessionState::InfoExchanged;
}
SessionState ReceiverGeneration::state() const { std::lock_guard<std::mutex> l(mutex_); return state_; }
ResourceCounts ReceiverGeneration::resources() const {
  std::lock_guard<std::mutex> l(mutex_);
  const auto count = [](const Stream* stream, bool owned) -> std::size_t {
    return stream && owned ? 1U : 0U;
  };
  const std::size_t listeners = count(primary_.get(), primary_ && primary_->listener && primary_->transport) +
                                count(secondary_.get(), secondary_ && secondary_->listener && secondary_->transport);
  const std::size_t security = count(primary_.get(), primary_ && primary_->security) +
                               count(secondary_.get(), secondary_ && secondary_->security);
  const std::size_t decoders = count(primary_.get(), primary_ && primary_->codec && primary_->decoded && primary_->packet) +
                               count(secondary_.get(), secondary_ && secondary_->codec && secondary_->decoded && secondary_->packet);
  return {(state_ == SessionState::Authenticated || state_ == SessionState::InfoExchanged ||
           state_ == SessionState::Active || state_ == SessionState::Closing) ? 1U : 0U,
    listeners, security, decoders, 0, listeners};
}
std::vector<std::string> ReceiverGeneration::events() const { std::lock_guard<std::mutex> l(mutex_); return events_; }

bool parse_media_packet(const std::vector<uint8_t>& bytes, uint64_t& generation,
    StreamType& type, uint16_t& connection_id, std::vector<uint8_t>& payload) {
  constexpr size_t header = 15;
  if (bytes.size() < header) return false;
  const uint8_t raw_type = bytes[8];
  if (raw_type != 110 && raw_type != 111) return false;
  generation = read_u64(bytes.data());
  type = static_cast<StreamType>(raw_type);
  connection_id = static_cast<uint16_t>((bytes[9] << 8U) | bytes[10]);
  const uint32_t length = read_u32(bytes.data() + 11);
  if (!generation || !connection_id || !length || length > kMaxPayload ||
      static_cast<size_t>(length) != bytes.size() - header) return false;
  payload.assign(bytes.begin() + header, bytes.end());
  return true;
}
bool MediaFramer::parse(const std::vector<uint8_t>& bytes, uint64_t& generation,
    StreamType& type, uint16_t& connection_id, std::vector<uint8_t>& payload) const {
  return parse_media_packet(bytes, generation, type, connection_id, payload);
}
bool MemoryFrameSink::present(const Frame& frame) noexcept {
  if (!available || frame.rgba.empty() || frame.rgba.size() != static_cast<size_t>(frame.stride) * frame.height) return false;
  try { frames_.push_back(frame); } catch (...) { return false; }
  cleared_ = false;
  return true;
}
void MemoryFrameSink::clear(uint64_t) noexcept { frames_.clear(); cleared_ = true; }
}  // namespace claritylink
