import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
for p in (ROOT/'src/claritylink-interposer',ROOT/'src/claritylink-negotiation',ROOT/'src/claritylink-transport'):
    sys.path.insert(0,str(p))
from models import *
from server_info import ClarityLinkServerInfoAugmentor
from listener import FakeSecondaryListenerFactory
from setup_interposer import *
from lifecycle_coord import ClarityLinkLifecycleCoordinator
from screen_parser import HEADER_SIZE
from receiver_core import HondaScreenReceiverCore, VideoConfigEvent, VideoMediaBufferEvent
from screen_kdf import derive_honda_type110_screen_key_iv

def msg(kind,body,ts=55):
    h=bytearray(HEADER_SIZE); h[:4]=len(body).to_bytes(4,'little'); h[4]=kind; h[8:16]=ts.to_bytes(8,'little'); return bytes(h)+body

def test_host_only_display_b_end_to_end_video_and_teardown():
    profile=ClarityLinkCapabilityProfile(descriptor=ClarityLinkSecondaryDisplayDescriptor(uuid=SourcedValue("cluster",Provenance.CONFIGURABLE)))
    info=ClarityLinkServerInfoAugmentor(profile).augment({"displays":[{"uuid":"main"}],"features":3})
    assert [d["uuid"] for d in info["displays"]]==["main","cluster"]
    request={"streams":[{"type":100,"dataPort":1},{"type":110,"streamConnectionID":20},{"type":111,"streamConnectionID":777,"unknownPeerField":"preserve-me"}]}
    stock_resp={"streams":[{"type":100,"dataPort":1000},{"type":110,"dataPort":1100,"keep":True}],"other":"stock"}
    def stock(original): assert original is request; return 0,stock_resp
    fac=FakeSecondaryListenerFactory()
    inter=ClarityLinkSetupInterposer(StockSetupDelegate(stock),fac,lambda cid:derive_honda_type110_screen_key_iv(b"T"*16,cid),ClarityLinkType111ResponseBuilder(Type111ResponseProfile(ResponseStrategy.MINIMAL)))
    _,response=inter.setup(request)
    assert response["streams"][:2]==stock_resp["streams"] and response["streams"][2]["type"]==111
    life=ClarityLinkLifecycleCoordinator(inter); assert life.session_start(True)
    generation=inter.current; generation.receiver=HondaScreenReceiverCore()
    avcc=bytes([1,66,0,30,0xFF,0xE1])+b"\x00\x02\x67\x42"+b"\x01\x00\x02\x68\xCE"
    video=(3).to_bytes(4,"big")+b"\x65\x88\x99"
    events=generation.receiver.feed(msg(1,avcc)+msg(0,video))
    assert any(isinstance(e,VideoConfigEvent) for e in events)
    media=next(e for e in events if isinstance(e,VideoMediaBufferEvent))
    assert media.data.startswith(b"\x00\x00\x00\x01\x67\x42") and media.data.endswith(b"\x00\x00\x00\x01\x65\x88\x99")
    life.teardown_type111_generation()
    assert inter.current is None and fac.created[0].closed
