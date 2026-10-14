"""Synthetic host-only bounds and lifecycle checks; no Honda coordinates."""

import json
from pathlib import Path
import random
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/claritylink-renderer"))

from model import ClarityLinkRenderer, DecodedFrame, MockDisplay1Backend  # noqa: E402
from safe_area import Rect, SafeAreaConfig, SafeAreaGate  # noqa: E402


SCHEMA = json.loads((ROOT / "research/architecture/p2c4-safe-area.schema.json").read_text())
EXAMPLE = SCHEMA["examples"][0]


def config(changes=None):
    return SafeAreaConfig.from_mapping(EXAMPLE | (changes or {}))


def full_frame():
    return DecodedFrame(800, 480, "RGBA_8888", 3200, 1,
                        rgba=bytes((11, 22, 33, 255)) * (800 * 480))


def test_schema_and_synthetic_provenance_gate():
    assert SCHEMA["properties"]["provenance"]["const"] == "SYNTHETIC_TEST_ONLY"
    config().validate()
    for change in ({"provenance": "HONDA_OBSERVED"}, {"safe": {"x": 799, "y": 0, "width": 2, "height": 1}},
                   {"protected": [{"x": 0, "y": 480, "width": 1, "height": 1}]},
                   {"scale_numerator": 2}, {"rotation_degrees": 90}, {"canvas_width": 801}):
        with pytest.raises(ValueError):
            config(change).validate()


def test_clipped_frame_never_has_content_outside_safe_or_inside_protected():
    backend = MockDisplay1Backend()
    renderer = ClarityLinkRenderer(backend, safe_area=SafeAreaGate(config()))
    renderer.start()
    renderer.submit(full_frame())
    output = backend.frames[-1].rgba
    assert output is not None
    policy = config()
    nonzero = 0
    for y in range(480):
        for x in range(800):
            pixel = output[(y * 800 + x) * 4:(y * 800 + x + 1) * 4]
            if policy.permits_pixel(x, y):
                assert pixel == bytes((11, 22, 33, 255))
                nonzero += 1
            else:
                assert pixel == b"\x00\x00\x00\x00"
    assert nonzero == 600 * 360 - 200 * 80
    renderer.close()


def test_property_random_rectangles_keep_content_within_configured_safe_area():
    rng = random.Random(0xC1A417)
    for _ in range(100):
        x, y = rng.randrange(800), rng.randrange(480)
        width, height = rng.randrange(1, 801 - x), rng.randrange(1, 481 - y)
        safe = Rect(x, y, width, height)
        protected = Rect(rng.randrange(800), rng.randrange(480), 1, 1)
        policy = config({"safe": vars(safe), "protected": [vars(protected)]})
        policy.validate()
        for _ in range(50):
            px, py = rng.randrange(800), rng.randrange(480)
            if policy.permits_pixel(px, py):
                assert safe.contains_pixel(px, py)
                assert not protected.contains_pixel(px, py)


def test_surface_loss_warning_preemption_recovery_and_invalid_geometry_withdrawal():
    backend = MockDisplay1Backend()
    gate = SafeAreaGate(config())
    renderer = ClarityLinkRenderer(backend, safe_area=gate)
    renderer.start()
    renderer.submit(full_frame())
    renderer.surface_lost()
    assert backend.frames == []
    with pytest.raises(ValueError):
        renderer.submit(full_frame())
    renderer.surface_restored()
    renderer.submit(full_frame())
    renderer.warning_preempted()
    assert backend.frames == []
    with pytest.raises(ValueError):
        renderer.submit(full_frame())
    renderer.warning_cleared()
    renderer.submit(full_frame())
    with pytest.raises(ValueError):
        renderer.update_safe_area(config({"scale_numerator": 2}))
    assert backend.frames == [] and not gate.active
    with pytest.raises(ValueError):
        renderer.submit(full_frame())
    renderer.update_safe_area(config())
    renderer.submit(full_frame())
    bad = DecodedFrame(799, 480, "RGBA_8888", 3196, 1,
                       rgba=bytes((1, 2, 3, 255)) * (799 * 480))
    with pytest.raises(ValueError):
        renderer.submit(bad)
    assert backend.frames == [] and not gate.active
    renderer.close()
