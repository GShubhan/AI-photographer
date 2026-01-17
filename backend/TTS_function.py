from elevenlabs import ElevenLabs
from io import BytesIO
import pygame
import time

# Replace with your ElevenLabs API key
client = ElevenLabs(api_key="sk_629c420fff32c41473bbc2c81579dea4e81626ba5af4b709")

pygame.mixer.init()

def speak(text):
    pygame.mixer.music.stop()
    # Replace with the voice ID of your chosen Singaporean voice
    audio = client.text_to_speech.convert(
        text=text,
        voice_id="aFxDLa1A1dSRlzW8nziT",
        model_id="eleven_multilingual_v2"
    )
    fp = BytesIO()
    for chunk in audio:
        fp.write(chunk)
    fp.seek(0)
    pygame.mixer.music.load(fp)
    pygame.mixer.music.play()
    # Estimate speech time
    speech_time = 0.4 + (len(text.split()) / 2.5)
    time.sleep(speech_time)

# Example usage
# speak("Eh, smile lah!")

# Example usage
# speak("Smile a little")
# speak("Perfect")
