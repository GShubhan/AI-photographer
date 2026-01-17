import cv2
import sys
import time

def frame_cap():
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        raise IOError("Cannot open webcam")


    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame")
        cap.release()
        return None

    cap.release()
    if cv2.waitKey(1) & 0xFF == ord("q"):
        return None
    cv2.imwrite("temp.jpg", frame)
    return frame

# while (True):
#     time.sleep(1)
#     frame = frame_cap()
#     if frame is not None:
#         cv2.imshow("Webcam Frame", frame)
#     else:
#         break
