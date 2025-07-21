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

class ImageGenerationRequest(BaseModel):
    prompt: str

class ImageGenerationResponse(BaseModel):
    image_url: str

# ---------- Endpoints ----------

@app.post("/image_gen_manual", response_model=ImageGenerationResponse)
async def image_gen_manual(request: ImageGenerationRequest):
    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=request.prompt,
            n=1,
            size="1024x1024"
        )
        image_url = response.data[0].url
        return ImageGenerationResponse(image_url=image_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
