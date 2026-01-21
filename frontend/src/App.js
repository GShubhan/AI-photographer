import React, { useRef, useState, useEffect } from 'react';
import './App.css';

const CAPTURE_INTERVAL_MS = 7000;
const CAPTURE_INTERVAL_SEC = CAPTURE_INTERVAL_MS / 1000;

function App() {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  
  // State management
  const [feedback, setFeedback] = useState('Position yourself in frame...');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [accepted, setAccepted] = useState(false);
  const [checks, setChecks] = useState({ face: false, eyes: false, blur: 0 });
  const [attemptCount, setAttemptCount] = useState(0);
  const [cameraReady, setCameraReady] = useState(false);
  const [countdown, setCountdown] = useState(CAPTURE_INTERVAL_SEC);
  const [finalImage, setFinalImage] = useState(null);
  const [availableCameras, setAvailableCameras] = useState([]);
  const [selectedCamera, setSelectedCamera] = useState(null);
  const [currentView, setCurrentView] = useState('camera'); // 'camera' or 'gallery'
  const [galleryPhotos, setGalleryPhotos] = useState([]);

  // Start camera when component loads
  useEffect(() => {
    listCameras();
    startCamera();
    return () => {
      // Cleanup: stop camera when component unmounts
      if (videoRef.current && videoRef.current.srcObject) {
        videoRef.current.srcObject.getTracks().forEach(track => track.stop());
      }
    };
  }, []);

  const listCameras = async () => {
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      const videoDevices = devices.filter(device => device.kind === 'videoinput');
      console.log('📹 Available cameras:', videoDevices);
      setAvailableCameras(videoDevices);
    } catch (err) {
      console.error('Error listing cameras:', err);
    }
  };

  const switchCamera = async (deviceId) => {
    // Stop current stream
    if (videoRef.current && videoRef.current.srcObject) {
      videoRef.current.srcObject.getTracks().forEach(track => track.stop());
    }
    
    setSelectedCamera(deviceId);
    setCameraReady(false);
    
    try {
      const constraints = {
        video: {
          deviceId: deviceId ? { exact: deviceId } : undefined,
          width: { ideal: 1920, max: 3840 },
          height: { ideal: 1080, max: 2160 },
          frameRate: { ideal: 30 }
        }
      };
      
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.onloadedmetadata = () => {
          const track = stream.getVideoTracks()[0];
          const settings = track.getSettings();
          console.log('📹 Switched to camera:', settings.width, 'x', settings.height);
          
          setCameraReady(true);
          setFeedback(`Camera ready! Resolution: ${settings.width}x${settings.height}`);
        };
      }
    } catch (err) {
      console.error('Camera switch error:', err);
      setFeedback('Failed to switch camera');
    }
  };

  // Main capture loop - ONLY runs when not analyzing and not accepted
  useEffect(() => {
    if (!cameraReady || accepted || isAnalyzing) {
      return; // Don't start interval if busy
    }

    console.log('🔄 Starting capture loop');
    
    // Countdown timer
    const countdownInterval = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) {
          return CAPTURE_INTERVAL_SEC; // Reset to interval
        }
        return prev - 1;
      });
    }, 1000);

    // Capture every X seconds
    const captureInterval = setInterval(() => {
      if (!isAnalyzing && !accepted) {
        console.log('📸 Triggering capture');
        captureAndAnalyze();
      }
    }, CAPTURE_INTERVAL_MS);
    
    return () => {
      clearInterval(countdownInterval);
      clearInterval(captureInterval);
    };
  }, [cameraReady, accepted, isAnalyzing]);

  const startCamera = async () => {
    try {
      // Request highest quality available
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { 
          width: { ideal: 1920, max: 3840 },    // Up to 4K
          height: { ideal: 1080, max: 2160 },   // Up to 4K
          frameRate: { ideal: 30 },
          facingMode: 'user'  // Front camera on mobile
        } 
      });
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.onloadedmetadata = () => {
          const track = stream.getVideoTracks()[0];
          const settings = track.getSettings();
          console.log('📹 Camera resolution:', settings.width, 'x', settings.height);
          console.log('📹 Camera settings:', settings);
          
          setCameraReady(true);
          setFeedback(`Camera ready! Resolution: ${settings.width}x${settings.height}. First capture in ${CAPTURE_INTERVAL_SEC} seconds...`);
        };
      }
    } catch (err) {
      console.error('Camera error:', err);
      setFeedback('Camera access denied. Please allow camera permissions and refresh.');
    }
  };

  const captureAndAnalyze = async () => {
    // Prevent multiple simultaneous captures
    if (isAnalyzing || accepted) {
      console.log('⏸️ Skipping capture - already analyzing or accepted');
      return;
    }
    
    console.log('🎬 Starting capture and analyze');
    setIsAnalyzing(true);
    setFeedback('Recording audio, please state your preferences for the photo');
    setCountdown(CAPTURE_INTERVAL_SEC); // Reset countdown
    
    try {
      // Capture frame from video
      const canvas = canvasRef.current;
      const video = videoRef.current;
      
      if (!video || !canvas) {
        console.error('Video or canvas not ready');
        setIsAnalyzing(false);
        setFeedback('Camera not ready, please wait...');
        return;
      }
      
      // Check if video stream is actually playing
      if (video.readyState !== video.HAVE_ENOUGH_DATA) {
        console.error('Video not ready yet, readyState:', video.readyState);
        setIsAnalyzing(false);
        setFeedback('Video loading, please wait...');
        return;
      }
      
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      
      // Check if video has valid dimensions
      if (canvas.width === 0 || canvas.height === 0) {
        console.error('Invalid video dimensions:', canvas.width, canvas.height);
        setIsAnalyzing(false);
        setFeedback('Camera initializing, please wait...');
        return;
      }
      
      const ctx = canvas.getContext('2d');
      ctx.drawImage(video, 0, 0);
      
      // Convert to base64 (use higher quality)
      const imageData = canvas.toDataURL('image/jpeg', 0.98);  // 98% quality instead of 95%
      
      // Verify we got valid image data
      if (!imageData || imageData.length < 1000) {
        console.error('Invalid image data captured, length:', imageData.length);
        setIsAnalyzing(false);
        setFeedback('Failed to capture image, retrying...');
        return;
      }
      
      console.log('📤 Sending to backend...');
      
      // Send to backend with timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 60000); // 60 second timeout
      
      const response = await fetch('http://localhost:5000/api/analyze', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          image: imageData,
          attemptCount: attemptCount + 1
        }),
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
      console.log('📥 Got result:', result);
      
      // Update attempt count
      setAttemptCount(prev => prev + 1);
      
      if (result.status === 'success') {
        setFeedback(result.feedback);
        setChecks(result.checks || {});
        
        // Speak the feedback
        // speak(result.feedback);
        
        if (result.accepted) {
          console.log('🎉 Photo accepted!');
          setAccepted(true);
          setFeedback(result.feedback);
          
          // Save final image
          if (result.final_image) {
            setFinalImage(result.final_image);
          } else {
            setFinalImage(imageData); // Use captured image if backend didn't send one
          }
          
          // isAnalyzing stays true to prevent more captures
          return; // Exit without setting isAnalyzing to false
        }
        
      } else if (result.status === 'rejected') {
        setFeedback(result.message || 'Checks failed - waiting for next capture...');
        setChecks(result.checks || {});
      } else {
        setFeedback(result.message || 'Unknown error');
      }
      
    } catch (error) {
      console.error('Analysis error:', error);
      
      if (error.name === 'AbortError') {
        setFeedback(`Request timeout. OpenAI is taking too long. Retrying in ${CAPTURE_INTERVAL_SEC}s...`);
      } else if (error.message.includes('Failed to fetch')) {
        setFeedback('Cannot connect to backend. Is it running on port 5000?');
      } else {
        setFeedback('Error: ' + error.message);
      }
    } finally {
      // Only set to false if not accepted
      if (!accepted) {
        console.log(`✅ Analysis complete, ready for next capture in ${CAPTURE_INTERVAL_SEC}s`);
        setIsAnalyzing(false);
      }
    }
  };

  const speak = (text) => {
    try {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.0;
      utterance.pitch = 1.0;
      utterance.volume = 1.0;
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(utterance);
    } catch (error) {
      console.error('TTS error:', error);
    }
  };

  const reset = () => {
    console.log('🔄 Resetting...');
    setAccepted(false);
    setIsAnalyzing(false);
    setFeedback(`Ready to go again! First capture in ${CAPTURE_INTERVAL_SEC} seconds...`);
    setAttemptCount(0);
    setChecks({ face: false, eyes: false, blur: 0 });
    setFinalImage(null);
    setCountdown(CAPTURE_INTERVAL_SEC);
    
    // Make sure video stream is active
    if (videoRef.current && videoRef.current.srcObject) {
      // Video stream still exists, just unhide it
      console.log('✓ Video stream still active');
    } else {
      // Video stream lost, restart camera
      console.log('⚠️ Video stream lost, restarting camera...');
      startCamera();
    }
  };

  const manualCapture = () => {
    if (!isAnalyzing && !accepted) {
      console.log('🖱️ Manual capture triggered');
      captureAndAnalyze();
    }
  };

  // Gallery functions
  const fetchGallery = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/gallery');
      const data = await response.json();
      setGalleryPhotos(data.photos || []);
    } catch (error) {
      console.error('Failed to fetch gallery:', error);
    }
  };

  const downloadPhoto = async (filename) => {
    try {
      const response = await fetch(`http://localhost:5000/api/gallery/download/${filename}`);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Failed to download photo:', error);
    }
  };

  const switchToGallery = () => {
    setCurrentView('gallery');
    fetchGallery();
  };

  const switchToCamera = () => {
    setCurrentView('camera');
  };

  return (
    <div className="App">
      <div className="container">
        <header>
          <h1>Shinchai Hasho Hasho</h1>
          <p className="subtitle">Powered by Computer Vision & OpenAI</p>
          <div className="view-switcher">
            <button
              onClick={switchToCamera}
              className={`view-btn ${currentView === 'camera' ? 'active' : ''}`}
            >
              Camera
            </button>
            <button
              onClick={switchToGallery}
              className={`view-btn ${currentView === 'gallery' ? 'active' : ''}`}
            >
              Gallery ({galleryPhotos.length})
            </button>
          </div>
        </header>

        <div className="main-content">
          {currentView === 'camera' ? (
            <>
              {/* Camera View */}
              <div className="camera-section">
            <div className="camera-container">
              <video 
                ref={videoRef} 
                autoPlay 
                playsInline
                muted
                className="video-feed"
                style={{ display: accepted && finalImage ? 'none' : 'block' }}
              />
              
              {/* Show final photo when accepted */}
              {accepted && finalImage && (
                <div className="final-photo-display">
                  <img src={finalImage} alt="Final accepted photo" />
                </div>
              )}
              
              {/* Countdown overlay */}
              {cameraReady && !isAnalyzing && !accepted && (
                <div className="countdown-overlay">
                  Next: {countdown}s
                </div>
              )}
              
              {/* Analyzing overlay */}
              {isAnalyzing && !accepted && (
                <div className="analyzing-overlay">
                  Analyzing...
                </div>
              )}
              
              <canvas ref={canvasRef} style={{ display: 'none' }} />
              
            </div>

            {/* Controls */}
            <div className="controls">
              {!accepted ? (
                <>
                  <button 
                    onClick={manualCapture} 
                    disabled={isAnalyzing}
                    className="btn-primary"
                  >
                    {isAnalyzing ? 'Analyzing...' : 'Capture Now'}
                  </button>
                  
                  {/* Camera selector dropdown */}
                  {availableCameras.length > 1 && (
                    <select 
                      onChange={(e) => switchCamera(e.target.value)}
                      value={selectedCamera || ''}
                      className="camera-select"
                      disabled={isAnalyzing}
                    >
                      <option value="">Default Camera</option>
                      {availableCameras.map((camera, idx) => (
                        <option key={camera.deviceId} value={camera.deviceId}>
                          {camera.label || `Camera ${idx + 1}`}
                        </option>
                      ))}
                    </select>
                  )}
                </>
              ) : (
                <button onClick={reset} className="btn-secondary">
                  Take Another Photo
                </button>
              )}
            </div>
          </div>

          {/* Feedback Section */}
          <div className="feedback-section">
            <div className={`feedback-card ${accepted ? 'accepted' : ''}`}>
              <p className="feedback-text">{feedback}</p>
              <div className="attempt-counter">
                Attempt #{attemptCount}
              </div>
            </div>

            {/* Stats */}
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-label">Face</div>
                <div className={`stat-value ${checks.face ? 'good' : 'bad'}`}>
                  {checks.face ? 'Detected' : 'Not Found'}
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Eyes</div>
                <div className={`stat-value ${checks.eyes ? 'good' : 'bad'}`}>
                  {checks.eyes ? 'Open' : 'Closed'}
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Quality</div>
                <div className={`stat-value ${checks.blur > 30 ? 'good' : 'bad'}`}>
                  {checks.blur ? checks.blur.toFixed(0) : '—'}
                </div>
              </div>
            </div>
          </div>
          </>
          ) : (
            /* Gallery View */
            <div className="gallery-section">
              <h2>Your Photo Gallery</h2>
              {galleryPhotos.length === 0 ? (
                <div className="empty-gallery">
                  <p>No photos yet! Switch to camera view and take some photos.</p>
                  <button onClick={switchToCamera} className="btn-primary">
                    Go to Camera
                  </button>
                </div>
              ) : (
                <div className="gallery-grid">
                  {galleryPhotos.map((photo) => (
                    <div key={photo.filename} className="gallery-item">
                      <img
                        src={`http://localhost:5000/api/gallery/download/${photo.filename}`}
                        alt={`Photo from ${new Date(photo.timestamp * 1000).toLocaleString()}`}
                        onError={(e) => {
                          e.target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZGRkIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtc2l6ZT0iMTQiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIiBmaWxsPSIjOTk5Ij5JbWFnZSBFcnJvcjwvdGV4dD48L3N2Zz4=';
                        }}
                      />
                      <div className="gallery-item-info">
                        <small>{new Date(photo.timestamp * 1000).toLocaleString()}</small>
                        <button
                          onClick={() => downloadPhoto(photo.filename)}
                          className="download-btn"
                        >
                          Download
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;