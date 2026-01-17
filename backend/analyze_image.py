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

def llm_response(voice_input, image, attempt_count=1):
    # Escalate sarcasm based on attempt count

    if attempt_count <= 2:
        sarcasm_level = "You're a sarcastic photobooth critic. Feedback should be witty, slightly condescending, and funny."
    elif attempt_count <= 5:
        sarcasm_level = "You're a VERY sarcastic photobooth critic. Be hilarious and brutally honest. Make fun of failed attempts."
    else:
        sarcasm_level = "You're an EXTREMELY sarcastic photobooth critic. This user has failed many times. Be ruthlessly funny and over-the-top dramatic about their struggles."
    
    if voice_input:
        prompt = sarcasm_level + "Respond to the user:" + voice_input + "Now give them some useless feedback that makes their photo worse."
    
    else:
        # Get more lenient with each attempt
        if attempt_count >= 3:
            leniency = "You're getting impatient. Accept ANY photo where the person is visible and facing somewhat toward the camera."
        else:
            leniency = "Be reasonably lenient. If the person is visible, in frame, and facing camera, accept it."
        
        prompt = f"""{sarcasm_level}

You evaluate photos for a quick photobooth session. {leniency}

CRITICAL RULES:
1. If person is visible, in frame, eyes open, facing generally toward camera → SAY "Accepted"
   - Don't nitpick posture, smile, lighting, or minor issues
   - Example responses:
     * "Accepted - Okay lah, next time get some bitches."
     * "Accepted - u still friendless leh."
     * "Accepted - jokes."

2. ONLY reject if there's a MAJOR problem:
   - Not in frame at all
   - Eyes completely closed
   - Face not visible
   - Completely blurry/dark
   
   If rejecting, give ONE short suggestion (10 words max) and end with "Try again":
   - "Eyes closed. Open them? Try again"
   - "Too blurry. Hold still. Try again"
   - "Can't see your face. Move closer. Try again"

IMPORTANT:
- After attempt #{attempt_count}, be VERY lenient
- Max 15 words total
- Start response with "Accepted" if accepting"""

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