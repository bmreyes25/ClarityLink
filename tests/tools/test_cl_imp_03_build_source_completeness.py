"""CL-HONDA-111-02: the explicit API17 source list must be dependency-complete.

`tools/build_cl_imp_03_apks.sh` deliberately compiles an explicit source list
(no broad globbing). That is safe, but it means a renderer class added to the
source tree and used by a listed file fails the CI build only when the emulator
workflow runs. This test checks, offline, that every renderer class referenced
by any listed source is itself listed, without replacing the list with a glob.
"""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "tools/build_cl_imp_03_apks.sh"
RENDERER_DIR = REPO / "src/claritylink-renderer/android-api17"

# Renderer classes that the lab build intentionally does not ship. Each entry
# needs a reason; adding one here is a reviewed decision, not a convenience.
INTENTIONALLY_EXCLUDED = {
    "NavigationUpdate": "structured-navigation path, built by build_cl_factory_03_api17_apk.sh",
    "NavigationGenerationLedger": "structured-navigation path",
    "StructuredNavigationContentView": "structured-navigation path",
    "StructuredNavigationOutputBackend": "structured-navigation path",
    "StructuredNavigationSink": "structured-navigation path",
}


def _listed_sources():
    text = SCRIPT.read_text()
    first = text.index('"${JAVAC:-javac}"')
    block = text[first:text.index("mkdir -p \"$out/assets\"")]
    return [REPO / m.replace("$repo/", "") for m in re.findall(r'"(\$repo/[^"]+\.java)"', block)]


def _strip_comments(src: str) -> str:
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"//[^\n]*", "", src)


def test_every_listed_source_exists():
    listed = _listed_sources()
    assert listed, "no sources parsed from the build script"
    assert [p for p in listed if not p.is_file()] == []
    assert len(set(listed)) == len(listed), "duplicate source in the explicit list"


def test_new_pane_classes_are_compiled_into_the_lab_apk():
    names = {p.name for p in _listed_sources()}
    assert {"PaneEvent.java", "PaneLease.java"} <= names


def test_renderer_dependency_closure_is_listed():
    listed = _listed_sources()
    listed_renderer = {p.stem for p in listed if p.parent == RENDERER_DIR}
    renderer_classes = {p.stem for p in RENDERER_DIR.glob("*.java")}
    missing = {}
    for path in listed:
        body = _strip_comments(path.read_text())
        for cls in renderer_classes - {path.stem}:
            if cls in listed_renderer or cls in INTENTIONALLY_EXCLUDED:
                continue
            if re.search(r"\b%s\b" % re.escape(cls), body):
                missing.setdefault(cls, []).append(path.name)
    assert missing == {}, "renderer classes used but not compiled: %r" % missing


def test_excluded_classes_are_not_used_by_the_listed_sources():
    listed = _listed_sources()
    for path in listed:
        body = _strip_comments(path.read_text())
        for cls in INTENTIONALLY_EXCLUDED:
            assert not re.search(r"\b%s\b" % cls, body), (cls, path.name)


def test_script_still_uses_an_explicit_list_not_a_glob():
    text = SCRIPT.read_text()
    first = text.index('"${JAVAC:-javac}"')
    block = text[first:text.index("mkdir -p \"$out/assets\"")]
    assert "find " not in block and "*.java" not in block
    assert "-source 1.7 -target 1.7" in block
