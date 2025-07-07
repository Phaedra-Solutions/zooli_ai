from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from openai import OpenAI
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

# Get API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("OPENAI_API_KEY not found in .env file.")

# Initialize OpenAI client
client = OpenAI(api_key=api_key)

# FastAPI app
app = FastAPI(
    title="Zooli.ai AI APIs",
    version="1.0.0"
)

# Request model
class TopicRequest(BaseModel):
    target_audience: str
    industry: str
    primary_goal: str

# Response model
class TopicResponse(BaseModel):
    topics: List[str]

@app.post("/generate-topics", response_model=TopicResponse)
async def generate_topics(request: TopicRequest):
    """
    Generate 3-5 blog topic ideas.
    """
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
        
        # Split into individual topics
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
