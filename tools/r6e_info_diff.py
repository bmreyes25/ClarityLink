#!/usr/bin/env python3
"""R6E path/type/count comparison; never print field values."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from r6b_info_diff import compare, load


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("reference", type=Path)
    parser.add_argument("candidate", type=Path)
    args = parser.parse_args()
    older = compare(load(args.reference), load(args.candidate))
    result = {
        "missing_path": older["missing_fields"],
        "extra_path": older["extra_fields"],
        "type_mismatch": older["type_mismatch"],
        "array_size_difference": [x for x in older["value_family_mismatch"] + older["display_mismatch"] if x.endswith(".count")],
        "capability_family_mismatch": older["feature_mismatch"] + [
            x for x in older["value_family_mismatch"] + older["display_mismatch"] if not x.endswith(".count")],
        "unknown_field": older["unknown_field"],
    }
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
