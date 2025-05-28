
from app.services.plagiarism import service as plagiarism_service, preprocess, crawler, similarity_calculation
from app.services import ai_detection

from fastapi import APIRouter, UploadFile, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from app.config import settings, redis_client

from urllib.parse import urlparse
from functools import lru_cache
from docx import Document
from typing import List

import traceback, requests, json


router = APIRouter()

CHUNK_SIZE = 300 

# @lru_cache(maxsize=200)
def google_search(query):
    BLOCKLIST_DOMAINS = {
        'reddit.com',
        'twitter.com',
        'x.com',
        'facebook.com',
        'instagram.com',
        'tiktok.com',
        'pinterest.com',
        'quora.com',
        'support.google.com',
        'ux.stackexchange.com',
        'stackexchange.com',
        'discussions.apple.com'
    }
    
    # Refine query to exclude unwanted sites
    refined_query = f"{query} -filetype:pdf -site:reddit.com -site:twitter.com -site:x.com "
    
    url = f"https://www.googleapis.com/customsearch/v1?key={settings.GOOGLE_CUSTOM_SEARCH_API_KEY}&cx={settings.GOOGLE_CUSTOM_SEARCH_ENGINE_ID}&q={refined_query}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        results = response.json().get("items", [])
        
        # Filter out URLs from blocklisted domains
        filtered_results = []
        for result in results:
            link = result.get('link', '')
            if not link or '.pdf' in link :
                continue

            domain = urlparse(link).netloc.lower()
            if domain.startswith('www.'):
                domain = domain[4:]

            if domain not in BLOCKLIST_DOMAINS:
                filtered_results.append(result)
            # else:
                # print(f"Blocked URL: {link} (Domain: {domain})")
        
        # Log filtered results
        # print('Filtered results: ', [r.get('link', '') for r in filtered_results])s
        print('Search API called ')
        return filtered_results
    except requests.RequestException as e:
        print(f"Error fetching Google Search results: {e}")
        return []




@router.post("/check-plagiarism/")
async def check_plagiarism_and_ai(file: UploadFile):
    try:
        file_name = preprocess.clean_file_names(file.filename)
        content = await file.read()
        file_size = len(content) 
        file.file.seek(0)

        text = await preprocess.extract_file_text(file)
        print('START REQUEST FILE NAME:  ', file_name, file_size)

        text = plagiarism_service.clean_text(text) 
        if len(text) > 8000:       
            text = plagiarism_service.sample_text(text, strategy="smart", max_chars=8000)


        all_results = []
        redis_urls_key = f'urls-{file_name}-{file_size}'
        redis_crawled_pages_key = f'crawled_pages-{file_name}-{file_size}'
        # Chunks for Google search
        chunks_for_search = preprocess.smart_tfidf_chunks(text, 40, 5)
        # Chunks for comparison with crawled data
        chunks_for_comparison = preprocess.simple_split_into_chunks(text)
        # return chunks_for_comparison

        all_urls = json.loads(redis_client.get(redis_urls_key)) if redis_client.get(redis_urls_key) else  []
        if not all_urls:
            for chunk in chunks_for_search:
                search_results = google_search(chunk)
                urls = [r['link'] for r in search_results[:3] if r.get('link')]
                all_urls.extend(urls)

        # Remove duplicates while preserving order
        all_urls = list(dict.fromkeys(all_urls))
        print('Urls: '  , all_urls)
        redis_client.setex(redis_urls_key, 770, json.dumps(all_urls))

        crawled_pages = json.loads(redis_client.get(redis_crawled_pages_key)) if redis_client.get(redis_crawled_pages_key) else await crawler.crawl_urls(all_urls)
        redis_client.setex(redis_crawled_pages_key, 770, json.dumps(crawled_pages))


        for page in iterate_crawled_pages(crawled_pages):
            if not page.get('content'):
                print('no content found! for URL: ', page['url'])
                continue
            
            # print('preprocessed page content: ', page_content[:300])

            for compare_chunk in chunks_for_comparison:
                page_content = plagiarism_service.clean_text(page['content'])
                similarity = similarity_calculation.find_matched_text(compare_chunk, page_content)
                print(similarity)
                if similarity > 0.67:
                    all_results.append({
                        "chunk": compare_chunk,
                        "url": page['url'],
                        "similarity": float(similarity),
                        "title": page['title'],
                        # "page_content": page_content
                    })
            
            if len(all_results) >= 15:
                break

        res = {
            'results': all_results,
        }
        return JSONResponse(status_code=200, content=res)
    except Exception as e:
        
        tb = traceback.extract_tb(e.__traceback__)[0]
        return JSONResponse(
            status_code=400,
            content={
                'error': f"{type(e).__name__}: {str(e)}",
                'file': tb.filename,
                'line': tb.lineno
            }
        )



@router.post("/ai-content-detection")
async def ai_content_detection(file: UploadFile):
    try:
        text = await preprocess.extract_file_text(file)
        text = plagiarism_service.prepare_text_for_api(text)
        if len(text) > 8000:       
            text = plagiarism_service.sample_text(text, strategy="smart", max_chars=8000)

        # Detect AI content
        ai_detection_result = ai_detection.detect(text)
        return JSONResponse(status_code=200, content=ai_detection_result)
    except Exception as e:
        tb = traceback.extract_tb(e.__traceback__)[0]
        return JSONResponse(
            status_code=400,
            content={
                'error': f"{type(e).__name__}: {str(e)}",
                'file': tb.filename,
                'line': tb.lineno
            }
        )


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE) -> List[str]:
    words = text.split()
    return [' '.join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]


def iterate_crawled_pages(crawled_pages):
    for page in crawled_pages:
        yield page 



