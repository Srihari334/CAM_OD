# CAM_OD - Obstacle Detection with Arduino Brake Control

A real-time obstacle detection system using YOLOv8 and MiDaS depth estimation with Arduino brake control.

## Features

- **YOLOv8 Object Detection**: Real-time object detection using YOLOv8 nano model
- **MiDaS Depth Estimation**: Monocular depth estimation for distance calculation
- **Arduino Integration**: Serial communication for brake control
- **Multi-threaded Frame Processing**: Optimized for smooth real-time performance
- **GPU Acceleration**: CUDA support for faster inference

## Hardware Requirements

- Webcam/USB Camera
- Arduino UNO R4 Minima or compatible
- Cytron Motor Driver (for brake control)
- PWM-capable motor/brake actuator

## Software Requirements

- Python 3.8+
- PyTorch with CUDA support (optional, CPU mode available)
- OpenCV
- Ultralytics YOLOv8
- Arduino CLI or Arduino IDE

## Installation

### Python Dependencies

```bash
pip install torch torchvision
pip install opencv-python
pip install ultralytics
pip install pyserial
pip install timm
pip install matplotlib numpy
```

### Arduino Setup

1. Install Arduino CLI or Arduino IDE
2. Connect Arduino UNO R4 Minima via USB
3. Upload `arduino.ino` to the board:

```bash
# Using Arduino CLI
arduino-cli compile -b arduino:renesas_uno:minima /path/to/sketch
arduino-cli upload -p /dev/ttyACM0 -b arduino:renesas_uno:minima /path/to/sketch
```

## Usage

### Linux/Mac (Default)

```bash
python3 TEST1.py
```

### Windows

```bash
python TEST2.py
```

### Command-line Options

- `--source`: Video source (default: '0' for webcam, or video file path)
- `--save-video`: Save output video to file
- `--depth-freq`: Process depth every N frames (default: 5)
- `--resolution`: Output resolution WxH (default: '640x360')

Example:
```bash
python3 TEST1.py --source 0 --save-video --depth-freq 5 --resolution 1280x720
```

### Keyboard Controls

- **q**: Quit the application
- **s**: Toggle depth visualization display

## Configuration

### Arduino Serial Port

Edit the `ARDUINO_PORT` variable in the script:
- **Linux/Mac**: `/dev/ttyACM0` or `/dev/ttyUSB0`
- **Windows**: `COM3`, `COM4`, etc.

### Danger Zone

Adjust `DANGER_ZONE_METERS` to set the braking distance:
```python
DANGER_ZONE_METERS = 1.5  # Apply brakes if object closer than 1.5 meters
```

### Depth Calibration

The depth estimation requires camera calibration. Adjust these values based on your setup:
```python
DEPTH_SCALE_FACTOR = 10.0  # Stretch/shrink calculated distance
DEPTH_OFFSET = 0.0  # Add/subtract fixed distance offset
```

## Files

- `TEST1.py` - Linux/Mac version with YOLOv8 + MiDaS + Arduino control
- `TEST2.py` - Windows version with adjusted serial port settings
- `arduino.ino` - Arduino firmware for brake control
- `yolov8n.pt` - YOLOv8 nano model weights (auto-downloaded on first run)

## Arduino Pinout

| Component | Pin | Type |
|-----------|-----|------|
| Motor Direction | 7 | Digital Output |
| Motor PWM | 9 | PWM Output |
| Status LED | 8 | Digital Output |
| Serial RX | 0 | Serial |
| Serial TX | 1 | Serial |

## Serial Commands

Commands sent from Python to Arduino:
- **'B'**: Apply brakes (set PWM to 255)
- **'R'**: Release brakes (set PWM to 0)
- **'P'**: Ping (check connection)

## Performance Notes

- YOLOv8 nano model for faster inference
- MiDaS small model for depth (smaller memory footprint)
- GPU acceleration recommended for real-time performance
- Tested on CUDA and CPU (slower but functional)

## Troubleshooting

### Arduino Connection Failed
- Check USB cable connection
- Verify serial port: `ls /dev/ttyACM*` (Linux/Mac) or Device Manager (Windows)
- Ensure Arduino firmware is uploaded correctly

### No Webcam Found
- Verify camera is connected: `ls /dev/video*` (Linux) or check Device Manager
- Try different camera indices: `--source 1`, `--source 2`

### Slow Performance
- Enable GPU acceleration if available
- Reduce resolution: `--resolution 480x360`
- Increase depth processing interval: `--depth-freq 10`

### Qt Platform Plugin Error
- Usually harmless; video display may not show but processing continues
- Set display environment variable if needed

## License

This project is provided as-is for educational and hobby use.

## Author

@aev (optimized version)

## References

- [YOLOv8 Documentation](https://docs.ultralytics.com/)
- [MiDaS Depth Estimation](https://github.com/isl-org/MiDaS)
- [Arduino Documentation](https://www.arduino.cc/)
