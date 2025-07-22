from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from openai import OpenAI
from dotenv import load_dotenv
import os
import requests
from bs4 import BeautifulSoup
import re

# Load environment variables
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not found in .env")
if not SERPER_API_KEY:
    raise RuntimeError("SERPER_API_KEY not found in .env")

client = OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI(title="Topic + Blog Generator API", version="1.0")

# ---------- MODELS ----------
class TopicRequest(BaseModel):
    niche: str
    intent: str
    audience: str
    keywords: Optional[List[str]] = None

class TopicResponse(BaseModel):
    topics: List[str]

class KeywordOutlineRequest(BaseModel):
    topic: str
    intent: str
    audience: str
    keywords: Optional[List[str]] = None

class KeywordOutlineResponse(BaseModel):
    outline: str
    keywords: List[str]
    recommended_word_count: int

class GenerateBlogRequest(BaseModel):
    topic: str
    outline: str
    keywords: List[str]
    recommended_word_count: int
    intent: str
    audience: str
    tone: str

class GenerateBlogResponse(BaseModel):
    blog_html: str

# ---------- ENDPOINTS ----------

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
        topics = [line.lstrip("0123456789.-) ").strip() for line in raw_text.split("\n") if line and (line[0].isdigit() or line.startswith("-"))]
        return TopicResponse(topics=topics)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-outline", response_model=KeywordOutlineResponse)
async def generate_outline(request: KeywordOutlineRequest):
    try:
        serper_url = "https://google.serper.dev/search"
        headers = {"X-API-KEY": SERPER_API_KEY}
        payload = {"q": request.topic, "num": 3}
        serper_response = requests.post(serper_url, json=payload, headers=headers)
        serper_response.raise_for_status()
        results = serper_response.json()
        urls = [item.get("link") for item in results.get("organic", [])[:3] if item.get("link")]

        combined_text = ""
        for url in urls:
            try:
                res = requests.get(url, timeout=10)
                res.raise_for_status()
                soup = BeautifulSoup(res.text, "html.parser")
                text = soup.get_text(separator=" ")
                snippet = " ".join(text.split()[:1500])
                combined_text += snippet + "\n"
            except Exception:
                continue

        keyword_clause = f" Target these keywords: {', '.join(request.keywords)}." if request.keywords else ""

        prompt = (
            "generate a detailed blog outline in HTML format using <h2> for section titles and <ul><li> for bullet points. "
            "Also suggest 10-15 SEO-friendly keywords, and recommend a word count for the article.\n"
            f"Topic: {request.topic}\nIntent: {request.intent}\nAudience: {request.audience}\n{keyword_clause}\n\n"
            f"REFERENCE CONTENT:\n{combined_text[:5000]}\n\n"
            "Return in this format:\n"
            "Outline:\n<html-formatted-outline>\n\nKeywords:\n1. keyword1\n...\n\nRecommended Word Count:\n<just the number>"
        )

        completion = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a skilled SEO blog planner who writes clean HTML."},
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
                outline += line
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

        return KeywordOutlineResponse(
            outline=outline.strip().replace("\n", ""),
            keywords=keywords,
            recommended_word_count=word_count
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-blog", response_model=GenerateBlogResponse)
async def generate_blog(request: GenerateBlogRequest):
    try:
        serper_url = "https://google.serper.dev/search"
        headers = {"X-API-KEY": SERPER_API_KEY}
        payload = {"q": request.topic, "num": 3}
        serper_response = requests.post(serper_url, json=payload, headers=headers)
        serper_response.raise_for_status()
        results = serper_response.json()
        urls = [item.get("link") for item in results.get("organic", [])[:3] if item.get("link")]

        reference_content = ""
        for url in urls:
            try:
                res = requests.get(url, timeout=10)
                res.raise_for_status()
                soup = BeautifulSoup(res.text, "html.parser")
                text = soup.get_text(separator=" ")
                snippet = " ".join(text.split()[:1500])
                reference_content += snippet + "\n"
            except Exception:
                continue

        sections = re.findall(r"<h2>(.*?)</h2>", request.outline)
        if not sections:
            raise ValueError("No <h2> headings found in the outline.")

        total_sections = len(sections)
        words_per_section = request.recommended_word_count // total_sections
        full_blog = ""

        for heading in sections:
            section_prompt = (
                f"You are an expert SEO blog writer. Write an HTML-formatted section for the blog heading '{heading}'.\n"
                f"Tone: {request.tone}. Intent: {request.intent}. Audience: {request.audience}.\n"
                f"Use all of these keywords naturally throughout the blog: {', '.join(request.keywords)}.\n"
                f"Aim for approximately {words_per_section} words.\n"
                f"Use <h2> for the heading, <p> for paragraphs, and <ul><li> for any lists.\n"
                f"Avoid emojis and markdown. Output valid HTML only.\n"
                f"REFERENCE MATERIAL:\n{reference_content[:3000]}"
            )

            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You generate high quality SEO optimized HTML blog content."},
                    {"role": "user", "content": section_prompt}
                ],
                temperature=0.5,
                max_tokens=1200
            )

            section_html = response.choices[0].message.content.strip()
            section_html = section_html.replace("```html", "").replace("```", "").replace("\n", " ").replace("> <", "><").strip()
            full_blog += section_html

        return GenerateBlogResponse(blog_html=full_blog)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
