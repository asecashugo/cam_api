import time
import threading

MAX_TILT_TIME_S=6
MAX_TILT_ANGLE=0
MIN_TILT_ANGLE=-90

MAX_PAN_TIME_S=29
MAX_PAN_ANGLE=350
MIN_PAN_ANGLE=0

# change console colors:
PAN_COLOR='\033[94m'  # Blue
TILT_COLOR='\033[92m'  # Green
RESET_COLOR='\033[0m'  # Reset to default

pan_speed_degps=(MAX_PAN_ANGLE - MIN_PAN_ANGLE) / MAX_PAN_TIME_S
tilt_speed_degps=(MAX_TILT_ANGLE - MIN_TILT_ANGLE) / MAX_TILT_TIME_S

ORIGIN_PAN_OFFSET_TO_NORTH_DEG=0

class PTZCommands:
    def __init__(self, ptz, profile, pt_speed=0.2):
        self.ptz = ptz
        self.profile = profile
        self.pt_speed = pt_speed
        self.est_pan_angle_deg = MIN_PAN_ANGLE + ORIGIN_PAN_OFFSET_TO_NORTH_DEG
        self.est_tilt_angle_deg = MIN_TILT_ANGLE
        self.est_zoom_level = 0
    
    
    def stop_ptz(self):
        if not self.ptz or not self.profile:
            print("ONVIF PTZ service not available")
            return
        try:
            print(self.ptz.Stop({'ProfileToken': self.profile.token,
                           'PanTilt': True,
                           'Zoom': True}))
            print(f"    ({round(self.est_pan_angle_deg), round(self.est_tilt_angle_deg)})")
        except Exception as e:
            print(f"Could not stop PTZ: {e}")

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

    def pan_left(self):
        threading.Thread(target=self.pan_speed, args=('left',), daemon=True).start()

    def pan_right(self):
        threading.Thread(target=self.pan_speed, args=('right',), daemon=True).start()

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

    def tilt_up(self):
        threading.Thread(target=self.tilt_speed, args=('up',), daemon=True).start()

    def tilt_down(self):
        threading.Thread(target=self.tilt_speed, args=('down',), daemon=True).start()

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

    def go_origin(self):
        SAFETY_FACTOR=1.2
        SAFETY_PAN_ANGLE= -10
        SAFETY_TILT_ANGLE= 10
        print("Moving to origin position...")
        if not self.ptz or not self.profile:
            print("ONVIF PTZ service not available")
            return
        if self.est_pan_angle_deg > 0:
            self.rel_pan(min(SAFETY_PAN_ANGLE,-self.est_pan_angle_deg*SAFETY_FACTOR))
        if self.est_tilt_angle_deg > 0:
            self.rel_tilt(min(SAFETY_TILT_ANGLE,-self.est_tilt_angle_deg*SAFETY_FACTOR))

        print('Origin position reached.')
    
    def hard_origin(self, blocking=True):
        print("Moving to hard origin position...")
        self.rel_pan(-(MAX_PAN_ANGLE-MIN_PAN_ANGLE), blocking=blocking)
        self.rel_tilt(-(MAX_TILT_ANGLE-MIN_TILT_ANGLE), blocking=blocking)
        self.est_pan_angle_deg = MIN_PAN_ANGLE+ORIGIN_PAN_OFFSET_TO_NORTH_DEG
        self.est_tilt_angle_deg = MIN_TILT_ANGLE

    def rel_pan(self, angle_deg, blocking=True):
        def pan_thread():
            sleep_time = abs(angle_deg) / pan_speed_degps
            if angle_deg > 0:
                print(f'    {PAN_COLOR}RIGHT {round(angle_deg)}...{RESET_COLOR} ({round(sleep_time, 2)} s)')
                self.pan_right()
            elif angle_deg < 0:
                print(f'    {PAN_COLOR}LEFT {round(-angle_deg)}...{RESET_COLOR} ({round(sleep_time, 2)} s)')
                self.pan_left()
            time.sleep(sleep_time)
            self.est_pan_angle_deg += angle_deg
            self.stop_ptz()

        t = threading.Thread(target=pan_thread, daemon=True)
        t.start()
        if blocking:
            t.join()

    def rel_tilt(self, angle_deg, blocking=True):
        def tilt_thread():
            sleep_time = abs(angle_deg) / tilt_speed_degps
            if angle_deg > 0:
                print(f'    {TILT_COLOR}UP {round(angle_deg)}...{RESET_COLOR} ({round(sleep_time, 2)} s)')
                self.tilt_up()
            elif angle_deg < 0:
                print(f'    {TILT_COLOR}DOWN {round(-angle_deg)}...{RESET_COLOR} ({round(sleep_time, 2)} s)')
                self.tilt_down()
            time.sleep(sleep_time)
            self.est_tilt_angle_deg += angle_deg
            self.stop_ptz()

        t = threading.Thread(target=tilt_thread, daemon=True)
        t.start()
        if blocking:
            t.join()

    def print_position(self):
        print(f"🛑 ({PAN_COLOR}{round(self.est_pan_angle_deg)}{RESET_COLOR}, {TILT_COLOR}{round(self.est_tilt_angle_deg)}{RESET_COLOR})")

    def abs_pan(self, angle_deg, blocking=False):
        self.rel_pan(angle_deg - self.est_pan_angle_deg, blocking=blocking)
        angle_deg=min(max(angle_deg, MIN_PAN_ANGLE), MAX_PAN_ANGLE)
        self.est_pan_angle_deg = angle_deg
        self.print_position()
    
    def abs_tilt(self, angle_deg, blocking=False):
        self.rel_tilt(angle_deg - self.est_tilt_angle_deg, blocking=blocking)
        angle_deg=min(max(angle_deg, MIN_TILT_ANGLE), MAX_TILT_ANGLE)
        self.est_tilt_angle_deg = angle_deg
        self.print_position()

    def abs_pantilt(self, pan_tilt, blocking=True):
        pan, tilt = pan_tilt
        if pan < tilt:
            self.abs_pan(pan, blocking=blocking)
            self.abs_tilt(tilt, blocking=blocking)
        else:
            self.abs_tilt(tilt, blocking=blocking)
            self.abs_pan(pan, blocking=blocking)
    
    def go_home(self):
        
        HOME_PAN_ANGLE_DEG=180
        HOME_TILT_ANGLE_DEG=-30
        self.abs_pantilt((HOME_PAN_ANGLE_DEG, HOME_TILT_ANGLE_DEG))