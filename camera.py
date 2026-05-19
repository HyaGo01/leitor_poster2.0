import cv2


class Camera:
    def __init__(self, indice=0):
        self.cap = cv2.VideoCapture(indice)

    def get_frame(self):
        ret, frame = self.cap.read()
        if ret:
            return frame
        return None

    def release(self):
        if self.cap:
            self.cap.release()