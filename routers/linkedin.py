from fastapi import APIRouter, HTTPException
from models import LinkedInPostRequest, LinkedInPostResponse, LinkedInTopicRequest, LinkedInTopicResponse, LinkedInImagePostRequest, LinkedInImagePostResponse
from config import client
import requests
from bs4 import BeautifulSoup

linkedin_router = APIRouter()

@linkedin_router.post("/blog-cta", response_model=LinkedInPostResponse)
async def linkedin_blog_cta(request: LinkedInPostRequest):
    try:
        prompt = (
            "Write a LinkedIn post summarizing the blog content and include a compelling CTA to read the full blog."
            f"\n\nBLOG TEXT:\n{request.blog_text}\n\n"
        )
        if request.blog_link:
            prompt += f"Include this link at the end: {request.blog_link}"

        completion = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a professional LinkedIn content strategist."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )

        post = completion.choices[0].message.content.strip()
        return LinkedInPostResponse(linkedin_post=post)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@linkedin_router.post("/general-emojis", response_model=LinkedInTopicResponse)
async def linkedin_general_emojis(request: LinkedInTopicRequest):
    try:
        prompt = (
            f"Write an engaging LinkedIn post about the topic: '{request.topic}'.\n"
            f"The post should include emojis and be formatted for professional engagement."
        )
        completion = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a LinkedIn post writing expert."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=500
        )
        post = completion.choices[0].message.content.strip()
        return LinkedInTopicResponse(linkedin_post=post)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@linkedin_router.post("/general-plain", response_model=LinkedInTopicResponse)
async def linkedin_general_plain(request: LinkedInTopicRequest):
    try:
        prompt = (
            f"Write an engaging LinkedIn post about the topic: '{request.topic}'.\n"
            f"The post should NOT contain any emojis and should maintain a professional tone."
        )
        completion = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a LinkedIn post writing expert."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=500
        )
        post = completion.choices[0].message.content.strip()
        return LinkedInTopicResponse(linkedin_post=post)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@linkedin_router.post("/image-post", response_model=LinkedInImagePostResponse)
async def linkedin_image_post(request: LinkedInImagePostRequest):
    try:
        content = request.blog_text or ""
        if not content and request.blog_url:
            page = requests.get(request.blog_url, timeout=10)
            soup = BeautifulSoup(page.text, "html.parser")
            content = soup.get_text(" ")[:3000]

        if not content:
            raise ValueError("Blog text or URL is required.")

        caption_prompt = (
            f"You are a social media expert. Write a professional and engaging LinkedIn post based on the following blog content. "
            f"Include an image-worthy idea in the style of an infographic or concept visual.\n\nCONTENT:\n{content}\n\n"
            "Return only the LinkedIn post text."
        )

        image_prompt_gen = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You generate creative visual image ideas."},
                {"role": "user", "content": caption_prompt}
            ],
            temperature=0.6,
            max_tokens=300
        )

        post_text = image_prompt_gen.choices[0].message.content.strip()
        visual_prompt_enhancer = (
            f"You're an expert visual designer for B2B marketing. Based on the blog content below, generate a stable diffusion prompt to create an image that conveys the core theme visually (without using any text in the image).\n\n"
            f"Guidelines:\n"
            f"- Focus on metaphorical or conceptual visuals (e.g., a rocket launch, team collaborating, brain circuits).\n"
            f"- Avoid literal charts, text, or infographics.\n"
            f"- Style: modern flat vector, clean white background, professional lighting.\n"
            f"- Do NOT include text, numbers, or UI screenshots in the image.\n\n"
            f"CONTENT:\n{content[:2000]}\n\n"
            f"Return only the image prompt."
        )

        image_prompt_response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You craft professional visual prompts for AI-generated business images."},
                {"role": "user", "content": visual_prompt_enhancer}
            ],
            temperature=0.3,
            max_tokens=300
        )

        image_description_prompt = image_prompt_response.choices[0].message.content.strip()

        image_response = client.images.generate(
            model="dall-e-3",
            prompt=image_description_prompt,
            n=1,
            size="1024x1024"
        )
        image_url = image_response.data[0].url

        return LinkedInImagePostResponse(image_url=image_url, post_text=post_text)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@linkedin_router.post("/image-post-cta", response_model=LinkedInImagePostResponse)
async def linkedin_image_post_cta(request: LinkedInImagePostRequest):
    try:
        content = request.blog_text or ""
        if not content and request.blog_url:
            page = requests.get(request.blog_url, timeout=10)
            soup = BeautifulSoup(page.text, "html.parser")
            content = soup.get_text(" ")[:3000]

        if not content:
            raise ValueError("Blog text or URL is required.")

        link_text = request.blog_url or "[Read more link]"
        caption_prompt = (
            f"You are a social media expert. Write a LinkedIn post with a strong hook and a visual idea, followed by a call-to-action to read the full blog post at {link_text}.\n\n"
            f"CONTENT:\n{content}\n\nReturn only the LinkedIn post text."
        )

        image_prompt_gen = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You generate creative visual image ideas."},
                {"role": "user", "content": caption_prompt}
            ],
            temperature=0.6,
            max_tokens=300
        )

        post_text = image_prompt_gen.choices[0].message.content.strip()
        image_description_prompt = f"Generate a visual image prompt suitable for a LinkedIn post based on this content: {content}"

        image_response = client.images.generate(
            model="dall-e-3",
            prompt=image_description_prompt,
            n=1,
            size="1024x1024"
        )
        image_url = image_response.data[0].url

        return LinkedInImagePostResponse(image_url=image_url, post_text=post_text)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))