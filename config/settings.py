from pathlib import Path

# Базовая директория проекта

BASE_DIR = Path(__file__).resolve().parent.parent

# -------------------------------------------------------------------------
# AMG
# -------------------------------------------------------------------------

# Пути к файлам и папкам

BASE_USERS_DIR = BASE_DIR / "data/permanent/users"
TELEGRAM_VIDEOS_DIR = BASE_DIR / "7874147018:AAHCxjTsjL7AY8iBNpRcUvlfSUHfmx8Os6c/videos"
TELEGRAM_DOCS_DIR = BASE_DIR / "7874147018:AAHCxjTsjL7AY8iBNpRcUvlfSUHfmx8Os6c/documents"

# Telegram-bot

TOKEN = "..."

ADMIN_IDS = [622328140, 987654321, 7934770455, 7874147018]

api_server_link = "http://localhost:8081"

ALLOWED_EXTENSIONS = {".mp4", ".mkv", ".avi"}

# -------------------------------------------------------------------------
# Timer2334
# -------------------------------------------------------------------------

VIDEO_PATH = BASE_DIR / "data" / "temp"
AUDIO_PATH = BASE_DIR / "data" / "temp"
OUTPUT_PATH = BASE_DIR / "data" / "temp"
TYPESCRIPT_PATH = Path("src") / "services" / "node-app" / "get_audio_download_link.ts"
TOKEN_FOR_YANDEX = ""
