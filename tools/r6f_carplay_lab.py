#!/usr/bin/env python3
"""R6F Mac lab CLI; all real-session modes fail closed without an authority."""
from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from r6e_real_ios_lab import main

if __name__ == "__main__":
    raise SystemExit(main())
