import copy
import hashlib
import pytest
from models import (ClarityLinkCapabilityProfile, ClarityLinkSecondaryDisplayDescriptor as Descriptor,
                    Provenance, SourcedValue, ResponseStrategy, Type111ResponseProfile, SecretBytes)
from server_info import ClarityLinkServerInfoAugmentor, ServerInfoError
from listener import FakeSecondaryListenerFactory
from setup_interposer import (ClarityLinkSetupInterposer, ClarityLinkType111ResponseBuilder,
                              StockSetupDelegate, append_response, parse_type111_view)
from lifecycle_coord import (ClarityLinkLifecycleCoordinator, ClarityLinkRedactedDiagnostics,
                       Event, HondaBinaryIdentity, ExpectedFunctionIdentity, HookGroupGate, FailClosedHookPolicy)
from screen_kdf import derive_honda_type110_screen_key_iv

def test_server_info_pure_additive_and_disabled():
    main={"uuid":"main","opaque":{"a":1}}
    stock={"displays":[main],"unknownFieldA":1,"unknownFieldB":[2]}
    prof=ClarityLinkCapabilityProfile(descriptor=Descriptor(uuid=SourcedValue("cluster",Provenance.CONFIGURABLE),pixel_width=SourcedValue(800,Provenance.CONFIGURABLE)))
    out=ClarityLinkServerInfoAugmentor(prof).augment(stock)
    assert out["displays"][0] == main and len(out["displays"])==2
    assert {k:v for k,v in out.items() if k!="displays"} == {k:v for k,v in stock.items() if k!="displays"}
    assert stock["displays"]==[main]
    assert ClarityLinkServerInfoAugmentor(ClarityLinkCapabilityProfile(enabled=False,descriptor=prof.descriptor)).augment(stock)==stock
    assert len(ClarityLinkServerInfoAugmentor(prof).augment(out)["displays"])==2

def test_server_info_rejects_bad_source_without_mutation():
    source={"displays":"bad"}
    with pytest.raises(ServerInfoError): ClarityLinkServerInfoAugmentor(ClarityLinkCapabilityProfile()).augment(source)
    assert source=={"displays":"bad"}

def test_request_view_and_profiles_preserve_opaque_data():
    peer={"type":111,"streamConnectionID":42,"opaque":{"nested":["keep"]}}
    view=parse_type111_view({"streams":[peer]})
    clone=ClarityLinkType111ResponseBuilder(Type111ResponseProfile(ResponseStrategy.PRIOR_ART_CLONE,True)).build(view,42000)
    assert clone=={**peer,"dataPort":42000,"streamID":111}
    assert ClarityLinkType111ResponseBuilder(Type111ResponseProfile()).build(view,42000)=={"type":111,"dataPort":42000}
    with pytest.raises(ValueError): parse_type111_view({"streams":[peer,peer]})

def test_cow_merge_supports_tuple_and_preserves_stock():
    original={"streams":({"type":110,"dataPort":1234,"x":1},),"unknown":True}
    merged=append_response(original,{"type":111,"dataPort":2345})
    assert len(original["streams"])==1 and merged["streams"][0]==original["streams"][0]
    assert merged["streams"][1]=={"type":111,"dataPort":2345} and merged["unknown"]

def setup_fixture(*,fail_listener=None,publisher=None,stock_status=0,security=None):
    req={"streams":[{"type":100,"opaque":"audio"},{"type":110,"dataPort":20},{"type":111,"streamConnectionID":991,"unknownPeerField":"preserve-me"}]}
    stock={"streams":[{"type":100,"dataPort":11},{"type":110,"dataPort":22,"opaque":"stock"}],"other":"keep"}
    seen=[]
    def stock_cb(value): seen.append(value); return stock_status,stock
    factory=FakeSecondaryListenerFactory(fail_at=fail_listener)
    provider=security or (lambda cid: derive_honda_type110_screen_key_iv(b"S"*16,cid))
    ip=ClarityLinkSetupInterposer(StockSetupDelegate(stock_cb),factory,provider,
        ClarityLinkType111ResponseBuilder(Type111ResponseProfile()),publisher)
    return req,stock,seen,factory,ip

def test_stock_first_setup_commit_and_exact_request_object():
    req,stock,seen,factory,ip=setup_fixture()
    status,result=ip.setup(req)
    assert status==0 and seen[0] is req
    assert result["streams"][:-1]==stock["streams"]
    assert result["streams"][-1]=={"type":111,"dataPort":41000}
    assert ip.current.stream_connection_id==991 and ip.current.state=="PREPARED"
    assert factory.created[0].port==41000

def test_failures_keep_stock_and_release_listener():
    for phase in ("socket","bind","getsockname","listen"):
        req,stock,_,factory,ip=setup_fixture(fail_listener=phase)
        _,result=ip.setup(req)
        assert result==stock and ip.current is None
        assert not factory.created
    req,stock,_,factory,ip=setup_fixture(publisher=lambda _:False)
    _,result=ip.setup(req)
    assert result==stock and factory.created[0].closed and ip.current is None
    req,stock,_,factory,ip=setup_fixture(security=lambda _: (_ for _ in ()).throw(RuntimeError("synthetic")))
    _,result=ip.setup(req)
    assert result==stock and not factory.created

def test_stock_failure_disabled_and_no_type111_have_no_project_side_effects():
    req,stock,seen,factory,ip=setup_fixture(stock_status=-9)
    status,result=ip.setup(req)
    assert status==-9 and result==stock and ip.current is None and not factory.created
    req,stock,_,factory,ip=setup_fixture()
    clean={"streams":[{"type":110,"streamConnectionID":5}]}
    _,result=ip.setup(clean,enabled=False)
    assert result==stock and ip.current is None and not factory.created
    _,result=ip.setup(clean)
    assert result==stock and ip.current is None and not factory.created

def test_duplicate_or_invalid_type111_fail_closed_after_stock():
    req,stock,_,factory,ip=setup_fixture()
    req["streams"].append(copy.deepcopy(req["streams"][-1]))
    _,result=ip.setup(req)
    assert result==stock and ip.current is None and not factory.created

def test_session_start_and_idempotent_teardown_clean_owned_secrets():
    req,_,_,factory,ip=setup_fixture()
    ip.setup(req)
    diag=ClarityLinkRedactedDiagnostics(); life=ClarityLinkLifecycleCoordinator(ip,diag)
    assert life.session_start(True)
    generation=ip.current
    key=generation.key; iv=generation.iv
    assert generation.state=="ACTIVE"
    life.teardown_type111_generation(); life.teardown_type111_generation()
    assert ip.current is None and factory.created[0].closed and factory.created[0].close_count==1
    assert len(key)==len(iv)==0
    assert generation.generation is None and generation.stream_connection_id is None and generation.data_port is None
    assert generation.receiver is None and generation.state=="CLOSED"
    assert repr(key)=="SecretBytes(<redacted>, length=0)"
    assert diag.events[-1].event is Event.TYPE111_TORN_DOWN

def test_failed_stock_session_start_rolls_back():
    req,_,_,factory,ip=setup_fixture(); ip.setup(req)
    life=ClarityLinkLifecycleCoordinator(ip)
    assert not life.session_start(False)
    assert ip.current is None and factory.created[0].closed

def test_identity_gate_is_exact_and_fail_closed():
    digest="a"*64; binary=HondaBinaryIdentity(digest,32,"little","ARM")
    f=ExpectedFunctionIdentity("Setup",0x1000,"Thumb",digest,b"\x01\x02")
    gate=HookGroupGate(binary,(f,))
    assert gate.eligible(binary,{"Setup":b"\x01\x02"},all_adapters_available=True)
    assert not gate.eligible(binary,{"Setup":b"bad"},all_adapters_available=True)
    assert not gate.eligible(binary,{"Setup":b"\x01\x02"},all_adapters_available=False)
    assert not FailClosedHookPolicy.enabled({"server_info":True,"setup":True})

def test_kdf_returns_only_synthetic_derived_values():
    key,iv=derive_honda_type110_screen_key_iv(bytes(range(16)),18446744073709551615)
    assert len(key)==len(iv)==16 and key!=iv
    secret=SecretBytes(key); assert "<redacted>" in repr(secret); secret.clear(); assert len(secret)==0

def test_response_build_and_merge_failures_close_listener():
    req,stock,_,factory,ip=setup_fixture()
    class BrokenBuilder:
        def build(self,*_): raise RuntimeError("synthetic response build failure")
    ip.response_builder=BrokenBuilder()
    _,result=ip.setup(req)
    assert result==stock and ip.current is None and factory.created[0].closed
    req,_,_,factory,ip=setup_fixture()
    def bad_stock(_): return 0,{"streams":"invalid"}
    ip.stock=StockSetupDelegate(bad_stock)
    _,result=ip.setup(req)
    assert result=={"streams":"invalid"} and ip.current is None and factory.created[0].closed

def test_fake_accept_is_owned_and_failure_can_be_injected():
    req,_,_,factory,ip=setup_fixture()
    ip.setup(req); life=ClarityLinkLifecycleCoordinator(ip); life.session_start(True)
    accepted=ip.current.accept()
    assert accepted is ip.current.accepted_socket
    life.teardown_type111_generation(); assert accepted.closed
    req,_,_,_,ip=setup_fixture(fail_listener="accept")
    ip.setup(req); ClarityLinkLifecycleCoordinator(ip).session_start(True)
    with pytest.raises(Exception): ip.current.accept()
