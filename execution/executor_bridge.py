"""
Executor Bridge - Complete C Integration
Bridges Python to C executors with full function support
"""

import ctypes
import os
import platform
from pathlib import Path
from utils.logger import setup_logger


class ExecutorBridge:
    """Bridge between Python and C executors"""
    
    def __init__(self):
        self.logger = setup_logger('ExecutorBridge')
        self.system_platform = platform.system()
        self.c_lib = None
        
        # Load C library
        try:
            lib_path = self._get_library_path()
            self.c_lib = ctypes.CDLL(lib_path)
            self._setup_functions()
            self.logger.info("C executor library loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to load C library: {e}")
            raise Exception("C executor library is REQUIRED. Please compile C executors.")
    
    def _get_library_path(self):
        """Get path to compiled C library"""
        base_path = Path(__file__).parent / 'c_executors'
        
        if self.system_platform == 'Windows':
            lib_name = 'executor.dll'
        elif self.system_platform == 'Darwin':
            lib_name = 'executor.dylib'
        else:
            lib_name = 'executor.so'
        
        lib_path = base_path / lib_name
        
        if not lib_path.exists():
            raise FileNotFoundError(f"C library not found at {lib_path}")
        
        return str(lib_path.absolute())
    
    def _setup_functions(self):
        """Setup C function signatures"""
        # Mouse functions
        self.c_lib.mouse_move.argtypes = [ctypes.c_int, ctypes.c_int]
        self.c_lib.mouse_move.restype = ctypes.c_int
        
        self.c_lib.mouse_click.argtypes = [ctypes.c_int]
        self.c_lib.mouse_click.restype = ctypes.c_int
        
        self.c_lib.mouse_scroll.argtypes = [ctypes.c_int]
        self.c_lib.mouse_scroll.restype = ctypes.c_int
        
        # Keyboard functions
        self.c_lib.keyboard_press_key.argtypes = [ctypes.c_int]
        self.c_lib.keyboard_press_key.restype = ctypes.c_int
        
        self.c_lib.keyboard_type_string.argtypes = [ctypes.c_char_p]
        self.c_lib.keyboard_type_string.restype = ctypes.c_int
    
    def launch_application(self, app_name):
        """Launch application (Windows: Win+Search+Enter)"""
        try:
            self.logger.info(f"Launching: {app_name}")
            
            # Press Windows key
            self.c_lib.keyboard_press_key(0x5B)  # VK_LWIN
            import time
            time.sleep(0.5)
            
            # Type app name
            app_bytes = app_name.encode('utf-8')
            self.c_lib.keyboard_type_string(app_bytes)
            time.sleep(0.5)
            
            # Press Enter
            self.c_lib.keyboard_press_key(0x0D)  # VK_RETURN
            
            return {'success': True}
        except Exception as e:
            self.logger.error(f"App launch error: {e}")
            return {'success': False, 'error': str(e)}
    
    def execute_action(self, action_type, coordinates, parameters):
        """Execute generic action"""
        try:
            if action_type == 'MOUSE_CLICK':
                x = coordinates.get('x', 0)
                y = coordinates.get('y', 0)
                self.c_lib.mouse_move(x, y)
                import time
                time.sleep(0.1)
                button = 0 if parameters.get('button') == 'left' else 1
                result = self.c_lib.mouse_click(button)
                return {'success': result == 0}
            
            elif action_type == 'TYPE_TEXT':
                text = parameters.get('text', '')
                text_bytes = text.encode('utf-8')
                result = self.c_lib.keyboard_type_string(text_bytes)
                return {'success': result == 0}
            
            elif action_type == 'PRESS_KEY':
                key = parameters.get('key', '')
                vk_code = self._key_to_vk(key)
                result = self.c_lib.keyboard_press_key(vk_code)
                return {'success': result == 0}
            
            elif action_type == 'MOUSE_SCROLL':
                amount = parameters.get('amount', 0)
                result = self.c_lib.mouse_scroll(amount)
                return {'success': result == 0}
            
            else:
                return {'success': False, 'error': f'Unknown action: {action_type}'}
        
        except Exception as e:
            self.logger.error(f"Action execution error: {e}")
            return {'success': False, 'error': str(e)}
    
    def _key_to_vk(self, key):
        """Convert key string to virtual key code"""
        key_map = {
            'enter': 0x0D,
            'tab': 0x09,
            'escape': 0x1B,
            'space': 0x20,
            'backspace': 0x08,
            'delete': 0x2E,
            'ctrl+l': 0x4C,  # Simplified
            'ctrl+c': 0x43,
            'ctrl+v': 0x56,
        }
        return key_map.get(key.lower(), 0x0D)
