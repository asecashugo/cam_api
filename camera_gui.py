import threading
import os
import time
import cv2
from tkinter import Tk, Label, Button
from PIL import Image, ImageTk


class CameraGUI:
    def __init__(self, master, cap, plate_cascade, reader, extract_plate, show_plate_roi, dynamodb, onvif_camera=None):
        self.master = master
        self.cap = cap
        self.plate_cascade = plate_cascade
        self.reader = reader
        self.extract_plate = extract_plate
        self.show_plate_roi = show_plate_roi
        self.dynamodb = dynamodb
        self.onvif_camera = onvif_camera
        self.panel = Label(master)
        self.panel.pack()
        self.btn_left = Button(master, text="Pan Left", command=self.pan_left)
        self.btn_left.pack(side='left')
        self.btn_right = Button(master, text="Pan Right", command=self.pan_right)
        self.btn_right.pack(side='right')
        self.last_detection_time = 0
        self.plates = []
        self.plate_texts = []
        self.update_frame()

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            self.master.after(20, self.update_frame)
            return
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        current_time = time.time()
        if current_time - self.last_detection_time >= 1.0:
            self.plates = self.plate_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
            self.plate_texts = []
            for (x, y, w, h) in self.plates:
                roi = gray[y:y+h, x:x+w]
                roi = cv2.resize(roi, (0, 0), fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
                plate_text = self.reader.readtext(roi, detail=0, allowlist='BCDFGHJKLMNPQRSTVWXYZ0123456789')
                plate_text = ' '.join(plate_text).strip()
                valid_plate = self.extract_plate(plate_text)
                self.plate_texts.append(valid_plate)
                if valid_plate:
                    output_path = os.path.join('output', f'{valid_plate}.jpg')
                    cv2.imwrite(output_path, roi)
                    print(f"Saved detected plate image to {output_path}")
                    self.dynamodb.save_plate_to_db(valid_plate)
            self.last_detection_time = current_time
        for idx, (x, y, w, h) in enumerate(self.plates):
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            self.show_plate_roi(frame, x, y, w, h)
            if idx < len(self.plate_texts):
                plate_text = self.plate_texts[idx]
                if plate_text:
                    cv2.putText(frame, plate_text, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                    print(f"Detected Plate: {plate_text}")
        frame = cv2.resize(frame, (640, int(frame.shape[0] * 640 / frame.shape[1])))
        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(img)
        imgtk = ImageTk.PhotoImage(image=img)
        self.panel.imgtk = imgtk
        self.panel.config(image=imgtk)
        self.master.after(20, self.update_frame)

    def pan(self, direction):
        if not self.onvif_camera:
            print("ONVIF not available")
            return
        ptz = self.onvif_camera.create_ptz_service()
        media = self.onvif_camera.create_media_service()
        profile = media.GetProfiles()[0]
        req = ptz.create_type('ContinuousMove')
        req.ProfileToken = profile.token
        req.Velocity = {'PanTilt': {'x': 0.2 if direction == 'right' else -0.2, 'y': 0}}
        ptz.ContinuousMove(req)

    def pan_left(self):
        threading.Thread(target=self.pan, args=('left',), daemon=True).start()

    def pan_right(self):
        threading.Thread(target=self.pan, args=('right',), daemon=True).start()

def start_gui(cap, plate_cascade, reader, extract_plate, show_plate_roi, dynamodb, onvif_camera=None):
    root = Tk()
    root.title("License Plate Detection")
    CameraGUI(root, cap, plate_cascade, reader, extract_plate, show_plate_roi, dynamodb, onvif_camera)
    root.mainloop()
