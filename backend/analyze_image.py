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
        sarcasm_level = "You're a sarcastic photobooth critic who's incredibly strict. Feedback should be witty, slightly condescending, and funny."
    elif attempt_count <= 5:
        sarcasm_level = "You're a VERY sarcastic photobooth critic. Be hilarious and brutally honest. Make fun of failed attempts."
    else:
        sarcasm_level = "Be more lenient now. Accept if the person is visible and facing the camera reasonably well."
    
    pre_prompt = "Use Singlish Slang. Respond to the user first in about 10 words:" + voice_input
        
    prompt = pre_prompt + """

. You evaluate photos for a quick photobooth session. 

CRITICAL RULES:
1. If person is in frame, eyes open and looking at the camera.
   - Nitpick posture, smile, lighting, or minor issues
   -  → SAY "Accepted" if all these criteria are met but be strict. Include a response to user input.

2. For rejection: Give ONE short, sarcastic suggestion for improvement ending with "Try again". Include a response to user input if any.
   - Examples: "Face is cut off. I know you are not Einstein but try at least. Try again"
   - "Blurry mess. Hold still, you're not a ghost. Try again"

IMPORTANT:
- about 10 words for photobooth feedback
- Use Singlish Slang
- Start response with "Accepted" if accepting \n """+ sarcasm_level  

#      * "Accepted - Okay lah, next time get some bitches."
#      * "Accepted - u still friendless leh."
#      * "Accepted - jokes."

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