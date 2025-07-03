import time
import threading

MAX_TILT_TIME_S=5
MAX_TILT_ANGLE=0
MIN_TILT_ANGLE=-90

MAX_PAN_TIME_S=20
MAX_PAN_ANGLE=350
MIN_PAN_ANGLE=0

pan_speed_degps=(MAX_PAN_ANGLE - MIN_PAN_ANGLE) / MAX_PAN_TIME_S
tilt_speed_degps=(MAX_TILT_ANGLE - MIN_TILT_ANGLE) / MAX_TILT_TIME_S

ORIGIN_PAN_OFFSET_TO_NORTH_DEG=45

class PTZCommands:
    def __init__(self, ptz, profile, pt_speed=0.2):
        self.ptz = ptz
        self.profile = profile
        self.pt_speed = pt_speed
        self.est_pan_angle_deg = 0
        self.est_tilt_angle_deg = 0
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
    
    def hard_origin(self):
        print("Moving to hard origin position...")
        self.rel_pan(-(MAX_PAN_ANGLE-MIN_PAN_ANGLE))
        self.rel_tilt(-(MAX_TILT_ANGLE-MIN_TILT_ANGLE))
        self.est_pan_angle_deg = MIN_PAN_ANGLE+ORIGIN_PAN_OFFSET_TO_NORTH_DEG
        self.est_tilt_angle_deg = MIN_TILT_ANGLE

    def rel_pan(self,angle_deg):
        # print(f'    ({round(angle_deg)},0)') if angle_deg>0 else print(f'    ({round(-angle_deg)},0)')
        if angle_deg>0:
            print(f'    RIGHT {round(angle_deg)} deg')
        else:
            print(f'    LEFT {round(-angle_deg)} deg')
        if angle_deg > 0:
            self.pan_right()
        elif angle_deg < 0:
            self.pan_left()
        time.sleep(abs(angle_deg) / pan_speed_degps)
        self.est_pan_angle_deg += angle_deg
    
    def rel_tilt(self, angle_deg):
        # print(f'    (0,{round(angle_deg)})') if angle_deg>0 else print(f'    (0,{round(-angle_deg)})')
        if angle_deg > 0:
            print(f'    UP {round(angle_deg)} deg')
        else:
            print(f'    DOWN {round(-angle_deg)} deg')
        if angle_deg > 0:
            self.tilt_up()
        elif angle_deg < 0:
            self.tilt_down()
        time.sleep(abs(angle_deg) / tilt_speed_degps)
        self.est_tilt_angle_deg += angle_deg

    def absolute_pan(self, angle_deg):
        self.rel_pan(angle_deg - self.est_pan_angle_deg)
        self.est_pan_angle_deg = angle_deg
    
    def absolute_tilt(self, angle_deg):
        self.rel_tilt(angle_deg - self.est_tilt_angle_deg)
        self.est_tilt_angle_deg = angle_deg

    def go_home(self):
        
        HOME_PAN_ANGLE_DEG=225
        HOME_TILT_ANGLE_DEG=0
        self.go_origin()
        # if HOME_PAN_ANGLE_DEG > self.est_pan_angle_deg:
        #     self.pan_right()
        # else:
        #     self.pan_left()
        # # Wait for the pan to complete
        # time.sleep(abs(HOME_PAN_ANGLE_DEG - self.est_pan_angle_deg) / pan_speed_degps)
        # if HOME_TILT_ANGLE_DEG > self.est_tilt_angle_deg:
        #     self.tilt_up()
        # else:
        #     self.tilt_down()
        # # Wait for the tilt to complete
        # time.sleep((HOME_TILT_ANGLE_DEG - self.est_tilt_angle_deg) / tilt_speed_degps)
        # self.rel_pan(HOME_PAN_ANGLE_DEG - self.est_pan_angle_deg)
        # self.rel_tilt(HOME_TILT_ANGLE_DEG - self.est_tilt_angle_deg)
        self.absolute_pan(HOME_PAN_ANGLE_DEG)
        self.absolute_tilt(HOME_TILT_ANGLE_DEG)