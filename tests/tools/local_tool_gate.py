"""Collection gate for tests whose implementation is intentionally local-only."""
from pathlib import Path

import pytest


def require_local_tools(test_file: str, *tool_names: str) -> None:
    """Keep private-tool tests runnable locally and visibly skipped in clean candidates."""
    root = Path(test_file).resolve().parents[2]
    missing = [name for name in tool_names if not (root / "tools" / name).is_file()]
    if missing:
        pytest.skip(
            "requires local-only tool(s) omitted from this public candidate: " + ", ".join(missing),
            allow_module_level=True,
        )
