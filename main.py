from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import cv2
from datetime import datetime
import os
from ptz_commands import PTZCommands
import json
import time

# Initialize FastAPI app
app = FastAPI(title="Camera Control API")

# Read environment configuration
with open("environ.json", "r") as f:
    environ = json.load(f)
pw = environ.get("pw", "admin")

# Initialize camera URL
CAMERA_URL = f"rtsp://admin:{pw}@192.168.1.139:554/12"

# Initialize PTZ commands (will be set up in startup event)
ptz_control = None

class PanTiltRequest(BaseModel):
    pan: float
    tilt: float

@app.on_event("startup")
async def startup_event():
    global ptz_control
    try:
        # Initialize your PTZ control here
        from onvif import ONVIFCamera
        print("Connecting to camera...")
        
        # Get camera IP from RTSP URL
        from urllib.parse import urlparse
        camera_url = urlparse(CAMERA_URL)
        camera_ip = camera_url.hostname
        
        # Create ONVIFCamera instance (simpler initialization like in CameraGUI)
        # cam = ONVIFCamera(camera_ip, 80, 'admin', pw)
        wsdl_dir=os.path.join('C:\\', 'Users', 'Hugo', 'AppData', 'Roaming', 'Python', 'Lib', 'site-packages', 'wsdl')
        cam = ONVIFCamera('192.168.1.139', 8080, 'admin', pw, wsdl_dir='wsdl')
        print("Camera connection established")
        
        # Create media service object
        print("Creating media service...")
        media = cam.create_media_service()
        
        # Create ptz service object
        print("Creating PTZ service...")
        ptz = cam.create_ptz_service()

        # Get target profile
        print("Getting media profile...")
        media_profile = media.GetProfiles()[0]
        
        # Initialize PTZ control
        print("Initializing PTZ control...")
        ptz_control = PTZCommands(ptz, media_profile)
        print("PTZ control initialized successfully")

        # go origin + go home
        ptz_control.hard_origin(blocking=True)
        ptz_control.go_home()
        
    except Exception as e:
        print(f"Could not initialize ONVIF services: {e}")
        ptz = None
        media = None
        ptz_control = None

@app.get("/move")
@app.post("/move")
async def move_camera(pan: float = None, tilt: float = None, request: PanTiltRequest = None):
    if not ptz_control:
        raise HTTPException(status_code=503, detail="PTZ control not available")
    
    try:
        # Get values either from query params (GET) or request body (POST)
        pan_value = pan if pan is not None else (request.pan if request else None)
        tilt_value = tilt if tilt is not None else (request.tilt if request else None)
        
        if pan_value is None or tilt_value is None:
            raise HTTPException(status_code=400, detail="Pan and tilt values are required")
        
        # Calculate absolute position based on current position plus relative movement
        new_pan = ptz_control.est_pan_angle_deg + pan_value
        new_tilt = ptz_control.est_tilt_angle_deg + tilt_value
        
        # First stop any ongoing movement
        ptz_control.stop_ptz()
        time.sleep(0.5)  # Small delay to ensure stop is processed
        
        # Move to requested position using absolute positioning
        if abs(new_pan) <= 350 and abs(new_tilt) <= 90:  # Check if within limits
            ptz_control.abs_pantilt((new_pan, new_tilt))
            return {
                "message": f"Moving relative pan: {pan_value}, tilt: {tilt_value}",
                "target_position": {
                    "pan": new_pan,
                    "tilt": new_tilt
                },
                "current_position": {
                    "pan": ptz_control.est_pan_angle_deg,
                    "tilt": ptz_control.est_tilt_angle_deg
                }
            }
        else:
            raise HTTPException(status_code=400, detail="Pan/Tilt values out of range")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/capture", response_model=dict)
@app.post("/capture", response_model=dict)
@app.get("/capture/{suffix}", response_model=dict)
@app.post("/capture/{suffix}", response_model=dict)
async def take_picture(suffix: str = ""):
    try:
        # Initialize capture
        cap = cv2.VideoCapture(CAMERA_URL)
        if not cap.isOpened():
            raise HTTPException(status_code=503, detail="Could not connect to camera")
        
        # Read a frame
        ret, frame = cap.read()
        if not ret:
            raise HTTPException(status_code=500, detail="Could not capture image")
        
        # Create output directory if it doesn't exist
        os.makedirs("output/pictures", exist_ok=True)
        
        # Generate filename with timestamp and suffix
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"output/pictures/{timestamp}_{suffix}_api.jpg"
        
        # Save the image
        cv2.imwrite(filename, frame)
        
        # Release the capture
        cap.release()
        
        return {"message": "Picture captured", "filename": filename}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/origin", response_model=dict)
@app.post("/origin", response_model=dict)
async def move_to_origin():
    if not ptz_control:
        raise HTTPException(status_code=503, detail="PTZ control not available")
    
    try:
        ptz_control.hard_origin(blocking=True)
        return {
            "message": "Moved to hard origin position",
            "current_position": {
                "pan": ptz_control.est_pan_angle_deg,
                "tilt": ptz_control.est_tilt_angle_deg
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/home", response_model=dict)
async def move_to_home():
    if not ptz_control:
        raise HTTPException(status_code=503, detail="PTZ control not available")
    
    try:
        # Move to a predefined home position
        ptz_control.go_home()
        return {
            "message": "Moved to home position",
            "current_position": {
                "pan": ptz_control.est_pan_angle_deg,
                "tilt": ptz_control.est_tilt_angle_deg
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)