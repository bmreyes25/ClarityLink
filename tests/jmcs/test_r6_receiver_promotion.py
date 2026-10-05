from __future__ import annotations
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "claritylink-jmcs"))
from claritylink_jmcs.capabilities import SecondaryDisplayCapability, host_info
from claritylink_jmcs.decoder import DecodeError, avcc_to_annexb
from claritylink_jmcs.media import FramingProfile, MediaError, read_profile_message
from claritylink_jmcs.receiver import Receiver, ReceiverError
from claritylink_jmcs.security import SecurityProfile, SessionSecurityContext, SecurityError
from claritylink_jmcs.setup import SetupRequest, SetupError


def test_info_profile_has_two_distinct_complete_display_structures():
    displays = host_info(SecondaryDisplayCapability())["displays"]
    assert [d["type"] for d in displays] == [110, 111]
    assert displays[0]["uuid"] != displays[1]["uuid"]
    assert displays[1]["initialURL"] == "maps:/car/instrumentcluster/map"
    for display in displays:
        assert display["viewAreas"][0]["safeArea"]["widthPixels"] == display["widthPixels"]
        assert display["widthPhysical"] > 0 and display["heightPhysical"] > 0


def test_duplicate_primary_rejected():
    with pytest.raises(SetupError, match="duplicate_primary"):
        SetupRequest.parse({"streams": [{"type": 110, "streamConnectionID": 1},
                                         {"type": 110, "streamConnectionID": 2}]}, 1)


def test_recreate_secondary_after_independent_teardown_has_no_stale_port():
    receiver = Receiver(clear_lab=True)
    generation = receiver.start_session()
    receiver.info_exchanged(generation)
    receiver.setup({"streams": [{"type": 110, "streamConnectionID": 1},
                                {"type": 111, "streamConnectionID": 2}]}, generation)
    receiver.teardown_secondary(generation)
    response = receiver.setup({"streams": [{"type": 111, "streamConnectionID": 3}]}, generation)
    assert [x["type"] for x in response.fields["streams"]] == [110, 111]
    assert response.fields["streams"][1]["dataPort"] == receiver.secondary.port
    receiver.teardown(generation)


def test_avcc_bounds_and_conversion():
    assert avcc_to_annexb(b"\x00\x00\x00\x02\x67\x42") == b"\x00\x00\x00\x01\x67\x42"
    for bad in (b"", b"\x00\x00", b"\x00\x00\x00\x04\x67"):
        with pytest.raises(DecodeError):
            avcc_to_annexb(bad)


def test_unknown_type111_framing_and_security_fail_closed():
    with pytest.raises(MediaError, match="type111_framing_evidence_required"):
        read_profile_message(None, 1, FramingProfile.LEGACY_TYPE111_PRIOR_ART)
    context = SessionSecurityContext(SecurityProfile.MODERN_CHACHA_SCREEN, "43P lab profile", 1, 7)
    with pytest.raises(SecurityError, match="type111_security_evidence_required"):
        context.unprotect(1, b"sealed")
    context.close()
    with pytest.raises(SecurityError, match="stale_security_context"):
        context.unprotect(1, b"sealed")


def test_host_window_generation_and_clear_with_fake_gui(monkeypatch):
    import types
    from claritylink_jmcs.decoder import DecodedFrame
    from claritylink_jmcs.display import DisplayError, HostWindowDisplay

    class FakeRoot:
        def title(self, value): pass
        def update(self): pass
        def destroy(self): pass
    class FakeCanvas:
        def __init__(self, *args, **kwargs): self.items = []
        def pack(self): pass
        def delete(self, tag): self.items.clear()
        def create_image(self, *args, **kwargs): self.items.append(args)
    class FakeImage:
        def __init__(self, data): self.data = data
        def width(self): return 1600
        def height(self): return 960
        def subsample(self, factor): return self
    monkeypatch.setitem(sys.modules, "tkinter", types.SimpleNamespace(Tk=FakeRoot, Canvas=FakeCanvas, PhotoImage=FakeImage))
    window = HostWindowDisplay()
    window.begin_generation(2)
    with pytest.raises(DisplayError, match="stale_display_frame"):
        window.show(DecodedFrame(b"png", 1, 1))
    window.show(DecodedFrame(b"png", 1, 2))
    assert window.current is not None and len(window.canvas.items) == 1
    window.clear()
    assert window.current is None and not window.canvas.items
    with pytest.raises(DisplayError, match="stale_display_frame"):
        window.show(DecodedFrame(b"png", 1, 2))
    window.close()


def test_current_host_profile_header_and_authenticated_frame():
    import os, socket
    from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
    from claritylink_jmcs.security import ModernChaChaScreenSecurity
    key = os.urandom(32)
    header = bytearray(128)
    header[:4] = (19).to_bytes(4, "little")  # three clear bytes + 16-byte tag
    header[4] = 0
    header[8:16] = (123).to_bytes(8, "little")
    sealed = ChaCha20Poly1305(key).encrypt(bytes(12), b"abc", bytes(header))
    sender, reader = socket.socketpair()
    reader.settimeout(0.2)
    try:
        sender.sendall(bytes(header) + sealed)
        message = read_profile_message(reader, 3, FramingProfile.CURRENT_IOS_TYPE111)
        assert message.header == bytes(header) and message.timestamp == 123
        provider = ModernChaChaScreenSecurity(key, provenance="generated test context")
        provider.open(3, 111)
        assert provider.unprotect(3, message.body, message.header) == b"abc"
        assert provider.counter == 1
        with pytest.raises(SecurityError, match="screen_authentication_failed"):
            provider.unprotect(3, message.body, message.header)
        assert provider.counter == 1
        provider.close()
        with pytest.raises(SecurityError, match="stale_security_context"):
            provider.unprotect(3, message.body, message.header)
    finally:
        sender.close()
        reader.close()


def test_current_host_profile_rejects_oversize_before_body():
    import socket
    sender, reader = socket.socketpair()
    reader.settimeout(0.2)
    try:
        header = bytearray(128)
        header[:4] = (8 * 1024 * 1024 + 1).to_bytes(4, "little")
        sender.sendall(header)
        with pytest.raises(MediaError, match="invalid_body_length"):
            read_profile_message(reader, 1, FramingProfile.CURRENT_IOS_TYPE111)
    finally:
        sender.close()
        reader.close()


def test_avcc_video_config_extracts_sps_pps_and_rejects_truncation():
    from claritylink_jmcs.decoder import parse_avcc_config
    config = bytes([1, 66, 0, 30, 255, 225, 0, 2, 0x67, 0x42, 1, 0, 2, 0x68, 0xCE])
    assert parse_avcc_config(b"xxxxavcC" + config) == (b"\x00\x00\x00\x01\x67\x42"
                                                     b"\x00\x00\x00\x01\x68\xCE")
    for bad in (b"", config[:10], config[:11]):
        with pytest.raises(DecodeError):
            parse_avcc_config(bad)


def test_generated_encrypted_current_profile_reaches_host_decoder():
    import os, socket, subprocess
    from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
    from claritylink_jmcs.media import FramingProfile
    from claritylink_jmcs.security import ModernChaChaScreenSecurity
    key = os.urandom(32)
    receiver = Receiver(framing_profile=FramingProfile.CURRENT_IOS_TYPE111,
                        security_factory=lambda: ModernChaChaScreenSecurity(key, provenance="generated fixture"))
    generation = receiver.start_session()
    receiver.info_exchanged(generation)
    response = receiver.setup({"streams": [{"type": 110, "streamConnectionID": 11},
                                           {"type": 111, "streamConnectionID": 12}]}, generation)
    assert [x["type"] for x in response.fields["streams"]] == [110, 111]
    access_unit = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                                  "color=c=red:s=32x32:r=1", "-frames:v", "1", "-c:v", "libx264", "-f", "h264", "pipe:1"],
                                 capture_output=True, timeout=5, check=True).stdout
    header = bytearray(128)
    header[:4] = (len(access_unit) + 16).to_bytes(4, "little")
    sealed = ChaCha20Poly1305(key).encrypt(bytes(12), access_unit, bytes(header))
    with socket.create_connection(("127.0.0.1", receiver.secondary.port), timeout=1) as client:
        receiver.accept_secondary(generation)
        client.sendall(bytes(header) + sealed)
        assert receiver.receive_secondary_frame(generation).startswith(b"\x89PNG")
    assert receiver.frames == 1
    receiver.teardown(generation)
    assert receiver.snapshot().sessions == 0


def test_shared_sanitized_protocol_fixture():
    import json
    fixture = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "r6" / "protocol-vectors.json").read_text())
    assert fixture["provenance"].startswith("SYNTHETIC_SANITIZED")
    displays = host_info(SecondaryDisplayCapability())["displays"]
    assert [x["type"] for x in displays] == fixture["info"]["display_types"]
    for index, request in enumerate(fixture["setup"], 1):
        parsed = SetupRequest.parse(request, index)
        assert [x.type for x in parsed.streams] == [x["type"] for x in request["streams"]]
    assert fixture["stream_header"]["size_bytes"] == 128
