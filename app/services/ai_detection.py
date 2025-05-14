
from app.config import settings

import requests





def detect(content: str):

    url = "https://ai-content-detector-ai-gpt.p.rapidapi.com/api/detectText/"

    payload = { "text": content }
    headers = {
        "x-rapidapi-key": settings.RAPID_API_KEY,
        "x-rapidapi-host": "ai-content-detector-ai-gpt.p.rapidapi.com",
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)
    return response.json()