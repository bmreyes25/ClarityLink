"""Connect the compiled host C transaction to the real host-only listener."""
import ctypes
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import threading

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/claritylink-interposer"))
sys.path.insert(0, str(ROOT / "src/claritylink-negotiation"))

from real_listener import InterfaceKind, InterfacePolicy, PreparedListener

REQUEST_MAGIC = 0x43525131
RESPONSE_MAGIC = 0x43525331
MAX_STREAMS = 8


class RequestStream(ctypes.Structure):
    _fields_ = [("type", ctypes.c_uint32), ("low", ctypes.c_uint32), ("high", ctypes.c_uint32)]


class Request(ctypes.Structure):
    _fields_ = [("magic", ctypes.c_uint32), ("count", ctypes.c_uint32),
                ("streams", RequestStream * MAX_STREAMS)]


class ResponseStream(ctypes.Structure):
    _fields_ = [("type", ctypes.c_uint32), ("data_port", ctypes.c_uint32)]


class Response(ctypes.Structure):
    _fields_ = [("magic", ctypes.c_uint32), ("count", ctypes.c_uint32),
                ("streams", ResponseStream * MAX_STREAMS)]


class SetupCall(ctypes.Structure):
    _fields_ = [("request", ctypes.POINTER(Request)), ("response", ctypes.POINTER(Response)),
                ("status_out", ctypes.POINTER(ctypes.c_int32)), ("session", ctypes.c_void_p),
                ("expected_status_out", ctypes.c_size_t)]


class PreparedTxn(ctypes.Structure):
    _fields_ = [(name, ctypes.c_uint32) for name in (
        "magic", "state", "gate_token", "generation", "stream_id_low", "stream_id_high",
        "data_port", "original_response_count", "response_appended", "listener_owned",
        "generation_owned")]


ClaimFn = ctypes.CFUNCTYPE(ctypes.c_int32, ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32))
ReleaseFn = ctypes.CFUNCTYPE(ctypes.c_int32, ctypes.c_void_p, ctypes.c_uint32)
GenerationPrepareFn = ctypes.CFUNCTYPE(ctypes.c_int32, ctypes.c_void_p, ctypes.c_uint32,
                                       ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint32))
ListenerPrepareFn = ctypes.CFUNCTYPE(ctypes.c_int32, ctypes.c_void_p, ctypes.c_uint32,
                                     ctypes.POINTER(ctypes.c_uint32))
ActionFn = ctypes.CFUNCTYPE(ctypes.c_int32, ctypes.c_void_p, ctypes.c_uint32)


class Services(ctypes.Structure):
    _fields_ = [("userdata", ctypes.c_void_p), ("gate_claim", ClaimFn),
                ("gate_release", ReleaseFn), ("generation_prepare", GenerationPrepareFn),
                ("listener_prepare", ListenerPrepareFn), ("generation_commit", ActionFn),
                ("generation_rollback", ActionFn), ("listener_rollback", ActionFn)]


@pytest.fixture(scope="module")
def native_library(tmp_path_factory):
    clang = shutil.which("clang")
    if not clang:
        pytest.skip("clang not available for native listener integration")
    tmp_path = tmp_path_factory.mktemp("native-listener")
    source = ROOT / "src/claritylink-negotiation/native_setup_txn.c"
    output = tmp_path / "libnative_setup_txn.dylib"
    subprocess.run([clang, "-std=c11", "-Wall", "-Wextra", "-Werror", "-O1",
                    "-dynamiclib", "-fPIC", "-I", str(source.parent), str(source),
                    "-o", str(output)], check=True, capture_output=True, text=True)
    lib = ctypes.CDLL(str(output))
    lib.cl_setup_prepare.argtypes = [ctypes.POINTER(SetupCall), ctypes.POINTER(PreparedTxn),
                                    ctypes.POINTER(Services)]
    lib.cl_setup_prepare.restype = ctypes.c_int32
    lib.cl_setup_finish.argtypes = [ctypes.POINTER(SetupCall), ctypes.POINTER(PreparedTxn),
                                    ctypes.c_int32, ctypes.c_int32, ctypes.POINTER(Services)]
    lib.cl_setup_finish.restype = ctypes.c_int32
    return lib


class HostServices:
    def __init__(self):
        self.lock = threading.Lock()
        self.gate_held = False
        self.next_generation = 0
        self.listeners = {}
        self.committed = []
        self.rolled_back = []
        self.listener_rolled_back = []
        self.fail_commit = False

        def claim(_userdata, out):
            if self.gate_held:
                return 0
            self.gate_held = True
            out[0] = 1
            return 1

        def release(_userdata, token):
            if token == 0 or not self.gate_held:
                return -1
            self.gate_held = False
            return 1

        def generation_prepare(_userdata, _low, _high, out):
            self.next_generation += 1
            out[0] = self.next_generation
            return 1

        def listener_prepare(_userdata, generation, port_out):
            try:
                listener = PreparedListener.create(
                    generation, InterfacePolicy(InterfaceKind.LOOPBACK_TEST))
                self.listeners[generation] = listener
                port_out[0] = listener.assigned_port
                return 1
            except Exception:
                return -1

        def generation_commit(_userdata, generation):
            if self.fail_commit:
                return -1
            self.committed.append(generation)
            return 1

        def generation_rollback(_userdata, generation):
            self.rolled_back.append(generation)
            return 1

        def listener_rollback(_userdata, generation):
            self.listener_rolled_back.append(generation)
            listener = self.listeners.get(generation)
            if listener is not None:
                listener.close()
            return 1

        self.callbacks = (ClaimFn(claim), ReleaseFn(release),
                          GenerationPrepareFn(generation_prepare),
                          ListenerPrepareFn(listener_prepare), ActionFn(generation_commit),
                          ActionFn(generation_rollback), ActionFn(listener_rollback))
        self.table = Services(None, *self.callbacks)


def _objects(stream_id):
    request = Request()
    request.magic = REQUEST_MAGIC
    request.count = 2
    request.streams[0] = RequestStream(110, 0x11223344, 1)
    request.streams[1] = RequestStream(111, stream_id, 2)
    response = Response()
    response.magic = RESPONSE_MAGIC
    response.count = 1
    response.streams[0] = ResponseStream(110, 41000)
    status = ctypes.c_int32(0)
    marker = ctypes.c_uint32(9)
    call = SetupCall(ctypes.pointer(request), ctypes.pointer(response), ctypes.pointer(status),
                     ctypes.c_void_p(ctypes.addressof(marker)), ctypes.addressof(status))
    return request, response, status, marker, call


def _contains_address(txn, address):
    raw = ctypes.string_at(ctypes.addressof(txn), ctypes.sizeof(txn))
    return ctypes.c_size_t(address).value.to_bytes(ctypes.sizeof(ctypes.c_size_t), "little") in raw


def test_compiled_host_prepare_listen_ready_serialize_commit_and_rollback(native_library):
    native = native_library
    svc = HostServices()
    request, response, status, marker, call = _objects(0x55667788)
    stock_type110 = bytes(response.streams[0])
    txn = PreparedTxn()
    assert native.cl_setup_prepare(ctypes.byref(call), ctypes.byref(txn), ctypes.byref(svc.table)) == 1
    assert response.count == 2 and response.streams[1].type == 111
    listener = svc.listeners[txn.generation]
    assert response.streams[1].data_port == listener.assigned_port
    assert bytes(response.streams[0]) == stock_type110
    for pointer in (ctypes.addressof(request), ctypes.addressof(response),
                    ctypes.addressof(status), ctypes.addressof(marker)):
        assert not _contains_address(txn, pointer)

    serializer_calls = 1
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect(("127.0.0.1", response.streams[1].data_port))
        accepted = listener.wait_accepted(timeout=1)
        assert accepted is not None
        assert native.cl_setup_finish(ctypes.byref(call), ctypes.byref(txn), 0xC8, 1,
                                      ctypes.byref(svc.table)) == 1
        assert svc.committed == [txn.generation] and svc.gate_held is False
        assert serializer_calls == 1
        listener.close()  # synthetic project teardown after committed ownership
        assert accepted.fileno() == -1 and not listener.worker.is_alive()
    finally:
        client.close()

    request, response, status, marker, call = _objects(0x55667789)
    txn = PreparedTxn()
    before = bytes(response)
    assert native.cl_setup_prepare(ctypes.byref(call), ctypes.byref(txn), ctypes.byref(svc.table)) == 1
    failed_generation = txn.generation
    assert native.cl_setup_finish(ctypes.byref(call), ctypes.byref(txn), 0x1F4, 0,
                                  ctypes.byref(svc.table)) == 2
    failed_listener = svc.listeners[failed_generation]
    assert bytes(response) == before
    assert failed_listener.sock.fileno() == -1 and not failed_listener.worker.is_alive()
    assert svc.listener_rolled_back == [failed_generation]
    assert svc.rolled_back == [failed_generation] and svc.gate_held is False
