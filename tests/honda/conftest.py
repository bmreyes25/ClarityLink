import sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[2]
for p in (ROOT/'src/claritylink-honda',ROOT/'src/claritylink-interposer',ROOT/'tools/honda-readonly-preflight'):
    sys.path.insert(0,str(p))


@pytest.fixture(autouse=True)
def provide_synthetic_adb_executable(monkeypatch):
    """Let host-only command-plan tests run without installing or invoking ADB."""
    import collector

    real_which = collector.shutil.which

    def which(command, *args, **kwargs):
        if command == "adb":
            return "/synthetic-test-tools/adb"
        return real_which(command, *args, **kwargs)

    monkeypatch.setattr(collector.shutil, "which", which)
