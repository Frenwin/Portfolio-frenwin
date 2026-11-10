import sys
from pathlib import Path

# Make `ingestion` importable when pytest runs from the project folder.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
