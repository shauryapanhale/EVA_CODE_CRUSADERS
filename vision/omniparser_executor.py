"""
OmniParser Executor - STRICT MODE (imports from util/utils.py)
"""
import logging
import sys
from pathlib import Path

logger = logging.getLogger("OmniParserExecutor")

class OmniParserExecutor:
    """OmniParser executor - MUST work or crash"""
    
    def __init__(self):
        """Initialize OmniParser - MUST succeed"""
        try:
            logger.info("Loading OmniParser (STRICT MODE)...")
            
            # Get EVA root directory
            eva_root = Path(__file__).parent.parent
            
            # Add BOTH util and utils to path to avoid conflicts
            util_folder = eva_root / "util"  # Contains utils.py with get_yolo_model
            
            # Verify util folder exists
            if not util_folder.exists():
                raise FileNotFoundError(f"CRITICAL: util/ folder not found at {util_folder}")
            
            # IMPORTANT: Insert at position 0 to prioritize over utils/ folder
            if str(util_folder) not in sys.path:
                sys.path.insert(0, str(util_folder))
            
            logger.info(f"Added to sys.path: {util_folder}")
            
            # Now import from util/utils.py (NOT from utils/ folder)
            # This works because we added util/ to sys.path
            logger.info("Importing get_yolo_model from util/utils.py...")
            
            # Import directly from the utils.py file inside util/
            import importlib.util
            utils_file = util_folder / "utils.py"
            
            if not utils_file.exists():
                raise FileNotFoundError(f"CRITICAL: utils.py not found at {utils_file}")
            
            spec = importlib.util.spec_from_file_location("omni_utils", utils_file)
            omni_utils = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(omni_utils)
            
            # Now we have the functions
            get_yolo_model = omni_utils.get_yolo_model
            check_ocr_box = omni_utils.check_ocr_box
            
            logger.info("✓ Successfully imported get_yolo_model, check_ocr_box")
            
            # Import other dependencies
            import torch
            from PIL import Image
            from paddleocr import PaddleOCR
            logger.info("✓ Imported torch, PIL, PaddleOCR")
            
            # Check for weights
            weights_path = eva_root / "weights"
            if not weights_path.exists():
                raise FileNotFoundError(f"CRITICAL: weights/ folder not found at {weights_path}\nPlease download OmniParser weights")
            
            # Load YOLO model
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            icon_model_path = weights_path / "icon_detect" / "best.pt"
            
            if not icon_model_path.exists():
                icon_model_path = weights_path / "icon_detect" / "model.pt"
            
            if not icon_model_path.exists():
                raise FileNotFoundError(f"CRITICAL: YOLO model not found. Checked:\n  - {weights_path / 'icon_detect' / 'best.pt'}\n  - {weights_path / 'icon_detect' / 'model.pt'}\nPlease download from OmniParser repository")
            
            logger.info(f"Loading YOLO model from {icon_model_path}...")
            self.som_model = get_yolo_model(model_path=str(icon_model_path))
            logger.info(f"✓ YOLO model loaded successfully on {device}")
            
                        # Load OCR
            logger.info("Loading PaddleOCR...")
            self.ocr_model = PaddleOCR(use_angle_cls=False, lang='en')
            logger.info("✓ PaddleOCR loaded successfully")

            logger.info("✓ PaddleOCR loaded successfully")
            
            self.device = device
            logger.info("✅ OmniParser fully initialized - READY")
            
        except Exception as e:
            logger.critical(f"❌ CRITICAL: OmniParser initialization FAILED")
            logger.critical(f"Error: {e}")
            raise RuntimeError(f"OmniParser MUST work. Error: {e}")
    
    def parse_screen(self, screenshot_path, user_command):
        """Parse screenshot - MUST work"""
        try:
            from PIL import Image
            import torch
            import numpy as np
            
            logger.info(f"📸 Parsing: {screenshot_path}")
            
            # Load image
            image = Image.open(screenshot_path)
            width, height = image.size
            logger.info(f"Image: {width}x{height}")
            
            elements = []
            element_id = 1
            
            # YOLO detection
            logger.info("Running YOLO detection...")
            results = self.som_model.predict(
                image,
                conf=0.15,
                device=self.device,
                verbose=False
            )
            
            clickable_count = 0
            for box in results[0].boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                center_x = int((x1 + x2) / 2)
                center_y = int((y1 + y2) / 2)
                conf = float(box.conf[0])
                
                elements.append({
                    'id': element_id,
                    'label': f'UI Element {element_id}',
                    'x': center_x,
                    'y': center_y,
                    'confidence': conf,
                    'type': 'clickable',
                    'bbox': [int(x1), int(y1), int(x2), int(y2)]
                })
                element_id += 1
                clickable_count += 1
            
            logger.info(f"✓ YOLO: {clickable_count} elements")
            
            # OCR detection
            logger.info("Running OCR...")
            img_array = np.array(image)
            ocr_result = self.ocr_model.ocr(img_array, cls=False)
            
            text_count = 0
            if ocr_result and ocr_result[0]:
                for line in ocr_result[0]:
                    bbox = line[0]
                    text = line[1][0]
                    conf = line[1][1]
                    
                    x_coords = [p[0] for p in bbox]
                    y_coords = [p[1] for p in bbox]
                    center_x = int(sum(x_coords) / len(x_coords))
                    center_y = int(sum(y_coords) / len(y_coords))
                    
                    if len(text.strip()) > 1:
                        elements.append({
                            'id': element_id,
                            'label': f'Text: {text}',
                            'x': center_x,
                            'y': center_y,
                            'confidence': conf,
                            'type': 'text',
                            'bbox': [int(min(x_coords)), int(min(y_coords)),
                                    int(max(x_coords)), int(max(y_coords))]
                        })
                        element_id += 1
                        text_count += 1
            
            logger.info(f"✓ OCR: {text_count} text elements")
            logger.info(f"✅ TOTAL: {len(elements)} elements detected")
            
            return {
                "elements": elements,
                "total": len(elements),
                "resolution": f"{width}x{height}"
            }
            
        except Exception as e:
            logger.critical(f"❌ CRITICAL: OmniParser parse failed: {e}")
            raise RuntimeError(f"OmniParser parse MUST work. Error: {e}")
