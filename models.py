from pydantic import BaseModel
from typing import List, Optional

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
    tone: Optional[str] = "neutral"
    intent: Optional[str] = "inform"
    audience: Optional[str] = "general"

class GenerateBlogResponse(BaseModel):
    blog_html: str

class LinkedInPostRequest(BaseModel):
    blog_text: str
    blog_link: Optional[str] = None

class LinkedInPostResponse(BaseModel):
    linkedin_post: str

class LinkedInTopicRequest(BaseModel):
    topic: str

class LinkedInTopicResponse(BaseModel):
    linkedin_post: str

class LinkedInImagePostRequest(BaseModel):
    blog_text: Optional[str] = None
    blog_url: Optional[str] = None

class LinkedInImagePostResponse(BaseModel):
    image_url: str
    post_text: str