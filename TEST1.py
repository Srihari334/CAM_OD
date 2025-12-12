#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Optimized Live obstacle detection with depth and Arduino brake control
using YOLOv8 + MiDaS.
High-performance version with GPU acceleration and optimizations.
@author: aev (optimized)
"""

import cv2
import torch
import time
import argparse
import numpy as np
import matplotlib.pyplot as plt
from ultralytics import YOLO
import os
from threading import Thread
import queue
import serial # Added for Arduino communication

# --- Constants for Brake Control ---
# IMPORTANT: Change '/dev/ttyACM0' to your Arduino's serial port (e.g., 'COM3' on Windows)
ARDUINO_PORT = '/dev/ttyACM0'
BAUD_RATE = 9600
# IMPORTANT: Calibrate this distance. Brakes will be applied if an object is closer than this value.
DANGER_ZONE_METERS = 5.0

# --- Initialize Serial Communication with Arduino ---
ser = None
try:
    ser = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
    time.sleep(2) # Wait for the connection to establish
    print(f"✅ Successfully connected to Arduino on {ARDUINO_PORT}")
except serial.SerialException as e:
    print(f"❌ Failed to connect to Arduino on {ARDUINO_PORT}. Error: {e}")
    print("Running in detection-only mode.")
    ser = None

# -------------- Argument Parser ------------------
parser = argparse.ArgumentParser()
# MODIFIED: Changed default source to '0' for the built-in laptop camera
parser.add_argument('--source', type=str, default='0',
                    help="Video file path, webcam index (0, 1...) or /dev/videoX")
parser.add_argument('--save-video', action='store_true', help="Save output video")
parser.add_argument('--depth-freq', type=int, default=5, help="Process depth every N frames")
parser.add_argument('--resolution', type=str, default='640x360', help="Resolution WxH")
args = parser.parse_args()

# Parse resolution
width, height = map(int, args.resolution.split('x'))

# ------------ Helper Functions -------------------
def is_valid_video_file(path):
    return os.path.isfile(path) and path.lower().endswith(('.mp4', '.avi', '.mov'))

def auto_select_camera(preferred='0', fallback_max_index=3):
    # Check preferred index first
    cap_check = cv2.VideoCapture(int(preferred))
    if cap_check.isOpened():
        print(f"✅ Using preferred camera index: {preferred}")
        cap_check.release()
        return int(preferred)

    print(f"⚠️ Preferred camera index '{preferred}' not found or failed to open. Trying fallback...")
    for i in range(fallback_max_index):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            cap.release()
            print(f"✅ Found fallback webcam at index: {i}")
            return i
    print("❌ No available webcam found.")
    return None

# ------------ Resolve Video Source ----------------
source_arg = args.source.strip()
source = None

if source_arg.isdigit():
    source = int(source_arg)
elif source_arg.startswith("/dev/video") and os.path.exists(source_arg):
    source = source_arg
elif is_valid_video_file(source_arg):
    source = source_arg
else:
    print(f"⚠️ Invalid or missing source '{source_arg}'. Attempting auto-select...")
    source = auto_select_camera()
    if source is None:
        exit()

# ------------ Initialize Video Capture ------------
cap = cv2.VideoCapture(source)
if not cap.isOpened():
    print(f"❌ Failed to open video source: {source}")
    exit()

# Optimize capture settings
cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
cap.set(cv2.CAP_PROP_FPS, 30)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer to prevent lag

print(f"📹 Using video source: {source} at {width}x{height}")

# ------------ Device Selection -------------------
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f"🖥️  Using device: {device}")

# ------------ MiDaS Depth Estimation (Optimized) --
model_type = "MiDaS_small"
print("🔄 Loading MiDaS model...")
midas = torch.hub.load("intel-isl/MiDaS", model_type)
midas.to(device).eval()

if device == 'cuda':
    # This line might cause issues on some setups, if so, comment it out.
    # midas = torch.jit.script(midas)
    pass


midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms")
transform = midas_transforms.small_transform

# ------------ YOLOv8 Model ------------------------
print("🔄 Loading YOLO model...")
model = YOLO("yolov8n.pt")
model.to(device)

model.overrides['verbose'] = False
model.overrides['save'] = False
model.overrides['save_txt'] = False
model.overrides['save_conf'] = False
model.overrides['save_crop'] = False

# ------------ Video Output Settings ---------------
out = None
if args.save_video:
    fps = 30
    out = cv2.VideoWriter('laptop_cam_output_depth.mp4',
                          cv2.VideoWriter_fourcc(*'mp4v'),
                          fps, (width, height))

# ------------ Optimized Picture-in-Picture ----------
def fast_picture_in_picture(main, overlay, scale=0.25, margin=10):
    h, w = main.shape[:2]
    oh, ow = overlay.shape[:2]
    new_h = int(h * scale)
    new_w = int(ow * new_h / oh)
    small_overlay = cv2.resize(overlay, (new_w, new_h))
    x_offset = w - new_w - margin
    y_offset = margin
    main[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = small_overlay
    return main

# ------------ Threaded Frame Reading ---------------
class FrameReader:
    def __init__(self, cap):
        self.cap = cap
        self.q = queue.Queue(maxsize=2)
        self.running = True

    def start(self):
        self.thread = Thread(target=self.update)
        self.thread.start()

    def update(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                self.running = False # Stop if camera disconnects
                break
            if not self.q.full():
                self.q.put(frame)
            else:
                self.q.get() # Discard oldest frame if queue is full
                self.q.put(frame)


    def read(self):
        return self.q.get()

    def stop(self):
        self.running = False
        if self.thread.is_alive():
            self.thread.join()

# ------------ Initialize Frame Reader -------------
frame_reader = FrameReader(cap)
frame_reader.start()

# ------------ Performance Tracking ----------------
frame_count = 0
start_time = time.time()
fps_counter = 0
current_fps = 0
depth_cache = None
depth_frame_counter = 0
plasma_colormap = plt.cm.plasma(np.linspace(0, 1, 256))[:, :3]

# --- Brake Control State ---
brake_applied = False

print("🚀 Starting optimized obstacle detection...")
print(f"📊 Depth processing every {args.depth_freq} frames")
print(f" braking distance set to < {DANGER_ZONE_METERS}m")
print("Press 'q' to quit, 's' to toggle depth display")

show_depth = True

try:
    while frame_reader.running:
        frame = frame_reader.read()
        if frame is None:
            continue

        frame_count += 1

        # ----- Object Detection (every frame) -----
        results = model.predict(frame, verbose=False, conf=0.5, device=device, half=True if device == 'cuda' else False)

        # ----- Depth Estimation (every N frames) -----
        if frame_count % args.depth_freq == 0:
            with torch.no_grad():
                # Smaller resize for faster processing
                depth_frame = cv2.resize(frame, (320, 240))
                input_batch = transform(depth_frame).to(device)

                with torch.cuda.amp.autocast() if device == 'cuda' else torch.no_grad():
                    prediction = midas(input_batch)
                    prediction = torch.nn.functional.interpolate(
                        prediction.unsqueeze(1),
                        size=(height, width),
                        mode='bilinear',
                        align_corners=False
                    ).squeeze()

                depth_map = prediction.cpu().numpy()
                depth_map = (depth_map - depth_map.min()) / (depth_map.max() - depth_map.min())
                depth_cache = depth_map

        # ----- Draw Detections & Check for Obstacles -----
        annotated_frame = frame.copy()
        obstacle_in_danger_zone = False

        for result in results:
            if result.boxes is None:
                continue

            boxes = result.boxes.xyxy.cpu().numpy()
            confidences = result.boxes.conf.cpu().numpy()
            classes = result.boxes.cls.cpu().numpy()

            for box, conf, cls in zip(boxes, confidences, classes):
                x1, y1, x2, y2 = map(int, box)

                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                class_name = result.names[int(cls)]

                distance_text = ""
                if depth_cache is not None:
                    center_x = (x1 + x2) // 2
                    center_y = (y1 + y2) // 2

                    h_margin = max(1, (y2 - y1) // 4)
                    w_margin = max(1, (x2 - x1) // 4)

                    depth_region = depth_cache[
                        max(0, center_y - h_margin):min(depth_cache.shape[0], center_y + h_margin),
                        max(0, center_x - w_margin):min(depth_cache.shape[1], center_x + w_margin)
                    ]

                    if depth_region.size > 0:
                        relative_depth = np.median(depth_region)
                        # This is an APPROXIMATION. You MUST calibrate this formula for your specific camera and setup.
                        distance = (1.0 - relative_depth) * 10
                        distance_text = f" | {distance:.1f}m"

                        # --- BRAKING LOGIC ---
                        if 0 < distance < DANGER_ZONE_METERS:
                            obstacle_in_danger_zone = True

                label = f"{class_name} {conf:.2f}{distance_text}"
                (label_width, label_height), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                cv2.rectangle(annotated_frame, (x1, y1 - label_height - 10), (x1 + label_width, y1), (0, 255, 0), -1)
                cv2.putText(annotated_frame, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

        # ----- Send Commands to Arduino -----
        if ser is not None:
            if obstacle_in_danger_zone and not brake_applied:
                ser.write(b'B') # Send 'B' to apply brake
                brake_applied = True
                print("BRAKE APPLIED!")
            elif not obstacle_in_danger_zone and brake_applied:
                ser.write(b'R') # Send 'R' to release brake
                brake_applied = False
                print("Brake Released.")

        # ----- Add Depth Overlay -----
        if show_depth and depth_cache is not None:
            depth_indices = (depth_cache * 255).astype(np.uint8)
            depth_colored = (plasma_colormap[depth_indices] * 255).astype(np.uint8)
            annotated_frame = fast_picture_in_picture(annotated_frame, depth_colored)

        # ----- FPS Calculation -----
        fps_counter += 1
        if (time.time() - start_time) > 1:
            current_fps = fps_counter / (time.time() - start_time)
            fps_counter = 0
            start_time = time.time()

        # ----- Display FPS & Brake Status -----
        cv2.putText(annotated_frame, f'FPS: {current_fps:.1f}', (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        brake_status_text = "BRAKE ON" if brake_applied else "BRAKE OFF"
        brake_color = (0, 0, 255) if brake_applied else (0, 255, 0)
        cv2.putText(annotated_frame, brake_status_text, (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, brake_color, 2)

        # ----- Show Frame -----
        cv2.imshow('Optimized Obstacle Detection', annotated_frame)

        # ----- Save Video -----
        if out is not None:
            out.write(annotated_frame)

        # ----- Handle Keys -----
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            show_depth = not show_depth
            print(f"Depth display: {'ON' if show_depth else 'OFF'}")

except KeyboardInterrupt:
    print("\n🛑 Interrupted by user")

finally:
    # ----- Cleanup -----
    print("🧹 Cleaning up...")
    if ser is not None:
        ser.write(b'R') # Ensure brake is released on exit
        ser.close()
    frame_reader.stop()
    cap.release()
    if out is not None:
        out.release()
    cv2.destroyAllWindows()
    print("✅ Cleanup complete")