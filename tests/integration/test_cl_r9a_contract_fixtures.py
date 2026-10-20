"""Independently authored, offline control-SETUP contract fixtures.

These fixtures exercise generic fail-closed invariants only. They are not
Honda protocol specifications and never call the laboratory receiver.
"""

from copy import deepcopy

import pytest


SUPPORTED = {"altScreen", "viewAreas"}


class ContractRejected(ValueError):
    pass


def validate_contract(info, request, response, owner, readiness):
    """Return accepted features only for one internally consistent transaction."""
    displays = info.get("displays")
    panels = info.get("displayPanels")
    if not isinstance(displays, list) or not isinstance(panels, list):
        raise ContractRejected("display_arrays_missing")
    if len(displays) < 1 or displays != panels:
        raise ContractRejected("display_metadata_inconsistent")
    ids = [d.get("uuid") for d in displays if isinstance(d, dict)]
    if len(ids) != len(displays) or any(not isinstance(x, str) or not x for x in ids):
        raise ContractRejected("display_identity_malformed")
    if len(set(ids)) != len(ids):
        raise ContractRejected("display_identity_not_unique")

    proposals = request.get("features")
    accepted = response.get("enabledFeatures")
    if not isinstance(proposals, list) or not all(isinstance(x, str) for x in proposals):
        raise ContractRejected("feature_proposal_malformed")
    if not isinstance(accepted, list) or not all(isinstance(x, str) for x in accepted):
        raise ContractRejected("enabled_features_absent_or_malformed")
    if len(set(accepted)) != len(accepted) or not set(accepted) <= set(proposals):
        raise ContractRejected("feature_agreement_invalid")
    if not set(accepted) <= SUPPORTED:
        raise ContractRejected("unsupported_feature_accepted")

    if owner.get("session") is None or owner.get("session") != request.get("session"):
        raise ContractRejected("session_owner_mismatch")
    if owner.get("generation") is None or owner.get("generation") != readiness.get("generation"):
        raise ContractRejected("generation_owner_mismatch")
    if "altScreen" in accepted and (len(displays) < 2 or not readiness.get("secondary_transport_ready")):
        raise ContractRejected("secondary_contract_not_ready")
    return tuple(accepted)


def fixture():
    info = {"displays": [{"uuid": "main-uuid", "type": 110}],
            "displayPanels": [{"uuid": "main-uuid", "type": 110}]}
    request = {"session": "session-A", "features": ["altScreen", "viewAreas"]}
    response = {"enabledFeatures": ["viewAreas"]}
    owner = {"session": "session-A", "generation": 7}
    readiness = {"generation": 7, "secondary_transport_ready": False}
    return info, request, response, owner, readiness


def test_main_display_identity_is_preserved_and_feature_agreement_is_subset():
    args = fixture()
    original_main = deepcopy(args[0]["displays"][0])
    assert validate_contract(*args) == ("viewAreas",)
    assert args[0]["displays"][0] == original_main


def test_secondary_identity_must_be_unique_and_transport_ready():
    args = fixture()
    secondary = {"uuid": "cluster-uuid", "type": 111}
    args[0]["displays"].append(secondary)
    args[0]["displayPanels"].append(deepcopy(secondary))
    args[2]["enabledFeatures"] = ["altScreen"]
    args[4]["secondary_transport_ready"] = True
    assert validate_contract(*args) == ("altScreen",)
    args[0]["displays"][1]["uuid"] = "main-uuid"
    args[0]["displayPanels"][1]["uuid"] = "main-uuid"
    with pytest.raises(ContractRejected, match="display_identity_not_unique"):
        validate_contract(*args)


def test_unsupported_proposal_must_not_be_accepted():
    args = fixture()
    args[1]["features"].append("unimplementedFeature")
    args[2]["enabledFeatures"] = ["unimplementedFeature"]
    with pytest.raises(ContractRejected, match="unsupported_feature_accepted"):
        validate_contract(*args)


def test_absent_enabled_features_fails_closed():
    args = fixture()
    args[2].pop("enabledFeatures")
    with pytest.raises(ContractRejected, match="enabled_features_absent"):
        validate_contract(*args)


@pytest.mark.parametrize("bad", [None, {}, [{"uuid": ""}], [{"uuid": 42}],
                                  [{"uuid": "x"}, {"uuid": "x"}]])
def test_malformed_display_metadata_fails_closed(bad):
    args = fixture()
    args[0]["displays"] = bad
    with pytest.raises(ContractRejected):
        validate_contract(*args)


def test_inconsistent_session_owner_fails_closed():
    args = fixture()
    args[3]["session"] = "session-B"
    with pytest.raises(ContractRejected, match="session_owner_mismatch"):
        validate_contract(*args)


def test_incomplete_secondary_transport_readiness_fails_closed():
    args = fixture()
    secondary = {"uuid": "cluster-uuid", "type": 111}
    args[0]["displays"].append(secondary)
    args[0]["displayPanels"].append(deepcopy(secondary))
    args[2]["enabledFeatures"] = ["altScreen"]
    with pytest.raises(ContractRejected, match="secondary_contract_not_ready"):
        validate_contract(*args)
