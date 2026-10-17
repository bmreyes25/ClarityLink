import os
import subprocess
import tempfile
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
BUILD_SCRIPT = REPO / "tools/build_cl_imp_03_apks.sh"


def run_build_guard(path: Path) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["CL_IMP_03_BUILD_DIR"] = str(path)
    return subprocess.run(
        ["sh", str(BUILD_SCRIPT)],
        cwd=REPO,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )


def test_refuses_nonempty_unmarked_build_directory_without_touching_contents():
    with tempfile.TemporaryDirectory(prefix="cl-r4-guard-", dir="/tmp") as temp:
        output = Path(temp)
        protected = output / "classes"
        protected.mkdir()
        sentinel = protected / "keep.txt"
        sentinel.write_text("preserve")

        result = run_build_guard(output)

        assert result.returncode != 0
        assert "Build output must be a fresh path" in result.stdout
        assert sentinel.read_text() == "preserve"


def test_refuses_existing_marked_directory_without_touching_contents():
    with tempfile.TemporaryDirectory(prefix="cl-r4-guard-", dir="/tmp") as temp:
        temp = Path(temp)
        output = temp
        (output / ".claritylink-build-root").write_text(str(REPO) + "\n")
        sentinel = output / "keep.txt"
        sentinel.write_text("preserve")

        result = run_build_guard(output)

        assert result.returncode != 0
        assert "Build output must be a fresh path" in result.stdout
        assert sentinel.read_text() == "preserve"


def test_refuses_symlinked_output_path():
    with tempfile.TemporaryDirectory(prefix="cl-r4-guard-", dir="/tmp") as temp:
        temp = Path(temp)
        target = temp / "target"
        target.mkdir()
        (target / "keep.txt").write_text("preserve")
        output = temp.parent / (temp.name + "-link")
        output.symlink_to(target, target_is_directory=True)
        try:
            result = run_build_guard(output)
            assert result.returncode != 0
            assert "Build output must be a fresh path" in result.stdout
            assert (target / "keep.txt").read_text() == "preserve"
        finally:
            output.unlink()
