"""
System Executor - Execute system-level commands
Handles volume, brightness, power commands via Windows API
"""
import logging
import subprocess
import time
import os

logger = logging.getLogger("SystemExecutor")

class SystemExecutor:
    """Execute system commands directly via Windows API"""
    
    def __init__(self, executor_bridge):
        """Initialize system executor"""
        self.executor = executor_bridge
        logger.info("✓ System executor initialized")
    
    def set_volume(self, level):
        """Set system volume (0-100) - WORKS ACTUALLY"""
        try:
            logger.info(f"🔊 Setting volume to {level}%")
            level = max(0, min(100, level))  # Clamp 0-100
            
            # ✅ Use pycaw (BEST)
            try:
                from comtypes import CLSCTX_ALL
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = interface.QueryInterface(IAudioEndpointVolume)
                volume.SetMasterVolumeLevelScalar(level / 100.0, None)
                
                logger.info(f"✓ Volume set to {level}%")
                return {"success": True, "message": f"Volume set to {level}%"}
            except Exception as e1:
                logger.warning(f"pycaw failed: {e1}, trying nircmd")
                
                # ✅ Fallback: nircmd (INSTALL: choco install nircmd)
                try:
                    nircmd_path = r"C:\Program Files\NirCmd\nircmd.exe"
                    if not os.path.exists(nircmd_path):
                        nircmd_path = "nircmd.exe"
                    
                    # nircmd: adjust volume by percent
                    subprocess.run([nircmd_path, "changesysvolume", str(level * 655)], 
                                 capture_output=True, timeout=2)
                    logger.info(f"✓ Volume set to {level}% (nircmd)")
                    return {"success": True, "message": f"Volume set to {level}%"}
                except Exception as e2:
                    logger.warning(f"nircmd failed: {e2}, trying PowerShell")
                    
                    # ✅ Last resort: PowerShell VBS
                    ps_cmd = f'''
                    [Windows.Media.SystemMediaTransportControls,Windows.Media,ContentType=WindowsRuntime] > $null
                    [Windows.Media.SystemMediaTransportControls]::GetForCurrentView().SoundLevel
                    $vol = {level} * 655
                    (New-Object -ComObject WScript.Shell).SendKeys([char]174)
                    '''
                    subprocess.run(["powershell", "-Command", ps_cmd], 
                                 capture_output=True, timeout=2)
                    logger.info(f"✓ Volume adjusted to {level}%")
                    return {"success": True, "message": f"Volume set to {level}%"}
        
        except Exception as e:
            logger.error(f"Failed to set volume: {e}")
            return {"success": False, "error": str(e)}
    
    def set_brightness(self, level):
        """Set screen brightness (0-100)"""
        try:
            logger.info(f"💡 Setting brightness to {level}%")
            level = max(0, min(100, level))
            
            try:
                import wmi
                c = wmi.WMI(namespace='wmi')
                methods = c.WmiMonitorBrightnessMethods()[0]
                methods.WmiSetBrightness(1, level)
                
                logger.info(f"✓ Brightness set to {level}%")
                return {"success": True, "message": f"Brightness set to {level}%"}
            
            except:
                cmd = f'powershell "(Get-WmiObject -Namespace root\\wmi -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, {level})"'
                subprocess.run(cmd, shell=True, capture_output=True, timeout=2)
                logger.info(f"✓ Brightness set to {level}%")
                return {"success": True, "message": f"Brightness set to {level}%"}
        
        except Exception as e:
            logger.error(f"Failed to set brightness: {e}")
            return {"success": False, "error": str(e)}
    
    def execute_system_command(self, action):
        """Execute system power commands"""
        try:
            logger.info(f"⚡ Executing system command: {action}")
            
            if action == 'shutdown':
                subprocess.run(['shutdown', '/s', '/t', '30'], check=False)
                return {"success": True, "message": "Shutting down in 30 seconds"}
            elif action == 'restart':
                subprocess.run(['shutdown', '/r', '/t', '30'], check=False)
                return {"success": True, "message": "Restarting in 30 seconds"}
            elif action == 'sleep':
                subprocess.run(['rundll32.exe', 'powrprof.dll,SetSuspendState', '0,1,0'], check=False)
                return {"success": True, "message": "Entering sleep mode"}
            elif action == 'lock':
                subprocess.run(['rundll32.exe', 'user32.dll,LockWorkStation'], check=False)
                return {"success": True, "message": "Screen locked"}
            else:
                return {"success": False, "error": f"Unknown command: {action}"}
        
        except Exception as e:
            logger.error(f"System command failed: {e}")
            return {"success": False, "error": str(e)}
