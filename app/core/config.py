from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]  # project/app/..
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "images.db"

# retention settings
PRE_MOTION_BUFFER = 3           # keep N previous frames when motion detected
RETENTION_HOURS = 24            # delete files older than 24 hours
KEEP_ALL_FRAMES = False         # if True, disable deletion
CLEANUP_INTERVAL_SECONDS = 60 * 60  # run periodic cleanup every hour
