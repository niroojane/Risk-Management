"""Risk Management web app backend.

The analytics come from the project's shared `src` package, one folder up (also used by
the notebooks and the Streamlit app): make that folder importable.
"""
import sys
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
if _PROJECT_ROOT not in sys.path:
    sys.path.append(_PROJECT_ROOT)
