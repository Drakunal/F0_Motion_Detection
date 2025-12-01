from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]  # project/app/..
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "images.db"
