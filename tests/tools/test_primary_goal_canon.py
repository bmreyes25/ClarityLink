"""Guards the canonical ClarityLink goal so it cannot drift back to ambiguity.

Documentation checks only: they do not exercise Type111 behavior and prove
nothing about a Honda or an iPhone. They keep the goal statement, the ten-stage
traceability matrix and its evidence-category vocabulary consistent.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOAL = ("PRIMARY GOAL: iPhone-origin Type111 secondary CarPlay video on factory "
        "Display 1, simultaneous with normal Type110 on Display 0.")
CANONICAL_DOCS = (
    "docs/project/primary-goal.md",
    "docs/roadmap/finish-line-definition.md",
    "docs/architecture/overview.md",
)
VOCABULARY = {"LAB", "MODEL", "OBSERVED-3P", "STATIC", "PARTIAL", "UNVERIFIED", "MISSING", "N/A"}
CATEGORIES = ("Synthetic lifecycle", "Type111 protocol handling", "iPhone-origin video",
              "Honda receiver integration", "Physical Display 1 output")
# Honda and physical columns must never carry lab or third-party results.
HONDA_COLUMN, PHYSICAL_COLUMN = 5, 6
FORBIDDEN_IN_HONDA_PHYSICAL = {"LAB", "MODEL", "OBSERVED-3P"}
NON_GOALS = ("homemade navigation interface", "turn-by-turn-only widget",
             "modified Honda Navigation APK", "mirroring Display 0",
             "prerecorded video", "simulated navigation frames")
MATRIX_HEADING = "## Ten-stage traceability matrix"


def _read(relative):
    return (ROOT / relative).read_text(encoding="utf-8")


def _table_rows(text, heading):
    section = text.split(heading, 1)[1]
    rows = []
    for line in section.splitlines()[1:]:
        if line.startswith("## "):
            break
        if line.startswith("|") and not re.match(r"^\|[-| ]+\|$", line):
            rows.append([cell.strip() for cell in line.strip().strip("|").split("|")])
    return rows[0], rows[1:]  # header, body


def test_goal_sentence_is_in_every_canonical_document():
    for relative in CANONICAL_DOCS:
        assert GOAL in _read(relative).replace("**", ""), relative


def _section(text, heading):
    return text.split(heading, 1)[1].split("\n## ", 1)[0]


def test_non_goals_are_listed_explicitly_in_their_own_section():
    section = _section(_read("docs/project/primary-goal.md"), "## Explicitly NOT the goal").lower()
    for phrase in NON_GOALS:
        assert phrase.lower() in section, phrase


def test_safety_boundaries_are_stated_in_the_goal_document():
    text = _read("docs/project/primary-goal.md")
    assert "`safeForHonda()` remains `false`" in text
    assert "VEHICLE_DEPLOYMENT_NOT_AUTHORIZED" in text
    assert "nothing here authorizes installation, Honda ADB, firmware writes" in text


def test_matrix_has_ten_stages_and_five_evidence_categories():
    header, rows = _table_rows(_read("docs/project/primary-goal.md"), MATRIX_HEADING)
    assert tuple(header[2:]) == CATEGORIES
    assert [row[0] for row in rows] == [str(n) for n in range(1, 11)]
    assert all(len(row) == 7 for row in rows)


def test_matrix_cells_use_the_controlled_vocabulary():
    _, rows = _table_rows(_read("docs/project/primary-goal.md"), MATRIX_HEADING)
    for row in rows:
        for cell in row[2:]:
            assert cell in VOCABULARY, (row[0], cell)


def test_honda_and_physical_columns_never_claim_lab_or_third_party_results():
    _, rows = _table_rows(_read("docs/project/primary-goal.md"), MATRIX_HEADING)
    for row in rows:
        assert row[HONDA_COLUMN] not in FORBIDDEN_IN_HONDA_PHYSICAL, row
        assert row[PHYSICAL_COLUMN] not in FORBIDDEN_IN_HONDA_PHYSICAL, row


# Ratchet: a cell may only move to a stronger value together with new evidence
# and a deliberate edit of this test. Today nothing is verified on a Honda.
ALLOWED_BY_COLUMN = {
    4: {"UNVERIFIED", "PARTIAL", "N/A", "OBSERVED-3P"},   # iPhone-origin video
    HONDA_COLUMN: {"UNVERIFIED", "MISSING", "N/A"},
    PHYSICAL_COLUMN: {"UNVERIFIED", "N/A"},
}


def test_matrix_columns_cannot_be_silently_strengthened():
    _, rows = _table_rows(_read("docs/project/primary-goal.md"), MATRIX_HEADING)
    for row in rows:
        for column, allowed in ALLOWED_BY_COLUMN.items():
            assert row[column] in allowed, (row[0], column, row[column])


def test_milestone_map_does_not_claim_honda_or_physical_results():
    _, rows = _table_rows(_read("docs/project/primary-goal.md"), "## Milestone → category map")
    for row in rows:
        for cell in (row[4], row[5]):
            assert not cell.lower().startswith("yes"), row


def test_cited_source_paths_exist():
    text = _read("docs/project/primary-goal.md")
    paths = set(re.findall(r"`((?:src|tools|research|docs|tests)/[A-Za-z0-9_./-]+?)`", text))
    paths = {p for p in paths if not p.endswith("/") and "*" not in p}
    missing = sorted(p for p in paths if not (ROOT / p).exists())
    assert not missing, missing


def test_no_stage_is_reported_as_a_bare_pass():
    section = _read("docs/project/primary-goal.md").split(MATRIX_HEADING, 1)[1]
    section = section.split("## What is real", 1)[0]
    assert "PASS" not in section
    assert "UNVERIFIED end to end" in section


def test_milestone_map_covers_the_same_five_categories_and_isolates_nav_lab():
    header, rows = _table_rows(_read("docs/project/primary-goal.md"),
                               "## Milestone → category map")
    assert tuple(header[1:]) == CATEGORIES
    nav_lab = [row for row in rows if "NAV-LAB" in row[0]]
    assert nav_lab, "NAV-LAB must be mapped explicitly"
    protocol, iphone = nav_lab[0][2], nav_lab[0][3]
    assert protocol.replace("*", "") == "no" and iphone.replace("*", "") == "no"
