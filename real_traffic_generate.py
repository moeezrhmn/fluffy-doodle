"""
Real browser traffic generator — fires actual GA events via headless Chromium.
Goal: generate genuine engagement signals to help Google index the subdomain.

Install: pip install playwright && playwright install chromium
Run:     python real_traffic_generate.py
"""

import os
import time
import random
import logging
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

load_dotenv()

# ── Configuration ──────────────────────────────────────────────────────────────

TARGET_ORIGIN = "https://moeezrehman.quanter.dev"

PROXY_URL = os.getenv("IP2WORLD_PROXY")  # e.g. http://user:pass@host:port

PAGES = [
    "/",
    "/about",
    "/projects",
    "/contact",
    "/blog",
    "/services",
    "/portfolio",
]

REFERRERS = [
    None,                                          # direct (weighted 3x)
    None,
    None,
    "https://www.linkedin.com/",
    "https://www.linkedin.com/in/moeezrhmn",
    "https://github.com/moeezrhmn",
    "https://twitter.com/",
    "https://www.facebook.com/",
    "https://linktr.ee/",
    "https://t.co/",
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
]

# Viewport sizes (desktop + mobile mix)
VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1440, "height": 900},
    {"width": 1366, "height": 768},
    {"width": 1280, "height": 800},
    {"width": 390,  "height": 844},   # iPhone 14
    {"width": 412,  "height": 915},   # Android
]

# Read time per page in seconds (lo, hi)
PAGE_READ_TIME = {
    "/":          (10, 30),
    "/about":     (15, 45),
    "/projects":  (20, 60),
    "/portfolio": (20, 60),
    "/blog":      (30, 90),
    "/services":  (10, 35),
    "/contact":   (5,  15),
}
DEFAULT_READ_TIME = (8, 30)

SESSION_DEPTH        = (1, 5)
INTER_PAGE_DELAY     = (2, 6)    # seconds between page navigations
INTER_SESSION_DELAY  = (20, 60)  # seconds between sessions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("traffic")


# ── Helpers ────────────────────────────────────────────────────────────────────

def proxy_config():
    if not PROXY_URL:
        log.warning("IP2WORLD_PROXY not set — no proxy used")
        return None
    # Playwright proxy format
    parts = PROXY_URL.replace("http://", "").replace("https://", "")
    if "@" in parts:
        creds, server = parts.rsplit("@", 1)
        username, password = creds.split(":", 1)
        return {"server": f"http://{server}", "username": username, "password": password}
    return {"server": f"http://{parts}"}


def read_delay(path: str) -> float:
    lo, hi = PAGE_READ_TIME.get(path, DEFAULT_READ_TIME)
    return max(lo * 0.6, random.gauss((lo + hi) / 2, (hi - lo) / 6))


def human_scroll(page, path: str):
    """Scroll down gradually then back up — simulates reading."""
    try:
        page_height = page.evaluate("document.body.scrollHeight")
        viewport_h  = page.viewport_size["height"]

        if page_height <= viewport_h:
            return  # page fits in one screen, no scroll needed

        # Scroll down in small random steps
        current = 0
        while current < page_height * 0.85:
            step = random.randint(80, 250)
            current = min(current + step, page_height)
            page.evaluate(f"window.scrollTo({{top: {current}, behavior: 'smooth'}})")
            time.sleep(random.uniform(0.3, 1.2))

        # Pause at bottom (finished reading)
        time.sleep(random.uniform(1, 3))

        # Scroll back to top (like a real user before clicking next link)
        page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
        time.sleep(random.uniform(0.5, 1.5))

    except Exception:
        pass  # non-critical


def pick_next_page(visited: list) -> str:
    candidates = [p for p in PAGES if p not in visited] or PAGES
    weights = [3 if p == "/" else 1 for p in candidates]
    return random.choices(candidates, weights=weights, k=1)[0]


def wait_for_ga(page, timeout_ms: int = 5000):
    """Wait until GA has sent at least one beacon (confirms event fired)."""
    try:
        page.wait_for_function(
            "() => window.ga || window.gtag || window.dataLayer?.length > 0",
            timeout=timeout_ms,
        )
    except PWTimeout:
        pass  # GA might not be installed — not a failure


# ── Session ────────────────────────────────────────────────────────────────────

def run_session(session_id: int, browser_type):
    ua       = random.choice(USER_AGENTS)
    viewport = random.choice(VIEWPORTS)
    referrer = random.choice(REFERRERS)
    depth    = random.randint(*SESSION_DEPTH)
    visited  = []

    proxy = proxy_config()

    context_opts = {
        "user_agent": ua,
        "viewport": viewport,
        "locale": random.choice(["en-US", "en-GB", "en-CA", "en-AU"]),
        "timezone_id": random.choice(["America/New_York", "America/Chicago",
                                       "America/Los_Angeles", "Europe/London",
                                       "Australia/Sydney"]),
        "java_script_enabled": True,
    }
    if proxy:
        context_opts["proxy"] = proxy

    log.info(
        f"[S{session_id}] depth={depth}  ua={ua[23:50]}...  "
        f"ref={'direct' if not referrer else referrer[8:35]}"
    )

    with browser_type.new_context(**context_opts) as ctx:
        page = ctx.new_page()

        # Block images, fonts, and media — keeps JS/CSS/GA loading, saves ~70% bandwidth
        def block_heavy_resources(route):
            if route.request.resource_type in ("image", "media", "font"):
                route.abort()
            else:
                route.continue_()

        page.route("**/*", block_heavy_resources)

        for step in range(depth):
            path = pick_next_page(visited)
            url  = TARGET_ORIGIN + path

            nav_opts = {}
            if referrer and step == 0:
                nav_opts["referer"] = referrer

            loaded = False
            for attempt in range(3):
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=30_000, **nav_opts)
                    loaded = True
                    break
                except PWTimeout:
                    log.warning(f"[S{session_id}] Timeout on {path} (attempt {attempt+1})")
                except Exception as exc:
                    log.warning(f"[S{session_id}] Error on {path} (attempt {attempt+1}): {exc}")
                time.sleep(2)
            if not loaded:
                break

            visited.append(path)
            wait_for_ga(page)

            dwell = read_delay(path)
            log.info(f"[S{session_id}] step={step+1}/{depth}  {path}  dwell={dwell:.1f}s")

            human_scroll(page, path)

            # remaining dwell after scrolling
            time.sleep(max(1, dwell - 3))

            if step < depth - 1:
                time.sleep(random.uniform(*INTER_PAGE_DELAY))

    log.info(f"[S{session_id}] Done — {' → '.join(visited)}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    proxy = proxy_config()
    log.info(f"Target  : {TARGET_ORIGIN}")
    log.info(f"Proxy   : {proxy['server'] if proxy else 'none'}")
    log.info("Starting — Ctrl+C to stop\n")

    session_id = 1
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",  # hide automation flag
                "--disable-dev-shm-usage",
            ],
        )
        try:
            while True:
                run_session(session_id, browser)
                session_id += 1
                gap = random.uniform(*INTER_SESSION_DELAY)
                log.info(f"Next session in {gap:.0f}s ...\n")
                time.sleep(gap)
        except KeyboardInterrupt:
            log.info(f"\nStopped after {session_id - 1} session(s).")
        finally:
            browser.close()


if __name__ == "__main__":
    main()
