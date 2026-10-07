#include "../platform/android/android_socket_adapter.hpp"
#include <arpa/inet.h>
#include <cassert>
#include <cerrno>
#include <cstdint>
#include <iostream>
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
  std::cout << "R7C_SOCKET_ADAPTER_PASS loopback=PASS wildcard=REJECTED generation=CHECKED peer-close=CHECKED limits=CHECKED\n";
}
