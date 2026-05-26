import cv2
import time


class Camera:
    def __init__(self, indice=0):
        self.indice = indice
        self.cap = None
        self.abrir_camera(indice)

    def abrir_camera(self, indice):
        if self.cap:
            self.cap.release()
            self.cap = None
            time.sleep(0.3)

        self.indice = indice

        self.cap = cv2.VideoCapture(self.indice, cv2.CAP_DSHOW)

        if not self.cap.isOpened():
            return False

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.cap.set(cv2.CAP_PROP_FPS, 30)

        return True

    def trocar_camera(self):
        indice_antigo = self.indice
        novo_indice = 1 if self.indice == 0 else 0

        sucesso = self.abrir_camera(novo_indice)

        if not sucesso:
            self.abrir_camera(indice_antigo)
            return indice_antigo, False

        return novo_indice, True

    def get_frame(self):
        if not self.cap:
            return None

        if not self.cap.isOpened():
            return None

        ret, frame = self.cap.read()

        if ret:
            return frame

        return None

    def release(self):
        if self.cap:
            self.cap.release()
            self.cap = None