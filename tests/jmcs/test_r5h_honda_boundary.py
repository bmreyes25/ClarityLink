from pathlib import Path
import sys

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src/claritylink-jmcs"))

from claritylink_jmcs.compat.honda.setup import EvidenceRequired, HondaStaticType110Adapter
from claritylink_jmcs.setup import SetupError


def test_honda_type111_setup_is_rejected_before_assuming_descriptor_fields():
    adapter = HondaStaticType110Adapter()
    request = {"streams": [{"type": 111, "vendor_extension": object()}]}

    with pytest.raises(EvidenceRequired, match="honda_type111_setup_dispatch"):
        adapter.parse_known_request(request, 1)


def test_honda_type111_without_lab_stream_connection_id_remains_unknown():
    adapter = HondaStaticType110Adapter()

    with pytest.raises(EvidenceRequired, match="honda_type111_setup_dispatch"):
        adapter.parse_known_request({"streams": [{"type": 111}]}, 1)


def test_static_honda_type110_contract_still_parses_and_builds_known_response():
    adapter = HondaStaticType110Adapter()
    request = adapter.parse_known_request(
        {"streams": [{"type": 110, "streamConnectionID": 0x1122334455667788}]}, 7
    )

    assert request.session_generation == 7
    assert request.streams[0].type == 110
    assert adapter.known_response_entry(49231) == {"type": 110, "dataPort": 49231}


def test_malformed_honda_setup_root_still_fails_closed():
    adapter = HondaStaticType110Adapter()

    with pytest.raises(SetupError, match="invalid_setup_root"):
        adapter.parse_known_request([], 1)


def test_honda_type111_response_schema_remains_unimplemented():
    adapter = HondaStaticType110Adapter()

    with pytest.raises(EvidenceRequired, match="honda_type111_response_schema"):
        adapter.type111_response({"type": 111}, 49231)
