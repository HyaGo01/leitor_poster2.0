import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

import cv2
import numpy as np
import pytesseract
import pyttsx3
from PIL import Image, ImageTk

from camera import Camera


# =========================
# CONFIG TESSERACT
# =========================

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

os.environ["TESSDATA_PREFIX"] = (
    r"C:\Program Files\Tesseract-OCR\tessdata"
)


# =========================
# DETECÇÃO DE PAPEL
# =========================

def ordenar_pontos(pts):
    rect = np.zeros((4, 2), dtype="float32")

    soma = pts.sum(axis=1)
    rect[0] = pts[np.argmin(soma)]
    rect[2] = pts[np.argmax(soma)]

    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]

    return rect


def detectar_papel(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    blur = cv2.GaussianBlur(gray, (5, 5), 0)

    _, thresh = cv2.threshold(
        blur,
        170,
        255,
        cv2.THRESH_BINARY
    )

    contornos, _ = cv2.findContours(
        thresh,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    if not contornos:
        return frame

    maior = max(contornos, key=cv2.contourArea)
    area = cv2.contourArea(maior)

    if area < 1000:
        return frame

    peri = cv2.arcLength(maior, True)

    aprox = cv2.approxPolyDP(
        maior,
        0.02 * peri,
        True
    )

    if len(aprox) != 4:
        return frame

    pts = aprox.reshape(4, 2)
    rect = ordenar_pontos(pts)

    tl, tr, br, bl = rect

    largura = int(max(
        np.linalg.norm(br - bl),
        np.linalg.norm(tr - tl)
    ))

    altura = int(max(
        np.linalg.norm(tr - br),
        np.linalg.norm(tl - bl)
    ))

    if largura <= 0 or altura <= 0:
        return frame

    destino = np.array([
        [0, 0],
        [largura - 1, 0],
        [largura - 1, altura - 1],
        [0, altura - 1]
    ], dtype="float32")

    matriz = cv2.getPerspectiveTransform(rect, destino)

    corrigida = cv2.warpPerspective(
        frame,
        matriz,
        (largura, altura)
    )

    return corrigida


# =========================
# MELHORIA DE IMAGEM
# =========================

def melhorar_imagem(img):
    if len(img.shape) == 2:
        gray = img.copy()
    else:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    h, w = gray.shape[:2]

    if w < 1200:
        escala = 1200 / w
        gray = cv2.resize(
            gray,
            None,
            fx=escala,
            fy=escala,
            interpolation=cv2.INTER_CUBIC
        )

    gray = cv2.GaussianBlur(gray, (3, 3), 0)

    gray = cv2.convertScaleAbs(
        gray,
        alpha=1.5,
        beta=10
    )

    _, thresh = cv2.threshold(
        gray,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    return thresh


# =========================
# LIMPEZA OCR
# =========================

def limpar_texto(texto):
    linhas = []

    for linha in texto.splitlines():
        linha = linha.strip()

        if len(linha) < 2:
            continue

        linha = linha.replace("|", "I")
        linha = linha.replace("  ", " ")

        sujeira = sum(
            1 for c in linha
            if not c.isalnum()
            and c not in " áéíóúãõâêôçÁÉÍÓÚÃÕÂÊÔÇ.,;:!?-/()"
        )

        if sujeira > len(linha) * 0.40:
            continue

        linhas.append(linha)

    return "\n".join(linhas)


# =========================
# OCR
# =========================

def extrair_texto_tesseract(frame, origem_camera=True):
    if origem_camera:
        papel = detectar_papel(frame)
    else:
        papel = frame.copy()

    imagem_tratada = melhorar_imagem(papel)

    config = (
        "--oem 3 "
        "--psm 6 "
        "-c preserve_interword_spaces=1 "
    )

    texto = pytesseract.image_to_string(
        imagem_tratada,
        lang="por",
        config=config
    )

    texto = limpar_texto(texto)

    return texto, imagem_tratada


# =========================
# VOZ
# =========================

def falar_texto(texto):
    if not texto.strip():
        return

    engine = pyttsx3.init()
    engine.setProperty("rate", 160)
    engine.say(texto)
    engine.runAndWait()


# =========================
# APP
# =========================

class App:
    def __init__(self, root):
        self.root = root

        self.root.title("Leitor OCR Otimizado")
        self.root.geometry("1400x850")
        self.root.configure(bg="#f0f0f0")

        self.camera = Camera(0)

        self.processando = False
        self.trocando_camera = False
        self.imagem_carregada = None

        # =========================
        # LAYOUT
        # =========================

        frame_principal = tk.Frame(
            root,
            bg="#f0f0f0"
        )

        frame_principal.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10
        )

        esquerda = tk.Frame(
            frame_principal,
            bg="#f0f0f0"
        )

        esquerda.pack(
            side="left",
            fill="both",
            expand=True
        )

        self.label_video = tk.Label(
            esquerda,
            bg="black"
        )

        self.label_video.pack(pady=10)

        self.texto_box = tk.Text(
            esquerda,
            height=10,
            font=("Arial", 14),
            wrap="word"
        )

        self.texto_box.pack(
            fill="both",
            expand=True
        )

        direita = tk.Frame(
            frame_principal,
            bg="#dcdcdc",
            width=260
        )

        direita.pack(
            side="right",
            fill="y",
            padx=10
        )

        direita.pack_propagate(False)

        titulo = tk.Label(
            direita,
            text="CONTROLES",
            bg="#dcdcdc",
            font=("Arial", 18, "bold")
        )

        titulo.pack(pady=20)

        botoes = [
            ("Capturar da câmera", self.capturar, "#4CAF50"),
            ("Trocar câmera", self.trocar_camera, "#009688"),
            ("Abrir imagem", self.abrir_imagem, "#673AB7"),
            ("Ler em voz alta", self.ler_texto, "#2196F3"),
            ("Limpar", self.limpar, "#FF9800"),
        ]

        for txt, cmd, cor in botoes:
            tk.Button(
                direita,
                text=txt,
                command=cmd,
                bg=cor,
                fg="white",
                font=("Arial", 12, "bold"),
                width=22,
                height=2
            ).pack(pady=10)

        self.status = tk.Label(
            direita,
            text=f"Sistema pronto - câmera {self.camera.indice}",
            bg="#dcdcdc",
            fg="green",
            font=("Arial", 12, "bold")
        )

        self.status.pack(pady=40)

        self.update_video()

    # =========================
    # VIDEO
    # =========================

    def update_video(self):
        if self.trocando_camera:
            self.root.after(100, self.update_video)
            return

        if self.imagem_carregada is not None:
            self.root.after(40, self.update_video)
            return

        frame = self.camera.get_frame()

        if frame is not None:
            self.mostrar_imagem(frame)

        self.root.after(30, self.update_video)

    def mostrar_imagem(self, frame):
        largura_max = 950
        altura_max = 520

        h, w = frame.shape[:2]

        escala = min(
            largura_max / w,
            altura_max / h
        )

        nova_largura = int(w * escala)
        nova_altura = int(h * escala)

        frame = cv2.resize(
            frame,
            (nova_largura, nova_altura),
            interpolation=cv2.INTER_AREA
        )

        if len(frame.shape) == 2:
            frame = cv2.cvtColor(
                frame,
                cv2.COLOR_GRAY2BGR
            )

        fundo = np.zeros(
            (altura_max, largura_max, 3),
            dtype=np.uint8
        )

        fundo[:] = (240, 240, 240)

        y = (altura_max - nova_altura) // 2
        x = (largura_max - nova_largura) // 2

        fundo[
            y:y + nova_altura,
            x:x + nova_largura
        ] = frame

        frame_rgb = cv2.cvtColor(
            fundo,
            cv2.COLOR_BGR2RGB
        )

        img = Image.fromarray(frame_rgb)

        imgtk = ImageTk.PhotoImage(image=img)

        self.label_video.imgtk = imgtk
        self.label_video.configure(image=imgtk)

    # =========================
    # AÇÕES
    # =========================

    def trocar_camera(self):
        if self.processando or self.trocando_camera:
            return

        self.trocando_camera = True
        self.imagem_carregada = None

        self.status.config(
            text="Trocando câmera...",
            fg="orange"
        )

        def tarefa():
            indice, sucesso = self.camera.trocar_camera()

            def atualizar_tela():
                if sucesso:
                    self.status.config(
                        text=f"Câmera atual: {indice}",
                        fg="blue"
                    )
                else:
                    self.status.config(
                        text=f"Erro ao trocar. Câmera atual: {indice}",
                        fg="red"
                    )

                    messagebox.showwarning(
                        "Aviso",
                        f"Não foi possível abrir a câmera {indice}."
                    )

                self.trocando_camera = False

            self.root.after(0, atualizar_tela)

        threading.Thread(
            target=tarefa,
            daemon=True
        ).start()

    def abrir_imagem(self):
        caminho = filedialog.askopenfilename(
            filetypes=[
                ("Imagens", "*.png *.jpg *.jpeg *.bmp")
            ]
        )

        if not caminho:
            return

        imagem = cv2.imread(caminho)

        if imagem is None:
            messagebox.showerror(
                "Erro",
                "Não foi possível abrir imagem."
            )
            return

        self.imagem_carregada = imagem
        self.mostrar_imagem(imagem)

        threading.Thread(
            target=self.processar_frame,
            args=(imagem, False),
            daemon=True
        ).start()

    def capturar(self):
        if self.processando or self.trocando_camera:
            return

        frame = self.camera.get_frame()

        if frame is None:
            messagebox.showwarning(
                "Aviso",
                "Câmera não encontrada."
            )
            return

        threading.Thread(
            target=self.processar_frame,
            args=(frame, True),
            daemon=True
        ).start()

    def processar_frame(self, frame, origem_camera=True):
        self.processando = True

        self.status.config(
            text="Processando OCR...",
            fg="orange"
        )

        self.texto_box.delete("1.0", tk.END)
        self.texto_box.insert(tk.END, "Lendo texto...\n")

        try:
            texto, imagem = extrair_texto_tesseract(
                frame,
                origem_camera
            )

            self.mostrar_imagem(imagem)

            self.texto_box.delete("1.0", tk.END)

            if texto.strip():
                self.texto_box.insert(tk.END, texto)

                self.status.config(
                    text="OCR concluído",
                    fg="green"
                )

            else:
                self.texto_box.insert(
                    tk.END,
                    "Nenhum texto detectado.\n\n"
                    "Tente uma imagem mais nítida, reta e com boa iluminação."
                )

                self.status.config(
                    text="Sem texto",
                    fg="red"
                )

        except Exception as e:
            self.texto_box.delete("1.0", tk.END)

            self.texto_box.insert(
                tk.END,
                f"Erro:\n{e}"
            )

            self.status.config(
                text="Erro",
                fg="red"
            )

        self.processando = False

    def ler_texto(self):
        texto = self.texto_box.get("1.0", tk.END)

        threading.Thread(
            target=falar_texto,
            args=(texto,),
            daemon=True
        ).start()

    def limpar(self):
        self.texto_box.delete("1.0", tk.END)

        self.imagem_carregada = None

        self.status.config(
            text=f"Sistema pronto - câmera {self.camera.indice}",
            fg="green"
        )

    def fechar(self):
        self.camera.release()
        self.root.destroy()


# =========================
# MAIN
# =========================

if __name__ == "__main__":
    root = tk.Tk()

    app = App(root)

    root.protocol(
        "WM_DELETE_WINDOW",
        app.fechar
    )

    root.mainloop()