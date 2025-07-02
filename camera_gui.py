import threading
import os
import time
import cv2
from tkinter import Tk, Label, Button
from PIL import Image, ImageTk
from tkinter import Frame


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
        self.ptz = None
        self.media = None
        self.profile = None
        if self.onvif_camera:
            try:
                self.ptz = self.onvif_camera.create_ptz_service()
                self.media = self.onvif_camera.create_media_service()
                self.profile = self.media.GetProfiles()[0]
            except Exception as e:
                print(f"Could not initialize ONVIF services: {e}")
                self.ptz = None
                self.media = None
                self.profile = None
        self.panel = Label(master)
        self.panel.pack()
        # Crosshair layout for PTZ controls with Stop on release
        from tkinter import Frame
        control_frame = Frame(master)
        control_frame.pack(pady=10)
        self.btn_up = Button(control_frame, text="UP", width=8)
        self.btn_up.grid(row=0, column=1, padx=5, pady=2)
        self.btn_up.bind('<ButtonPress>', lambda e: self.tilt_up())
        self.btn_up.bind('<ButtonRelease>', lambda e: self.stop_ptz())
        self.btn_left = Button(control_frame, text="LEFT", width=8)
        self.btn_left.grid(row=1, column=0, padx=5, pady=2)
        self.btn_left.bind('<ButtonPress>', lambda e: self.pan_left())
        self.btn_left.bind('<ButtonRelease>', lambda e: self.stop_ptz())
        self.btn_stop = Button(control_frame, text="STOP", width=8, command=self.stop_ptz, bg='red', fg='white', font=('Arial', 12, 'bold'))
        self.btn_stop.grid(row=1, column=1, padx=5, pady=2)
        self.btn_right = Button(control_frame, text="RIGHT", width=8)
        self.btn_right.grid(row=1, column=2, padx=5, pady=2)
        self.btn_right.bind('<ButtonPress>', lambda e: self.pan_right())
        self.btn_right.bind('<ButtonRelease>', lambda e: self.stop_ptz())
        self.btn_down = Button(control_frame, text="DOWN", width=8)
        self.btn_down.grid(row=2, column=1, padx=5, pady=2)
        self.btn_down.bind('<ButtonPress>', lambda e: self.tilt_down())
        self.btn_down.bind('<ButtonRelease>', lambda e: self.stop_ptz())
        self.btn_zoom_in = Button(control_frame, text="ZOOM +", width=8)
        self.btn_zoom_in.grid(row=0, column=2, padx=5, pady=2)
        self.btn_zoom_in.bind('<ButtonPress>', lambda e: self.zoom_in())
        self.btn_zoom_in.bind('<ButtonRelease>', lambda e: self.stop_ptz())
        self.btn_zoom_out = Button(control_frame, text="ZOOM -", width=8)
        self.btn_zoom_out.grid(row=2, column=2, padx=5, pady=2)
        self.btn_zoom_out.bind('<ButtonPress>', lambda e: self.zoom_out())
        self.btn_zoom_out.bind('<ButtonRelease>', lambda e: self.stop_ptz())
        # Add buttons to set PanTilt speed
        self.pt_speed = 0.2  # default
        btn_set_speed_005 = Button(master, text="Set PanTilt Speed 0.05", command=lambda: self.set_pt_speed(0.05))
        btn_set_speed_005.pack(side='left')
        btn_set_speed_02 = Button(master, text="Set PanTilt Speed 0.2", command=lambda: self.set_pt_speed(0.2))
        btn_set_speed_02.pack(side='left')
        btn_set_speed_1 = Button(master, text="Set PanTilt Speed 1", command=lambda: self.set_pt_speed(1.0))
        btn_set_speed_1.pack(side='left')
        # Add resolution selection buttons
        self.resolutions = [640, 800, 1024, 1280, 1920, 2560, 3840]
        self.current_resolution = 640
        res_frame = Frame(master)
        res_frame.pack(pady=5)
        Label(res_frame, text="Resolution:").pack(side='left')
        for res in self.resolutions:
            btn = Button(res_frame, text=str(res), command=lambda r=res: self.set_resolution(r))
            btn.pack(side='left')
        # Add button to take a picture
        btn_picture = Button(master, text="Take Picture", command=self.take_picture, bg='blue', fg='white', font=('Arial', 12, 'bold'))
        btn_picture.pack(pady=5)
        # Add stopmotion buttons
        self.stopmotion_running = False
        self.stopmotion_folder = None
        btn_start_stopmotion = Button(master, text="Start Stopmotion", command=self.start_stopmotion, bg='green', fg='white', font=('Arial', 12, 'bold'))
        btn_start_stopmotion.pack(pady=2)
        btn_stop_stopmotion = Button(master, text="Stop Stopmotion", command=self.stop_stopmotion, bg='orange', fg='black', font=('Arial', 12, 'bold'))
        btn_stop_stopmotion.pack(pady=2)
        self.last_detection_time = 0
        self.plates = []
        self.plate_texts = []
        self.update_frame()
        self.Get_Status()

    def set_resolution(self, width):
        self.current_resolution = width
        print(f"Resolution set to width: {width}")

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
        # Use selected resolution for display
        width = self.current_resolution
        frame = cv2.resize(frame, (width, int(frame.shape[0] * width / frame.shape[1])))
        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(img)
        imgtk = ImageTk.PhotoImage(image=img)
        self.panel.imgtk = imgtk
        self.panel.config(image=imgtk)
        self.master.after(20, self.update_frame)

    def pan(self, direction):
        if not self.ptz or not self.profile:
            print("ONVIF PTZ service not available")
            return
        req = self.ptz.create_type('ContinuousMove')
        req.ProfileToken = self.profile.token
        req.Velocity = {'PanTilt': {'x': 0.2 if direction == 'right' else -0.2, 'y': 0}}
        self.ptz.ContinuousMove(req)

    def pan_left(self):
        threading.Thread(target=self.pan_speed, args=('left',), daemon=True).start()

    def pan_right(self):
        threading.Thread(target=self.pan_speed, args=('right',), daemon=True).start()

    def set_pt_speed(self, speed):
        self.pt_speed = speed
        print(f"PanTilt speed set to {speed}")

    def pan_speed(self, direction, speed=None):
        if not self.ptz or not self.profile:
            print("ONVIF PTZ service not available")
            return
        if speed is None:
            speed = self.pt_speed
        req = self.ptz.create_type('ContinuousMove')
        req.ProfileToken = self.profile.token
        req.Velocity = {'PanTilt': {'x': speed if direction == 'right' else -speed, 'y': 0}}
        self.ptz.ContinuousMove(req)

    def stop_ptz(self):
        if not self.ptz or not self.profile:
            print("ONVIF PTZ service not available")
            return
        try:
            print(self.ptz.Stop({'ProfileToken': self.profile.token,
                           'PanTilt': True,
                           'Zoom': True}))
            print("PTZ movement stopped.")
        except Exception as e:
            print(f"Could not stop PTZ: {e}")

    def get_pan_position(self):
        if not self.ptz or not self.profile:
            return None
        try:
            status = self.ptz.GetStatus({'ProfileToken': self.profile.token})
            return status.Position.PanTilt.x if hasattr(status.Position.PanTilt, 'x') else None
        except Exception as e:
            print(f"Could not get pan position: {e}")
            return None

    def get_absolute_position(self):
        if not self.ptz or not self.profile:
            return None
        try:
            status = self.ptz.GetStatus({'ProfileToken': self.profile.token})
            pan = status.Position.PanTilt.x if hasattr(status.Position.PanTilt, 'x') else 0.0
            tilt = status.Position.PanTilt.y if hasattr(status.Position.PanTilt, 'y') else 0.0
            zoom = status.Position.Zoom.x if hasattr(status.Position.Zoom, 'x') else 0.0
            return pan, tilt, zoom
        except Exception as e:
            print(f"Could not get absolute position: {e}")
            return None

    def Get_Status(self):
        # Get range of pan and tilt
        global XMAX, XMIN, YMAX, YMIN, XNOW, YNOW, Velocity, Zoom
        try:
            ptz_configuration_options = self.ptz.GetConfigurationOptions({'ConfigurationToken': self.profile.PTZConfiguration.token})
            if not ptz_configuration_options or not ptz_configuration_options.Spaces:
                print("PTZ configuration options not available")
                return
            XMAX = ptz_configuration_options.Spaces.AbsolutePanTiltPositionSpace[0].XRange.Max
            XMIN = ptz_configuration_options.Spaces.AbsolutePanTiltPositionSpace[0].XRange.Min
            YMAX = ptz_configuration_options.Spaces.AbsolutePanTiltPositionSpace[0].YRange.Max
            YMIN = ptz_configuration_options.Spaces.AbsolutePanTiltPositionSpace[0].YRange.Min
            status = self.ptz.GetStatus({'ProfileToken': self.profile.token})
            XNOW = status.Position.PanTilt.x
            YNOW = status.Position.PanTilt.y
            Velocity = ptz_configuration_options.Spaces.PanTiltSpeedSpace[0].XRange.Max
            Zoom = status.Position.Zoom.x if hasattr(status.Position, 'Zoom') and hasattr(status.Position.Zoom, 'x') else 0.0
            print(f"PTZ Configuration - X Range: [{XMIN}, {XMAX}], Y Range: [{YMIN}, {YMAX}], "
                  f"Current Position - X: {XNOW}, Y: {YNOW}, Velocity: {Velocity}, Zoom: {Zoom}")
        except Exception as e:
            print(f"Could not get PTZ status/configuration: {e}")


    def get_ptz_configuration_options(self):
        options= self.ptz.GetConfigurationOptions({'ConfigurationToken': self.profile.PTZConfiguration.token})
        # print(f"PTZ Configuration Options: {options}")
        return options
    
    def set_DefaultPTZSpeed(self,PanTilt=None,Zoom=None):
        if Zoom is None or PanTilt is None:
            # get configuration options
            ptz_configuration_options = self.get_ptz_configuration_options()
            if not ptz_configuration_options or not ptz_configuration_options.Spaces:
                print("PTZ configuration options not available")
                return
            PanTilt = ptz_configuration_options.Spaces.PanTiltSpeedSpace[0].XRange.Max
            if not PanTilt:
                print("PanTilt speed not available in configuration options")
                return
            Zoom = ptz_configuration_options.Spaces.ZoomSpeedSpace[0].XRange.Max
            if not self.ptz or not self.profile:
                print("ONVIF PTZ service not available")
                return
        self.ptz.SetConfiguration({
            'PTZConfiguration': {
                'Name': self.profile.PTZConfiguration.Name,
                'token': self.profile.PTZConfiguration.token,
                'UseCount':1,
                'NodeToken': self.profile.PTZConfiguration.NodeToken,
                'DefaultPTZSpeed': {
                    'PanTilt': {'x': PanTilt, 'y': PanTilt},
                    'Zoom': {'x': Zoom}
                    }
                },
            'ForcePersistence': False
        })

    def tilt_up(self):
        threading.Thread(target=self.tilt_speed, args=('up',), daemon=True).start()

    def tilt_down(self):
        threading.Thread(target=self.tilt_speed, args=('down',), daemon=True).start()

    def tilt_speed(self, direction, speed=None):
        if not self.ptz or not self.profile:
            print("ONVIF PTZ service not available")
            return
        if speed is None:
            speed = self.pt_speed
        req = self.ptz.create_type('ContinuousMove')
        req.ProfileToken = self.profile.token
        req.Velocity = {'PanTilt': {'x': 0, 'y': speed if direction == 'up' else -speed}}
        self.ptz.ContinuousMove(req)

    def zoom_in(self):
        threading.Thread(target=self.zoom_speed, args=(1,), daemon=True).start()

    def zoom_out(self):
        threading.Thread(target=self.zoom_speed, args=(-1,), daemon=True).start()

    def zoom_speed(self, direction):
        if not self.ptz or not self.profile:
            print("ONVIF PTZ service not available")
            return
        speed = self.pt_speed
        req = self.ptz.create_type('ContinuousMove')
        req.ProfileToken = self.profile.token
        req.Velocity = {'Zoom': {'x': speed * direction}}
        self.ptz.ContinuousMove(req)

    def take_picture(self):
        ret, frame = self.cap.read()
        if not ret:
            print("Failed to capture image from camera.")
            return
        # Save at 3840x2160 regardless of GUI stream resolution
        target_width, target_height = 3840, 2160
        frame_highres = cv2.resize(frame, (target_width, target_height), interpolation=cv2.INTER_CUBIC)
        from datetime import datetime
        os.makedirs('output/pictures', exist_ok=True)
        filename = datetime.now().strftime('output/pictures/%Y%m%d_%H%M%S.jpg')
        cv2.imwrite(filename, frame_highres)
        print(f"Picture saved to {filename} at 3840x2160")

    def start_stopmotion(self):
        if self.stopmotion_running:
            print("Stopmotion already running.")
            return
        from datetime import datetime
        self.stopmotion_folder = datetime.now().strftime('output/stopmotion/%Y%m%d_%H%M%S')
        os.makedirs(self.stopmotion_folder, exist_ok=True)
        self.stopmotion_running = True
        print(f"Stopmotion started. Saving to {self.stopmotion_folder}")
        self._stopmotion_loop()

    def _stopmotion_loop(self):
        if not self.stopmotion_running:
            return
        ret, frame = self.cap.read()
        if ret:
            from datetime import datetime
            filename = datetime.now().strftime(f'{self.stopmotion_folder}/%Y%m%d_%H%M%S.jpg')
            # Save at 3840x2160
            frame_highres = cv2.resize(frame, (3840, 2160), interpolation=cv2.INTER_CUBIC)
            cv2.imwrite(filename, frame_highres)
            print(f"Stopmotion frame saved to {filename}")
        self.master.after(3000, self._stopmotion_loop)

    def stop_stopmotion(self):
        if self.stopmotion_running:
            self.stopmotion_running = False
            print("Stopmotion stopped.")
        else:
            print("Stopmotion is not running.")


def start_gui(cap, plate_cascade, reader, extract_plate, show_plate_roi, dynamodb, onvif_camera=None):
    root = Tk()
    root.title("License Plate Detection")
    CameraGUI(root, cap, plate_cascade, reader, extract_plate, show_plate_roi, dynamodb, onvif_camera)
    root.mainloop()

