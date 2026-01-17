from preprocess.local_checks import *
from Final.TTS_worker import speak
from Processing.analyze_image import llm_response, encode_image
import time
from concurrent.futures import ThreadPoolExecutor
from preprocess.frame_capture_worker import frame_cap

def main():
    """Pipeline: frame capture -> local checks -> text-to-speech"""

    executor = ThreadPoolExecutor(max_workers=2)    

    while True:

        frame_cap()

        if (face_check("temp.jpg") and eyes_open_check("temp.jpg") and isnt_blurry("temp.jpg")>30 == False):
            continue

        base64_image = encode_image("temp.jpg")

        with ThreadPoolExecutor(max_workers=1) as executor:
            futures = executor.submit(llm_response,base64_image)
            print("waiting for llm response\n")
            response = futures.result()

        with ThreadPoolExecutor(max_workers=1) as executor:
            futures = executor.submit(speak, response)
            print("waiting for speaking\n")

        print("all done, moving on\n")

        if ("Accepted" in response or "accepted" in response):
            break

    cv2.imshow("Final Frame", frame)
    cv2.waitKey(0)

if __name__ == "__main__":
    result = main()



# import streamlit as st
# import cv2
# import numpy as np

# st.set_page_config(page_title="Photo Assistant", layout="wide")

# if 'gallery' not in st.session_state:
#     st.session_state.gallery = []
# if 'capture_now' not in st.session_state:
#     st.session_state.capture_now = False


# st.markdown('<h1 style="text-align:center;">No More Stupid Photos</h1>', unsafe_allow_html=True)
# st.divider()

# with st.sidebar:
#     st.header("Settings")
#     audio_enabled = st.toggle("Enable Audio Feedback", value=True)
    
#     auto_click_enabled = st.toggle("Enable Auto-Capture", value=False, help="Automatically takes a photo when the backend detects a perfect shot.")
    
#     if auto_click_enabled:
#         st.info("🤖 Auto-Capture is ACTIVE")
    
#     st.divider()
#     if st.button("Clear Gallery"):
#         st.session_state.gallery = []
#         st.rerun()

# col_feed, col_gal = st.columns([1.2, 1])

# with col_feed:
#     st.subheader("Live Camera")
#     frame_placeholder = st.empty()
#     run = st.checkbox('Start Camera', value=True)
    
#     if st.button('TAKE PHOTO MANUALLY', use_container_width=True):
#         st.session_state.capture_now = True

# with col_gal:
#     st.subheader("Gallery")
#     gallery_container = st.empty()

# def update_gallery_ui():
#     with gallery_container.container():
#         if not st.session_state.gallery:
#             st.info("No photos captured yet.")
#         else:
#             cols = st.columns(2)
#             for i, img in enumerate(reversed(st.session_state.gallery)):
#                 with cols[i % 2]:
#                     st.image(img, use_container_width=True, caption=f"Capture {len(st.session_state.gallery) - i}")

# # Initial draw
# update_gallery_ui()

# cap = cv2.VideoCapture(0)

# while run:
#     ret, frame = cap.read()
#     if not ret:
#         st.error("Camera disconnected.")
#         break

#     frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

#     backend_trigger = False 
    
#     should_capture = st.session_state.capture_now or (auto_click_enabled and backend_trigger)

#     if should_capture:
#         st.session_state.gallery.append(frame_rgb)
        
#         if audio_enabled:
#             # st.audio("path_to_audio.mp3", autoplay=True)
#             st.toast("🔊 Playing Audio Feedback...")
        
#         update_gallery_ui()
        
#         st.session_state.capture_now = False
#         st.toast("Photo Captured!")

#     frame_placeholder.image(frame_rgb, channels="RGB", use_container_width=True)

# cap.release()