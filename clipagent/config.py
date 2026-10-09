from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
JOBS = DATA / "jobs"
MODELS = DATA / "models"
DATABASE = DATA / "clipagent.sqlite3"
DEMO = DATA / "demo"

MAX_FILES = 3
MAX_TOTAL_SECONDS = 15 * 60
MAX_UPLOAD_BYTES = 2 * 1024 * 1024 * 1024
