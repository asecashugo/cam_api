import cv2
print(1)
import easyocr
print(2)
import os
import dynamodb
import urllib.request
import time
from roi_utils import show_plate_roi
from plate_format import extract_plate

cascade_path = "haarcascade_russian_plate_number.xml"
custom_config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'

plate_cascade = cv2.CascadeClassifier(cascade_path)
if plate_cascade.empty():
    print("Error loading cascade classifier! The file may be corrupted or incompatible with your OpenCV version.")
    exit()

cap = cv2.VideoCapture(0)
# cap.set(cv2.CAP_PROP_FRAME_WIDTH, 2560)
# cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1440)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_FPS, 30)
print("Width:", cap.get(cv2.CAP_PROP_FRAME_WIDTH))
print("Height:", cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
print("FPS:", cap.get(cv2.CAP_PROP_FPS))

reader = easyocr.Reader(['en'])

last_detection_time = 0
plates = []
plate_texts = []

# Ensure output directory exists
os.makedirs('output', exist_ok=True)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    current_time = time.time()
    if current_time - last_detection_time >= 1.0:
        plates = plate_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
        plate_texts = []
        for (x, y, w, h) in plates:
            roi = gray[y:y+h, x:x+w]
            # Apply CLAHE to optimize brightness/contrast
            # clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8,8))
            # roi_eq = clahe.apply(roi)
            # resize the ROI to x2
            roi = cv2.resize(roi, (0, 0), fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            # Apply adaptive thresholding for high-contrast black/white
            # roi_bw = cv2.adaptiveThreshold(roi_eq, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            # _, roi_bw = cv2.threshold(roi_eq, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            plate_text = reader.readtext(roi, detail=0, allowlist='BCDFGHJKLMNPQRSTVWXYZ0123456789')
            plate_text = ' '.join(plate_text).strip()
            valid_plate = extract_plate(plate_text)
            plate_texts.append(valid_plate)
            # Save the processed ROI if a valid plate is detected
            if valid_plate:
                output_path = os.path.join('output', f'{valid_plate}.jpg')
                cv2.imwrite(output_path, roi)
                print(f"Saved detected plate image to {output_path}")
                dynamodb.save_plate_to_db(valid_plate)
        last_detection_time = current_time

    for idx, (x, y, w, h) in enumerate(plates):
        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
        show_plate_roi(frame, x, y, w, h)
        if idx < len(plate_texts):
            plate_text = plate_texts[idx]
            if plate_text:
                cv2.putText(frame, plate_text, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                print(f"Detected Plate: {plate_text}")

    cv2.imshow("License Plate Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
