import cv2

cap = cv2.VideoCapture(0)  # 0 is usually your default webcam

focus_min = 0
focus_max = 255
focus_step = 5
focus_value = focus_min
focus_direction = 1  # 1 for increasing, -1 for decreasing

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Draw focus value on the frame
    cv2.putText(frame, f"Focus: {focus_value}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    cv2.imshow("Webcam Feed", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
