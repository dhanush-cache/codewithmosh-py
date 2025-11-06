import os
from pathlib import Path

ON_ANDROID = "ANDROID_STORAGE" in os.environ
HOME = Path("/sdcard") if ON_ANDROID else Path.home()
TEMP = HOME / "tmp"
TEMP.mkdir(parents=True, exist_ok=True)
DOWNLOADS = next(HOME.glob("Download*"))
CACHE = Path("cache")
