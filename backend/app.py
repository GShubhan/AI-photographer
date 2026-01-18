from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import base64
import cv2
import numpy as np
import os
import sys
import time
import threading

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from preprocess.local_checks import face_check, eyes_open_check, isnt_blurry
    from analyze_image import llm_response, encode_image
    from STT_function import STTListener  # Import the instance, not the class
    from TTS_function import speak
    print("✓ All modules imported successfully")
except ImportError as e:
    print(f"✗ Import error: {e}")
    import traceback
    traceback.print_exc()

app = Flask(__name__)
CORS(app)


@app.route('/api/analyze', methods=['POST'])
def analyze():
    """
    Receives: { "image": "data:image/jpeg;base64,...", "attemptCount": 1 }
    Returns: { "status": "success", "feedback": "...", "accepted": true/false, "stt_text": "..." }
    """
    start_time = time.time()
    
    stt_listener = STTListener()

    try:
        print("📥 Received analysis request")
        
        data = request.json
        if not data or 'image' not in data:
            return jsonify({'status': 'error', 'message': 'No image data'}), 400
        
        attempt_count = data.get('attemptCount', 1)
        
        # ===== DECODE IMAGE =====
        image_data_url = data['image']
        if ',' not in image_data_url:
            return jsonify({'status': 'error', 'message': 'Invalid image format'}), 400
        
        image_data = image_data_url.split(',')[1]
        
        try:
            image_bytes = base64.b64decode(image_data)
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                return jsonify({'status': 'error', 'message': 'Failed to decode image'}), 400
        except Exception as decode_error:
            return jsonify({'status': 'error', 'message': f'Decode error: {str(decode_error)}'}), 400
        
        cv2.imwrite('temp.jpg', img)
        print("💾 Image saved")
        
        # ===== LOCAL CHECKS =====
        print("🔍 Running local checks...")
        has_face = face_check('temp.jpg')
        eyes_open = eyes_open_check('temp.jpg')
        blur_score = isnt_blurry('temp.jpg')
        
        print(f"  Face: {has_face}, Eyes: {eyes_open}, Blur: {blur_score:.1f}")
        
        if not (has_face and eyes_open and blur_score > 30):
            print("❌ Local checks failed")
            return jsonify({
                'status': 'rejected',
                'reason': 'local_checks_failed',
                'checks': {
                    'face': has_face,
                    'eyes': eyes_open,
                    'blur': float(blur_score)
                }
            })
        
        # ===== START STT IN BACKGROUND =====
        print("🎤 Starting background listener...")
        stt_listener.clear_queue()
        stt_listener.start_listening()
        
        # ===== WAIT FOR STT TEXT (MANDATORY, UP TO 15 SECONDS) =====
        print("🎤 Waiting for user voice input...")
        text = ""
        still_listening = True
        max_attempts = 1  # Allow retries if no speech
        
        for attempt in range(max_attempts):
            stt_result = stt_listener.get_latest_text(timeout=25)  # Increased timeout
            
            if stt_result and stt_result['status'] == 'success':
                text = stt_result['text']
                still_listening = stt_result['still_listening']
                print(f"✅ Got speech: {text}")
                break
            else:
                print(f"⚠️  No speech detected (attempt {attempt+1}/{max_attempts})")
                if attempt < max_attempts - 1:
                    print("🎤 Listening again...")
                else:
                    # If still no speech, use a default prompt or reject
                    text = "No voice input detected. Please say something!"
        
        stt_listener.stop_listening()
        
        # ===== PROCESS IMAGE WITH LLM (NOW WITH VOICE) =====
        print("🤖 Calling OpenAI API with image and voice...")
        api_start = time.time()
        base64_image = encode_image('temp.jpg')
        
        # Call LLM with text + image (voice is now guaranteed)
        feedback = llm_response(text, base64_image, attempt_count=attempt_count)
        api_duration = time.time() - api_start
        
        print(f"✅ Got feedback: {feedback}")
        print(f"⏱️  API took {api_duration:.1f}s")

        # Play audio on the server (background thread to not block response)
        print("🔊 Playing ElevenLabs audio...")
        threading.Thread(target=speak, args=(feedback,), daemon=True).start()
        
        is_accepted = 'accepted' in feedback.lower()
        
        response_data = {
            'status': 'success',
            'feedback': feedback,
            'accepted': is_accepted,
            'stt_text': text,
            'still_listening': still_listening,
            'checks': {
                'face': has_face,
                'eyes': eyes_open,
                'blur': float(blur_score)
            }
        }
        
        if is_accepted:
            print("🎉 PHOTO ACCEPTED!")
            with open('temp.jpg', 'rb') as f:
                img_data = base64.b64encode(f.read()).decode('utf-8')
                response_data['final_image'] = f"data:image/jpeg;base64,{img_data}"

            # Save to gallery with timestamp
            timestamp = int(time.time())
            gallery_path = f'gallery/photo_{timestamp}.jpg'
            cv2.imwrite(gallery_path, img)
            print(f"💾 Saved to gallery: {gallery_path}")
        
        total_duration = time.time() - start_time
        print(f"✅ Total request time: {total_duration:.1f}s\n")
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        stt_listener.stop_listening()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/gallery', methods=['GET'])
def get_gallery():
    """Get list of gallery photos"""
    try:
        import os
        gallery_dir = 'gallery'
        if not os.path.exists(gallery_dir):
            return jsonify({'photos': []})

        photos = []
        for filename in sorted(os.listdir(gallery_dir), reverse=True):  # Most recent first
            if filename.endswith('.jpg'):
                filepath = os.path.join(gallery_dir, filename)
                # Get file modification time
                mod_time = os.path.getmtime(filepath)
                photos.append({
                    'filename': filename,
                    'timestamp': int(mod_time),
                    'url': f'/api/gallery/download/{filename}'
                })

        return jsonify({'photos': photos})

    except Exception as e:
        print(f"❌ Gallery error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/gallery/download/<filename>', methods=['GET'])
def download_photo(filename):
    """Download a specific photo"""
    try:
        import os
        from flask import send_from_directory

        gallery_dir = 'gallery'
        filepath = os.path.join(gallery_dir, filename)

        if not os.path.exists(filepath):
            return jsonify({'error': 'Photo not found'}), 404

        return send_from_directory(gallery_dir, filename, as_attachment=True)

    except Exception as e:
        print(f"❌ Download error: {str(e)}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("🚀 Starting Flask server...")
    print("📁 Current directory:", os.getcwd())
    print("🔗 Server will run on http://localhost:5000")
    app.run(
        debug=True, 
        port=5000, 
        host='0.0.0.0',
        threaded=True,
        use_reloader=False
    )
