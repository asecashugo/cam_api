import cv2

def show_plate_roi(frame, x, y, w, h):
    """
    Extracts the ROI from the frame and displays it in a window.
    """
    roi = frame[y:y+h, x:x+w]
    # cv2.imshow("Plate Region", roi)
