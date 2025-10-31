"""
Semantic Classifier - Uses Local LLM (Mistral) via Ollama
Replaces Model 1 - understands intent semantically
"""
import logging
import json
import requests
from typing import Dict

logger = logging.getLogger("SemanticClassifier")

class SemanticClassifier:
    """Classify commands using local LLM"""
    
    def __init__(self, model="mistral", host="http://localhost:11434"):
        """Initialize with local Ollama"""
        self.model = model
        self.host = host
        self.api_endpoint = f"{host}/api/generate"
        logger.info(f"✓ Semantic Classifier initialized (Model: {model})")
        
        # Check if Ollama is running
        try:
            requests.get(f"{host}/api/tags", timeout=2)
            logger.info("✓ Ollama is running at localhost:11434")
        except:
            logger.error("❌ Ollama not running! Run: ollama serve (in another terminal)")
            raise Exception("Ollama required - must be running!")
    
    def classify(self, text: str) -> Dict:
        """Classify command using local LLM"""
        
        prompt = f"""You are a command classifier for a voice assistant.

Analyze this command and return ONLY a JSON response.

CATEGORIES:
- APP_LAUNCH: Opening applications (open chrome, launch spotify, start notepad)
- SYSTEM_ACTION: Volume, brightness, power (set volume to 50, increase brightness, mute)
- IN_APP_ACTION: Actions inside apps (play music, pause, send message, click button, next song, close)
- WEB_ACTION: Search and navigation (search for python, go to youtube, look up weather)

USER COMMAND: "{text}"

Return ONLY valid JSON (no explanation):
{{"category": "CATEGORY", "confidence": 0.95, "action": "action_name"}}

Examples:
1. "play music" → {{"category": "IN_APP_ACTION", "confidence": 0.95, "action": "play"}}
2. "set volume to 50" → {{"category": "SYSTEM_ACTION", "confidence": 0.95, "action": "set_volume"}}
3. "search for python" → {{"category": "WEB_ACTION", "confidence": 0.9, "action": "search"}}
4. "open chrome" → {{"category": "APP_LAUNCH", "confidence": 0.95, "action": "launch"}}
5. "pause" → {{"category": "IN_APP_ACTION", "confidence": 0.95, "action": "pause"}}
6. "next track" → {{"category": "IN_APP_ACTION", "confidence": 0.9, "action": "next"}}
7. "send whatsapp message" → {{"category": "IN_APP_ACTION", "confidence": 0.9, "action": "send"}}
8. "close window" → {{"category": "IN_APP_ACTION", "confidence": 0.95, "action": "close"}}
"""
        
        try:
            # Call local Ollama
            response = requests.post(
                self.api_endpoint,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.2  # Low = consistent
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get('response', '').strip()
                
                # Extract JSON from response
                try:
                    start = response_text.find('{')
                    end = response_text.rfind('}') + 1
                    if start >= 0 and end > start:
                        json_str = response_text[start:end]
                        classification = json.loads(json_str)
                        
                        logger.info(f"🧠 '{text}' → {classification.get('category')} ({classification.get('confidence')*100:.0f}%)")
                        return classification
                except json.JSONDecodeError:
                    logger.warning(f"⚠️ Invalid JSON: {response_text}")
                    return {"category": "IN_APP_ACTION", "confidence": 0.5, "action": "unknown"}
            else:
                logger.error(f"Ollama error: {response.status_code}")
                return {"category": "IN_APP_ACTION", "confidence": 0.5, "action": "unknown"}
        
        except requests.exceptions.Timeout:
            logger.error("❌ Ollama timeout (maybe overloaded, wait 2 sec)")
            return {"category": "IN_APP_ACTION", "confidence": 0.5, "action": "unknown"}
        except Exception as e:
            logger.error(f"❌ Classification error: {e}")
            return {"category": "IN_APP_ACTION", "confidence": 0.5, "action": "unknown"}
