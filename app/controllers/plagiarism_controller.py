
from app.services.plagiarism import service as plagiarism_service, preprocess, crawler, similarity_calculation
from app.services import ai_detection

from fastapi import APIRouter, UploadFile, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from app.config import settings

from urllib.parse import urlparse
from functools import lru_cache
from docx import Document
from typing import List

import traceback, requests


router = APIRouter()

CHUNK_SIZE = 300 

@lru_cache(maxsize=200)
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
        'support.google.com'
    }
    
    # Refine query to exclude unwanted sites
    refined_query = f"{query} -site:reddit.com -site:twitter.com -site:x.com"
    
    url = f"https://www.googleapis.com/customsearch/v1?key={settings.GOOGLE_CUSTOM_SEARCH_API_KEY}&cx={settings.GOOGLE_CUSTOM_SEARCH_ENGINE_ID}&q={refined_query}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        results = response.json().get("items", [])
        
        # Filter out URLs from blocklisted domains
        filtered_results = []
        for result in results:
            link = result.get('link', '')
            if not link:
                continue
            # Normalize domain by removing 'www.' prefix
            domain = urlparse(link).netloc.lower()
            if domain.startswith('www.'):
                domain = domain[4:]
            if domain not in BLOCKLIST_DOMAINS:
                filtered_results.append(result)
            # else:
                # print(f"Blocked URL: {link} (Domain: {domain})")
        
        # Log filtered results
        # print('Filtered results: ', [r.get('link', '') for r in filtered_results])
        
        return filtered_results
    except requests.RequestException as e:
        print(f"Error fetching Google Search results: {e}")
        return []




@router.post("/check-plagiarism/")
async def check_plagiarism_and_ai(file: UploadFile):
    try:
        text = await preprocess.extract_file_text(file)
        
        text = plagiarism_service.prepare_text_for_api(text) 
        if len(text) > 8000:       
            text = plagiarism_service.sample_text(text, strategy="smart", max_chars=8000)
                
        all_results = []
        # Chunks for Google search
        chunks_for_search = preprocess.smart_tfidf_chunks(text, 40, 5)
        # Chunks for comparison with crawled data
        chunks_for_comparison = preprocess.split_into_chunks(text, 20, 200)
       
        all_urls = []
        for chunk in chunks_for_search:
            search_results = google_search(chunk)
            urls = [r['link'] for r in search_results[:3] if r.get('link')]
            all_urls.extend(urls)

        # Remove duplicates while preserving order
        all_urls = list(dict.fromkeys(all_urls))
        print('Urls: '  , all_urls)

        # Crawl all URLs in one go
        if all_urls:
            crawled_pages = await crawler.crawl_urls(all_urls)
        else:
            crawled_pages = []

        for page in iterate_crawled_pages(crawled_pages):
            if not page.get('content'):
                print('no content found! for URL: ', page['url'])
                continue
            
            page_content = preprocess.preprocess_text(page['content'])
            print('preprocessed page content: ', page_content[:300])

            for compare_chunk in chunks_for_comparison:
                preprocessed_chunk = preprocess.preprocess_text(compare_chunk)
                similarity = similarity_calculation.compare_similarity(preprocessed_chunk, page_content)

                if similarity > 0.53:
                    all_results.append({
                        "chunk": compare_chunk,
                        "url": page['url'],
                        "similarity": similarity,
                        "title": page['title'],
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



