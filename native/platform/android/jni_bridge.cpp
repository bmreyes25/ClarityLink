#include "android_surface_sink.hpp"
#include "opaque_handle_allocator.hpp"
#include "android_socket_adapter.hpp"

#include <android/native_window_jni.h>
#include <jni.h>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <set>

namespace {
using claritylink::ReceiverGeneration;
using claritylink::StreamConfig;
using claritylink::StreamType;
using claritylink::SyntheticTestAuthenticationAuthority;
using claritylink::UnavailableAuthenticationAuthority;
using claritylink::android::AndroidSurfaceSink;
std::mutex registry_mutex;
claritylink::android::OpaqueHandleAllocator next_handle;
claritylink::android::OpaqueHandleTable<AndroidSurfaceSink> surfaces(next_handle);
claritylink::android::OpaqueHandleTable<ReceiverGeneration> receivers(next_handle);
std::set<jlong> lab_receivers;

void fail(JNIEnv* env, const char* message) {
  jclass type = env->FindClass("java/lang/IllegalStateException");
  if (type) env->ThrowNew(type, message);
}
bool valid_stream(jint value) { return value == 110 || value == 111; }
}

extern "C" JNIEXPORT jlong JNICALL
Java_org_claritylink_android_NativeBridge_nativeAttachSurface(JNIEnv* env, jclass,
    jobject surface, jlong generation, jint stream, jlong token) try {
  if (!surface || generation <= 0 || token <= 0 || !valid_stream(stream)) {
    fail(env, "invalid surface ownership tuple"); return 0;
  }
  ANativeWindow* window = ANativeWindow_fromSurface(env, surface);
  if (env->ExceptionCheck()) { if(window) ANativeWindow_release(window); return 0; }
  if (!window) { fail(env, "Surface has no native window"); return 0; }
  std::unique_ptr<ANativeWindow, decltype(&ANativeWindow_release)> temporary_window(window, &ANativeWindow_release);
  auto sink = std::make_shared<AndroidSurfaceSink>(window, static_cast<uint64_t>(generation),
      static_cast<StreamType>(stream), static_cast<uint64_t>(token));
  temporary_window.reset(); // sink acquired its own reference
  if (!sink->valid()) { fail(env, "surface sink initialization failed"); return 0; }
  return static_cast<jlong>(surfaces.insert(std::move(sink)));
} catch (...) { fail(env, "native surface attach failed"); return 0; }

extern "C" JNIEXPORT void JNICALL
Java_org_claritylink_android_NativeBridge_nativeReleaseSurface(JNIEnv* env, jclass, jlong id) {
  std::shared_ptr<AndroidSurfaceSink> sink;
  sink = surfaces.erase(id);
  if (!sink) { fail(env, "invalid or released surface handle"); return; }
  sink->invalidate();
}

extern "C" JNIEXPORT void JNICALL
Java_org_claritylink_android_NativeBridge_nativeClearSurface(JNIEnv* env, jclass, jlong id, jlong generation) {
  std::shared_ptr<AndroidSurfaceSink> sink;
  if (generation <= 0 || !(sink = surfaces.get(id))) {
    fail(env,"invalid surface clear request"); return;
  }
  sink->clear(static_cast<uint64_t>(generation));
}

extern "C" JNIEXPORT jlong JNICALL
Java_org_claritylink_android_NativeBridge_nativeCreateReceiver(JNIEnv* env, jclass,
    jlong generation, jlong primary_id, jlong secondary_id, jboolean lab_mode) try {
  if (generation <= 0 || primary_id <= 0) { fail(env, "receiver requires generation and primary surface"); return 0; }
  std::shared_ptr<AndroidSurfaceSink> primary, secondary;
  primary = surfaces.get(primary_id);
  if (!primary) { fail(env, "unknown primary surface handle"); return 0; }
  if (secondary_id != 0) { secondary = surfaces.get(secondary_id); if (!secondary) { fail(env, "unknown secondary surface handle"); return 0; } }
  if (!primary->matches(static_cast<uint64_t>(generation), StreamType::Type110) ||
      (secondary && !secondary->matches(static_cast<uint64_t>(generation), StreamType::Type111))) {
    fail(env, "surface generation or stream does not match receiver"); return 0;
  }
  std::shared_ptr<claritylink::AuthenticationAuthority> authority;
  if (lab_mode == JNI_TRUE) authority = std::make_shared<SyntheticTestAuthenticationAuthority>();
  else authority = std::make_shared<UnavailableAuthenticationAuthority>();
  auto receiver = std::make_shared<ReceiverGeneration>(static_cast<uint64_t>(generation), primary, secondary, authority);
  if (!receiver->exchange_info(static_cast<uint64_t>(generation))) { fail(env, "authentication or receiver start rejected"); return 0; }
  const jlong id = static_cast<jlong>(receivers.insert(std::move(receiver)));
  if (lab_mode == JNI_TRUE) {
    try { std::lock_guard<std::mutex> lock(registry_mutex); lab_receivers.insert(id); }
    catch (...) { auto failed = receivers.erase(id); if (failed) failed->close(); throw; }
  }
  return id;
} catch (...) { fail(env, "native receiver creation failed"); return 0; }

extern "C" JNIEXPORT jboolean JNICALL
Java_org_claritylink_android_NativeBridge_nativeSetup(JNIEnv* env, jclass, jlong id,
    jlong generation, jint primary_connection, jint secondary_connection, jboolean include_secondary) try {
  if(generation<=0 || primary_connection<=0 || primary_connection>65535 ||
     (include_secondary==JNI_TRUE && (secondary_connection<=0 || secondary_connection>65535 ||
                                      secondary_connection==primary_connection))) {
    fail(env,"invalid stream setup configuration"); return JNI_FALSE;
  }
  std::shared_ptr<ReceiverGeneration> receiver;
  receiver = receivers.get(id);
  if (!receiver) { fail(env, "invalid receiver handle"); return JNI_FALSE; }
  std::vector<StreamConfig> configs; configs.push_back({StreamType::Type110, static_cast<uint16_t>(primary_connection), false});
  if (include_secondary == JNI_TRUE) configs.push_back({StreamType::Type111, static_cast<uint16_t>(secondary_connection), false});
  return receiver->setup(static_cast<uint64_t>(generation), configs) ? JNI_TRUE : JNI_FALSE;
} catch (...) { fail(env, "native receiver setup failed"); return JNI_FALSE; }

extern "C" JNIEXPORT jboolean JNICALL
Java_org_claritylink_android_NativeBridge_nativeTestIngestSyntheticPacket(JNIEnv* env, jclass,
    jlong id, jlong generation, jbyteArray bytes) try {
  if (!bytes || generation <= 0) { fail(env, "invalid synthetic packet input"); return JNI_FALSE; }
  const jsize n=env->GetArrayLength(bytes);
  if (env->ExceptionCheck()) return JNI_FALSE;
  if (n < 15 || n > 2*1024*1024+15) { fail(env, "synthetic packet length outside bounds"); return JNI_FALSE; }
  std::shared_ptr<ReceiverGeneration> receiver;
  receiver = receivers.get(id);
  bool is_lab = false;
  { std::lock_guard<std::mutex> lock(registry_mutex); is_lab = lab_receivers.count(id) != 0; }
  if (!receiver || !is_lab) {
    fail(env,"synthetic framing is available only to explicit lab-mode receivers"); return JNI_FALSE;
  }
  std::vector<uint8_t> packet(static_cast<size_t>(n));
  env->GetByteArrayRegion(bytes,0,n,reinterpret_cast<jbyte*>(packet.data()));
  if (env->ExceptionCheck()) return JNI_FALSE;
  uint64_t packet_generation=0; StreamType type{}; uint16_t connection=0; std::vector<uint8_t> payload;
  if (!claritylink::parse_media_packet(packet,packet_generation,type,connection,payload) ||
      packet_generation!=static_cast<uint64_t>(generation)) return JNI_FALSE;
  return receiver->ingest(packet_generation,connection,packet,0)?JNI_TRUE:JNI_FALSE;
} catch (...) { fail(env, "synthetic media processing failed"); return JNI_FALSE; }

extern "C" JNIEXPORT void JNICALL
Java_org_claritylink_android_NativeBridge_nativeDisconnect(JNIEnv* env, jclass, jlong id) {
  std::shared_ptr<ReceiverGeneration> receiver;
  receiver = receivers.get(id);
  if (!receiver) { fail(env, "invalid or released receiver handle"); return; }
  receiver->close();
}

extern "C" JNIEXPORT void JNICALL
Java_org_claritylink_android_NativeBridge_nativeReleaseReceiver(JNIEnv* env, jclass, jlong id) {
  std::shared_ptr<ReceiverGeneration> receiver;
  receiver = receivers.erase(id);
  if (!receiver) { fail(env, "invalid or released receiver handle"); return; }
  { std::lock_guard<std::mutex> lock(registry_mutex); lab_receivers.erase(id); }
  receiver->close();
}

#if defined(CLARITYLINK_TEST_DIAGNOSTICS)
extern "C" JNIEXPORT jboolean JNICALL
Java_org_claritylink_android_R7C3TestBridge_receiveSocketFrame(JNIEnv* env, jclass,
    jlong id, jlong generation, jstring address, jint port, jint timeout_ms) {
  // This seam is compiled only into the isolated x86 test library.  The socket
  // adapter itself is the same production class linked into the ARM library.
  if (env->ExceptionCheck()) return JNI_FALSE;
  if (!address || generation <= 0 || port <= 0 || port > 65535 || timeout_ms <= 0 || timeout_ms > 30000) {
    fail(env, "invalid test socket request"); return JNI_FALSE;
  }
  const char* ipv4 = env->GetStringUTFChars(address, nullptr);
  if (env->ExceptionCheck() || !ipv4) return JNI_FALSE;
  std::string numeric;
  try { numeric.assign(ipv4); }
  catch (...) { env->ReleaseStringUTFChars(address, ipv4); fail(env, "test socket address allocation failed"); return JNI_FALSE; }
  env->ReleaseStringUTFChars(address, ipv4);
  if (env->ExceptionCheck()) return JNI_FALSE;
  if (numeric != "127.0.0.1") { fail(env, "test socket is restricted to 127.0.0.1"); return JNI_FALSE; }
  try {
    auto receiver = receivers.get(id);
    if (!receiver) { fail(env, "invalid socket receiver handle"); return JNI_FALSE; }
    bool is_lab = false;
    { std::lock_guard<std::mutex> lock(registry_mutex); is_lab = lab_receivers.count(id) != 0; }
    if (!is_lab) { fail(env, "socket LAB ingress requires explicit lab mode"); return JNI_FALSE; }
    claritylink::android::AndroidSocketAdapter socket;
    claritylink::android::SocketEndpoint endpoint{numeric, "127.0.0.1",
      static_cast<uint16_t>(port), static_cast<uint32_t>(timeout_ms), static_cast<uint64_t>(generation)};
    if (!socket.connect(endpoint)) return JNI_FALSE;
    // Read the bounded LAB packet header and body with explicit partial-read
    // handling.  Maximum packet size matches the receiver's synthetic limit.
    std::vector<uint8_t> packet(15);
    size_t used = 0;
    auto read_exact = [&](uint8_t* out, size_t count) {
      size_t offset = 0;
      while (offset < count) {
        int n = socket.read(out + offset, count - offset, static_cast<uint64_t>(generation));
        if (n <= 0) return false;
        offset += static_cast<size_t>(n);
      }
      return true;
    };
    if (!read_exact(packet.data(), packet.size())) return JNI_FALSE;
    const uint32_t payload_size = (static_cast<uint32_t>(packet[11]) << 24) |
      (static_cast<uint32_t>(packet[12]) << 16) | (static_cast<uint32_t>(packet[13]) << 8) | packet[14];
    if (payload_size == 0 || payload_size > 2u * 1024u * 1024u) return JNI_FALSE;
    used = packet.size(); packet.resize(used + payload_size);
    if (!read_exact(packet.data() + used, payload_size)) return JNI_FALSE;
    uint64_t packet_generation = 0; StreamType type{}; uint16_t connection = 0; std::vector<uint8_t> payload;
    if (!claritylink::parse_media_packet(packet, packet_generation, type, connection, payload) ||
        packet_generation != static_cast<uint64_t>(generation)) return JNI_FALSE;
    socket.shutdown(); socket.close();
    return receiver->ingest(packet_generation, connection, packet, 0) ? JNI_TRUE : JNI_FALSE;
  } catch (...) { fail(env, "native test socket frame failed"); return JNI_FALSE; }
}

extern "C" JNIEXPORT jboolean JNICALL
Java_org_claritylink_android_R7C3TestBridge_pendingExceptionProbe(JNIEnv* env, jclass) {
  if (env->ExceptionCheck()) return JNI_FALSE;
  jclass type = env->FindClass("java/lang/IllegalArgumentException");
  if (env->ExceptionCheck() || !type) return JNI_FALSE;
  env->ThrowNew(type, "R7C3 pending-exception probe");
  if (env->ExceptionCheck()) { env->DeleteLocalRef(type); return JNI_TRUE; }
  env->DeleteLocalRef(type);
  return JNI_FALSE;
}

extern "C" JNIEXPORT jboolean JNICALL
Java_org_claritylink_android_R7C3TestBridge_lookupFailureProbe(JNIEnv* env, jclass) {
  if (env->ExceptionCheck()) return JNI_FALSE;
  env->FindClass("org/claritylink/test/DeliberatelyMissingHelper");
  if (env->ExceptionCheck()) return JNI_TRUE; // Preserve ClassNotFoundException; perform no dependent JNI call.
  return JNI_FALSE;
}

extern "C" JNIEXPORT jlongArray JNICALL
Java_org_claritylink_android_NativeBridge_nativeDebugResourceCounts(JNIEnv* env, jclass) {
  jlong streams = 0, decoders = 0, listeners = 0, display_owners = 0;
  const auto active_receivers = receivers.values_snapshot();
  for (const auto& receiver : active_receivers) {
    const auto r = receiver->resources();
    streams += static_cast<jlong>(r.streams);
    decoders += static_cast<jlong>(r.decoders);
    listeners += static_cast<jlong>(r.listeners);
    display_owners += static_cast<jlong>(r.display_ownership);
  }
  const jlong counts[8] = {
    static_cast<jlong>(receivers.size()),
    static_cast<jlong>(surfaces.size()),
    static_cast<jlong>(0), // JNI global references: this bridge owns none.
    static_cast<jlong>(0), // Native-to-Java workers: this bridge creates none.
    streams, decoders, listeners, display_owners
  };
  jlongArray result = env->NewLongArray(8);
  if (env->ExceptionCheck() || !result) return nullptr;
  env->SetLongArrayRegion(result, 0, 8, counts);
  return env->ExceptionCheck() ? nullptr : result;
}
#endif
