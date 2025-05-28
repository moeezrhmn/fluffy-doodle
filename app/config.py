# App configuration
from dotenv import load_dotenv
import os, re
import redis
load_dotenv()


class Settings():
    REQUEST_TIMEOUT: str = os.getenv('REQUEST_TIMEOUT')
    
    TEMP_MAIL_DOMAIN = os.getenv("TEMP_MAIL_DOMAIN")
    TEMP_MAIL_USERNAME = os.getenv("TEMP_MAIL_USERNAME")
    TEMP_MAIL_PASSWORD = os.getenv("TEMP_MAIL_PASSWORD")
    EMAIL_EXPIRY = int(os.getenv("EMAIL_EXPIRY", "600"))  # 10 minutes in seconds
    
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB = int(os.getenv("REDIS_DB", "0"))

    # Integrations 
    IP2WORLD_PROXY: str = os.getenv('IP2WORLD_PROXY')
    IP2WORLD_STICKY_PROXY: str = os.getenv('IP2WORLD_STICKY_PROXY')    

    GOOGLE_CUSTOM_SEARCH_API_KEY: str = os.getenv('GOOGLE_CUSTOM_SEARCH_API_KEY')
    GOOGLE_CUSTOM_SEARCH_ENGINE_ID: str = os.getenv('GOOGLE_CUSTOM_SEARCH_ENGINE_ID')

    HUGGING_FACE_API_KEY: str = os.getenv('HUGGING_FACE_API_KEY')

    GO_WINSTON_BASE_URL: str = os.getenv('GO_WINSTON_BASE_URL')
    GO_WINSTON_API_KEY: str = os.getenv('GO_WINSTON_AI_API_KEY')

    RAPID_API_KEY: str = os.getenv('RAPID_API_KEY')



settings = Settings()


redis_client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB)


DOWNLOAD_DIR='downloads'
MAX_SIZE_LIMIT=50
VIDEO_FORMAT_QUALITY = 'best[height<=480]'
PROXIES=[
    {"http": "socks5://198.12.249.249:62529", "https": "socks5://198.12.249.249:62529"},
    {"http": "http://108.170.12.11:80", "https": "http://108.170.12.11:80"},
    {"http": "http://68.188.93.171:8080", "https": "http://68.188.93.171:8080"},
    {"http": "http://51.254.132.238:80", "https": "http://51.254.132.238:80"},
    {"http": "https://164.163.42.2:10000", "https": "https://164.163.42.2:10000"}
]

VALID_VIDEO_DOMAINS = re.compile(r"^(https?:\/\/)?(www\.)?"
                                r"(facebook\.com|fb\.watch|instagram\.com|instagr\.am|youtube\.com|youtu\.be)", re.IGNORECASE)

IP2WORLD_PROXY= settings.IP2WORLD_PROXY
IP2WORLD_STICKY_PROXY= settings.IP2WORLD_STICKY_PROXY