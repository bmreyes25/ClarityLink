#include "android_socket_adapter.hpp"
#include <arpa/inet.h>
#include <cerrno>
#include <fcntl.h>
#include <poll.h>
#include <sys/socket.h>
#include <unistd.h>

namespace claritylink::android {
namespace { constexpr size_t kMaxTransfer=1024u*1024u; }
AndroidSocketAdapter::~AndroidSocketAdapter() { close(); }
bool AndroidSocketAdapter::connect(const SocketEndpoint& ep) {
  close(); error_=0;
  if(ep.ipv4.empty() || ep.ipv4=="0.0.0.0" || ep.bind_ipv4.empty() || ep.bind_ipv4=="0.0.0.0" ||
     ep.port==0 || ep.timeout_ms==0 || ep.timeout_ms>30000 || ep.generation==0) { error_=EINVAL; return false; }
  sockaddr_in addr{}; addr.sin_family=AF_INET; addr.sin_port=htons(ep.port);
  if(inet_pton(AF_INET,ep.ipv4.c_str(),&addr.sin_addr)!=1 || addr.sin_addr.s_addr==htonl(INADDR_ANY)) { error_=EINVAL; return false; }
  sockaddr_in local{}; local.sin_family=AF_INET;
  if(inet_pton(AF_INET,ep.bind_ipv4.c_str(),&local.sin_addr)!=1 || local.sin_addr.s_addr==htonl(INADDR_ANY)) { error_=EINVAL; return false; }
  fd_=socket(AF_INET,SOCK_STREAM,0); if(fd_<0) { error_=errno; return false; }
  if(::bind(fd_,reinterpret_cast<sockaddr*>(&local),sizeof(local))<0) { error_=errno; close(); return false; }
  const int flags=fcntl(fd_,F_GETFL,0); if(flags<0 || fcntl(fd_,F_SETFL,flags|O_NONBLOCK)<0) { error_=errno; close(); return false; }
  int result=::connect(fd_,reinterpret_cast<sockaddr*>(&addr),sizeof(addr));
  if(result<0 && errno!=EINPROGRESS) { error_=errno; close(); return false; }
  if(result<0) { pollfd p{fd_,POLLOUT,0}; result=poll(&p,1,static_cast<int>(ep.timeout_ms));
    if(result<=0) { error_=result==0?ETIMEDOUT:errno; close(); return false; }
    socklen_t n=sizeof(error_); if(getsockopt(fd_,SOL_SOCKET,SO_ERROR,&error_,&n)<0 || error_!=0) { if(error_==0)error_=errno; close(); return false; }
  }
  generation_=ep.generation; return true;
}
int AndroidSocketAdapter::read(uint8_t* buffer,size_t cap,uint64_t gen) {
  if(fd_<0 || gen!=generation_ || !buffer || cap==0 || cap>kMaxTransfer) { error_=EINVAL; return -1; }
  pollfd p{fd_,POLLIN,0}; int r=poll(&p,1,1000); if(r<=0) { error_=r==0?ETIMEDOUT:errno; return -1; }
  ssize_t n=recv(fd_,buffer,cap,0); if(n<0)error_=errno; else if(n==0) { error_=ECONNRESET; return -1; }
  return static_cast<int>(n);
}
int AndroidSocketAdapter::write(const uint8_t* data,size_t length,uint64_t gen) {
  if(fd_<0 || gen!=generation_ || !data || length==0 || length>kMaxTransfer) { error_=EINVAL; return -1; }
  pollfd p{fd_,POLLOUT,0}; int r=poll(&p,1,1000); if(r<=0) { error_=r==0?ETIMEDOUT:errno; return -1; }
  ssize_t n=send(fd_,data,length,MSG_NOSIGNAL); if(n<0)error_=errno; return static_cast<int>(n); // partial writes are reported to caller; peer-close cannot SIGPIPE the process
}
void AndroidSocketAdapter::shutdown() { if(fd_>=0) ::shutdown(fd_,SHUT_RDWR); }
void AndroidSocketAdapter::close() { if(fd_>=0) { ::close(fd_); fd_=-1; } generation_=0; }
} // namespace claritylink::android
