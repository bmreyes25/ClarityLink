#include "../platform/android/android_socket_adapter.hpp"
#include "../platform/android/r7c6_race_controller.hpp"
#include <arpa/inet.h>
#include <cassert>
#include <atomic>
#include <cerrno>
#include <condition_variable>
#include <cstdint>
#include <iostream>
#include <mutex>
#include <sys/socket.h>
#include <unistd.h>
#include <thread>
#include <vector>

using claritylink::android::AndroidSocketAdapter;
using claritylink::android::SocketEndpoint;
int main() {
  SocketEndpoint bad{"0.0.0.0","0.0.0.0",1234,100,1}; AndroidSocketAdapter reject;
  assert(!reject.connect(bad) && reject.error()==EINVAL);
  int server=socket(AF_INET,SOCK_STREAM,0); assert(server>=0);
  sockaddr_in addr{}; addr.sin_family=AF_INET; addr.sin_addr.s_addr=htonl(INADDR_LOOPBACK); addr.sin_port=0;
  assert(bind(server,reinterpret_cast<sockaddr*>(&addr),sizeof(addr))==0);
  socklen_t n=sizeof(addr); assert(getsockname(server,reinterpret_cast<sockaddr*>(&addr),&n)==0);
  assert(listen(server,4)==0);
  int duplicate=socket(AF_INET,SOCK_STREAM,0); assert(duplicate>=0);
  assert(bind(duplicate,reinterpret_cast<sockaddr*>(&addr),sizeof(addr))<0 && errno==EADDRINUSE);
  close(duplicate);
  std::thread worker([&] { int peer=accept(server,nullptr,nullptr); assert(peer>=0);
    uint8_t data[32]{}; ssize_t r=recv(peer,data,sizeof(data),0); assert(r==4);
    assert(send(peer,"ok",2,0)==2); close(peer); });
  SocketEndpoint ep{"127.0.0.1","127.0.0.1",ntohs(addr.sin_port),1000,44}; AndroidSocketAdapter client;
  assert(client.connect(ep)); const uint8_t msg[]={1,2,3,4}; assert(client.write(msg,4,44)==4);
  assert(client.write(msg,4,45)<0); uint8_t reply[8]{}; assert(client.read(reply,sizeof(reply),44)==2);
  assert(reply[0]=='o' && reply[1]=='k'); assert(client.read(reply,sizeof(reply),44)<0);
  (void)client.write(msg,4,44); // A closed peer may reject this write; it must never SIGPIPE the process.
  std::vector<uint8_t> huge(1024*1024+1); assert(client.write(huge.data(),huge.size(),44)<0);
  client.shutdown(); client.close(); worker.join(); close(server);

  const auto make_listener = [](uint16_t& port) {
    int listener = socket(AF_INET, SOCK_STREAM, 0); assert(listener >= 0);
    sockaddr_in local{}; local.sin_family=AF_INET; local.sin_addr.s_addr=htonl(INADDR_LOOPBACK); local.sin_port=0;
    assert(bind(listener,reinterpret_cast<sockaddr*>(&local),sizeof(local))==0);
    socklen_t size=sizeof(local); assert(getsockname(listener,reinterpret_cast<sockaddr*>(&local),&size)==0);
    assert(listen(listener,2)==0); port=ntohs(local.sin_port); return listener;
  };

  // Deterministic active-read shutdown: close wakes a reader paused after the
  // production adapter acquired a shared descriptor owner.
  uint16_t read_port=0; int read_listener=make_listener(read_port);
  std::mutex peer_mutex; std::condition_variable peer_changed; bool release_read_peer=false;
  std::thread read_peer([&] { int peer=accept(read_listener,nullptr,nullptr); assert(peer>=0); std::unique_lock<std::mutex> lock(peer_mutex); peer_changed.wait(lock,[&]{return release_read_peer;}); close(peer); });
  AndroidSocketAdapter read_client;
  assert(read_client.connect(SocketEndpoint{"127.0.0.1","127.0.0.1",read_port,1000,101}));
  std::atomic<int> read_result{0};
  assert(claritylink::android::r7c6test::arm(claritylink::android::r7c6test::Checkpoint::SocketReadActive,101,110,3000));
  std::thread reader([&] { claritylink::android::r7c6test::set_stream_context(110); uint8_t b[16]{}; read_result.store(read_client.read(b,sizeof(b),101)); });
  assert(claritylink::android::r7c6test::wait_reached(claritylink::android::r7c6test::Checkpoint::SocketReadActive,101,110,3000));
  read_client.shutdown();
  assert(claritylink::android::r7c6test::release(claritylink::android::r7c6test::Checkpoint::SocketReadActive,101,110));
  reader.join(); read_client.close(); { std::lock_guard<std::mutex> lock(peer_mutex); release_read_peer=true; } peer_changed.notify_all(); read_peer.join(); close(read_listener);
  assert(read_result.load()<0);

  // Deterministic active-write shutdown has the same bounded ownership rule.
  uint16_t write_port=0; int write_listener=make_listener(write_port);
  bool release_write_peer=false;
  std::thread write_peer([&] { int peer=accept(write_listener,nullptr,nullptr); assert(peer>=0); std::unique_lock<std::mutex> lock(peer_mutex); peer_changed.wait(lock,[&]{return release_write_peer;}); close(peer); });
  AndroidSocketAdapter write_client;
  assert(write_client.connect(SocketEndpoint{"127.0.0.1","127.0.0.1",write_port,1000,102}));
  std::atomic<int> write_result{0};
  assert(claritylink::android::r7c6test::arm(claritylink::android::r7c6test::Checkpoint::SocketWriteActive,102,111,3000));
  std::thread writer([&] { claritylink::android::r7c6test::set_stream_context(111); const uint8_t b[16]={}; write_result.store(write_client.write(b,sizeof(b),102)); });
  assert(claritylink::android::r7c6test::wait_reached(claritylink::android::r7c6test::Checkpoint::SocketWriteActive,102,111,3000));
  write_client.shutdown();
  assert(claritylink::android::r7c6test::release(claritylink::android::r7c6test::Checkpoint::SocketWriteActive,102,111));
  writer.join(); write_client.close(); { std::lock_guard<std::mutex> lock(peer_mutex); release_write_peer=true; } peer_changed.notify_all(); write_peer.join(); close(write_listener);
  assert(write_result.load()<0);
  std::cout << "R7C_SOCKET_ADAPTER_PASS loopback=PASS wildcard=REJECTED generation=CHECKED peer-close=CHECKED limits=CHECKED\n";
}
