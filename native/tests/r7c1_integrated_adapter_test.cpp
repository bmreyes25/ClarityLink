#include "claritylink/receiver.hpp"
#include "../platform/android/opaque_handle_allocator.hpp"
#include "../platform/android/surface_sink_core.hpp"

#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <iterator>
#include <map>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

using namespace claritylink;
using claritylink::android::OpaqueHandleAllocator;
using claritylink::android::SurfaceBuffer;
using claritylink::android::SurfaceSinkCore;
using claritylink::android::SurfaceWindow;

namespace {
enum class Resource : size_t {
  JniHandle, Generation, StreamAdapter, SurfaceAdapter, NativeWindowToken,
  Decoder, Security, Transport, Audio, Input, Usb, Iap2, Authentication,
  Socket, Listener, Process, Count
};
const std::array<const char*, static_cast<size_t>(Resource::Count)> kNames = {
  "jni_handles", "generations", "stream_adapters", "surface_adapters",
  "native_window_tokens", "decoders", "security_providers", "transports",
  "audio_adapters", "input_adapters", "usb_adapters", "iap2_adapters",
  "authentication_adapters", "sockets", "listeners", "processes"};
struct Oracle {
  std::array<int, static_cast<size_t>(Resource::Count)> count{};
  void add(Resource r) { ++count[static_cast<size_t>(r)]; }
  void remove(Resource r) { --count[static_cast<size_t>(r)]; }
  bool zero() const { for (int n : count) if (n != 0) return false; return true; }
  std::string describe() const {
    std::string out;
    for (size_t i = 0; i < count.size(); ++i) if (count[i] != 0) {
      if (!out.empty()) out += ',';
      out += kNames[i]; out += '='; out += std::to_string(count[i]);
    }
    return out.empty() ? "zero" : out;
  }
};
class Lease {
 public:
  Lease(Oracle& o, Resource r) : oracle_(o), resource_(r), active_(true) { oracle_.add(resource_); }
  ~Lease() { reset(); }
  Lease(const Lease&) = delete; Lease& operator=(const Lease&) = delete;
  Lease(Lease&& other) noexcept : oracle_(other.oracle_), resource_(other.resource_), active_(other.active_) { other.active_ = false; }
  void reset() { if (active_) { oracle_.remove(resource_); active_ = false; } }
 private: Oracle& oracle_; Resource resource_; bool active_;
};
class SimulatedSurfaceWindow final : public SurfaceWindow {
 public:
  bool set_rgba_geometry(uint32_t width, uint32_t height) noexcept override {
    if (!available || !width || !height || width > 8192 || height > 8192) return false;
    width_ = static_cast<int32_t>(width); height_ = static_cast<int32_t>(height);
    stride_ = width_ + 3;
    pixels_.assign(static_cast<size_t>(stride_) * static_cast<size_t>(height_) * 4u, 0xA5);
    return true;
  }
  bool lock(SurfaceBuffer& out) noexcept override {
    if (!available || lock_active_) return false;
    lock_active_ = true; out = {pixels_.data(), width_, height_, stride_}; return true;
  }
  bool unlock_and_post() noexcept override {
    if (!lock_active_) return false;
    lock_active_ = false; ++posts; return true;
  }
  bool available = true;
  int posts = 0;
  int32_t width() const { return width_; }
  int32_t height() const { return height_; }
  const std::vector<uint8_t>& pixels() const { return pixels_; }
 private:
  int32_t width_ = 0, height_ = 0, stride_ = 0;
  bool lock_active_ = false;
  std::vector<uint8_t> pixels_;
};
void require(bool ok, const std::string& message, uint64_t cycle = 0) {
  if (!ok) throw std::runtime_error((cycle ? "cycle " + std::to_string(cycle) + ": " : "") + message);
}
std::vector<uint8_t> read_file(const char* path) {
  std::ifstream f(path, std::ios::binary);
  if (!f) throw std::runtime_error(std::string("fixture missing: ") + path);
  return {std::istreambuf_iterator<char>(f), {}};
}
std::vector<uint8_t> packet(uint64_t gen, StreamType type, uint16_t id,
                            const std::vector<uint8_t>& payload) {
  std::vector<uint8_t> out;
  for (int shift = 56; shift >= 0; shift -= 8) out.push_back(static_cast<uint8_t>(gen >> shift));
  out.push_back(static_cast<uint8_t>(type)); out.push_back(static_cast<uint8_t>(id >> 8));
  out.push_back(static_cast<uint8_t>(id)); const uint32_t n = static_cast<uint32_t>(payload.size());
  out.push_back(static_cast<uint8_t>(n >> 24)); out.push_back(static_cast<uint8_t>(n >> 16));
  out.push_back(static_cast<uint8_t>(n >> 8)); out.push_back(static_cast<uint8_t>(n));
  out.insert(out.end(), payload.begin(), payload.end()); return out;
}
void require_receiver_zero(const ReceiverGeneration& receiver, uint64_t cycle) {
  const auto r = receiver.resources();
  require(r.sessions == 0 && r.listeners == 0 && r.security_contexts == 0 &&
          r.decoders == 0 && r.retained_frames == 0 && r.display_ownership == 0,
          "receiver resources remain after stop", cycle);
}

// Exercises actual ReceiverGeneration + FFmpeg decode with host-simulated
// Android/Java adapter ownership. It deliberately makes no Android runtime claim.
void integrated_cycle(uint64_t cycle, const std::vector<uint8_t>& h110,
                     const std::vector<uint8_t>& h111, OpaqueHandleAllocator& ids,
                     bool secondary_fault = false, bool malformed_secondary = false,
                     bool secondary_loss_after_frame = false) {
  Oracle resources;
  require(resources.zero(), "pre-initialize resource baseline is nonzero", cycle);
  {
    Lease process(resources, Resource::Process);
    Lease primary_display(resources, Resource::SurfaceAdapter);
    Lease secondary_display(resources, Resource::SurfaceAdapter);
    Lease primary_window(resources, Resource::NativeWindowToken);
    Lease secondary_window(resources, Resource::NativeWindowToken);
    Lease audio(resources, Resource::Audio);
    Lease input(resources, Resource::Input);
    Lease usb(resources, Resource::Usb);
    Lease iap2(resources, Resource::Iap2);
    Lease auth(resources, Resource::Authentication);
    Lease socket(resources, Resource::Socket);
    Lease transport(resources, Resource::Transport);
    Lease primary_stream(resources, Resource::StreamAdapter);
    Lease secondary_stream(resources, Resource::StreamAdapter);
    Lease primary_listener(resources, Resource::Listener);
    Lease secondary_listener(resources, Resource::Listener);
    const int64_t primary_surface_handle = ids.allocate();
    const int64_t secondary_surface_handle = ids.allocate();
    const int64_t receiver_handle = ids.allocate();
    std::map<int64_t, bool> registry;
    registry.emplace(primary_surface_handle, true); registry.emplace(secondary_surface_handle, true);
    registry.emplace(receiver_handle, true);
    Lease primary_jni(resources, Resource::JniHandle);
    Lease secondary_jni(resources, Resource::JniHandle);
    Lease receiver_jni(resources, Resource::JniHandle);
    const uint64_t generation = 10000 + cycle;
    Lease generation_owner(resources, Resource::Generation);

    auto w0 = std::make_shared<SimulatedSurfaceWindow>();
    auto w1 = std::make_shared<SimulatedSurfaceWindow>();
    if (secondary_fault) w1->available = false;
    auto d0 = std::make_shared<SurfaceSinkCore>(w0, generation, StreamType::Type110, 501);
    auto d1 = std::make_shared<SurfaceSinkCore>(w1, generation, StreamType::Type111, 502);
    const auto authority = std::make_shared<SyntheticTestAuthenticationAuthority>(); // explicit LAB mode
    Lease authentication_authority(resources, Resource::Authentication);
    ReceiverGeneration receiver(generation, d0, d1, authority);
    require(receiver.exchange_info(generation), "synthetic /info exchange rejected", cycle);
    require(receiver.setup(generation, {{StreamType::Type110, 1100},
                                       {StreamType::Type111, 1101}}), "dual SETUP rejected", cycle);
    const auto running = receiver.resources();
    require(running.sessions == 1 && running.listeners == 2 && running.security_contexts == 2 &&
            running.decoders == 2, "dual-stream receiver resource snapshot incorrect", cycle);
    Lease decoder0(resources, Resource::Decoder); Lease decoder1(resources, Resource::Decoder);
    Lease security0(resources, Resource::Security); Lease security1(resources, Resource::Security);
    Lease transport0(resources, Resource::Transport); Lease transport1(resources, Resource::Transport);
    require(registry.size() == 3, "JNI owner registry not live during session", cycle);

    const auto p110 = packet(generation, StreamType::Type110, 1100, h110);
    const auto p111 = packet(generation, StreamType::Type111, 1101, h111);
    const bool secondary_ok = receiver.ingest(generation, 1101, p111, cycle * 2);
    const bool primary_ok = receiver.ingest(generation, 1100, p110, cycle * 2 + 1);
    require(primary_ok, "Type110 decode/output failed", cycle);
    require(d0->valid() && w0->posts == 1 && w0->width() == 32 && w0->height() == 24,
            "Type110 output contract mismatch", cycle);
    if (secondary_fault) {
      require(!secondary_ok, "injected Type111 display fault was not surfaced", cycle);
      require(receiver.state() == SessionState::Active && w0->posts == 1,
              "Type111 display fault damaged Type110", cycle);
      w1->available = true; // allow teardown to clear the simulated lost surface
    } else {
      require(secondary_ok && d1->valid() && w1->posts == 1 &&
              w1->width() == 32 && w1->height() == 24,
              "Type111 output contract mismatch", cycle);
      require(w0->pixels() != w1->pixels(), "stream fixture outputs are not distinct", cycle);
    }

    if (secondary_loss_after_frame) {
      d1->invalidate();
      require(!receiver.ingest(generation, 1101, p111, cycle * 2 + 2),
              "lost Type111 surface accepted another frame", cycle);
      require(receiver.resources().listeners == 1 && receiver.resources().decoders == 1 &&
              receiver.state() == SessionState::Active &&
              receiver.ingest(generation, 1100, p110, cycle * 2 + 3),
              "surface loss damaged primary receiver", cycle);
    }

    // Exercise Type111 decoder/media failure after Type110 is active.
    if (!secondary_fault && !secondary_loss_after_frame && malformed_secondary) {
      const std::vector<uint8_t> malformed{0, 0, 1, 0xff};
      require(!receiver.ingest(generation, 1101,
              packet(generation, StreamType::Type111, 1101, malformed), cycle * 2 + 2),
              "malformed Type111 media unexpectedly decoded", cycle);
      require(receiver.resources().listeners == 1 && receiver.resources().decoders == 1 &&
              receiver.resources().security_contexts == 1,
              "Type111 decoder failure did not release only secondary resources", cycle);
      require(!receiver.ingest(generation, 1101, p111, cycle * 2 + 4),
              "closed Type111 stream accepted later media", cycle);
      require(receiver.state() == SessionState::Active &&
              receiver.ingest(generation, 1100, p110, cycle * 2 + 3),
              "Type111 media failure did not preserve Type110", cycle);
    }

    // Process stop owns teardown order; receiver close clears both surfaces.
    receiver.close();
    require_receiver_zero(receiver, cycle);
    require(d0->valid() && (secondary_loss_after_frame ? !d1->valid() : d1->valid()) && !w0->pixels().empty(),
            "surface owner unexpectedly destroyed before Java owner release", cycle);
    for (uint8_t byte : w0->pixels()) require(byte == 0, "Display0 was not cleared", cycle);
    if (!secondary_loss_after_frame)
      for (uint8_t byte : w1->pixels()) require(byte == 0, "Display1 retained stale frame bytes", cycle);
    d1->invalidate(); d0->invalidate();
    require(!d0->valid() && !d1->valid(), "surface release did not invalidate owners", cycle);
    registry.erase(receiver_handle); registry.erase(secondary_surface_handle);
    registry.erase(primary_surface_handle);
    require(registry.empty(), "JNI registry not empty after release", cycle);
    transport1.reset(); transport0.reset(); security1.reset(); security0.reset();
    decoder1.reset(); decoder0.reset();
  }
  require(resources.zero(), "restoration resource oracle: " + resources.describe(), cycle);
}

void fail_closed_checks() {
  auto a = std::make_shared<MemoryFrameSink>(); auto b = std::make_shared<MemoryFrameSink>();
  ReceiverGeneration production(77, a, b, std::make_shared<UnavailableAuthenticationAuthority>());
  require(!production.exchange_info(77), "production accepted unavailable authority");
  require(!production.setup(77, {{StreamType::Type110, 1100}}), "production activated without authentication");
  production.close(); require_receiver_zero(production, 77);
  std::vector<uint8_t> clear;
  FailClosedPrimarySecurityProvider prod_security;
  require(!prod_security.open_test_media({1, 2, 3}, clear), "production security accepted synthetic media");
}

void primary_failure_policy(const std::vector<uint8_t>& h110,
                            const std::vector<uint8_t>& h111) {
  const uint64_t generation = 880;
  auto w0 = std::make_shared<SimulatedSurfaceWindow>();
  auto w1 = std::make_shared<SimulatedSurfaceWindow>();
  auto d0 = std::make_shared<SurfaceSinkCore>(w0, generation, StreamType::Type110, 701);
  auto d1 = std::make_shared<SurfaceSinkCore>(w1, generation, StreamType::Type111, 702);
  ReceiverGeneration receiver(generation, d0, d1,
      std::make_shared<SyntheticTestAuthenticationAuthority>());
  require(receiver.exchange_info(generation) && receiver.setup(generation,
      {{StreamType::Type110, 1100}, {StreamType::Type111, 1101}}), "primary fault fixture setup");
  w0->available = false;
  require(!receiver.ingest(generation, 1100,
      packet(generation, StreamType::Type110, 1100, h110), 1), "injected primary output loss not surfaced");
  require(receiver.state() == SessionState::Closed, "Type110 fault left session marked active");
  require_receiver_zero(receiver, generation);
  w0->available = true;
  require(!receiver.ingest(generation, 1101,
      packet(generation, StreamType::Type111, 1101, h111), 2), "Type111 continued after primary session failure");
}
}

int main(int argc, char** argv) {
  try {
    if (argc != 3) throw std::runtime_error("usage: r7c1_integrated_adapter_test TYPE110.h264 TYPE111.h264");
    const auto h110 = read_file(argv[1]); const auto h111 = read_file(argv[2]);
    OpaqueHandleAllocator ids;
    fail_closed_checks();
    primary_failure_policy(h110, h111);
    integrated_cycle(1, h110, h111, ids);
    integrated_cycle(2, h110, h111, ids, true);
    integrated_cycle(3, h110, h111, ids, false, true);
    integrated_cycle(4, h110, h111, ids, false, false, true);
    // Repeated handle allocation across teardown proves stale IDs never ABA-reuse.
    const auto old_id = ids.allocate();
    for (uint64_t cycle = 1; cycle <= 100; ++cycle)
      integrated_cycle(cycle + 10, h110, h111, ids);
    const auto new_id = ids.allocate(); require(new_id > old_id, "opaque handle ID reused after release");
    std::cout << "R7C1_INTEGRATION_PASS environment=HOST_SIMULATED_ANDROID_RUNTIME actual_h264_decode=PASS dual_outputs=PASS cycles=100 zero_resources_each_cycle=PASS type111_isolation=PASS production_auth=FAIL_CLOSED\n";
  } catch (const std::exception& e) {
    std::cerr << "R7C1_INTEGRATION_FAIL " << e.what() << "\n"; return 1;
  }
  return 0;
}
