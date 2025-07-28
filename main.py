from fastapi import FastAPI
from config import client, SERPER_API_KEY
from routers import blog, linkedin, ai_image

app = FastAPI(title="Topic + Blog Generator API", version="1.0")

# Include routers
app.include_router(blog.blog_router, prefix="/blog", tags=["Blog"])
app.include_router(linkedin.linkedin_router, prefix="/linkedin", tags=["LinkedIn"])
app.include_router(ai_image.ai_image_router, prefix="/ai_image", tags=["AI Image"])