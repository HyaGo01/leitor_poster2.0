import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

import cv2
import numpy as np
import pytesseract
import pyttsx3
from PIL import Image, ImageTk

# Biblioteca de IA do Google
from google import genai

from camera import Camera

# =========================
# CONFIG TESSERACT
# =========================
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
os.environ["TESSDATA_PREFIX"] = r"C:\Program Files\Tesseract-OCR\tessdata"

# =========================
# CONFIG CHAVE DA IA (GEMINI)
# =========================
API_KEY_GEMINI = "AIzaSyA0fcxzZICWRBVHNaTSkXh5libT0_e76oQ"

client_gemini = None
if API_KEY_GEMINI and API_KEY_GEMINI != "SUA_CHAVE_API_AQUI":
    try:
        client_gemini = genai.Client(api_key=API_KEY_GEMINI)
    except Exception as e:
        print(f"[Erro Inicialização IA]: {e}")


# =========================
# CORREÇÃO INTELIGENTE POR IA
# =========================
def corrigir_texto_com_ia(texto_sujo):
    global client_gemini
    if not texto_sujo.strip() or client_gemini is None:
        return texto_sujo

    try:
        prompt = (
            "Você é um assistente especialista em pós-processamento de OCR.\n"
            "Sua tarefa é corrigir erros de leitura de uma imagem binarizada, juntar palavras separadas "
            "indevidamente, ajustar pontuações e erros ortográficos em português (Brasil).\n"
            "Tente deduzir o sentido real das frases baseando-se em contextos de cartazes, eventos acadêmicos "
            "(como Semana da Computação, SECOMP, datas, anos) ou documentos.\n"
            "Importante: Devolva APENAS o texto corrigido final limpo, sem nenhuma nota, introdução ou explicação."
        )

        response = client_gemini.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"{prompt}\n\nTexto bruto do OCR:\n{texto_sujo}",
        )
        
        if response.text:
            return response.text.strip()
    except Exception as e:
        print(f"[Aviso IA]: Falha na requisição: {e}")
    
    return texto_sujo


# =========================
# CORTE INTELIGENTE SEM DEFORMAÇÃO
# =========================
def detectar_papel(frame):
    """Mantém o frame original estável removendo apenas ruído de bordas."""
    h_orig, w_orig = frame.shape[:2]
    margem_w, margem_h = int(w_orig * 0.02), int(h_orig * 0.02)
    return frame[margem_h:h_orig-margem_h, margem_w:w_orig-margem_w]


# =========================
# MELHORIA DE IMAGEM EQUILIBRADA
# =========================
def melhorar_imagem(img):
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img.copy()

    h, w = gray.shape[:2]
    if w < 1200:
        escala = 1200 / w
        gray = cv2.resize(gray, None, fx=escala, fy=escala, interpolation=cv2.INTER_CUBIC)

    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    return clahe.apply(gray)


def limpar_texto(texto):
    linhas = []
    for bundle in texto.splitlines():
        bundle = bundle.strip()
        if len(bundle) < 2:
            continue
        bundle = bundle.replace("|", "I").replace("  ", " ")
        sujeira = sum(1 for c in bundle if not c.isalnum() and c not in " áéíóúãõâêôçÁÉÍÓÚÃÕÂÊÔÇ.,;:!?-/()")
        if sujeira > len(bundle) * 0.65:
            continue
        linhas.append(bundle)
    return "\n".join(linhas)


# =========================
# APP INTERFACE
# =========================
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Leitor OCR Otimizado com IA")
        self.root.geometry("1400x850")
        self.root.configure(bg="#f0f0f0")

        self.camera = Camera(0)
        self.processando = False
        self.trocando_camera = False
        self.imagem_carregada = None
        self.estavel = False
        
        self.engine_voz = pyttsx3.init()
        self.engine_voz.setProperty("rate", 160)

        self.root.bind("<space>", self.atalho_espaco)

        # LAYOUT
        frame_principal = tk.Frame(root, bg="#f0f0f0")
        frame_principal.pack(fill="both", expand=True, padx=10, pady=10)

        esquerda = tk.Frame(frame_principal, bg="#f0f0f0")
        esquerda.pack(side="left", fill="both", expand=True)

        self.label_video = tk.Label(esquerda, bg="black")
        self.label_video.pack(pady=10)

        self.texto_box = tk.Text(esquerda, height=10, font=("Arial", 14), wrap="word")
        self.texto_box.pack(fill="both", expand=True)

        direita = tk.Frame(frame_principal, bg="#dcdcdc", width=280)
        direita.pack(side="right", fill="y", padx=10)
        direita.pack_propagate(False)

        titulo = tk.Label(direita, text="CONTROLES", bg="#dcdcdc", font=("Arial", 18, "bold"))
        titulo.pack(pady=20)

        botoes = [
            ("Capturar (Espaço)", self.capturar, "#4CAF50"),
            ("Trocar câmera", self.trocar_camera, "#009688"),
            ("Abrir imagem", self.abrir_imagem, "#673AB7"),
            ("Ler em voz alta", self.ler_texto, "#2196F3"),
            ("Limpar", self.limpar, "#FF9800"),
        ]

        for txt, cmd, cor in botoes:
            tk.Button(
                direita, text=txt, command=cmd, bg=cor, fg="white",
                font=("Arial", 12, "bold"), width=22, height=2
            ).pack(pady=10)

        self.status = tk.Label(
            direita, text=f"Sistema pronto\nCâmera {self.camera.indice}",
            bg="#dcdcdc", fg="green", font=("Arial", 12, "bold"),
            anchor="center", justify="center", wrap=260
        )
        self.status.pack(pady=30, fill="x")

        self.update_video()

    def atalho_espaco(self, event):
        if not self.processando:
            self.capturar()

    def verificar_estabilidade(self, frame):
        """
        MÉTODO ULTRA-RÁPIDO: Mede a variação de foco (Laplaciano).
        Evita lentidões e mantém o vídeo fluido a 60 FPS.
        """
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            # Calcula a variação focal (foco/nitidez)
            valor_foco = cv2.Laplacian(gray, cv2.CV_64F).var()
            # Se o valor for maior que 70, a imagem está nítida e sem desfoque de movimento
            return valor_foco > 70
        except Exception:
            return False

    def update_video(self):
        if self.trocando_camera or self.imagem_carregada is not None:
            self.root.after(30, self.update_video)
            return

        frame = self.camera.get_frame()
        if frame is not None:
            frame_visual = frame.copy()
            self.estavel = self.verificar_estabilidade(frame_visual)

            # Desenha a bolinha indicadora na tela ao vivo
            h, w = frame_visual.shape[:2]
            ponto = (int(w * 0.05), int(h * 0.05))
            if self.estavel:
                cv2.circle(frame_visual, ponto, 10, (0, 255, 0), -1)
                cv2.putText(frame_visual, "ESTAVEL", (ponto[0]+20, ponto[1]+5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            else:
                cv2.circle(frame_visual, ponto, 10, (0, 0, 255), -1)
                cv2.putText(frame_visual, "INSTAVEL (Foque no Texto)", (ponto[0]+20, ponto[1]+5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

            self.mostrar_imagem(frame_visual)

        self.root.after(10, self.update_video)

    def mostrar_imagem(self, frame):
        largura_max, altura_max = 950, 520
        h, w = frame.shape[:2]

        escala = min(largura_max / w, altura_max / h)
        nova_largura, nova_altura = int(w * escala), int(h * escala)

        frame = cv2.resize(frame, (nova_largura, nova_altura), interpolation=cv2.INTER_AREA)

        if len(frame.shape) == 2:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

        fundo = np.zeros((altura_max, largura_max, 3), dtype=np.uint8)
        fundo[:] = (240, 240, 240)

        y = (altura_max - nova_altura) // 2
        x = (largura_max - nova_largura) // 2
        fundo[y:y + nova_altura, x:x + nova_largura] = frame

        frame_rgb = cv2.cvtColor(fundo, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)
        imgtk = ImageTk.PhotoImage(image=img)

        self.label_video.imgtk = imgtk
        self.label_video.configure(image=imgtk)

    def trocar_camera(self):
        if self.processando or self.trocando_camera:
            return

        self.trocando_camera = True
        self.imagem_carregada = None
        self.status.config(text="Trocando câmera...", fg="orange")

        def tarefa():
            indice, sucesso = self.camera.trocar_camera()
            def atualizar_tela():
                if sucesso:
                    self.status.config(text=f"Câmera atual:\n{indice}", fg="blue")
                else:
                    self.status.config(text=f"Erro ao trocar\nCâmera atual: {indice}", fg="red")
                    messagebox.showwarning("Aviso", f"Não foi possível abrir a câmera {indice}.")
                self.trocando_camera = False

            self.root.after(0, atualizar_tela)

        threading.Thread(target=tarefa, daemon=True).start()

    def abrir_imagem(self):
        caminho = filedialog.askopenfilename(filetypes=[("Imagens", "*.png *.jpg *.jpeg *.bmp")])
        if not caminho:
            return

        imagem = cv2.imread(caminho)
        if imagem is None:
            messagebox.showerror("Erro", "Não foi possível abrir imagem.")
            return

        self.imagem_carregada = imagem
        self.mostrar_imagem(imagem)
        threading.Thread(target=self.processar_frame, args=(imagem, False), daemon=True).start()

    def capturar(self):
        if self.processando or self.trocando_camera:
            return

        frame = self.camera.get_frame()
        if frame is None:
            messagebox.showwarning("Aviso", "Câmera não encontrada.")
            return

        self.imagem_carregada = frame.copy()
        self.mostrar_imagem(frame)
        threading.Thread(target=self.processar_frame, args=(frame, True), daemon=True).start()

    def processar_frame(self, frame, origem_camera=True):
        self.processando = True
        self.status.config(text="Processando\nOCR Local...", fg="orange")
        
        self.texto_box.delete("1.0", tk.END)
        self.texto_box.insert(tk.END, "Processando imagem localmente...\n")

        try:
            if origem_camera:
                papel = detectar_papel(frame)
            else:
                papel = frame.copy()

            imagem_proc = melhorar_imagem(papel)
            
            config = "--oem 3 --psm 3 -c preserve_interword_spaces=1"
            texto_bruto = pytesseract.image_to_string(imagem_proc, lang="por", config=config)
            texto_bruto = limpar_texto(texto_bruto)
            
            self.texto_box.delete("1.0", tk.END)
            
            if texto_bruto.strip():
                self.texto_box.insert(tk.END, texto_bruto)
                self.status.config(text="IA Refinando\nTexto...", fg="blue")
                threading.Thread(target=self.async_refinar_ia, args=(texto_bruto,), daemon=True).start()
            else:
                self.texto_box.insert(tk.END, "Nenhum caractere confiável detectado.\nAproxime mais o texto.")
                self.status.config(text="Sem texto", fg="red")
                self.processando = False

        except Exception as e:
            self.texto_box.delete("1.0", tk.END)
            self.texto_box.insert(tk.END, f"Erro no processamento:\n{e}")
            self.status.config(text="Erro", fg="red")
            self.processando = False

    def async_refinar_ia(self, texto_bruto):
        texto_corrigido = corrigir_texto_com_ia(texto_bruto)
        
        def atualizar_interface():
            if texto_corrigido == texto_bruto:
                self.status.config(text="Concluído\n(OCR Local / Sem retorno IA)", fg="#d35400")
            else:
                self.texto_box.delete("1.0", tk.END)
                self.texto_box.insert(tk.END, texto_corrigido)
                self.status.config(text="Concluído com IA", fg="green")
            
            self.processando = False

        self.root.after(0, atualizar_interface)

    def ler_texto(self):
        text = self.texto_box.get("1.0", tk.END).strip()
        if not text or "Processando imagem" in text:
            return

        def tarefa_fala():
            try:
                self.engine_voz.say(text)
                self.engine_voz.runAndWait()
            except Exception as e:
                print(f"[Aviso Som]: {e}")

        threading.Thread(target=tarefa_fala, daemon=True).start()

    def limpar(self):
        try:
            self.engine_voz.stop()
        except Exception:
            pass

        self.texto_box.delete("1.0", tk.END)
        self.imagem_carregada = None
        self.estavel = False
        self.status.config(text=f"Sistema pronto\nCâmera {self.camera.indice}", fg="green")

    def fechar(self):
        try:
            self.engine_voz.stop()
        except Exception:
            pass
        self.camera.release()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.protocol("WM_DELETE_WINDOW", app.fechar)
    root.mainloop()