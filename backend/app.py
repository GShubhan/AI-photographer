from flask import Flask, request, jsonify
from flask_cors import CORS
import base64
import cv2
import numpy as np
import os
import sys
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from preprocess.local_checks import face_check, eyes_open_check, isnt_blurry
    from analyze_image import llm_response, encode_image
    from STT_function import STTListener  # Import the instance, not the class
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
        
        # ===== PROCESS IMAGE WITH LLM =====
        print("🤖 Calling OpenAI API...")
        api_start = time.time()
        base64_image = encode_image('temp.jpg')
        
        # Wait for STT text (up to 8 seconds)
        text = ""
        still_listening = True
        
        stt_result = stt_listener.get_latest_text(timeout=8)
        
        if stt_result:
            if stt_result['status'] == 'success':
                text = stt_result['text']
                still_listening = stt_result['still_listening']
                print(f"✅ Got speech: {text}")
            else:
                print(f"⚠️  STT error: {stt_result['error']}")
        else:
            print("⚠️  No speech detected (timeout)")
        
        stt_listener.stop_listening()
        
        # Call LLM with text + image
        feedback = llm_response(text, base64_image, attempt_count=attempt_count)
        api_duration = time.time() - api_start
        
        print(f"✅ Got feedback: {feedback}")
        print(f"⏱️  API took {api_duration:.1f}s")
        
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
        
        total_duration = time.time() - start_time
        print(f"✅ Total request time: {total_duration:.1f}s\n")
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        stt_listener.stop_listening()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health():
    """Check if backend is running"""
    return jsonify({'status': 'ok', 'message': 'Backend is running'})


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
