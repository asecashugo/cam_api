from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import cv2
from datetime import datetime
import os
from ptz_commands import PTZCommands
import json
import time
import subprocess

# Initialize FastAPI app
app = FastAPI(title="Camera Control API")

# Read environment configuration
with open("environ.json", "r") as f:
    environ = json.load(f)
pw = environ.get("pw", "admin")

# Initialize camera URL
CAMERA_IP = '192.168.1.139'
CAMERA_URL = f"rtsp://admin:{pw}@{CAMERA_IP}:554/12"

# Initialize PTZ commands (will be set up in startup event)
ptz_control = None

class PTZRequest(BaseModel):
    pan: float
    tilt: float
    zoom: float | None = None  # Optional zoom parameter

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
    
    except:
        print(f"Failed to connect to camera usinf ONVIF. Pinging {CAMERA_IP}...")
        # ping CAMERA_URL to check if it's reachable, with timeout
        ping=subprocess.run(["ping", "-n", "1", "-w", "2000", CAMERA_IP], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if ping.returncode != 0:
            raise HTTPException(status_code=503, detail="Camera is not reachable")
        raise HTTPException(status_code=500, detail="Failed to connect to camera, although it is reachable")
    
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

@app.get("/move")
@app.post("/move")
async def move_camera(pan: float = None, tilt: float = None, zoom: float = None, request: PTZRequest = None):
    if not ptz_control:
        raise HTTPException(status_code=503, detail="PTZ control not available")
    
    try:
        # Get values either from query params (GET) or request body (POST)
        pan_value = pan if pan is not None else (request.pan if request else None)
        tilt_value = tilt if tilt is not None else (request.tilt if request else None)
        zoom_value = zoom if zoom is not None else (request.zoom if request else None)
        
        if pan_value is None and tilt_value is None and zoom_value is None:
            raise HTTPException(status_code=400, detail="At least one of pan, tilt, or zoom must be provided")
        
        # Calculate absolute position based on current position plus relative movement
        new_pan = ptz_control.est_pan_angle_deg + pan_value if pan_value is not None else ptz_control.est_pan_angle_deg
        new_tilt = ptz_control.est_tilt_angle_deg + tilt_value if tilt_value is not None else ptz_control.est_tilt_angle_deg
        new_zoom = ptz_control.est_zoom_level + zoom_value if zoom_value is not None else ptz_control.est_zoom_level
        
        # First stop any ongoing movement
        ptz_control.stop_ptz()
        time.sleep(0.5)  # Small delay to ensure stop is processed
        
        # Move to requested position using absolute positioning
        if (abs(new_pan) <= 350 and abs(new_tilt) <= 90 and 
            (new_zoom is None or (0 <= new_zoom <= 1))):  # Check if within limits
            
            # Then move zoom if specified
            if zoom_value is not None:
                ptz_control.abs_zoom(new_zoom)

            # Move pan/tilt first if specified
            if pan or tilt:
                ptz_control.abs_pantilt((new_pan, new_tilt))
            
            
            # Build message with only the movements that were requested
            movements = []
            if pan_value is not None:
                movements.append(f"pan: {pan_value}")
            if tilt_value is not None:
                movements.append(f"tilt: {tilt_value}")
            if zoom_value is not None:
                movements.append(f"zoom: {zoom_value}")
            
            return {
                "message": f"Moving relative {', '.join(movements)}",
                "target_position": {
                    "pan": new_pan,
                    "tilt": new_tilt,
                    "zoom": new_zoom
                },
                "current_position": {
                    "pan": ptz_control.est_pan_angle_deg,
                    "tilt": ptz_control.est_tilt_angle_deg,
                    "zoom": ptz_control.est_zoom_level
                }
            }
        else:
            raise HTTPException(status_code=400, detail=f"Pan/Tilt values out of range: {new_pan}, {new_tilt}. Zoom must be between 0 and 1 if specified: {new_zoom}")
            
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
                "tilt": ptz_control.est_tilt_angle_deg,
                "zoom": ptz_control.est_zoom_level
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
    
# Load preset locations
with open("locations.json", "r") as f:
    preset_locations = json.load(f)

@app.get("/goto/{location}", response_model=dict)
async def move_to_preset(location: str):
    if not ptz_control:
        raise HTTPException(status_code=503, detail="PTZ control not available")
    
    try:
        # Find the location in presets
        location = location.lower()  # case-insensitive matching
        if location not in preset_locations:
            available_locations = list(preset_locations.keys())
            raise HTTPException(
                status_code=404, 
                detail=f"Location '{location}' not found. Available locations: {available_locations}"
            )
        
        # Get the preset coordinates
        preset = preset_locations[location]
        
        # Move to the preset position
        ptz_control.abs_zoom(preset["zoom"])
        ptz_control.abs_pantilt((preset["pan"], preset["tilt"]))
        
        return {
            "message": f"Moved to preset location: {location}",
            "preset": preset,
            "current_position": {
                "pan": ptz_control.est_pan_angle_deg,
                "tilt": ptz_control.est_tilt_angle_deg,
                "zoom": ptz_control.est_zoom_level
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/savelocation/{name}", response_model=dict)
@app.get("/savelocation/{name}", response_model=dict)
async def save_current_position(name: str):
    if not ptz_control:
        raise HTTPException(status_code=503, detail="PTZ control not available")
    
    try:
        # Clean the location name and validate
        name = name.lower().strip()
        if not name:
            raise HTTPException(status_code=400, detail="Location name cannot be empty")
        
        # Get current position
        current_position = {
            "pan": ptz_control.est_pan_angle_deg,
            "tilt": ptz_control.est_tilt_angle_deg,
            "zoom": ptz_control.est_zoom_level
        }
        
        # Read existing locations
        try:
            with open("locations.json", "r") as f:
                locations = json.load(f)
        except FileNotFoundError:
            locations = {}
        
        # Add or update the location
        was_updated = name in locations
        locations[name] = current_position
        
        # Save back to file with pretty formatting
        with open("locations.json", "w") as f:
            json.dump(locations, f, indent=4)
        
        return {
            "message": f"Location '{name}' {'updated' if was_updated else 'saved'}",
            "location_name": name,
            "position": current_position,
            "available_locations": list(locations.keys())
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/take_picture/{location}", response_model=dict)
async def take_picture_at_location(location: str):
    if not ptz_control:
        raise HTTPException(status_code=503, detail="PTZ control not available")
    
    try:
        # First, move to the location
        location = location.lower()  # case-insensitive matching
        if location not in preset_locations:
            available_locations = list(preset_locations.keys())
            raise HTTPException(
                status_code=404, 
                detail=f"Location '{location}' not found. Available locations: {available_locations}"
            )
        
        # Get the preset coordinates and move there
        preset = preset_locations[location]
        ptz_control.abs_pantilt((preset["pan"], preset["tilt"]))
        ptz_control.abs_zoom(preset["zoom"])
        
        # Small delay to ensure camera has stopped moving
        time.sleep(1)
        
        # Now take the picture
        cap = cv2.VideoCapture(CAMERA_URL)
        if not cap.isOpened():
            raise HTTPException(status_code=503, detail="Could not connect to camera")
        
        # Read a frame
        ret, frame = cap.read()
        if not ret:
            raise HTTPException(status_code=500, detail="Could not capture image")
        
        # Create output directory if it doesn't exist
        os.makedirs("output/pictures", exist_ok=True)
        
        # Generate filename with timestamp and location name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"output/pictures/{timestamp}_{location}.jpg"
        
        # Save the image
        cv2.imwrite(filename, frame)
        
        # Release the capture
        cap.release()
        
        return {
            "message": f"Moved to location '{location}' and took picture",
            "location": preset,
            "current_position": {
                "pan": ptz_control.est_pan_angle_deg,
                "tilt": ptz_control.est_tilt_angle_deg,
                "zoom": ptz_control.est_zoom_level
            },
            "picture": {
                "filename": filename,
                "timestamp": timestamp
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)