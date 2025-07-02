import cv2
import easyocr
import os
import dynamodb
import cap_mgr
import time
from roi_utils import show_plate_roi
from plate_format import extract_plate
from camera_gui import start_gui
from onvif import ONVIFCamera

def main():
    cascade_path = "haarcascade_russian_plate_number.xml"
    custom_config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    plate_cascade = cv2.CascadeClassifier(cascade_path)
    if plate_cascade.empty():
        print("Error loading cascade classifier! The file may be corrupted or incompatible with your OpenCV version.")
        exit()
    reader = easyocr.Reader(['en'])
    import json
    with open("environ.json", "r") as f:
        environ = json.load(f)
    pw = environ.get("pw", "admin")
    wsdl_dir=os.path.join('C:\\', 'Users', 'Hugo', 'AppData', 'Roaming', 'Python', 'Lib', 'site-packages', 'wsdl')
    onvif_camera = ONVIFCamera('192.168.1.149', 8080, 'admin', pw, wsdl_dir=wsdl_dir)
    print(f"ONVIF Camera initialized: {onvif_camera.devicemgmt.GetDeviceInformation()}")
    cap = cap_mgr.get_cap('rtsp')
    os.makedirs('output', exist_ok=True)
    start_gui(cap, plate_cascade, reader, extract_plate, show_plate_roi, dynamodb, onvif_camera)

if __name__ == "__main__":
    main()
