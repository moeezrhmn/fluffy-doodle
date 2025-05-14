import aiohttp
import asyncio
import trafilatura
import pdfplumber
from io import BytesIO
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Referer': 'https://www.google.com/'
}

async def fetch_url(session, url, semaphore, retries=3, backoff_factor=1):
    async with semaphore:
        for attempt in range(retries):
            try:
                async with session.get(url, headers=headers, timeout=15) as response:
                    if response.status == 403:
                        logger.warning(f"403 Forbidden for {url}, attempt {attempt + 1}/{retries}")
                        if attempt < retries - 1:
                            await asyncio.sleep(backoff_factor * (2 ** attempt))
                        continue
                    elif response.status != 200:
                        logger.warning(f"Failed to fetch {url}: Status {response.status}")
                        return {'url': url, 'content': None, 'title': None}
                    
                    content_type = response.headers.get('Content-Type', '').lower()
                    content = await response.read()

                    if 'text/html' in content_type:
                        html = content.decode('utf-8', errors='ignore')
                        extracted = trafilatura.extract(html, include_comments=False, include_tables=False)
                        soup = BeautifulSoup(html, 'html.parser')
                        title = soup.title.string if soup.title else 'Untitled'
                        return {'url': url, 'content': extracted or '', 'title': title}
                    
                    elif 'application/pdf' in content_type:
                        if len(content) > 10_000_000:  # Skip PDFs larger than 10MB
                            logger.warning(f"Skipping large PDF {url}: {len(content)} bytes")
                            return {'url': url, 'content': None, 'title': None}
                        try:
                            pdf_file = BytesIO(content)
                            with pdfplumber.open(pdf_file) as pdf:
                                text = '\n'.join(page.extract_text() or '' for page in pdf.pages[:30])  # Limit to first 30 pages
                            return {'url': url, 'content': text, 'title': url}
                        except Exception as e:
                            logger.error(f"Failed to process PDF {url}: {str(e)}")
                            return {'url': url, 'content': None, 'title': None}
                    
                    else:
                        logger.warning(f"Unsupported content type for {url}: {content_type}")
                        return {'url': url, 'content': None, 'title': None}
                    
            except Exception as e:
                logger.error(f"Error fetching {url}: {str(e)}, attempt {attempt + 1}/{retries}")
                if attempt < retries - 1:
                    await asyncio.sleep(backoff_factor * (2 ** attempt))
                continue

        logger.error(f"Failed to fetch {url} after {retries} attempts")
        return {'url': url, 'content': None, 'title': None}



async def crawl_urls(urls, max_concurrency=7):
    semaphore = asyncio.Semaphore(max_concurrency)
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_url(session, url, semaphore) for url in urls]
        return await asyncio.gather(*tasks, return_exceptions=True)