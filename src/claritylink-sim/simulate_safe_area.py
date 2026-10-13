"""Run the P2-C4 synthetic Display 1 safe-area withdrawal scenario offline."""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/claritylink-renderer"))

from model import ClarityLinkRenderer, MockDisplay1Backend, SyntheticPatternSource  # noqa: E402
from safe_area import SafeAreaConfig, SafeAreaGate  # noqa: E402


def run() -> dict[str, object]:
    schema = json.loads((ROOT / "research/architecture/p2c4-safe-area.schema.json").read_text())
    config = SafeAreaConfig.from_mapping(schema["examples"][0])
    backend = MockDisplay1Backend()
    renderer = ClarityLinkRenderer(backend, safe_area=SafeAreaGate(config))
    source = SyntheticPatternSource()
    renderer.start()
    renderer.submit(source.next_frame())
    first = backend.frames[-1].rgba
    assert first is not None
    visible = sum(first[offset + 3] != 0 for offset in range(0, len(first), 4))
    renderer.warning_preempted()
    warning_withdrawn = not backend.frames
    renderer.warning_cleared()
    renderer.submit(source.next_frame())
    renderer.surface_lost()
    surface_withdrawn = not backend.frames
    renderer.surface_restored()
    renderer.submit(source.next_frame())
    recovered = len(backend.frames) == 1
    renderer.close()
    return {
        "provenance": "SYNTHETIC_TEST_ONLY",
        "canvas": [800, 480],
        "visible_pixels": visible,
        "maximum_permitted_pixels": 600 * 360 - 200 * 80,
        "warning_withdrawn": warning_withdrawn,
        "surface_withdrawn": surface_withdrawn,
        "recovered": recovered,
        "closed": backend.target is None and not backend.frames,
    }


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True))
