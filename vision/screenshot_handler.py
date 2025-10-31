"""Screenshot capture functionality"""

import mss
import os
from datetime import datetime
import config
from utils.logger import setup_logger

class ScreenshotHandler:
    """Capture and manage screenshots"""
    
    def __init__(self):
        self.logger = setup_logger('ScreenshotHandler')
        self.sct = mss.mss()
        
    def capture(self, monitor_number=1):
        """Capture screenshot of specified monitor"""
        try:
            # Get monitor info
            monitor = self.sct.monitors[monitor_number]
            
            # Capture screenshot
            screenshot = self.sct.grab(monitor)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"screen_{timestamp}.png"
            filepath = os.path.join(config.SCREENSHOT_TEMP_DIR, filename)
            
            # Save screenshot
            mss.tools.to_png(screenshot.rgb, screenshot.size, output=filepath)
            
            self.logger.info(f"Screenshot saved: {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Screenshot capture error: {e}")
            return None
    
    def cleanup_old_screenshots(self, keep_last_n=10):
        """Clean up old screenshots, keeping only the last N"""
        try:
            screenshots = sorted([
                os.path.join(config.SCREENSHOT_TEMP_DIR, f)
                for f in os.listdir(config.SCREENSHOT_TEMP_DIR)
                if f.startswith('screen_') and f.endswith('.png')
            ])
            
            if len(screenshots) > keep_last_n:
                for screenshot in screenshots[:-keep_last_n]:
                    os.remove(screenshot)
                    self.logger.info(f"Removed old screenshot: {screenshot}")
                    
        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")
