from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI()

import base64

# Function to encode image to base64
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def llm_response(image, attempt_count=1):
    # Start strict, become more lenient with attempts
    if attempt_count == 1:
        leniency = "Be critical and helpful. Only accept near-perfect photos. Provide useful advice for improvement."
    elif attempt_count == 2:
        leniency = "Still be somewhat strict, but give constructive feedback. Accept if mostly good with minor issues."
    else:
        leniency = "Be more lenient now. Accept if the person is visible and facing the camera reasonably well."
    
    prompt = f"""You evaluate photos for a photobooth session with sarcastic, witty humor. {leniency}

CRITICAL RULES:
1. For acceptance: Say "Accepted" with a positive, sarcastic comment.
   - Example: "Accepted - Wow, you actually look presentable!"

2. For rejection: Give ONE short, sarcastic suggestion (under 15 words) ending with "Try again".
   - Examples: "Face is cut off. Get your whole head in frame, genius. Try again"
   - "Blurry mess. Hold still, you're not a ghost. Try again"

IMPORTANT: Max 15 words total. Start with "Accepted" only if truly good."""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image}"},
                },
            ],
        }],
    )
    return response.choices[0].message.content