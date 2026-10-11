"""Reset data/campus_customs_new.db to the original shop data before a full run."""

import shutil
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
ORIGINAL = DATA_DIR / "campus_customs.db"
WORKING = DATA_DIR / "campus_customs_new.db"

if __name__ == "__main__":
    shutil.copyfile(ORIGINAL, WORKING)
    WORKING.chmod(0o644)
    print(f"Reset {WORKING.name} from {ORIGINAL.name}")
