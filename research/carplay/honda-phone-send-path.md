# Honda phone-facing Setup send path

```text
HTTP connection/message
  -> _connectionHandleMessage 0x28a30c [AirTunesServer.c]
  -> parsed CF property-list request dictionary
  -> AirPlayReceiverSessionSetup 0x2854e0
  -> mutable response CF dictionary (streams array)
  -> _requestSendPlistResponse 0x289f60
  -> CFPropertyListCreateData(format 0xc8; binary plist)
  -> CFDataGetBytePtr + CFDataGetLength
  -> HTTPMessageSetBody
  -> HTTPHeader_Commit in HTTPConnectionSendResponse 0x29dbe4
  -> outgoing HTTP connection state
  -> _HTTPConnectionRunStateMachine 0x29d698
  -> SocketWriteData 0x2a01c0
  -> writev(fd, iovec[], iovcnt)
```

The Setup response pointer is the exact object passed as the plist serializer input. The caller releases it after the helper returns. The helper installs the encoded bytes as the body of a 200 HTTP response; the enclosing dispatcher handles HTTP status and headers and calls `HTTPConnectionSendResponse`. This proves an HTTP-like control response, not a raw plist-only socket payload. Body length is supplied to `HTTPMessageSetBody`, which owns the message body representation and later derives/sends its framing.

Transaction/session correlation is held in the HTTP connection/request context, but a Setup-specific transaction ID field is not recovered. `application/x-apple-binary-plist` is the serializer content type. `_HTTPConnectionRunStateMachine` calls `SocketWriteData` with the connection descriptor and pending iovec state; `SocketWriteData` invokes `writev@plt`, handles partial writes, and updates the iovec. Static tracing therefore reaches the TCP write syscall. Runtime packet segmentation and exact emitted bytes were not captured.
