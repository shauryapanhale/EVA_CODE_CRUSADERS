"""
Screen Understanding using Gemini (Vision)
Methodology: Produces 1-2 line screen summary for step generation
"""

import logging
import json
import re
import google.generativeai as genai

logger = logging.getLogger("ScreenAnalyzer")


class ScreenAnalyzer:
    """Gemini-based screen understanding and coordinate selection"""
    
    def __init__(self, api_key):
        """Initialize Gemini for screen analysis"""
        self.logger = logging.getLogger("ScreenAnalyzer")
        
        try:
            genai.configure(api_key=api_key)
            
            # ✅ Try models in order - NO TEST CALL
            models_to_try = [
                'gemini-2.0-flash-exp',
                'gemini-1.5-pro',
                'gemini-1.5-flash',
                'gemini-pro'
            ]
            
            self.model = None
            for model_name in models_to_try:
                try:
                    # Just create the model object, don't test it
                    test_model = genai.GenerativeModel(model_name)
                    self.model = test_model
                    self.logger.info(f"✓ Gemini initialized: {model_name}")
                    break
                except Exception as e:
                    self.logger.debug(f"Model {model_name} unavailable: {e}")
                    continue
            
            if not self.model:
                self.logger.error("❌ NO GEMINI MODELS AVAILABLE - Check:")
                self.logger.error("1. GEMINI_API_KEY is valid in .env")
                self.logger.error("2. API key has quota remaining")
                self.logger.error("3. Models are enabled in Google AI Studio")
                raise Exception("No Gemini model available - check GEMINI_API_KEY")
        
        except Exception as e:
            self.logger.error(f"❌ Gemini initialization failed: {e}")
            raise
    
    def get_screen_summary(self, screenshot_path):
        """
        Get 1-2 line screen summary (Methodology requirement)
        
        Args:
            screenshot_path: Path to PNG screenshot
        
        Returns:
            str: Brief screen state description
        """
        try:
            with open(screenshot_path, 'rb') as f:
                image_data = f.read()
            
            image_part = {
                "mime_type": "image/png",
                "data": image_data
            }
            
            prompt = """Analyze this screenshot and provide a concise 1-2 line summary describing:

1. What application is open
2. Current screen state
3. Visible UI elements

Keep it brief and factual. Example: "Chrome browser is open showing YouTube homepage with search bar visible at top."

Summary:"""
            
            self.logger.info("Requesting screen summary from Gemini...")
            response = self.model.generate_content([prompt, image_part])
            
            # Extract text safely
            if hasattr(response, 'text'):
                summary = response.text.strip()
            else:
                summary = str(response).strip()
            
            self.logger.info(f"Screen summary: {summary[:100]}...")
            return summary
        
        except Exception as e:
            self.logger.error(f"Screen summary error: {e}")
            return "Unable to analyze screen"
    
    def filter_coordinates(self, omniparser_elements, step_description):
        """
        Filter OmniParser elements to find best match for step
        
        Methodology: "Gemini filters the OmniParser UI element list"
        
        Args:
            omniparser_elements: List of UI elements from OmniParser
            step_description: Current step description
        
        Returns:
            dict: {"x": int, "y": int, "operation": str, "confidence": float}
        """
        try:
            # Simplify elements for Gemini
            simplified = []
            for e in omniparser_elements[:30]:  # Top 30 elements
                simplified.append({
                    'id': e.get('id'),
                    'label': e.get('label', ''),
                    'x': e.get('x'),
                    'y': e.get('y'),
                    'type': e.get('type')
                })
            
            prompt = f"""You are filtering UI elements to execute this step: "{step_description}"

Available elements:
{json.dumps(simplified, indent=2)}

Return ONLY JSON:
{{
  "element_id": 5,
  "x": 100,
  "y": 200,
  "operation": "click",
  "confidence": 85
}}

Valid operations: click, double_click, right_click

JSON:"""
            
            self.logger.info(f"Filtering coordinates for: {step_description}")
            response = self.model.generate_content(prompt)
            
            # Extract and parse JSON safely
            if hasattr(response, 'text'):
                response_text = response.text.strip()
            else:
                response_text = str(response).strip()
            
            # ✅ FIX: Handle markdown JSON properly
            if '```':
                response_text = response_text.split('```json').split('```')
            elif '```' in response_text:
                parts = response_text.split('```')
                for part in parts:
                    if '{' in part and '}' in part:
                        response_text = part.strip()
                        break
            
            # Extract JSON object
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
                self.logger.info(f"Selected: ({result.get('x')}, {result.get('y')}) confidence: {result.get('confidence')}%")
                return result
            else:
                self.logger.warning("No JSON found in response")
                return {"x": 0, "y": 0, "operation": "click", "confidence": 0}
        
        except Exception as e:
            self.logger.error(f"Coordinate filtering error: {e}")
            return {"x": 0, "y": 0, "operation": "click", "confidence": 0}
    
    def select_coordinate(self, elements, target_label, step_context):
        """
        Use Gemini to select best coordinate from OmniParser elements
        
        Args:
            elements: List of {id, label, x, y, type, confidence} from OmniParser
            target_label: What we're looking for (e.g., "Code Crusaders", "Type a message")
            step_context: Full step dict with description
        
        Returns:
            (x, y) tuple or None
        """
        if not elements:
            self.logger.warning("No elements to select from")
            return None
        
        # Format elements for Gemini
        element_list = []
        for elem in elements:
            element_list.append(
                f"{elem['id']}: '{elem['label']}' at ({elem['x']}, {elem['y']}) "
                f"[type: {elem.get('type', 'unknown')}, conf: {elem.get('confidence', 0):.2f}]"
            )
        
        prompt = f"""You are a UI element selector for a Windows automation assistant.

TASK: Select the best UI element to click for this action.

TARGET: "{target_label}"
ACTION DESCRIPTION: "{step_context.get('description', '')}"

AVAILABLE UI ELEMENTS:
{chr(10).join(element_list)}

RULES:
1. Return ONLY a JSON object: {{"id": N, "reason": "..."}}
2. Prefer exact label matches
3. Prefer elements with type 'text' if target is text-based
4. Prefer higher confidence scores
5. If no match found, return {{"id": -1, "reason": "No confident match"}}

Examples:
- Target "Code Crusaders" → Select element with "Code Crusaders" in label
- Target "Type a message" → Select text element or input field
- Target "Send" button → Select clickable element with "Send"

Return ONLY JSON, no explanation.
"""
        
        try:
            response = self.model.generate_content(prompt)
            
            # Extract text safely
            if hasattr(response, 'text'):
                response_text = response.text.strip()
            else:
                response_text = str(response).strip()
            
            self.logger.info(f"Gemini response: {response_text[:200]}")
            
            # ✅ FIX: Handle markdown JSON properly
            if '```json' in response_text:
                response_text = response_text.split('``````')[0].strip()
            elif '```':
                parts = response_text.split('```')
                for part in parts:
                    if '{' in part and '}' in part:
                        response_text = part.strip()
                        break
            
            # Try to find JSON object
            json_match = re.search(r'\{[^}]+\}', response_text)
            if json_match:
                result = json.loads(json_match.group(0))
                elem_id = result.get('id', -1)
                
                # Find element by id
                for elem in elements:
                    if elem['id'] == elem_id:
                        self.logger.info(f"✓ Selected: '{elem['label']}' at ({elem['x']}, {elem['y']})")
                        return (elem['x'], elem['y'])
                
                self.logger.warning(f"Element ID {elem_id} not found. Reason: {result.get('reason')}")
            else:
                self.logger.warning(f"No JSON found in response")
            
            return None
        
        except Exception as e:
            self.logger.error(f"Coordinate selection error: {e}", exc_info=True)
            return None
