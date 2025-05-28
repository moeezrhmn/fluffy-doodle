
import requests, random, re, httpx, subprocess, json
from app.config import settings
from bs4 import BeautifulSoup



MAX_CHARS_TO_SEND = 5000

async def ai_content_detect(text: str):
    base_url = settings.GO_WINSTON_BASE_URL
    api_key = settings.GO_WINSTON_API_KEY
    url = f"{base_url}/ai-content-detection"
    
    headers = {
        'Authorization':'Bearer ' + api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "text": text,
        "sentences": True,
        "version": "latest",
        "language": "en",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        print(response)

    if response.status_code != 200:
        raise Exception(f"Error: {response.status_code} - {response.text}")
    
    return response.json()


async def plagiarised_content_detect(text: str):
    base_url = settings.GO_WINSTON_BASE_URL
    api_key = settings.GO_WINSTON_API_KEY
    url = f"{base_url}/plagiarism"
    
    headers = {
        'Authorization':'Bearer ' + api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "text": text,
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(url, json=payload, headers=headers)

    if response.status_code != 200:
        raise Exception(f"Error: {response.status_code} - {response.text}")
    
    return response.json()




def sample_text(text: str, strategy="start", max_chars=MAX_CHARS_TO_SEND):
    text = text.strip()
    if len(text) <= max_chars:
        return text
    
    if strategy == "start":
        return text[:max_chars]

    elif strategy == "random":
        start_index = random.randint(0, len(text) - max_chars)
        return text[start_index:start_index + max_chars]

    elif strategy == "smart":
        third = max_chars // 3
        parts = [
            text[:third],
            text[len(text)//2:len(text)//2 + third],
            text[-third:]
        ]
        return "...\n".join(parts)

    else:
        return text[:max_chars]



def remove_urls(text: str) -> str:
    url_pattern = r'https?://\S+|www\.\S+'
    return re.sub(url_pattern, '', text)



def clean_text(text: str) -> str:
    if not text:
        return ""

    # 1. Remove HTML tags using BeautifulSoup (for safety)
    text = BeautifulSoup(text, "html.parser").get_text()

    # 2. Remove URLs
    text = re.sub(r'https?://\S+|www\.\S+', '', text)

    # 3. Remove email addresses
    text = re.sub(r'\b[\w.-]+?@\w+?\.\w+?\b', '', text)

    # 4. Remove footnotes or citations like [1], (2), etc.
    text = re.sub(r'\[\d+\]|\(\d+\)', '', text)

    # 5. Remove long numeric strings (e.g. 10-digit order numbers, etc.)
    text = re.sub(r'\b\d{6,}\b', '', text)

    # 6. Remove excessive spaces, tabs, newlines
    text = re.sub(r'\s+', ' ', text).strip()

    return text



def run_spider(urls, app):
    with app.app_context():
        result = subprocess.run(
            ['python', 'app/services/plagiarism/crawler.py', json.dumps(urls)],
            capture_output=True,
            text=True
        )
        print(result.stdout)
        if result.returncode != 0:
            raise Exception("Spider failed: " + result.stderr)
    
        return result.stdout