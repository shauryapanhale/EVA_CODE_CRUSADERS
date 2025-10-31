"""
Screen Understanding using Gemini (Vision)
Methodology: Produces 1-2 line screen summary for step generation
"""
import logging
import google.generativeai as genai

logger = logging.getLogger("ScreenAnalyzer")

class ScreenAnalyzer:
    """Gemini-based screen understanding (summary only)"""
    
    def __init__(self, api_key):
        """Initialize Gemini for screen analysis"""
        try:
            genai.configure(api_key=api_key)
            
            models_to_try = [
                'models/gemini-2.0-flash-exp',
                'models/gemini-1.5-flash',
                'models/gemini-1.5-pro'
            ]
            
            self.model = None
            for model_name in models_to_try:
                try:
                    self.model = genai.GenerativeModel(model_name)
                    logger.info(f"✓ Gemini initialized: {model_name}")
                    break
                except:
                    continue
            
            if not self.model:
                raise Exception("No Gemini model available")
                
        except Exception as e:
            logger.error(f"❌ Gemini initialization failed: {e}")
            raise
    
    def get_screen_summary(self, screenshot_path):
        """
        Get 1-2 line screen summary (Methodology requirement)
        
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
            
            logger.info("Requesting screen summary from Gemini...")
            
            response = self.model.generate_content([prompt, image_part])
            
            # Extract text
            if hasattr(response, 'text'):
                summary = response.text.strip()
            else:
                summary = str(response).strip()
            
            logger.info(f"Screen summary: {summary[:100]}...")
            
            return summary
            
        except Exception as e:
            logger.error(f"Screen summary error: {e}")
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
            import json
            
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
            
            logger.info(f"Filtering coordinates for: {step_description}")
            
            response = self.model.generate_content(prompt)
            
            # Extract and parse JSON
            if hasattr(response, 'text'):
                response_text = response.text.strip()
            else:
                response_text = str(response).strip()
            
            # Clean JSON
            if '```':
                response_text = response_text.split('```json').split('```')
            elif '```' in response_text:
                parts = response_text.split('```')
                for part in parts:
                    if '{' in part and '}' in part:
                        response_text = part.strip()
                        break
            
            result = json.loads(response_text)
            
            logger.info(f"Selected coordinate: ({result.get('x')}, {result.get('y')}) confidence: {result.get('confidence')}%")
            
            return result
            
        except Exception as e:
            logger.error(f"Coordinate filtering error: {e}")
            return {"x": 0, "y": 0, "operation": "click", "confidence": 0}
