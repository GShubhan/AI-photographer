import React, { useRef, useState, useEffect } from 'react';
import './App.css';

function App() {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  
  // State management
  const [feedback, setFeedback] = useState('Position yourself in frame...');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [accepted, setAccepted] = useState(false);
  const [checks, setChecks] = useState({ face: false, eyes: false, blur: 0 });
  const [attemptCount, setAttemptCount] = useState(0);
  const [captureInterval, setCaptureInterval] = useState(null);
  const [cameraReady, setCameraReady] = useState(false);

  // Start camera when component loads
  useEffect(() => {
    startCamera();
    return () => {
      // Cleanup: stop camera when component unmounts
      if (videoRef.current && videoRef.current.srcObject) {
        videoRef.current.srcObject.getTracks().forEach(track => track.stop());
      }
      if (captureInterval) {
        clearInterval(captureInterval);
      }
    };
  }, []);

  // Start auto-capture after camera is ready
  useEffect(() => {
    if (cameraReady && !accepted) {
      const interval = setInterval(() => {
        captureAndAnalyze();
      }, 3000); // Capture every 3 seconds
      
      setCaptureInterval(interval);
      
      return () => clearInterval(interval);
    }
  }, [cameraReady, accepted]);

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { 
          width: { ideal: 1280 },
          height: { ideal: 720 }
        } 
      });
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.onloadedmetadata = () => {
          setCameraReady(true);
          setFeedback('Camera ready! Analyzing in 3 seconds...');
        };
      }
    } catch (err) {
      console.error('Camera error:', err);
      setFeedback('❌ Camera access denied. Please allow camera permissions and refresh.');
    }
  };

  const captureAndAnalyze = async () => {
    if (isAnalyzing || accepted || !cameraReady) return;
    
    setIsAnalyzing(true);
    setFeedback('📸 Analyzing...');
    
    try {
      // Capture frame from video
      const canvas = canvasRef.current;
      const video = videoRef.current;
      
      if (!video || !canvas) {
        console.error('Video or canvas not ready');
        setIsAnalyzing(false);
        return;
      }
      
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(video, 0, 0);
      
      // Convert to base64
      const imageData = canvas.toDataURL('image/jpeg', 0.95);
      
      // Send to backend
      const response = await fetch('http://localhost:5000/api/analyze', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ image: imageData })
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
      
      // Update attempt count
      setAttemptCount(prev => prev + 1);
      
      if (result.status === 'success') {
        setFeedback(result.feedback);
        setChecks(result.checks || {});
        
        // Speak the feedback
        speak(result.feedback);
        
        if (result.accepted) {
          setAccepted(true);
          setFeedback('✅ ' + result.feedback);
          // Stop auto-capture
          if (captureInterval) {
            clearInterval(captureInterval);
          }
        }
      } else if (result.status === 'rejected') {
        setFeedback(result.message || 'Checks failed - adjusting...');
        setChecks(result.checks || {});
      } else {
        setFeedback('⚠️ ' + (result.message || 'Unknown error'));
      }
      
    } catch (error) {
      console.error('Analysis error:', error);
      setFeedback('❌ Connection error. Is the backend running on port 5000?');
    }
    
    setIsAnalyzing(false);
  };

  const speak = (text) => {
    try {
      // Use browser's speech synthesis
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.0;
      utterance.pitch = 1.0;
      utterance.volume = 1.0;
      window.speechSynthesis.cancel(); // Stop any ongoing speech
      window.speechSynthesis.speak(utterance);
    } catch (error) {
      console.error('TTS error:', error);
    }
  };

  const reset = () => {
    setAccepted(false);
    setFeedback('Ready to go again!');
    setAttemptCount(0);
    setChecks({ face: false, eyes: false, blur: 0 });
  };

  const manualCapture = () => {
    captureAndAnalyze();
  };

  return (
    <div className="App">
      <div className="container">
        <header>
          <h1>📸 Sarcastic AI Photographer</h1>
          <p className="subtitle">Let's see if you can take a decent photo...</p>
        </header>

        <div className="main-content">
          {/* Camera View */}
          <div className="camera-section">
            <div className="camera-container">
              <video 
                ref={videoRef} 
                autoPlay 
                playsInline
                muted
                className="video-feed"
              />
              <canvas ref={canvasRef} style={{ display: 'none' }} />
              
              {/* Overlay indicators */}
              {cameraReady && (
                <div className="overlay-checks">
                  <span className={checks.face ? 'check-pass' : 'check-fail'}>
                    {checks.face ? '✓' : '✗'} Face
                  </span>
                  <span className={checks.eyes ? 'check-pass' : 'check-fail'}>
                    {checks.eyes ? '✓' : '✗'} Eyes
                  </span>
                  <span className={checks.blur > 30 ? 'check-pass' : 'check-fail'}>
                    {checks.blur > 30 ? '✓' : '✗'} Focus
                  </span>
                </div>
              )}
            </div>

            {/* Controls */}
            <div className="controls">
              <button 
                onClick={manualCapture} 
                disabled={isAnalyzing || accepted}
                className="btn-primary"
              >
                {isAnalyzing ? '⏳ Analyzing...' : '📸 Capture Now'}
              </button>
              
              {accepted && (
                <button onClick={reset} className="btn-secondary">
                  🔄 Take Another Photo
                </button>
              )}
            </div>
          </div>

          {/* Feedback Section */}
          <div className="feedback-section">
            <div className={`feedback-card ${accepted ? 'accepted' : ''}`}>
              <div className="feedback-icon">
                {isAnalyzing ? '🤔' : accepted ? '🎉' : '💭'}
              </div>
              <p className="feedback-text">{feedback}</p>
              <div className="attempt-counter">
                Attempt #{attemptCount}
              </div>
            </div>

            {/* Stats */}
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-label">Face Detected</div>
                <div className={`stat-value ${checks.face ? 'good' : 'bad'}`}>
                  {checks.face ? 'Yes ✓' : 'No ✗'}
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Eyes Open</div>
                <div className={`stat-value ${checks.eyes ? 'good' : 'bad'}`}>
                  {checks.eyes ? 'Yes ✓' : 'No ✗'}
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Image Quality</div>
                <div className={`stat-value ${checks.blur > 30 ? 'good' : 'bad'}`}>
                  {checks.blur ? checks.blur.toFixed(1) : '—'}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;