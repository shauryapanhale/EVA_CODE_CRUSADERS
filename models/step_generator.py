"""
Model 2: Step Generator
Generates execution steps based on command category
"""
import logging
import pickle
from pathlib import Path
import config

logger = logging.getLogger("StepGenerator")

class StepGenerator:
    """Generates step-by-step execution plans"""
    
    def __init__(self):
        """Initialize step generator"""
        self.logger = logging.getLogger("StepGenerator")
        self.model_path = Path(config.MODEL_WEIGHTS_DIR) / 'step_model.pkl'
        
        if self.model_path.exists():
            self.load_model()
        else:
            self.create_default_rules()
        
        self.logger.info("✓ Step Generator initialized")
    
    def load_model(self):
        """Load pre-trained rules"""
        try:
            with open(self.model_path, 'rb') as f:
                self.rules = pickle.load(f)
            self.logger.info("✓ Step rules loaded from pickle")
        except Exception as e:
            self.logger.warning(f"Failed to load model: {e}, using defaults")
            self.create_default_rules()
    
    def create_default_rules(self):
        """Create default step rules for all categories"""
        self.rules = {
            # APP LAUNCH: Win + Type + Enter
            "APP_LAUNCH": [
                {"action": "press_key", "key": "win", "description": "Press Windows key"},
                {"action": "wait", "duration": 0.5, "description": "Wait for start menu"},
                {"action": "type", "text": "{app_name}", "description": "Type app name"},
                {"action": "press_key", "key": "enter", "description": "Press Enter to launch"},
            ],
            
            # SYSTEM ACTION: Direct execution via Windows API
            "SYSTEM_ACTION": [
                {"action": "direct_execute", "description": "Execute via Windows API (no Model 2 needed)"}
            ],
            
            # IN APP: Alt + Type + Enter
            "IN_APP_ACTION": [
                {"action": "press_key", "key": "alt", "description": "Open app menu"},
                {"action": "wait", "duration": 0.3, "description": "Wait for menu"},
                {"action": "type", "text": "{action}", "description": "Type action"},
                {"action": "press_key", "key": "enter", "description": "Execute"},
            ],
            
            # WEB: Ctrl+L + Type + Enter
            "WEB_ACTION": [
                {"action": "press_key", "key": "ctrl+l", "description": "Focus address bar"},
                {"action": "wait", "duration": 0.2, "description": "Wait"},
                {"action": "type", "text": "{target}", "description": "Type URL"},
                {"action": "press_key", "key": "enter", "description": "Navigate"},
            ],
        }
        self.logger.info("✓ Created default step rules")
    
    def generate(self, command_data):
        """Generate steps for a command (METHOD THAT WAS MISSING!)"""
        category = command_data['classification']['category']
        
        # ✅ SYSTEM_ACTION bypasses Model 2 - goes directly to executor
        if category == 'SYSTEM_ACTION':
            self.logger.info("📍 SYSTEM_ACTION detected - bypassing Model 2, using direct Windows API")
            return []  # ✅ NO STEPS - handled by action_router directly
        
        # Get steps for category
        steps = self.rules.get(category, [])
        
        # ✅ Replace placeholders with actual entity values
        entities = command_data['entities']
        app_name = entities.get('app_name', '')
        
        # Replace {app_name} in steps
        for step in steps:
            if 'text' in step and '{app_name}' in step['text']:
                step['text'] = app_name
        
        self.logger.info(f"✓ Generated {len(steps)} steps for {category}")
        return steps
