"""R4B synthetic route-card contract checks."""

from __future__ import annotations

import ast
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "src/claritylink-renderer/turn_cards.py"
sys.path.insert(0, str(MODULE.parent))

from turn_cards import (  # noqa: E402
    ColorMode, FRESH_SECONDS, HEIGHT, LAYOUT, LOST_SECONDS, MAX_STREET_CHARS,
    ManeuverKind, RendererState, Route, RouteState, WarningState, WIDTH, render_card,
)


FIXTURES = json.loads((ROOT / "tests/fixtures/r4b_turn_cards.json").read_text())


def case(name):
    data = FIXTURES[name]
    return render_card(Route.from_mapping(data["route"]), data["now_s"], ColorMode(data["mode"]))


def test_fixture_inventory_and_schema_validation():
    assert len(FIXTURES) == 10
    for data in FIXTURES.values():
        Route.from_mapping(data["route"])
    bad = dict(FIXTURES["simple_left_right"]["route"])
    for change in ({"current_index": 99}, {"generation": True}, {"updated_at_s": -1}, {"source_trusted": "yes"}):
        with pytest.raises(ValueError):
            Route.from_mapping(bad | change)
    for distance in (-1, float("nan"), float("inf")):
        steps = [dict(bad["steps"][0], distance_remaining_m=distance)]
        with pytest.raises(ValueError):
            Route.from_mapping(bad | {"steps": steps})
    with pytest.raises(ValueError):
        Route.from_mapping(bad | {"steps": [dict(bad["steps"][0], maneuver="private_api")]})
    with pytest.raises(ValueError):
        Route.from_mapping(bad | {"steps": [dict(bad["steps"][0], street_name="Bad\nRoad")]})


@pytest.mark.parametrize("kind", list(ManeuverKind))
def test_each_maneuver_is_validated_and_unknown_fails_closed(kind):
    raw = dict(FIXTURES["simple_left_right"]["route"])
    raw["steps"] = [dict(raw["steps"][0], maneuver=kind.value)]
    card = render_card(Route.from_mapping(raw), 100)
    if kind is ManeuverKind.UNKNOWN:
        assert card.warning is WarningState.UNKNOWN_MANEUVER
        assert card.maneuver is None
    else:
        assert card.renderer_state is RendererState.GUIDANCE
        assert card.maneuver == kind.value


def test_layout_is_bounded_and_regions_do_not_overlap():
    assert (WIDTH, HEIGHT) == (800, 480)
    assert all(rect.inside_canvas() for rect in LAYOUT.values())
    rects = list(LAYOUT.values())
    for i, a in enumerate(rects):
        for b in rects[i + 1:]:
            assert a.x + a.width <= b.x or b.x + b.width <= a.x or a.y + a.height <= b.y or b.y + b.height <= a.y


def test_long_and_missing_street_and_next_step():
    long_card = case("long_street_name")
    assert len(long_card.street_text) <= MAX_STREET_CHARS
    assert long_card.street_text.endswith("...")
    assert case("missing_street_name").street_text == "ROAD NAME UNAVAILABLE"
    simple = case("simple_left_right")
    assert simple.next_maneuver == "turn_right"
    assert simple.distance_text == "250 m"
    assert simple.eta_text == "12 min remaining"
    assert simple.progress_text == "Step 1 of 2"
    assert case("freeway_exit").secondary_text == "Use the right lane"


def test_freshness_boundaries_and_warning_suppression():
    raw = FIXTURES["simple_left_right"]["route"]
    route = Route.from_mapping(raw)
    assert render_card(route, 100 + FRESH_SECONDS).renderer_state is RendererState.GUIDANCE
    assert render_card(route, 100 + FRESH_SECONDS + 0.001).warning is WarningState.STALE
    assert render_card(route, 100 + LOST_SECONDS).warning is WarningState.STALE
    assert render_card(route, 100 + LOST_SECONDS + 0.001).warning is WarningState.LOST
    for name, expected in (("stale_update", WarningState.STALE), ("lost_route", WarningState.LOST)):
        card = case(name)
        assert card.warning is expected
        assert card.maneuver is None and card.street_text is None and card.distance_text is None


@pytest.mark.parametrize("state,warning", [
    (RouteState.STALE, WarningState.STALE),
    (RouteState.LOST, WarningState.LOST),
    (RouteState.ERROR, WarningState.ERROR),
    (RouteState.REROUTING, WarningState.REROUTING),
    (RouteState.ARRIVED, WarningState.ARRIVED),
    (RouteState.NOT_STARTED, WarningState.NOT_STARTED),
])
def test_explicit_state_never_leaks_old_turn(state, warning):
    raw = dict(FIXTURES["simple_left_right"]["route"], state=state.value)
    card = render_card(Route.from_mapping(raw), 100)
    assert card.warning is warning
    assert card.maneuver is None


def test_rerouting_arrival_clear_and_untrusted_source():
    assert case("reroute_event").warning is WarningState.REROUTING
    assert case("arrival").warning is WarningState.ARRIVED
    route = Route.from_mapping(FIXTURES["simple_left_right"]["route"])
    assert render_card(route, 100, manual_clear=True).warning is WarningState.CLEARED
    assert render_card(Route.from_mapping(dict(FIXTURES["simple_left_right"]["route"], source_trusted=False)), 100).warning is WarningState.UNTRUSTED_SOURCE
    assert render_card(route, 99).warning is WarningState.ERROR
    assert render_card("bad route", 100).warning is WarningState.ERROR


def test_day_night_and_json_projection():
    assert case("night_mode").mode is ColorMode.NIGHT
    assert case("simple_left_right").mode is ColorMode.DAY
    payload = case("night_mode").to_dict()
    assert payload["canvas"] == {"width": 800, "height": 480}
    assert "MODEL_ONLY" in payload["evidence_label"]
    json.dumps(payload, sort_keys=True)


def test_host_only_dependency_boundary():
    tree = ast.parse(MODULE.read_text())
    imports = {alias.name.split(".")[0] for node in ast.walk(tree)
               if isinstance(node, (ast.Import, ast.ImportFrom))
               for alias in (node.names if isinstance(node, ast.Import) else [ast.alias(node.module or "")])}
    assert imports <= {"__future__", "dataclasses", "enum", "typing"}
    source = MODULE.read_text().lower()
    for forbidden in ("jmcs", "type111", "android", "socket", "listener", "ptrace", "adb", "hondahack"):
        assert forbidden not in source
