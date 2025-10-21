import cv2

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Impossible d'ouvrir la caméra !")
else:
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Impossible de lire l'image !")
            break
        cv2.imshow("Test Caméra", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
cap.release()
cv2.destroyAllWindows()
