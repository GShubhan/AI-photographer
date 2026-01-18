# STT_function.py
import pyaudio
import speech_recognition as sr
import threading
from queue import Queue

class STTListener:
    def __init__(self):
        self.r = sr.Recognizer()
        self.result_queue = Queue()
        self.listening = False
        self.thread = None
    
    def start_listening(self):
        """Start background listening"""
        if self.listening:
            print("⚠️  Already listening")
            return
        
        self.listening = True
        self.thread = threading.Thread(target=self._listener_loop, daemon=True)
        self.thread.start()
        print("🎤 Background listener started")
    
    def stop_listening(self):
        """Stop listening"""
        self.listening = False
        print("🎤 Listener stopped")
    
    def _listener_loop(self):
        """Runs in background thread - continuously listens"""
        try:
            with sr.Microphone() as source:
                self.r.adjust_for_ambient_noise(source, duration=1)
                print("Speak something...")
                
                while self.listening:
                    try:
                        # Listen with timeout
                        audio = self.r.listen(source, timeout=10)
                        print("Audio captured. Processing...")
                        
                        # Recognize speech
                        text = self.r.recognize_google(audio)
                        print(f"You said: {text}")
                        
                        # Check for commands
                        still_listening = True
                        if "i am done" in text.lower():
                            print("finally you stop talking")
                            still_listening = False
                        
                        # Put result in queue
                        self.result_queue.put({
                            'status': 'success',
                            'text': text,
                            'still_listening': still_listening,
                            'error': None
                        })
                        
                        # If user said stop, exit loop
                        if not still_listening:
                            self.listening = False
                    
                    except sr.UnknownValueError:
                        print("Sorry, could not understand the audio.")
                        self.result_queue.put({
                            'status': 'error',
                            'text': "",
                            'still_listening': True,
                            'error': 'Could not understand audio'
                        })
                    
                    except sr.RequestError as e:
                        print(f"Could not request results; {e}")
                        self.result_queue.put({
                            'status': 'error',
                            'text': "",
                            'still_listening': True,
                            'error': str(e)
                        })
                    
                    except sr.WaitTimeoutError:
                        # Timeout - just continue listening
                        continue
        
        except Exception as e:
            print(f"❌ Listener error: {e}")
            self.result_queue.put({
                'status': 'error',
                'text': "",
                'still_listening': False,
                'error': str(e)
            })
    
    def get_latest_text(self, timeout=1):
        """Get text without blocking, returns None if not ready"""
        try:
            return self.result_queue.get(timeout=timeout)
        except:
            return None
    
    def is_queue_empty(self):
        """Check if there's new text available"""
        return self.result_queue.empty()
    
    def clear_queue(self):
        """Clear all queued results"""
        while not self.result_queue.empty():
            try:
                self.result_queue.get_nowait()
            except:
                break


# Global instance
stt_listener = STTListener()

# stt_listener.start_listening()
# cnt = 0

# while True:
#     print(stt_listener.get_latest_text())
#     cnt+=1
#     if cnt>100 or not stt_listener.listening:
#         break

# Keep backward compatibility
def stt_function(listening):
    """
    Original function signature - kept for backward compatibility
    Returns: text (string)
    """
    text = ""
    
    if listening:
        stt_listener.start_listening()
        
        # Wait up to 5 seconds for result
        stt_result = stt_listener.get_latest_text(timeout=5)
        
        if stt_result and stt_result['status'] == 'success':
            text = stt_result['text']
        
        stt_listener.stop_listening()
    
    return text
