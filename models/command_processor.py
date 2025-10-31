"""
Command Processor - Now uses Semantic Classifier (Ollama)
This REPLACES Model 1
"""
import logging
import re
from models.semantic_classifier import SemanticClassifier

logger = logging.getLogger("CommandProcessor")

class CommandProcessor:
    """Process commands with semantic understanding"""
    
    def __init__(self):
        """Initialize with Semantic Classifier"""
        try:
            self.classifier = SemanticClassifier(model="mistral")
        except Exception as e:
            logger.error(f"Failed to initialize semantic classifier: {e}")
            raise
    
    def process(self, text):
        """Process command using Ollama LLM"""
        if not text or len(text.strip()) < 2:
            raise Exception("Text too short")
        
        # ✅ Use Semantic Classifier (Ollama LLM)
        classification = self.classifier.classify(text)
        category = classification.get('category', '')
        confidence = classification.get('confidence', 0)
        action = classification.get('action', '')
        
        # Filter valid categories
        valid_categories = ['SYSTEM_ACTION', 'APP_LAUNCH', 'IN_APP_ACTION', 'WEB_ACTION']
        if category not in valid_categories:
            logger.warning(f"Invalid: {category}")
            raise Exception(f"Invalid category: {category}")
        
        # Extract entities
        entities = self._extract_entities(text, category, action)
        
        return {
            "classification": {
                "category": category,
                "confidence": confidence,
                "action": action,
                "raw_command": text
            },
            "entities": entities,
            "raw_command": text
        }
    
    def _extract_entities(self, text, category, action):
        """Extract parameters from command"""
        entities = {"action": action}
        
        if category == 'APP_LAUNCH':
            match = re.search(r'(?:open|launch|start)\s+(\w+)', text, re.IGNORECASE)
            if match:
                entities['app_name'] = match.group(1).lower().rstrip('.')
        
        elif category == 'SYSTEM_ACTION':
            match = re.search(r'(\d+)\s*%?', text)
            if match:
                entities['value'] = int(match.group(1))
        
        return entities
