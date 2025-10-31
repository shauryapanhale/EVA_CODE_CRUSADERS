import os
from dotenv import load_dotenv
import logging
load_dotenv()

# API Keys
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'AIzaSyD7yJt1qn9rVD8TEUyIA9huDl6MCm6H5mA')
PICOVOICE_ACCESS_KEY = os.getenv('PICOVOICE_ACCESS_KEY', '8wrQWIEGVr2yXgIlWhJqpb20Y2KhxuECYbLb0/3ARSld8KVGy8gBSQ==')  # ✅ REQUIRED

# Wake Word
WAKE_WORD = "jarvis"
GOODBYE_PHRASE = "goodbye jarvis"

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_WEIGHTS_DIR = os.path.join(BASE_DIR, 'models', 'model_weights')
C_EXECUTOR_DIR = os.path.join(BASE_DIR, 'execution', 'c_executors')
SCREENSHOT_TEMP_DIR = os.path.join(BASE_DIR, 'temp_screenshots')
LOG_DIR = os.path.join(BASE_DIR, 'logs')

# Whisper Model Settings
WHISPER_MODEL_SIZE = "large"  # ✅ Changed to large (methodology)
WHISPER_DEVICE = "cpu"
WHISPER_COMPUTE_TYPE = "int8"

LOG_LEVEL = logging.INFO

# Gemini Settings (for screen summary + coordinate filtering ONLY)
GEMINI_MODEL = "models/gemini-2.0-flash-exp"
GEMINI_FALLBACK_MODELS = [
    "models/gemini-2.0-flash-exp",
    "models/gemini-1.5-flash",
    "models/gemini-1.5-pro"
]
GEMINI_TEMPERATURE = 0.3
GEMINI_MAX_RETRIES = 3

# Classification Settings
CLASSIFICATION_CONFIDENCE_THRESHOLD = 0.6

# Audio Settings
CHUNK_SIZE = 1024
SAMPLE_RATE = 16000
RECORD_SECONDS = 5

# Session Settings
SESSION_TIMEOUT = 10  # seconds
