import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
for p in (ROOT/'src/claritylink-honda',ROOT/'src/claritylink-interposer'):
    sys.path.insert(0,str(p))
