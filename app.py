# run this object detection app by using command "streamlit run app.py" on terminal
import streamlit as st
import google.generativeai as palm
from io import BytesIO
from datetime import datetime

import os
import sys
import numpy as np
import pandas as pd
import torch
from pathlib import Path
from PIL import Image 

FILE = Path(__file__).resolve()
ROOT = FILE.parents[0]  # YOLOv5 root directory
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))  # add ROOT to PATH
ROOT = Path(os.path.relpath(ROOT, Path.cwd()))  # relative

from models.common import DetectMultiBackend
from utils.dataloaders import LoadImagesCV
from utils.general import (LOGGER, Profile, check_img_size, cv2,non_max_suppression, scale_coords, strip_optimizer)
from utils.plots import Annotator, colors
from utils.segment.general import process_mask, scale_masks
from utils.segment.plots import plot_masks
from utils.torch_utils import select_device, smart_inference_mode

@smart_inference_mode()
def run(
        weights=ROOT / "runs/detect/yolov7.pt",  # model.pt path(s)
        source=None,  # opencv image array
        data=ROOT / 'data/coco128.yaml',  # dataset.yaml path
        imgsz=(640, 640),  # inference size (height, width)
        conf_thres=0.25,  # confidence threshold # 0.25
        iou_thres=0.45,  # NMS IOU threshold
        max_det=1000,  # maximum detections per image
        device='',  # cuda device, i.e. 0 or 0,1,2,3 or cpu
        classes=None,  # filter by class: --class 0, or --class 0 2 3
        agnostic_nms=False,  # class-agnostic NMS
        augment=False,  # augmented inference
        update=False,  # update all models
        line_thickness=3,  # bounding box thickness (pixels)
        hide_labels=False,  # hide labels
        hide_conf=False,  # hide confidences
        half=False,  # use FP16 half-precision inference
        dnn=False,  # use OpenCV DNN for ONNX inference
):  

    # Load model
    device = select_device(device)
    model = DetectMultiBackend(weights, device=device, dnn=dnn, data=data, fp16=half)
    stride, names, pt = model.stride, model.names, model.pt
    imgsz = check_img_size(imgsz, s=stride)  # check image size

    # Dataloader
    dataset = LoadImagesCV(source, img_size=imgsz, stride=stride, auto=pt)
    bs = 1  # batch_size

    # Run inference
    model.warmup(imgsz=(1 if pt else bs, 3, *imgsz))  # warmup
    seen, windows, dt = 0, [], (Profile(), Profile(), Profile())
    for im, im0s, s in dataset:
        with dt[0]:
            im = torch.from_numpy(im).to(device)
            im = im.half() if model.fp16 else im.float()  # uint8 to fp16/32
            im /= 255  # 0 - 255 to 0.0 - 1.0
            if len(im.shape) == 3:
                im = im[None]  # expand for batch dim

        # Inference
        with dt[1]:
            pred = model(im, augment=augment, visualize=False)

        # NMS
        with dt[2]:
            pred = non_max_suppression(pred, conf_thres, iou_thres, classes, agnostic_nms, max_det=max_det, nm=32)

        # Process predictions
        for i, det in enumerate(pred):  # per image
            seen += 1
            im0, frame = im0s.copy(), getattr(dataset, 'frame', 0)

            #s += '%gx%g ' % im.shape[2:]  # print string

            annotator = Annotator(im0, line_width=line_thickness, example=str(names))
            if len(det):
                # masks = process_mask(proto[i], det[:, 6:], det[:, :4], im.shape[2:], upsample=True)  # HWC

                # Rescale boxes from img_size to im0 size
                det[:, :4] = scale_coords(im.shape[2:], det[:, :4], im0.shape).round()

                # Print results
                for c in det[:, 5].unique():
                    n = (det[:, 5] == c).sum()  # detections per class
                    s += f"- {n} {names[int(c)]}{'s' * (n > 1)}, "  # add to string

                # Write results
                for j, (*xyxy, conf, cls) in enumerate(reversed(det[:, :6])):
                    c = int(cls)  # integer class
                    label = None if hide_labels else (names[c] if hide_conf else f'{names[c]} {conf:.2f}')
                    annotator.box_label(xyxy, label, color=colors(c, True))
            im0 = annotator.result()

        # Print time (inference-only)
        LOGGER.info(f"{s}{'' if len(det) else '(no detections), '}{dt[1].dt * 1E3:.1f}ms")
        LOGGER.info(f"{s} yo im here ")

    # Print results
    t = tuple(x.t / seen * 1E3 for x in dt)  # speeds per image
    LOGGER.info(f'Speed: %.1fms pre-process, %.1fms inference, %.1fms NMS per image at shape {(1, 3, *imgsz)}' % t)
    if update:
        strip_optimizer(weights[0])  # update model (to fix SourceChangeWarning)
    return im0,s

def create_opencv_image_from_stringio(img_stream, cv2_img_flag=1):
    img_stream.seek(0)
    img_array = np.asarray(bytearray(img_stream.read()), dtype=np.uint8)
    return cv2.imdecode(img_array, cv2_img_flag)

def chat_with_palm(prompt):
    palm.configure(api_key='AIzaSyDYTiHCkpFbjNB28PKKgCkhi-kpchwv8GA') 
    response = palm.chat(messages=prompt)
    answer = response.last
    return answer

# Interface =========================================================

st.set_page_config(
  page_title="My YOLO App",
  page_icon="🚀"
)

st.title('AIVISION')
st.subheader('Your AI assistant for vision')
st.markdown("Take a pic and upload here to detect objects in the image. Then ask me anything about the objects in the image.")
img_files = st.file_uploader(label="Choose an image files",
                 type=['png', 'jpg', 'jpeg'],
                 accept_multiple_files=True,
                 )
for n, img_file_buffer in enumerate(img_files):
    if img_file_buffer is not None:
        open_cv_image = create_opencv_image_from_stringio(img_file_buffer)
        # predict
        im0, detected_labels = run(source=open_cv_image)        #, conf_thres=0.2
        #print the names of detected objects
        print(":::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::")
        st.subheader("Detected objects are: ")
        st.write(detected_labels[10:])
        if im0 is not None:
            # show image
            left_col, center_col,last_col = st.columns([1,6,1])
            with center_col:
                st.image(im0, channels="BGR", caption=f'Detection Results ({n+1}/{len(img_files)})')

    user_prompt = "Given list of objects, guess the place or describe the environment, also give a detail of each of those." + detected_labels[10:]
    response = chat_with_palm(user_prompt)
    print("AI Assistant:", response)
    st.write("AI Assistant:", response)

    question=st.text_input("Ask me anything: ")
    if question:
        user_input = question + "Given list of objects are: " + detected_labels[10:]
        response = chat_with_palm(user_input)
        print("AI Assistant:", response)
        st.write("AI Assistant:", response)