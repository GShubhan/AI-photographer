# Local checks (every frame)
#   ─ face detected
#   ─ eyes open 
#   ─ motion < threshold 
#   ─ time >=10s - check in main() 
import cv2

def face_check(img):
    file = cv2.imread(img)
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    gray = cv2.cvtColor(file, cv2.COLOR_BGR2GRAY)
    return (len(face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5))>=1)

def eyes_open_check(img):
    file = cv2.imread(img)
    eye_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_eye.xml"
    )
    gray = cv2.cvtColor(file, cv2.COLOR_BGR2GRAY)
    return (len(eye_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5))>=1)

#My function to check bluriness is not working well, maybe we can just as LLM to decide that?

def isnt_blurry(img, threshold=40):
    file = cv2.imread(img)
    gray = cv2.cvtColor(file, cv2.COLOR_BGR2GRAY)
    lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    #return lap_var > threshold
    return lap_var


# print(face_check("temp.jpg"))
# print(eyes_open_check("temp.jpg"))
# print(isnt_blurry("temp.jpg"))