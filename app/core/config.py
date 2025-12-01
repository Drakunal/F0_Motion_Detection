from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]  # project/app/..
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "images.db"

# Retention and buffer settings (tune these)
# Number of previous frames to keep whenever motion is detected
PRE_MOTION_BUFFER = 3           # keep N previous frames when motion is detected

# Maximum age (in hours) for any saved image before automatic deletion
RETENTION_HOURS = 24            # delete any images older than 24 hours

# Whether to keep all frames by default. If False, storage_service will delete
# non-motion frames outside the buffer. (You want False.)
KEEP_ALL_FRAMES = False

# How often the periodic cleanup runs (seconds)
CLEANUP_INTERVAL_SECONDS = 60 * 60  # 1 hour
