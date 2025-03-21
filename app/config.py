# App configuration
import os, re


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

# IP2WORLD_PROXY= os.getenv('PROXY_SERVER')
IP2WORLD_PROXY= "http://downloader-zone-resi:903090@d50562158869c95b.nbd.us.ip2world.vip:6001"
IP2WORLD_STICKY_PROXY= "http://downloader-zone-resi-session-d09ecace1ed0-sessTime-1:903090@d50562158869c95b.gfh.de.ip2world.vip:6001"
# IP2WORLD_PROXY = "http://downloader-zone-resi:903090@d50562158869c95b.gfh.de.ip2world.vip:6001"
# proxy_url = "http://downloader-zone-resi:903090@pr.ip2world.com:6001"