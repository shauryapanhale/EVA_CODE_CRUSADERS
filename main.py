"""
EVA - Enhanced Virtual Assistant
Main entry point following methodology EXACTLY
"""
import time
from colorama import Fore, Style, init
from speech.wake_word_detector import WakeWordDetector
from speech.speech_to_text import SpeechToText
from speech.text_to_speech import TextToSpeech
from models.command_processor import CommandProcessor
from models.step_generator import StepGenerator  # MODEL 2
from vision.screen_analyzer import ScreenAnalyzer  # Gemini (summary + filtering)
from vision.screenshot_handler import ScreenshotHandler
from execution.executor_bridge import ExecutorBridge
from execution.action_router import ActionRouter
from execution.system_executor import SystemExecutor
from session.session_manager import SessionManager
from utils.logger import setup_logger
import config


init(autoreset=True)


class EVA:
    """Enhanced Virtual Assistant"""
    
    def __init__(self):
        """Initialize all EVA components"""
        self.logger = setup_logger('EVA')
        self.logger.info("🚀 Initializing EVA Assistant...")
        
        try:
            # Speech components
            self.wake_word = WakeWordDetector(wake_word=config.WAKE_WORD)
            self.stt = SpeechToText()
            self.tts = TextToSpeech()
            
            # NLP components (Model 1)
            self.command_processor = CommandProcessor()
            
            # Step generation (Model 2)
            self.step_generator = StepGenerator()
            
            # Vision components
            self.screen_analyzer = ScreenAnalyzer(config.GEMINI_API_KEY)  # Gemini
            self.screenshot_handler = ScreenshotHandler()
            
            # Execution components
            self.executor_bridge = ExecutorBridge()
            self.system_executor = SystemExecutor(self.executor_bridge)
            
            # Action router (connects everything)
            self.action_router = ActionRouter(
                self.system_executor,
                self.screenshot_handler
            )
            
            # Session manager
            self.session_manager = SessionManager(timeout_seconds=10)
            
            self.logger.info("✅ EVA initialized successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Initialization failed: {e}", exc_info=True)
            raise
    
    def run(self):
        """
        Main run loop following methodology
        Methodology: Wake word → Session start → Commands → Goodbye/Timeout
        """
        print("\n" + "=" * 60)
        print(f"{Fore.CYAN}  EVA - Enhanced Virtual Assistant{Style.RESET_ALL}")
        print("=" * 60)
        print(f"\n{Fore.YELLOW}Wake word:{Style.RESET_ALL} '{config.WAKE_WORD.upper()}' (Porcupine)")
        print(f"{Fore.YELLOW}Session timeout:{Style.RESET_ALL} 10 seconds inactivity")
        print(f"{Fore.YELLOW}End session:{Style.RESET_ALL} Say '{config.GOODBYE_PHRASE}'\n")
        
        try:
            # Start wake word detector (Porcupine)
            self.logger.info("Starting Porcupine wake word detection...")
            self.wake_word.start()
            
            while True:
                # IDLE STATE: Wait for wake word
                print(f"{Fore.MAGENTA}🎤 Listening for '{config.WAKE_WORD.upper()}'...{Style.RESET_ALL}")
                
                wake_detected = False
                while not wake_detected:
                    if self.wake_word.listen():
                        wake_detected = True
                        self.logger.info("✓ Wake word detected!")
                        print(f"\n{Fore.GREEN}✓ Wake word detected!{Style.RESET_ALL}")
        
                        # Greet user (Methodology: "audible acknowledgment")
                        self.tts.speak("Hey, how can I help you?")
        
                        # Start session
                        self.session_manager.start_session()
                        break  # ✅ FIX: Added break to exit wake word loop
    
                # ACTIVE STATE: Session loop
                while self.session_manager.is_active():
                    # Check timeout (Methodology: "10-second inactivity")
                    if self.session_manager.check_timeout():
                        print(f"\n{Fore.YELLOW}⏱️ Session timeout (10s inactivity){Style.RESET_ALL}")
                        self.tts.speak("Session timeout")
                        self.session_manager.end_session()
                        break
                    
                    # Listen for command
                    print(f"\n{Fore.CYAN}✓ Listening for command...{Style.RESET_ALL}")
                    command_text = self.stt.listen()
                    
                    if not command_text or command_text.strip() == "":
                        continue
                    
                    print(f"{Fore.WHITE}You: {command_text}{Style.RESET_ALL}")
                    self.logger.info(f"Command: '{command_text}'")
                    
                    # Check for goodbye (Methodology: "deactivated by 'Goodbye'")
                    if self.session_manager.should_end_session(command_text):
                        print(f"\n{Fore.GREEN}👋 Goodbye!{Style.RESET_ALL}")
                        self.tts.speak("Goodbye! Have a great day.")
                        self.session_manager.end_session()
                        break
                    
                    # Process and execute
                    print(f"{Fore.YELLOW}⚙️ Processing...{Style.RESET_ALL}")
                    result = self.execute_command(command_text)
                    
                    # Update session
                    self.session_manager.add_command(command_text, result)
                    
                    # Feedback (Methodology: "TTS confirmations")
                    if result.get('success'):
                        message = result.get('message', 'Done')
                        print(f"{Fore.GREEN}✅ {message}{Style.RESET_ALL}")
                        # self.tts.speak(message)  # ✅ OPTIONAL: TTS feedback
                    else:
                        error = result.get('error', 'Failed')
                        print(f"{Fore.RED}❌ {error}{Style.RESET_ALL}")
                        # self.tts.speak(f"Sorry, {error}")  # ✅ OPTIONAL: TTS error
                
                # Session ended, return to wake word listening
                print(f"\n{Fore.MAGENTA}📴 Session ended. Returning to idle...{Style.RESET_ALL}\n")
        
        except KeyboardInterrupt:
            print(f"\n\n{Fore.YELLOW}Shutting down EVA...{Style.RESET_ALL}")
            self.shutdown()
        
        except Exception as e:
            self.logger.error(f"Runtime error: {e}", exc_info=True)
            print(f"{Fore.RED}Fatal error: {e}{Style.RESET_ALL}")
            self.shutdown()
    
    def execute_command(self, command_text):
        """Process and execute command following methodology pipeline"""
        try:
            # Step 1: Command Understanding (Model 1 - Classifier)
            command_data = self.command_processor.process(command_text)
        
            category = command_data['classification']['category']
            self.logger.info(f"Category: {category}")
        
            # ✅ SYSTEM_ACTION: Skip Model 2, go directly to executor
            if category == 'SYSTEM_ACTION':
                self.logger.info("🔵 SYSTEM_ACTION bypass → Direct Windows API execution")
                result = self.action_router.execute(
                category=category,
                steps=[],  # ✅ Empty steps - not needed for system commands
                entities=command_data['entities'],
                raw_command=command_text,
                classification=command_data['classification']
                )
                return result
        
            # ✅ OTHER CATEGORIES: Use Model 2 to generate steps
            steps = self.step_generator.generate(command_data)
        
            result = self.action_router.execute(
            category=category,
            steps=steps,
            entities=command_data['entities'],
            raw_command=command_text,
            classification=command_data['classification']
            )
        
            return result
        
        except Exception as e:
            self.logger.error(f"Command execution failed: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    
    def shutdown(self):
        """Clean shutdown"""
        try:
            self.wake_word.stop()
            if self.session_manager.is_active():
                self.session_manager.end_session()
            self.logger.info("EVA shutdown complete")
        except Exception as e:
            self.logger.error(f"Shutdown error: {e}")


if __name__ == "__main__":
    eva = EVA()
    eva.run()
