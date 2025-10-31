"""
Action Router - Routes commands to appropriate executors
Executes keyboard and mouse actions for IN_APP
"""
import logging
from colorama import Fore, Style
import time
from pynput.keyboard import Controller, Key
from pynput.mouse import Controller as MouseController

logger = logging.getLogger("ActionRouter")
keyboard = Controller()
mouse = MouseController()

class ActionRouter:
    """Routes commands and executes steps"""
    
    def __init__(self, system_executor, screenshot_handler):
        """Initialize action router"""
        self.system_executor = system_executor
        self.screenshot_handler = screenshot_handler
        logger.info("✓ Action router initialized")
    
    def execute(self, category, steps, entities, raw_command, classification):
        """Execute the action"""
        logger.info(f"📍 Routing {category} command")
        
        try:
            if category == 'APP_LAUNCH':
                return self._execute_app_launch(entities)
            elif category == 'SYSTEM_ACTION':
                return self._execute_system_action(entities, classification, raw_command)
            elif category == 'IN_APP_ACTION':
                return self._execute_in_app_action(entities, raw_command)
            elif category == 'WEB_ACTION':
                return self._execute_web_action(entities, raw_command)
            else:
                return {"success": False, "error": f"Unknown category: {category}"}
        except Exception as e:
            logger.error(f"❌ Execution error: {e}")
            return {"success": False, "error": str(e)}
    
    def _execute_app_launch(self, entities):
        """Launch application"""
        app_name = entities.get('app_name', '').lower().rstrip('.')
        logger.info(f"🚀 Launching app: {app_name}")
        
        try:
            result = self.system_executor.executor.launch_application(app_name)
            if result.get('success'):
                print(f"{Fore.GREEN}✅ Opened {app_name}{Style.RESET_ALL}")
            return result
        except Exception as e:
            logger.error(f"❌ App launch failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _execute_system_action(self, entities, classification, raw_command):
        """Execute volume, brightness, power"""
        subcategory = classification.get('subcategory', '').lower()
        logger.info(f"⚙️ System action: {subcategory}")
        
        try:
            if subcategory == 'volume':
                import re
                match = re.search(r'(\d+)', raw_command)
                if match:
                    level = int(match.group(1))
                    result = self.system_executor.set_volume(level)
                    if result.get('success'):
                        print(f"{Fore.GREEN}✅ {result['message']}{Style.RESET_ALL}")
                    return result
                return {"success": False, "error": "No volume level found"}
            
            elif subcategory == 'brightness':
                import re
                match = re.search(r'(\d+)', raw_command)
                if match:
                    level = int(match.group(1))
                    result = self.system_executor.set_brightness(level)
                    if result.get('success'):
                        print(f"{Fore.GREEN}✅ {result['message']}{Style.RESET_ALL}")
                    return result
                return {"success": False, "error": "No brightness level found"}
            
            elif subcategory in ['shutdown', 'restart', 'sleep', 'lock']:
                result = self.system_executor.execute_system_command(subcategory)
                if result.get('success'):
                    print(f"{Fore.GREEN}✅ {result['message']}{Style.RESET_ALL}")
                return result
            
            else:
                return {"success": False, "error": f"Unknown system action"}
        
        except Exception as e:
            logger.error(f"❌ System action error: {e}")
            return {"success": False, "error": str(e)}
    
    def _execute_in_app_action(self, entities, raw_command):
        """Execute IN_APP_ACTION: close, click, type"""
        action = entities.get('action', '').lower()
        logger.info(f"🔄 In-app action: {action}")
        
        try:
            if action == 'close':
                # Alt+F4 to close window
                keyboard.press(Key.alt)
                keyboard.press(Key.f4)
                keyboard.release(Key.f4)
                keyboard.release(Key.alt)
                time.sleep(0.5)
                print(f"{Fore.GREEN}✅ Window closed{Style.RESET_ALL}")
                return {"success": True, "message": "Window closed"}
            
            elif action == 'click':
                # Click center of screen
                mouse.click()
                time.sleep(0.3)
                print(f"{Fore.GREEN}✅ Clicked{Style.RESET_ALL}")
                return {"success": True, "message": "Clicked"}
            
            elif action == 'type':
                # Extract text to type
                import re
                match = re.search(r'type\s+(.+)', raw_command, re.IGNORECASE)
                if match:
                    text = match.group(1)
                    keyboard.type(text)
                    time.sleep(0.2)
                    print(f"{Fore.GREEN}✅ Typed: {text}{Style.RESET_ALL}")
                    return {"success": True, "message": f"Typed: {text}"}
            
            else:
                return {"success": False, "error": f"Unknown in-app action: {action}"}
        
        except Exception as e:
            logger.error(f"❌ In-app action error: {e}")
            return {"success": False, "error": str(e)}
    
    def _execute_web_action(self, entities, raw_command):
        """Execute WEB_ACTION"""
        logger.info(f"🌐 Web action")
        return {"success": True, "message": "Web action completed"}
