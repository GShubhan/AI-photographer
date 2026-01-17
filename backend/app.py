from flask import Flask, request, jsonify
from flask_cors import CORS
import base64
import cv2
import numpy as np
import os
import sys

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import your existing modules
try:
    from preprocess.local_checks import face_check, eyes_open_check, isnt_blurry
    from analyze_image import llm_response, encode_image  # Using root analyze_image.py with sarcasm feature
    print("✓ All modules imported successfully")
except ImportError as e:
    print(f"✗ Import error: {e}")
    print("Make sure you have __init__.py files in preprocess/ and Processing/ folders")

app = Flask(__name__)
CORS(app)  # Allow React to call this API

@app.route('/api/analyze', methods=['POST'])
def analyze():
    """
    Receives: { "image": "data:image/jpeg;base64,...", "attemptCount": 1 }
    Returns: { "status": "success", "feedback": "...", "accepted": true/false }
    """
    import time
    start_time = time.time()
    
    try:
        print("📥 Received analysis request")
        print(f"⏰ Request started at {time.strftime('%H:%M:%S')}")
        
        # Get base64 image from React
        data = request.json
        if not data or 'image' not in data:
            return jsonify({
                'status': 'error',
                'message': 'No image data received'
            }), 400
        
        # Get attempt count from frontend
        attempt_count = data.get('attemptCount', 1)
        print(f"📊 Attempt count: {attempt_count}")
        
        image_data_url = data['image']
        
        # Check if it's a data URL
        if ',' not in image_data_url:
            return jsonify({
                'status': 'error',
                'message': 'Invalid image format'
            }), 400
            
        image_data = image_data_url.split(',')[1]  # Remove "data:image/jpeg;base64,"
        
        # Decode and save
        print("🔄 Decoding image...")
        try:
            image_bytes = base64.b64decode(image_data)
            print(f"📊 Decoded {len(image_bytes)} bytes")
            
            if len(image_bytes) == 0:
                return jsonify({
                    'status': 'error',
                    'message': 'Empty image data received'
                }), 400
            
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                return jsonify({
                    'status': 'error',
                    'message': 'Failed to decode image - corrupted data'
                }), 400
        except Exception as decode_error:
            print(f"❌ Decode error: {decode_error}")
            return jsonify({
                'status': 'error',
                'message': f'Image decode error: {str(decode_error)}'
            }), 400
        
        # Save temporarily
        cv2.imwrite('temp.jpg', img)
        print("💾 Image saved as temp.jpg")
        
        # Run your local checks
        print("🔍 Running local checks...")
        has_face = face_check('temp.jpg')
        eyes_open = eyes_open_check('temp.jpg')
        blur_score = isnt_blurry('temp.jpg')
        
        print(f"  Face: {has_face}, Eyes: {eyes_open}, Blur: {blur_score:.1f}")
        
        # If checks fail, return early
        if not (has_face and eyes_open and blur_score > 30):
            print("❌ Local checks failed")
            return jsonify({
                'status': 'rejected',
                'reason': 'local_checks_failed',
                'message': f'Face: {has_face}, Eyes: {eyes_open}, Blur: {blur_score:.1f}',
                'checks': {
                    'face': has_face,
                    'eyes': eyes_open,
                    'blur': float(blur_score)
                }
            })
        
        # Call OpenAI (your existing function)
        print(f"🤖 Calling OpenAI API (attempt {attempt_count})...")
        api_start = time.time()
        base64_image = encode_image('temp.jpg')
        feedback = llm_response(base64_image, attempt_count=attempt_count)
        api_duration = time.time() - api_start
        
        print(f"✅ Got feedback: {feedback}")
        print(f"⏱️  OpenAI API took {api_duration:.1f}s")
        
        # Check if accepted
        is_accepted = 'accepted' in feedback.lower()
        
        response_data = {
            'status': 'success',
            'feedback': feedback,
            'accepted': is_accepted,
            'checks': {
                'face': has_face,
                'eyes': eyes_open,
                'blur': float(blur_score)
            }
        }
        
        # If accepted, include the image
        if is_accepted:
            print("🎉 PHOTO ACCEPTED!")
            with open('temp.jpg', 'rb') as f:
                img_data = base64.b64encode(f.read()).decode('utf-8')
                response_data['final_image'] = f"data:image/jpeg;base64,{img_data}"
        
        total_duration = time.time() - start_time
        print(f"✅ Total request time: {total_duration:.1f}s")
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Check if backend is running"""
    return jsonify({'status': 'ok', 'message': 'Backend is running'})

if __name__ == '__main__':
    print("🚀 Starting Flask server...")
    print("📁 Current directory:", os.getcwd())
    print("🔗 Server will run on http://localhost:5000")
    print("⏱️  OpenAI API calls may take 5-30 seconds")
    print("💡 Keep this terminal window open!")
    
    # Production-ready settings
    app.run(
        debug=True, 
        port=5000, 
        host='0.0.0.0',
        threaded=True,  # Handle multiple requests
        use_reloader=False  # Prevent double startup in debug mode
    )