#include "claritylink/receiver.hpp"

#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <thread>

using namespace claritylink;
namespace {
void require(bool value, const char* message) { if (!value) throw std::runtime_error(message); }
std::shared_ptr<AuthenticationAuthority> synthetic_authority() {
  return std::make_shared<SyntheticTestAuthenticationAuthority>();
}
std::vector<uint8_t> read_file(const char* path) {
  std::ifstream f(path, std::ios::binary);
  if (!f) throw std::runtime_error(std::string("fixture missing: ") + path);
  return std::vector<uint8_t>(std::istreambuf_iterator<char>(f), {});
}
std::vector<uint8_t> packet(uint64_t generation, StreamType type, uint16_t id,
                            const std::vector<uint8_t>& payload) {
  std::vector<uint8_t> result;
  for (int shift = 56; shift >= 0; shift -= 8) result.push_back(static_cast<uint8_t>(generation >> shift));
  result.push_back(static_cast<uint8_t>(type));
  result.push_back(static_cast<uint8_t>(id >> 8)); result.push_back(static_cast<uint8_t>(id));
  const uint32_t n = static_cast<uint32_t>(payload.size());
  result.push_back(static_cast<uint8_t>(n >> 24)); result.push_back(static_cast<uint8_t>(n >> 16));
  result.push_back(static_cast<uint8_t>(n >> 8)); result.push_back(static_cast<uint8_t>(n));
  result.insert(result.end(), payload.begin(), payload.end());
  return result;
}
void verify_pair(uint64_t generation, const std::vector<StreamConfig>& order,
                 uint16_t primary_id, uint16_t secondary_id,
                 const std::vector<uint8_t>& red, const std::vector<uint8_t>& blue) {
  auto d0 = std::make_shared<MemoryFrameSink>(); auto d1 = std::make_shared<MemoryFrameSink>();
  ReceiverGeneration receiver(generation, d0, d1, synthetic_authority());
  require(receiver.exchange_info(generation), "info exchange");
  require(receiver.setup(generation, order), "dual setup");
  auto p110 = packet(generation, StreamType::Type110, primary_id, red);
  auto p111 = packet(generation, StreamType::Type111, secondary_id, blue);
  bool a = false, b = false;
  std::thread t0([&] { a = receiver.ingest(generation, primary_id, p110, 100); });
  std::thread t1([&] { b = receiver.ingest(generation, secondary_id, p111, 200); });
  t0.join(); t1.join();
  require(a && b, "both decoders present a frame");
  require(d0->frames().size() == 1 && d1->frames().size() == 1, "independent sinks");
  const Frame& f0 = d0->frames().front(); const Frame& f1 = d1->frames().front();
  require(f0.stream == StreamType::Type110 && f1.stream == StreamType::Type111, "stream association");
  require(f0.generation == generation && f1.generation == generation, "generation association");
  require(f0.width == 32 && f0.height == 24 && f1.width == 32 && f1.height == 24, "decoded dimensions");
  require(f0.rgba != f1.rgba, "distinct frame content");
  receiver.close(); receiver.close();
  require(receiver.resources().sessions == 0 && receiver.resources().listeners == 0 &&
          receiver.resources().security_contexts == 0 && receiver.resources().decoders == 0,
          "resources released");
  require(d0->frames().empty() && d1->frames().empty(), "frames cleared");
  require(!receiver.ingest(generation, primary_id, p110, 300), "post-close media rejected");
}
}
int main(int argc, char** argv) {
  try {
    if (argc != 5) throw std::runtime_error("usage: receiver_test TYPE110.h264 TYPE111.h264 PRIMARY_ID SECONDARY_ID");
    auto red = read_file(argv[1]); auto blue = read_file(argv[2]);
    const unsigned long primary_value = std::stoul(argv[3]);
    const unsigned long secondary_value = std::stoul(argv[4]);
    if (!primary_value || primary_value > 65535 || !secondary_value || secondary_value > 65535)
      throw std::runtime_error("invalid vector connection ID");
    const auto primary_id = static_cast<uint16_t>(primary_value);
    const auto secondary_id = static_cast<uint16_t>(secondary_value);
    verify_pair(1, {{StreamType::Type111, secondary_id}, {StreamType::Type110, primary_id}}, primary_id, secondary_id, red, blue);
    verify_pair(2, {{StreamType::Type110, primary_id}, {StreamType::Type111, secondary_id}}, primary_id, secondary_id, red, blue);

    auto d0 = std::make_shared<MemoryFrameSink>(); auto d1 = std::make_shared<MemoryFrameSink>();
    ReceiverGeneration isolated(3, d0, d1, synthetic_authority());
    require(isolated.exchange_info(3), "isolation info");
    require(!isolated.setup(3, {{StreamType::Type110, primary_id}, {StreamType::Type111, secondary_id, true}}), "secondary failure surfaced");
    require(isolated.state() == SessionState::Active, "primary survives secondary setup failure");
    require(isolated.ingest(3, primary_id, packet(3, StreamType::Type110, primary_id, red), 1), "primary works");
    require(!isolated.ingest(3, secondary_id, packet(3, StreamType::Type111, secondary_id, blue), 1), "failed secondary absent");
    require(!isolated.ingest(2, primary_id, packet(3, StreamType::Type110, primary_id, red), 2), "stale generation rejected");
    require(!isolated.ingest(3, primary_id, packet(2, StreamType::Type110, primary_id, red), 2), "wrong packet generation rejected");
    isolated.close_stream(StreamType::Type111); isolated.close();

    // Independent single-stream configurations and invalid duplicate ownership.
    for (StreamType only : {StreamType::Type110, StreamType::Type111}) {
      auto s0 = std::make_shared<MemoryFrameSink>(); auto s1 = std::make_shared<MemoryFrameSink>();
      ReceiverGeneration single(20 + static_cast<uint8_t>(only), s0, s1, synthetic_authority());
      const uint64_t g = single.generation();
      require(single.exchange_info(g), "single info");
      require(single.setup(g, {{only, only == StreamType::Type110 ? primary_id : secondary_id}}), "single setup");
      const auto& media = only == StreamType::Type110 ? red : blue;
      const uint16_t id = only == StreamType::Type110 ? primary_id : secondary_id;
      require(single.ingest(g, id, packet(g, only, id, media), 1), "single stream decode");
      require((only == StreamType::Type110 ? s0 : s1)->frames().size() == 1, "single output association");
      single.close();
    }
    auto dup0 = std::make_shared<MemoryFrameSink>(); auto dup1 = std::make_shared<MemoryFrameSink>();
    ReceiverGeneration duplicate(30, dup0, dup1, synthetic_authority()); duplicate.exchange_info(30);
    require(!duplicate.setup(30, {{StreamType::Type110, 44}, {StreamType::Type111, 44}}), "duplicate id rejected");
    require(duplicate.resources().listeners == 0, "duplicate setup left no listener"); duplicate.close();
    auto fail0 = std::make_shared<MemoryFrameSink>(); auto fail1 = std::make_shared<MemoryFrameSink>();
    ReceiverGeneration failed_primary(31, fail0, fail1, synthetic_authority()); failed_primary.exchange_info(31);
    require(!failed_primary.setup(31, {{StreamType::Type110, primary_id, true}}), "primary setup failure");
    require(failed_primary.resources().listeners == 0, "primary rollback released resources"); failed_primary.close();
    auto gone0 = std::make_shared<MemoryFrameSink>(); auto gone1 = std::make_shared<MemoryFrameSink>();
    ReceiverGeneration listener(32, gone0, gone1, synthetic_authority()); listener.exchange_info(32);
    require(listener.setup(32, {{StreamType::Type110, primary_id}, {StreamType::Type111, secondary_id}}), "listener setup");
    listener.close_stream(StreamType::Type111);
    require(listener.ingest(32, primary_id, packet(32, StreamType::Type110, primary_id, red), 1), "primary survives secondary listener disconnect");
    require(!listener.ingest(32, secondary_id, packet(32, StreamType::Type111, secondary_id, blue), 1), "closed secondary listener rejects input");
    listener.close();
    auto dead0 = std::make_shared<MemoryFrameSink>(); auto dead1 = std::make_shared<MemoryFrameSink>();
    dead1->available = false;
    ReceiverGeneration display_loss(33, dead0, dead1, synthetic_authority()); display_loss.exchange_info(33);
    require(display_loss.setup(33, {{StreamType::Type110, primary_id}, {StreamType::Type111, secondary_id}}), "display loss setup");
    require(!display_loss.ingest(33, secondary_id, packet(33, StreamType::Type111, secondary_id, blue), 1), "unavailable secondary rejects frame");
    require(display_loss.ingest(33, primary_id, packet(33, StreamType::Type110, primary_id, red), 2), "primary survives secondary output loss");
    display_loss.close();
    auto race0 = std::make_shared<MemoryFrameSink>(); auto race1 = std::make_shared<MemoryFrameSink>();
    ReceiverGeneration racing(34, race0, race1, synthetic_authority()); racing.exchange_info(34);
    require(racing.setup(34, {{StreamType::Type110, primary_id}}), "race setup");
    auto race_packet = packet(34, StreamType::Type110, primary_id, red);
    std::thread receiving([&] { (void)racing.ingest(34, primary_id, race_packet, 1); });
    std::thread closing([&] { racing.close(); });
    receiving.join(); closing.join();
    require(racing.resources().sessions == 0 && race0->frames().empty(), "concurrent disconnect clears delivered frame");

    uint64_t gen; uint16_t id; StreamType type; std::vector<uint8_t> payload;
    for (const auto& bad : {std::vector<uint8_t>{}, std::vector<uint8_t>(14, 0),
         std::vector<uint8_t>{0,0,0,0,0,0,0,1,110,0,1,0xff,0xff,0xff,0xff}})
      require(!parse_media_packet(bad, gen, type, id, payload), "malformed packet rejected");
    auto unknown_type = packet(4, StreamType::Type110, primary_id, red); unknown_type[8] = 112;
    require(!parse_media_packet(unknown_type, gen, type, id, payload), "unknown stream type rejected");
    auto huge = packet(4, StreamType::Type110, primary_id, std::vector<uint8_t>(2U * 1024U * 1024U + 1U, 0));
    require(!parse_media_packet(huge, gen, type, id, payload), "oversized media payload rejected");
    auto malformed = packet(4, StreamType::Type110, primary_id, std::vector<uint8_t>{0,0,1,0xff});
    auto m0 = std::make_shared<MemoryFrameSink>(); auto m1 = std::make_shared<MemoryFrameSink>();
    ReceiverGeneration parser(4, m0, m1, synthetic_authority()); parser.exchange_info(4);
    require(parser.setup(4, {{StreamType::Type110, primary_id}}), "single primary setup");
    require(!parser.ingest(4, primary_id, malformed, 1), "decoder rejects malformed media"); parser.close();

    for (uint64_t cycle = 1; cycle <= 100; ++cycle)
      verify_pair(1000 + cycle, {{StreamType::Type110, primary_id}, {StreamType::Type111, secondary_id}}, primary_id, secondary_id, red, blue);
    // Fail-closed production mode must not silently accept test media as plaintext.
    auto q0 = std::make_shared<MemoryFrameSink>(); auto q1 = std::make_shared<MemoryFrameSink>();
    ReceiverGeneration production(9000, q0, q1, std::make_shared<UnavailableAuthenticationAuthority>());
    require(!production.exchange_info(9000), "missing production authentication rejected");
    require(!production.setup(9000, {{StreamType::Type110, primary_id}}), "unauthenticated setup rejected");
    require(production.resources().sessions == 0, "unauthenticated session not counted active");
    std::vector<uint8_t> clear;
    FailClosedPrimarySecurityProvider psecurity;
    FailClosedSecondarySecurityProvider ssecurity;
    require(!psecurity.open_test_media(red, clear) && !ssecurity.open_test_media(blue, clear),
            "production media security fails closed");
    production.close();
    std::cout << "NATIVE_R7B_PASS dual_orderings=2 secondary_isolation=PASS decoded_per_sink=102 cycles=100 malformed=PASS production_security=FAIL_CLOSED resources=0\n";
    return 0;
  } catch (const std::exception& e) {
    std::cerr << "NATIVE_R7B_FAIL " << e.what() << "\n";
    return 1;
  }
}
