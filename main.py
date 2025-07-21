from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from openai import OpenAI
from dotenv import load_dotenv
import os
import requests
from bs4 import BeautifulSoup
import re

# Load .env
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not found in .env.")
if not SERPER_API_KEY:
    raise RuntimeError("SERPER_API_KEY not found in .env.")

client = OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI(
    title="Topic Generator API",
    description="Generates blog topics, outlines, keywords, word count recommendations, and full blog articles.",
    version="1.0.0"
)

# ---------- Models ----------
class TopicRequest(BaseModel):
    niche: str
    intent: str
    audience: str
    keywords: Optional[List[str]] = None

class TopicResponse(BaseModel):
    topics: List[str]

class KeywordOutlineRequest(BaseModel):
    topic: str

class KeywordOutlineResponse(BaseModel):
    keywords: List[str]
    outline: str
    recommended_word_count: int

class BlogGenerationRequest(BaseModel):
    topic: str
    keywords: List[str]
    outline: str
    recommended_word_count: int

class BlogGenerationResponse(BaseModel):
    blog: str

class GenerateOutlineRequest(BaseModel):
    topic: str
    intent: str
    audience: str
    keywords: Optional[List[str]] = None

class GenerateOutlineResponse(BaseModel):
    outline: str
    keywords: List[str]
    recommended_word_count: int

# ---------- Endpoints ----------

@app.post("/generate-topics", response_model=TopicResponse)
async def generate_topics(request: TopicRequest):
    keyword_text = f" Include the following keywords in the topic ideas: {', '.join(request.keywords)}." if request.keywords else ""
    prompt = (
        f"Generate 3 to 5 creative blog topic ideas in the niche '{request.niche}', "
        f"with the intent of '{request.intent}', targeted at '{request.audience}'."
        f"{keyword_text} Return the topics as a numbered list."
    )
    try:
        completion = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful marketing assistant that generates blog topic ideas."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=300
        )
        raw_text = completion.choices[0].message.content.strip()
        topics = []
        for line in raw_text.split("\n"):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith("-")):
                topic = line.lstrip("0123456789.-) ").strip()
                if topic:
                    topics.append(topic)
        if not topics:
            raise ValueError("No topics were generated.")
        return TopicResponse(topics=topics)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-outline", response_model=GenerateOutlineResponse)
async def generate_outline(request: GenerateOutlineRequest):
    try:
        serper_url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": SERPER_API_KEY
        }
        payload = {
            "q": request.topic,
            "num": 3
        }
        serper_response = requests.post(serper_url, json=payload, headers=headers)
        serper_response.raise_for_status()
        search_data = serper_response.json()

        organic_results = search_data.get("organic", [])
        urls = [item.get("link") for item in organic_results[:3] if item.get("link")]
        if not urls:
            raise ValueError("No valid URLs found in search results.")

        combined_text = ""
        for url in urls:
            try:
                page = requests.get(url, timeout=10)
                page.raise_for_status()
                soup = BeautifulSoup(page.text, "html.parser")
                text = soup.get_text(separator=" ").strip()
                words = text.split()
                truncated = " ".join(words[:2000])
                combined_text += truncated + "\n"
            except Exception:
                continue

        if not combined_text:
            raise ValueError("No usable content could be extracted from fetched pages.")

        keyword_clause = f"Focus on incorporating the following keywords: {', '.join(request.keywords)}." if request.keywords else ""
        prompt = (
            f"You are an expert SEO content strategist. Based on the reference content below, "
            f"generate a detailed blog outline, suggest 10-15 SEO-friendly keywords, and recommend a word count for the article."
            f"Topic: {request.topic}\nIntent: {request.intent}\nAudience: {request.audience}\n{keyword_clause}\n\n"
            f"REFERENCE CONTENT:\n{combined_text}\n\n"
            f"Return in this format:\n"
            f"Outline:\n<outline here>\n\nKeywords:\n1. keyword1\n...\n\nRecommended Word Count:\n<just the number>"
        )

        completion = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a skilled SEO blog planner."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
            max_tokens=1000
        )

        response_text = completion.choices[0].message.content.strip()

        keywords = []
        outline = ""
        word_count = 0
        in_keywords = in_outline = in_word_count = False

        for line in response_text.split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.lower().startswith("outline"):
                in_outline = True
                in_keywords = in_word_count = False
                continue
            if line.lower().startswith("keywords"):
                in_keywords = True
                in_outline = in_word_count = False
                continue
            if line.lower().startswith("recommended word count"):
                in_word_count = True
                in_outline = in_keywords = False
                continue
            if in_outline:
                outline += line + "\n"
            elif in_keywords:
                kw = line.lstrip("0123456789.-) ").strip()
                if kw:
                    keywords.append(kw)
            elif in_word_count:
                match = re.search(r"\d+", line)
                if match:
                    word_count = int(match.group())

        if not outline or not keywords or word_count == 0:
            raise ValueError("Incomplete response parsing.")

        return GenerateOutlineResponse(
            outline=outline.strip(),
            keywords=keywords,
            recommended_word_count=word_count
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
