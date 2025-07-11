from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from openai import OpenAI
from dotenv import load_dotenv
import os
import requests
from bs4 import BeautifulSoup
import re

# Load .env
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERP_API_KEY = os.getenv("SERP_API_KEY")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not found in .env.")
if not SERP_API_KEY:
    raise RuntimeError("SERP_API_KEY not found in .env.")

client = OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI(
    title="Topic Generator API",
    description="Generates blog topics, outlines, keywords, word count recommendations, and full blog articles.",
    version="1.0.0"
)

class TopicRequest(BaseModel):
    target_audience: str
    industry: str
    primary_goal: str

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

# --- Models ---
class TopicRequest(BaseModel):
    target_audience: str
    industry: str
    primary_goal: str

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

# --- Existing endpoints omitted for brevity ---
# (Assume you already have /generate-topics, /generate-keywords-outline, /generate-blog as we built before.)

# --- Image generation endpoint ---
@app.post("/image_gen_manual", response_model=ImageGenerationResponse)
async def image_gen_manual(request: ImageGenerationRequest):
    """
    Generates an image from a text prompt using OpenAI's DALL·E API.
    """
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
    prompt = (
        f"Generate 3 to 5 creative blog topic ideas targeting '{request.target_audience}' "
        f"in the '{request.industry}' industry, with the primary goal of '{request.primary_goal}'. "
        "Return the topics as a numbered list."
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


@app.post("/generate-keywords-outline", response_model=KeywordOutlineResponse)
async def generate_keywords_outline(request: KeywordOutlineRequest):
    serp_url = "https://serpapi.com/search.json"

    params = {
        "q": request.topic,
        "api_key": SERP_API_KEY,
        "engine": "google",
        "num": "3"
    }

    try:
        serp_response = requests.get(serp_url, params=params, timeout=10)
        serp_response.raise_for_status()
        data = serp_response.json()

        organic_results = data.get("organic_results", [])
        if not organic_results:
            raise ValueError("No organic results found.")

        urls = [result.get("link") for result in organic_results[:3] if result.get("link")]
        if not urls:
            raise ValueError("No URLs found in SERP results.")

        combined_text = ""
        total_words = 0
        MAX_WORDS_PER_PAGE = 2000
        MAX_TOTAL_WORDS = 10000

        for url in urls:
            try:
                page = requests.get(url, timeout=10)
                page.raise_for_status()
                soup = BeautifulSoup(page.text, "html.parser")
                text = soup.get_text(separator="\n").strip()

                if not text:
                    continue

                words = text.split()
                truncated_words = words[:MAX_WORDS_PER_PAGE]
                truncated_text = " ".join(truncated_words)

                word_count = len(truncated_words)
                total_words += word_count

                combined_text += truncated_text + "\n\n"

            except Exception as fetch_err:
                print(f"Error fetching {url}: {fetch_err}")
                continue

        if not combined_text.strip():
            raise ValueError("Failed to extract any content from pages.")

        all_words = combined_text.split()
        if len(all_words) > MAX_TOTAL_WORDS:
            all_words = all_words[:MAX_TOTAL_WORDS]
        safe_text = " ".join(all_words)

        prompt = (
            "Based on the following content, extract a list of the top 10 SEO keywords, "
            "create a detailed blog outline, and suggest an appropriate recommended word count as a number only (e.g., 2000).\n\n"
            f"CONTENT:\n{safe_text}\n\n"
            f"The combined word count of the reference articles is approximately {total_words} words.\n\n"
            "Return the output formatted as:\n"
            "Keywords:\n"
            "1. keyword1\n2. keyword2\n...\n\nOutline:\nOutline text here.\n\nRecommended Word Count:\nNumber only."
        )

        completion = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert SEO content strategist."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=800
        )

        response_text = completion.choices[0].message.content.strip()

        keywords = []
        outline = ""
        recommended_word_count_str = ""
        in_keywords = False
        in_outline = False
        in_word_count = False

        for line in response_text.split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.lower().startswith("keywords"):
                in_keywords = True
                in_outline = False
                in_word_count = False
                continue
            if line.lower().startswith("outline"):
                in_keywords = False
                in_outline = True
                in_word_count = False
                continue
            if line.lower().startswith("recommended word count"):
                in_keywords = False
                in_outline = False
                in_word_count = True
                continue
            if in_keywords:
                kw = line.lstrip("0123456789.-) ").strip()
                if kw:
                    keywords.append(kw)
            elif in_outline:
                outline += line + "\n"
            elif in_word_count:
                recommended_word_count_str += line

        match = re.search(r"\d+", recommended_word_count_str.replace(",", ""))
        if not match:
            raise ValueError(f"Could not parse recommended word count from: '{recommended_word_count_str}'")

        recommended_word_count = int(match.group())

        if not keywords or not outline:
            raise ValueError("Failed to parse keywords or outline.")

        return KeywordOutlineResponse(
            keywords=keywords,
            outline=outline.strip(),
            recommended_word_count=recommended_word_count
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


from bs4 import BeautifulSoup

@app.post("/generate-blog", response_model=BlogGenerationResponse)
async def generate_blog(request: BlogGenerationRequest):
    """
    Generates a full SEO-optimized blog article following the given outline, keywords, and word count,
    by chunking generation per heading and returning clean, validated HTML.
    """
    try:
        # Split outline into sections
        headings = [line.strip() for line in request.outline.strip().split("\n") if line.strip()]

        if not headings:
            raise ValueError("No headings found in the outline.")

        # Calculate word budget per section
        total_headings = len(headings)
        target_word_count = request.recommended_word_count
        avg_words_per_section = target_word_count // total_headings

        sections = []

        for heading in headings:
            section_prompt = (
                f"You are an expert SEO content writer.\n\n"
                f"Write an HTML-formatted section titled '{heading}' for a blog about '{request.topic}'.\n\n"
                f"Requirements:\n"
                f"- The section should be approximately {avg_words_per_section} words.\n"
                f"- Include these keywords organically: {', '.join(request.keywords)}.\n"
                f"- Use proper HTML formatting:\n"
                f"  - Heading in <h2>\n"
                f"  - Paragraphs in <p>\n"
                f"  - Bullet lists in <ul><li>\n"
                f"- Do NOT include emojis.\n"
                f"- Do NOT include any extra commentary or explanations.\n"
                f"- Do NOT include Markdown code fences (like ```html).\n"
                f"- Return ONLY valid HTML.\n"
            )

            completion = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You generate clean, semantic HTML for web content."},
                    {"role": "user", "content": section_prompt}
                ],
                temperature=0.5,
                max_tokens=1500
            )

            section_html = completion.choices[0].message.content.strip()

            # Remove any Markdown code fences or explanations
            section_html = section_html.replace("```html", "").replace("```", "").strip()

            # Clean up newlines and spaces between tags
            section_html = section_html.replace("\n", " ").replace("> <", "><").strip()

            # Validate and prettify HTML using BeautifulSoup
            soup = BeautifulSoup(section_html, "html.parser")
            validated_html = str(soup)

            sections.append(validated_html)

        # Combine all sections into one HTML string
        final_blog_html = "".join(sections)

        return BlogGenerationResponse(blog=final_blog_html)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
