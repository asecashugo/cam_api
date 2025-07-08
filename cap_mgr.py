import cv2

# read pw from environ.json
import json
with open("environ.json", "r") as f:
    environ = json.load(f)
# Use a default if not found 'admin'
pw = environ.get("pw", "admin")

url = f"rtsp://admin:{pw}@192.168.1.139:554/12"
cap = cv2.VideoCapture(url)

def get_cap(source:str):
    if source=='webcam':
        cap = cv2.VideoCapture(0)
    elif source=='rtsp':
        cap = cv2.VideoCapture(url)
    else:
        raise ValueError("Invalid source. Use 'webcam' or 'rtsp'.")
    return cap