from fastapi import APIRouter, HTTPException
from models import AIImageRequest, AIImageResponse
from config import client

ai_image_router = APIRouter()

@ai_image_router.post("/generate", response_model=AIImageResponse)
async def generate_ai_image(request: AIImageRequest):
    try:
        # Validate number of variations
        num_variations = max(3, min(request.num_variations, 5))  # Restrict to 3–5 variations

        # Create a detailed prompt for hyper-realistic style
        base_prompt = (
            f"You are an expert visual designer specializing in photorealistic imagery. Based on the following content, generate a highly detailed prompt for a hyper-realistic image that vividly captures the core theme. "
            f"Guidelines:\n"
            f"- Style: Ultra-photorealistic, 8K resolution quality, hyper-detailed textures, lifelike depth, and cinematic composition.\n"
            f"- Lighting: Natural, dynamic lighting with soft shadows and realistic light diffusion (e.g., golden hour, diffused daylight, or subtle evening glow).\n"
            f"- Focus: Emphasize realistic scenes, objects, or people directly inspired by the content, with intricate details like skin textures, fabric folds, or environmental elements.\n"
            f"- Composition: Balanced, visually compelling, with a clear focal point and harmonious color palette.\n"
            f"- Avoid: Text, numbers, charts, UI elements, abstract or cartoonish styles, copyrighted characters, logos, or brand identifiers.\n"
            f"- Environment: Include a relevant, detailed background that complements the subject (e.g., natural landscapes, urban settings, or interior scenes).\n"
            f"CONTENT:\n{request.content[:2000]}\n\n"
            f"Return only the image prompt as a concise, descriptive paragraph (100–150 words)."
        )

        # Generate the base image prompt using ChatGPT
        prompt_response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You craft precise, photorealistic image prompts for AI-generated images, focusing on vivid detail and realism."},
                {"role": "user", "content": base_prompt}
            ],
            temperature=0.4,  # Lower temperature for more precise output
            max_tokens=200
        )

        base_image_prompt = prompt_response.choices[0].message.content.strip()

        # Generate variations with subtle, realistic modifications
        image_urls = []
        variations = [
            base_image_prompt,  # Original prompt
            f"{base_image_prompt}, bathed in soft golden hour sunlight, warm tones, gentle bokeh effect",
            f"{base_image_prompt}, under moody twilight lighting, cooler blue tones, subtle mist",
            f"{base_image_prompt}, high-angle perspective, expansive depth of field, vibrant textures",
            f"{base_image_prompt}, macro close-up, hyper-detailed textures, soft natural light"
        ][:num_variations]  # Limit to requested number of variations

        for variation_prompt in variations:
            image_response = client.images.generate(
                model="dall-e-3",
                prompt=variation_prompt,
                n=1,
                size="1024x1024",
                quality="hd"  # Use higher quality for more realistic output
            )
            image_urls.append(image_response.data[0].url)

        return AIImageResponse(
            prompt=base_image_prompt,
            image_urls=image_urls
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))