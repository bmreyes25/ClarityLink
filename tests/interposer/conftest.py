import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
for p in (ROOT/'src/claritylink-interposer', ROOT/'src/claritylink-negotiation', ROOT/'src/claritylink-transport'):
    sys.path.insert(0,str(p))
