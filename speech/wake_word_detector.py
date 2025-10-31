"""
Wake Word Detection using Porcupine API
Strict Porcupine-only implementation
"""
import logging
import pvporcupine
import pyaudio
import struct
import config

logger = logging.getLogger("WakeWordDetector")

class WakeWordDetector:
    """Porcupine-based wake word detector"""
    
    def __init__(self, wake_word="jarvis"):
        """Initialize Porcupine"""
        self.wake_word = wake_word.lower()
        
        try:
            # Initialize Porcupine with API key
            logger.info(f"Initializing Porcupine with keyword: '{wake_word}'")
            self.porcupine = pvporcupine.create(
                access_key=config.PICOVOICE_ACCESS_KEY,
                keywords=[wake_word]
            )
            
            self.pa = pyaudio.PyAudio()
            self.audio_stream = None
            
            logger.info(f"✓ Porcupine initialized (keyword: '{wake_word}')")
            logger.info(f"Sample rate: {self.porcupine.sample_rate}, Frame length: {self.porcupine.frame_length}")
            
        except Exception as e:
            logger.critical(f"❌ Porcupine initialization FAILED: {e}")
            logger.critical("Check your API key at https://console.picovoice.ai/")
            raise RuntimeError(f"Porcupine MUST work. Error: {e}")
    
    def start(self):
        """Start Porcupine listening"""
        try:
            logger.info("Opening audio stream...")
            self.audio_stream = self.pa.open(
                rate=self.porcupine.sample_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=self.porcupine.frame_length
            )
            logger.info("🎤 Porcupine listening for wake word...")
            logger.info(f"✓ Audio stream started (say '{self.wake_word.upper()}' clearly)")
            
        except Exception as e:
            logger.critical(f"❌ Failed to start audio: {e}")
            raise RuntimeError(f"Audio stream failed: {e}")
    
    def listen(self):
        """Listen for wake word using Porcupine"""
        if not self.audio_stream:
            raise RuntimeError("Audio stream not started")
        
        try:
            # Read audio data
            pcm = self.audio_stream.read(
                self.porcupine.frame_length, 
                exception_on_overflow=False
            )
            
            # Unpack to PCM
            pcm = struct.unpack_from("h" * self.porcupine.frame_length, pcm)
            
            # Process with Porcupine
            keyword_index = self.porcupine.process(pcm)
            
            if keyword_index >= 0:
                logger.info(f"🎯 WAKE WORD '{self.wake_word.upper()}' DETECTED!")
                return True
            
            return False
                
        except Exception as e:
            logger.error(f"Listen error: {e}")
            return False
    
    def stop(self):
        """Stop Porcupine"""
        if self.audio_stream:
            self.audio_stream.stop_stream()
            self.audio_stream.close()
        
        if self.porcupine:
            self.porcupine.delete()
        
        logger.info("Porcupine stopped")
