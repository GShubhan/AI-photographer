from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI()


# Function to create a file with the Files API
def create_file(file_path):
  with open(file_path, "rb") as file_content:
    result = client.files.create(
        file=file_content,
        purpose="vision",
    )
    return result.id

import base64

# Function to encode image to base64
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def llm_response(image):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": "You are a friendly but slightly sarcastic photographer. Your job is to help the user take great photos quickly - they want to wrap up within 1 minute. Analyze the image and decide if it's acceptable. Be lenient with camera quality, lighting imperfections, and minor technical issues. Focus mainly on the core elements: Are they in frame? Is the pose/facial expression at least decent? Is the composition reasonable? Do NOT nitpick about things that are hard to fix on the fly or require equipment changes. Give your assessment as follows:\n\n1. If the photo captures a good moment with acceptable composition, facial expression/posture is decent, and the subject is well-framed, respond with: 'Accepted'\n2. If there's a quick, easy fix that would significantly improve the shot (like 'Step back a bit', 'Smile more', 'Move slightly to the left', 'Better lighting angle'), give 1 clear instruction followed by 'Try again'.\n3. Only suggest fixes that can be done in seconds without equipment changes.\n\nBe encouraging and use light sarcasm. Remember: good enough is good enough when time is limited! Also dont write more than 25 words."},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image}"},
                },
            ],
        }],
    )
    return response.choices[0].message.content