# voice.py
from gtts import gTTS
from playsound import playsound
import tempfile
import threading
import os
import time

# Cache for repeated phrases
_voice_cache = {}

# Cooldown tracking
last_prompt_time = {
    "face_detected": 0,
    "remove_accessory": 0,
    "scan_complete_threat": 0,
    "scan_complete_safe": 0,
    "camera_start": 0
}

PROMPT_COOLDOWN = {
    "face_detected": 15,
    "remove_accessory": 8,
    "scan_complete_threat": 5,
    "scan_complete_safe": 5,
    "camera_start": 60
}

# Global voice lock to prevent overlapping
_voice_lock = threading.Lock()
_currently_speaking = False

def _save_tts(text):
    """Generate TTS file once and return its path."""
    if text in _voice_cache:
        return _voice_cache[text]
    tts = gTTS(text=text, lang='en')
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tts.save(tmp_file.name)
    _voice_cache[text] = tmp_file.name
    return tmp_file.name

def speak_async(text):
    """Play in background without blocking, but ensure no overlap."""
    def _play():
        global _currently_speaking
        
        # Wait if another voice is playing
        with _voice_lock:
            if _currently_speaking:
                print(f"[Voice] Skipping - already speaking: {text}")
                return
            _currently_speaking = True
            
        try:
            path = _save_tts(text)
            playsound(path)
        except Exception as e:
            print(f"[Voice] Async error: {e}")
        finally:
            # Always release the lock
            with _voice_lock:
                _currently_speaking = False
                
    threading.Thread(target=_play, daemon=True).start()

def speak_sync(text):
    """Play and wait (blocking), with overlap protection."""
    global _currently_speaking
    
    with _voice_lock:
        if _currently_speaking:
            print(f"[Voice] Skipping sync - already speaking: {text}")
            return
        _currently_speaking = True
        
    try:
        path = _save_tts(text)
        playsound(path)
    except Exception as e:
        print(f"[Voice] Sync error: {e}")
    finally:
        with _voice_lock:
            _currently_speaking = False

def speak_event(key, text, sync=False):
    """Speak only if cooldown passed for this event AND no other voice is playing."""
    now = time.time()
    
    # Check cooldown first
    if now - last_prompt_time.get(key, 0) <= PROMPT_COOLDOWN.get(key, 0):
        return
        
    # Check if already speaking (additional protection)
    with _voice_lock:
        if _currently_speaking:
            print(f"[Voice] Skipping event - already speaking: {text}")
            return
    
    if sync:
        speak_sync(text)
    else:
        speak_async(text)
    last_prompt_time[key] = now