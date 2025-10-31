# from ultralytics import YOLO
import os
import io
import base64
import time
from PIL import Image, ImageDraw, ImageFont
import json
import requests
from openai import AzureOpenAI
import sys
import cv2
import numpy as np
from matplotlib import pyplot as plt
import easyocr
from paddleocr import PaddleOCR
import torch
from typing import Tuple, List, Union
from torchvision.ops import box_convert
import re
from torchvision.transforms import ToPILImage
import supervision as sv
import torchvision.transforms as T
from util.box_annotator import BoxAnnotator

# Initialize OCR readers
reader = easyocr.Reader(['en'])
paddle_ocr = PaddleOCR(
    lang='en',
    use_angle_cls=False,
    rec_batch_num=1024
)



def get_caption_model_processor(model_name, model_name_or_path="Salesforce/blip2-opt-2.7b", device=None):
    """Load caption model and processor for BLIP-2 or Florence-2"""
    if not device:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    
    if model_name == "blip2":
        from transformers import Blip2Processor, Blip2ForConditionalGeneration
        processor = Blip2Processor.from_pretrained("Salesforce/blip2-opt-2.7b")
        if device == 'cpu':
            model = Blip2ForConditionalGeneration.from_pretrained(
                model_name_or_path, device_map=None, torch_dtype=torch.float32
            )
        else:
            model = Blip2ForConditionalGeneration.from_pretrained(
                model_name_or_path, device_map=None, torch_dtype=torch.float16
            ).to(device)
    elif model_name == "florence2":
        from transformers import AutoProcessor, AutoModelForCausalLM
        processor = AutoProcessor.from_pretrained("microsoft/Florence-2-base", trust_remote_code=True)
        if device == 'cpu':
            model = AutoModelForCausalLM.from_pretrained(
                model_name_or_path, torch_dtype=torch.float32, trust_remote_code=True
            )
        else:
            model = AutoModelForCausalLM.from_pretrained(
                model_name_or_path, torch_dtype=torch.float16, trust_remote_code=True
            ).to(device)
    
    return {'model': model.to(device), 'processor': processor}


def get_yolo_model(model_path):
    """Load YOLO model from ultralytics"""
    from ultralytics import YOLO
    model = YOLO(model_path)
    return model


@torch.inference_mode()
def get_parsed_content_icon(filtered_boxes, starting_idx, image_source, caption_model_processor, prompt=None, batch_size=64):
    """
    Extract icon descriptions using vision-language models.
    Updated batch_size default to 64 (optimized for memory usage).
    """
    to_pil = ToPILImage()
    
    if starting_idx:
        non_ocr_boxes = filtered_boxes[starting_idx:]
    else:
        non_ocr_boxes = filtered_boxes
    
    croped_pil_image = []
    for i, coord in enumerate(non_ocr_boxes):
        try:
            xmin, xmax = int(coord[0] * image_source.shape[1]), int(coord[2] * image_source.shape[1])
            ymin, ymax = int(coord[1] * image_source.shape[0]), int(coord[3] * image_source.shape[0])
            cropped_image = image_source[ymin:ymax, xmin:xmax, :]
            cropped_image = cv2.resize(cropped_image, (64, 64))
            croped_pil_image.append(to_pil(cropped_image))
        except:
            continue

    model, processor = caption_model_processor['model'], caption_model_processor['processor']
    
    if not prompt:
        if 'florence' in model.config.name_or_path:
            prompt = "<CAPTION>"
        else:
            prompt = "The image shows"
    
    generated_texts = []
    device = model.device
    
    for i in range(0, len(croped_pil_image), batch_size):
        batch = croped_pil_image[i:i+batch_size]
        
        if model.device.type == 'cuda':
            inputs = processor(images=batch, text=[prompt]*len(batch), return_tensors="pt", do_resize=False).to(device=device, dtype=torch.float16)
        else:
            inputs = processor(images=batch, text=[prompt]*len(batch), return_tensors="pt").to(device=device)
        
        if 'florence' in model.config.name_or_path:
            generated_ids = model.generate(
                input_ids=inputs["input_ids"],
                pixel_values=inputs["pixel_values"],
                max_new_tokens=20,
                num_beams=1,
                do_sample=False
            )
        else:
            generated_ids = model.generate(
                **inputs,
                max_length=100,
                num_beams=5,
                no_repeat_ngram_size=2,
                early_stopping=True,
                num_return_sequences=1
            )
        
        generated_text = processor.batch_decode(generated_ids, skip_special_tokens=True)
        generated_text = [gen.strip() for gen in generated_text]
        generated_texts.extend(generated_text)
    
    return generated_texts


def get_parsed_content_icon_phi3v(filtered_boxes, ocr_bbox, image_source, caption_model_processor):
    """Extract icon descriptions using Phi-3 Vision model"""
    to_pil = ToPILImage()
    
    if ocr_bbox:
        non_ocr_boxes = filtered_boxes[len(ocr_bbox):]
    else:
        non_ocr_boxes = filtered_boxes
    
    croped_pil_image = []
    for i, coord in enumerate(non_ocr_boxes):
        xmin, xmax = int(coord[0] * image_source.shape[1]), int(coord[2] * image_source.shape[1])
        ymin, ymax = int(coord[1] * image_source.shape[0]), int(coord[3] * image_source.shape[0])
        cropped_image = image_source[ymin:ymax, xmin:xmax, :]
        croped_pil_image.append(to_pil(cropped_image))

    model, processor = caption_model_processor['model'], caption_model_processor['processor']
    device = model.device
    messages = [{"role": "user", "content": "<|image_1|>\ndescribe the icon in one sentence"}]
    prompt = processor.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

    batch_size = 5
    generated_texts = []

    for i in range(0, len(croped_pil_image), batch_size):
        images = croped_pil_image[i:i+batch_size]
        image_inputs = [processor.image_processor(x, return_tensors="pt") for x in images]
        inputs = {'input_ids': [], 'attention_mask': [], 'pixel_values': [], 'image_sizes': []}
        texts = [prompt] * len(images)
        
        for i, txt in enumerate(texts):
            input = processor._convert_images_texts_to_inputs(image_inputs[i], txt, return_tensors="pt")
            inputs['input_ids'].append(input['input_ids'])
            inputs['attention_mask'].append(input['attention_mask'])
            inputs['pixel_values'].append(input['pixel_values'])
            inputs['image_sizes'].append(input['image_sizes'])
        
        max_len = max([x.shape[1] for x in inputs['input_ids']])
        for i, v in enumerate(inputs['input_ids']):
            inputs['input_ids'][i] = torch.cat([processor.tokenizer.pad_token_id * torch.ones(1, max_len - v.shape[1], dtype=torch.long), v], dim=1)
            inputs['attention_mask'][i] = torch.cat([torch.zeros(1, max_len - v.shape[1], dtype=torch.long), inputs['attention_mask'][i]], dim=1)
        
        inputs_cat = {k: torch.concatenate(v).to(device) for k, v in inputs.items()}

        generation_args = {
            "max_new_tokens": 25,
            "temperature": 0.01,
            "do_sample": False,
        }
        
        generate_ids = model.generate(**inputs_cat, eos_token_id=processor.tokenizer.eos_token_id, **generation_args)
        generate_ids = generate_ids[:, inputs_cat['input_ids'].shape[1]:]
        response = processor.batch_decode(generate_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)
        response = [res.strip('\n').strip() for res in response]
        generated_texts.extend(response)

    return generated_texts
def get_model(*args, **kwargs):
    raise NotImplementedError("get_model is not implemented yet")


def remove_overlap_new(boxes, iou_threshold, ocr_bbox=None):
    """
    Remove overlapping boxes with improved logic.
    Updated version from OmniParser-v2.
    
    Args:
        boxes: List of dicts with format [{'type': 'icon', 'bbox':[x,y,x,y], 'interactivity':True, 'content':None}, ...]
        iou_threshold: IoU threshold for overlap detection
        ocr_bbox: List of dicts with format [{'type': 'text', 'bbox':[x,y,x,y], 'interactivity':False, 'content':str}, ...]
    """
    assert ocr_bbox is None or isinstance(ocr_bbox, List)

    def box_area(box):
        return (box[2] - box[0]) * (box[3] - box[1])

    def intersection_area(box1, box2):
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        return max(0, x2 - x1) * max(0, y2 - y1)

    def IoU(box1, box2):
        intersection = intersection_area(box1, box2)
        union = box_area(box1) + box_area(box2) - intersection + 1e-6
        if box_area(box1) > 0 and box_area(box2) > 0:
            ratio1 = intersection / box_area(box1)
            ratio2 = intersection / box_area(box2)
        else:
            ratio1, ratio2 = 0, 0
        return max(intersection / union, ratio1, ratio2)

    def is_inside(box1, box2):
        intersection = intersection_area(box1, box2)
        ratio1 = intersection / box_area(box1)
        return ratio1 > 0.80

    filtered_boxes = []
    if ocr_bbox:
        filtered_boxes.extend(ocr_bbox)
    
    for i, box1_elem in enumerate(boxes):
        box1 = box1_elem['bbox']
        is_valid_box = True
        
        for j, box2_elem in enumerate(boxes):
            box2 = box2_elem['bbox']
            if i != j and IoU(box1, box2) > iou_threshold and box_area(box1) > box_area(box2):
                is_valid_box = False
                break
        
        if is_valid_box:
            if ocr_bbox:
                box_added = False
                ocr_labels = ''
                
                for box3_elem in ocr_bbox:
                    if not box_added:
                        box3 = box3_elem['bbox']
                        if is_inside(box3, box1):  # OCR inside icon
                            try:
                                ocr_labels += box3_elem['content'] + ' '
                                filtered_boxes.remove(box3_elem)
                            except:
                                continue
                        elif is_inside(box1, box3):  # Icon inside OCR
                            box_added = True
                            break
                
                if not box_added:
                    if ocr_labels:
                        filtered_boxes.append({
                            'type': 'icon',
                            'bbox': box1_elem['bbox'],
                            'interactivity': True,
                            'content': ocr_labels.strip(),
                        })
                    else:
                        filtered_boxes.append({
                            'type': 'icon',
                            'bbox': box1_elem['bbox'],
                            'interactivity': True,
                            'content': None,
                        })
            else:
                filtered_boxes.append(box1)
    
    return filtered_boxes


def annotate(image_source: np.ndarray, boxes: torch.Tensor, logits: torch.Tensor, phrases: List[str], 
             text_scale: float, text_padding=5, text_thickness=2, thickness=3) -> np.ndarray:
    """
    Annotate image with bounding boxes and labels.
    
    Args:
        image_source: Source image (np.ndarray)
        boxes: Bounding box coordinates in cxcywh format (torch.Tensor)
        logits: Confidence scores
        phrases: Labels for each box
        text_scale: Text size (0.8 for mobile/web, 0.3 for desktop)
    """
    h, w, _ = image_source.shape
    boxes = boxes * torch.Tensor([w, h, w, h])
    xyxy = box_convert(boxes=boxes, in_fmt="cxcywh", out_fmt="xyxy").numpy()
    xywh = box_convert(boxes=boxes, in_fmt="cxcywh", out_fmt="xywh").numpy()
    detections = sv.Detections(xyxy=xyxy)

    labels = [f"{phrase}" for phrase in range(boxes.shape[0])]

    box_annotator = BoxAnnotator(
        text_scale=text_scale,
        text_padding=text_padding,
        text_thickness=text_thickness,
        thickness=thickness
    )
    
    annotated_frame = image_source.copy()
    annotated_frame = box_annotator.annotate(
        scene=annotated_frame,
        detections=detections,
        labels=labels,
        image_size=(w, h)
    )

    label_coordinates = {f"{phrase}": v for phrase, v in zip(phrases, xywh)}
    return annotated_frame, label_coordinates


def predict_yolo(model, image, box_threshold, imgsz, scale_img, iou_threshold=0.7):
    """Run YOLO prediction with updated API"""
    if scale_img:
        result = model.predict(
            source=image,
            conf=box_threshold,
            imgsz=imgsz,
            iou=iou_threshold,
        )
    else:
        result = model.predict(
            source=image,
            conf=box_threshold,
            iou=iou_threshold,
        )
    
    boxes = result[0].boxes.xyxy
    conf = result[0].boxes.conf
    phrases = [str(i) for i in range(len(boxes))]

    return boxes, conf, phrases


def int_box_area(box, w, h):
    """Calculate box area in pixels"""
    x1, y1, x2, y2 = box
    int_box = [int(x1*w), int(y1*h), int(x2*w), int(y2*h)]
    area = (int_box[2] - int_box[0]) * (int_box[3] - int_box[1])
    return area


def get_som_labeled_img(
    image_source: Union[str, Image.Image],
    model=None,
    BOX_TRESHOLD=0.01,
    output_coord_in_ratio=False,
    ocr_bbox=None,
    text_scale=0.4,
    text_padding=5,
    draw_bbox_config=None,
    caption_model_processor=None,
    ocr_text=[],
    use_local_semantics=True,
    iou_threshold=0.9,
    prompt=None,
    scale_img=False,
    imgsz=None,
    batch_size=64
):
    """
    Main function to process image with YOLO + OCR and generate labeled output.
    Updated with latest OmniParser-v2 logic.
    """
    if isinstance(image_source, str):
        image_source = Image.open(image_source)
    
    image_source = image_source.convert("RGB")
    w, h = image_source.size
    
    if not imgsz:
        imgsz = (h, w)
    
    # Run YOLO detection
    xyxy, logits, phrases = predict_yolo(
        model=model,
        image=image_source,
        box_threshold=BOX_TRESHOLD,
        imgsz=imgsz,
        scale_img=scale_img,
        iou_threshold=0.1
    )
    
    xyxy = xyxy / torch.Tensor([w, h, w, h]).to(xyxy.device)
    image_source = np.asarray(image_source)
    phrases = [str(i) for i in range(len(phrases))]

    # Process OCR bboxes
    if ocr_bbox:
        ocr_bbox = torch.tensor(ocr_bbox) / torch.Tensor([w, h, w, h])
        ocr_bbox = ocr_bbox.tolist()
    else:
        print('No OCR bbox provided')
        ocr_bbox = None

    ocr_bbox_elem = [
        {'type': 'text', 'bbox': box, 'interactivity': False, 'content': txt}
        for box, txt in zip(ocr_bbox, ocr_text) if int_box_area(box, w, h) > 0
    ]
    
    xyxy_elem = [
        {'type': 'icon', 'bbox': box, 'interactivity': True, 'content': None}
        for box in xyxy.tolist() if int_box_area(box, w, h) > 0
    ]
    
    # Remove overlapping boxes
    filtered_boxes = remove_overlap_new(
        boxes=xyxy_elem,
        iou_threshold=iou_threshold,
        ocr_bbox=ocr_bbox_elem
    )
    
    # Sort boxes
    filtered_boxes_elem = sorted(filtered_boxes, key=lambda x: x['content'] is None)
    starting_idx = next((i for i, box in enumerate(filtered_boxes_elem) if box['content'] is None), -1)
    filtered_boxes = torch.tensor([box['bbox'] for box in filtered_boxes_elem])
    
    print(f'Total filtered boxes: {len(filtered_boxes)}, Starting index: {starting_idx}')

    # Get parsed icon semantics
    time1 = time.time()
    if use_local_semantics:
        caption_model = caption_model_processor['model']
        
        if 'phi3_v' in caption_model.config.model_type:
            parsed_content_icon = get_parsed_content_icon_phi3v(
                filtered_boxes, ocr_bbox, image_source, caption_model_processor
            )
        else:
            parsed_content_icon = get_parsed_content_icon(
                filtered_boxes, starting_idx, image_source,
                caption_model_processor, prompt=prompt, batch_size=batch_size
            )
        
        ocr_text = [f"Text Box ID {i}: {txt}" for i, txt in enumerate(ocr_text)]
        icon_start = len(ocr_text)
        
        # Fill None content with parsed icon descriptions
        for i, box in enumerate(filtered_boxes_elem):
            if box['content'] is None:
                box['content'] = parsed_content_icon.pop(0)
        
        parsed_content_icon_ls = [
            f"Icon Box ID {str(i+icon_start)}: {txt}"
            for i, txt in enumerate(parsed_content_icon)
        ]
        parsed_content_merged = ocr_text + parsed_content_icon_ls
    else:
        ocr_text = [f"Text Box ID {i}: {txt}" for i, txt in enumerate(ocr_text)]
        parsed_content_merged = ocr_text
    
    print(f'Time to get parsed content: {time.time()-time1:.2f}s')

    filtered_boxes = box_convert(boxes=filtered_boxes, in_fmt="xyxy", out_fmt="cxcywh")
    phrases = [i for i in range(len(filtered_boxes))]
    
    # Draw bounding boxes
    if draw_bbox_config:
        annotated_frame, label_coordinates = annotate(
            image_source=image_source,
            boxes=filtered_boxes,
            logits=logits,
            phrases=phrases,
            **draw_bbox_config
        )
    else:
        annotated_frame, label_coordinates = annotate(
            image_source=image_source,
            boxes=filtered_boxes,
            logits=logits,
            phrases=phrases,
            text_scale=text_scale,
            text_padding=text_padding
        )
    
    pil_img = Image.fromarray(annotated_frame)
    buffered = io.BytesIO()
    pil_img.save(buffered, format="PNG")
    encoded_image = base64.b64encode(buffered.getvalue()).decode('ascii')
    
    if output_coord_in_ratio:
        label_coordinates = {
            k: [v[0]/w, v[1]/h, v[2]/w, v[3]/h]
            for k, v in label_coordinates.items()
        }
        assert w == annotated_frame.shape[1] and h == annotated_frame.shape[0]

    return encoded_image, label_coordinates, filtered_boxes_elem


def get_xywh(input):
    """Convert polygon coordinates to xywh format"""
    x, y, w, h = input[0][0], input[0][1], input[2][0] - input[0][0], input[2][1] - input[0][1]
    return int(x), int(y), int(w), int(h)


def get_xyxy(input):
    """Convert polygon coordinates to xyxy format"""
    x, y, xp, yp = input[0][0], input[0][1], input[2][0], input[2][1]
    return int(x), int(y), int(xp), int(yp)


def check_ocr_box(
    image_source: Union[str, Image.Image],
    display_img=True,
    output_bb_format='xywh',
    goal_filtering=None,
    easyocr_args=None,
    use_paddleocr=False
):
    """
    Perform OCR on image using either EasyOCR or PaddleOCR.
    Updated with PaddleOCR 3.0 compatibility.
    """
    if isinstance(image_source, str):
        image_source = Image.open(image_source)
    
    if image_source.mode == 'RGBA':
        image_source = image_source.convert('RGB')
    
    image_np = np.array(image_source)
    w, h = image_source.size
    
    if use_paddleocr:
        if easyocr_args is None:
            text_threshold = 0.5
        else:
            text_threshold = easyocr_args.get('text_threshold', 0.5)
        
        result = paddle_ocr.ocr(image_np, cls=False)[0]
        coord = [item[0] for item in result if item[1][1] > text_threshold]
        text = [item[1][0] for item in result if item[1][1] > text_threshold]
    else:  # EasyOCR
        if easyocr_args is None:
            easyocr_args = {}
        
        result = reader.readtext(image_np, **easyocr_args)
        coord = [item[0] for item in result]
        text = [item[1] for item in result]
    
    if display_img:
        opencv_img = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
        bb = []
        for item in coord:
            x, y, a, b = get_xywh(item)
            bb.append((x, y, a, b))
            cv2.rectangle(opencv_img, (x, y), (x+a, y+b), (0, 255, 0), 2)
        plt.imshow(cv2.cvtColor(opencv_img, cv2.COLOR_BGR2RGB))
    else:
        if output_bb_format == 'xywh':
            bb = [get_xywh(item) for item in coord]
        elif output_bb_format == 'xyxy':
            bb = [get_xyxy(item) for item in coord]
    
    return (text, bb), goal_filtering
