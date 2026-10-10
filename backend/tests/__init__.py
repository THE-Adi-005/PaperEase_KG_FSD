import sys
from pathlib import Path

# Add project root and backend to sys.path
project_root = Path(__file__).resolve().parent.parent.parent
backend_dir = project_root / "backend"

for p in [str(project_root), str(backend_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)
