import logging
import time
from pynput.keyboard import Controller as PyKeyboardController, Key as PyKey
import pyautogui

logger = logging.getLogger("ActionRouter")

class ActionRouter:
    """Action Router with integrated vision capabilities."""
    
    def __init__(self, system_executor, screenshot_handler, screen_analyzer, omniparser):
        self.system_executor = system_executor
        self.screenshot_handler = screenshot_handler
        self.screen_analyzer = screen_analyzer
        self.omniparser = omniparser
        self.py_keyboard = PyKeyboardController()
        logger.info("✓ Action Router initialized with Vision and C Executor Bridge.")

    def execute(self, category, steps, entities, raw_command, classification):
        logger.info(f"🔄 Executing {len(steps)} steps for command: '{raw_command}'")
        if not steps:
            return {"success": False, "error": "No execution plan (steps) provided."}
        
        try:
            for i, step in enumerate(steps):
                action_type = step.get('action_type')
                params = step.get('parameters', {})
                description = step.get('description', 'No description')

                logger.info(f"  -> Step {i+1}/{len(steps)}: {action_type} - {description}")

                if action_type == "PRESS_KEY":
                    key_str = params.get('key', '')
                    if key_str:
                        self.system_executor.executor.execute_action("PRESS_KEY", {}, {"key": key_str})
                        logger.info(f"  -> Action successful: Pressed key(s) '{key_str}'")
                
                elif action_type == "TYPE_TEXT":
                    text_to_type = params.get('text', '')
                    if text_to_type:
                        self.system_executor.executor.execute_action("TYPE_TEXT", {}, {"text": text_to_type})
                        logger.info(f"  -> Action successful: Typed '{text_to_type}'")
                
                elif action_type == "WAIT":
                    duration = params.get('duration', 0.5)
                    time.sleep(float(duration))

                elif action_type == "MOUSE_CLICK" or action_type == "SCREEN_ANALYSIS":
                    # Vision-powered click
                    target_description = description # Use the full description as the target
                    logger.info(f"  -> Vision: Looking for '{target_description}'")
                    
                    screenshot_path = self.screenshot_handler.capture()
                    if not screenshot_path:
                        logger.error("  -> Vision: Failed to capture screenshot. Skipping step.")
                        continue

                    elements = self.omniparser.parse_screen(screenshot_path, raw_command).get('elements', [])
                    
                    if not elements:
                        logger.error("  -> Vision: OmniParser found no elements on screen.")
                        # Fallback to a blind click at the current position
                        self.system_executor.executor.execute_action("MOUSE_CLICK", {}, {"button": "left"})
                        logger.info("  -> Action successful: Performed blind click")
                        continue

                    # Use ScreenAnalyzer to select the best coordinate
                    coordinate = self.screen_analyzer.select_coordinate(elements, target_description, step)

                    if coordinate:
                        x, y = coordinate
                        logger.info(f"  -> Vision: Clicking at ({x}, {y}) for '{target_description}'")
                        self.system_executor.executor.execute_action("MOUSE_CLICK", {'x': x, 'y': y}, {"button": "left"})
                        logger.info(f"  -> Action successful: Clicked at ({x}, {y})")
                    else:
                        logger.warning(f"  -> Vision: Could not find a coordinate for '{target_description}'. Performing blind click.")
                        self.system_executor.executor.execute_action("MOUSE_CLICK", {}, {"button": "left"})
                        logger.info("  -> Action successful: Performed blind click")

                elif action_type == "SYSTEM_ACTION":
                    action = params.get('action', '')
                    self.system_executor.execute_system_command(action)
                    logger.info(f"  -> Action successful: Executed system action '{action}'")

                elif action_type == "FOCUS_WINDOW":
                    title = params.get('title', '')
                    if title:
                        self.system_executor.executor.focus_window_by_title(title)
                        logger.info(f"  -> Action successful: Focused window with title '{title}'")

                else:
                    logger.warning(f"Unknown action_type: {action_type}. Skipping step.")
            
            return {"success": True, "message": "All steps executed successfully."}

        except Exception as e:
            logger.error(f"❌ Execution error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}