# 📖 Leitor Inteligente de Pôsteres em Tempo Real

Sistema desenvolvido em Python para leitura inteligente de textos em pôsteres utilizando:

- OCR (Tesseract)
- OpenCV
- Processamento Digital de Imagens
- Tkinter
- Conversão de voz (Text-to-Speech)

O projeto permite capturar imagens da webcam em tempo real, aplicar filtros para melhorar a leitura e extrair textos automaticamente.

---

# 🚀 Funcionalidades

✅ Leitura OCR em tempo real  
✅ Compatível com webcam USB  
✅ Troca dinâmica de câmera  
✅ Processamento de imagem para melhorar OCR  
✅ Leitura de textos coloridos  
✅ Interface gráfica em Tkinter  
✅ Conversão de texto em voz  
✅ Captura em tempo real pela câmera  

---

# 🖼️ Tecnologias Utilizadas

- Python 3.12
- OpenCV
- PyTesseract
- Pillow
- NumPy
- pyttsx3
- Tkinter

---

# 📂 Estrutura do Projeto

```bash
📦 leitor_poster2.0
 ┣ 📂 venv
 ┣ 📂 __pycache__
 ┣ 📜 camera.py
 ┣ 📜 main.py
 ┣ 📜 requirements.txt
 ┣ 📜 .gitignore
 ┗ 📜 README.md
```

---

# ⚙️ Instalação

## 1️⃣ Clone o repositório

```bash
git clone https://github.com/SEU_USUARIO/leitor_poster2.0.git
```

Entre na pasta:

```bash
cd leitor_poster2.0
```

---

# 🐍 Criar Ambiente Virtual

## Windows

```bash
py -3.12 -m venv venv
```

---

# ▶️ Ativar Ambiente Virtual

## Windows

```bash
.\venv\Scripts\activate
```

Após ativar, o terminal ficará parecido com:

```bash
(venv) C:\projeto>
```

---

# 📦 Instalar Dependências

```bash
pip install -r requirements.txt
```

---

# ▶️ Executar o Projeto

```bash
python main.py
```

---

# 📄 requirements.txt

O projeto utiliza as seguintes bibliotecas:

```txt
opencv-python
pillow
pytesseract
pyttsx3
numpy
```

---

# 🔍 Configuração do Tesseract OCR

Este projeto utiliza o Tesseract OCR.

## Instale o Tesseract:

### Windows

Baixe em:

https://github.com/UB-Mannheim/tesseract/wiki

Após instalar, configure o caminho no código caso necessário:

```python
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

---

# 📷 Funcionalidades da Webcam

O sistema suporta:

- Webcam integrada
- Webcam USB
- Troca dinâmica de câmera
- Captura em tempo real

---

# 🧠 Processamento de Imagem

O sistema aplica técnicas de:

- Escala de cinza
- Threshold
- Nitidez
- Contraste
- Redução de ruído

para melhorar a precisão do OCR.

---

# 🔊 Conversão de Texto em Voz

Após reconhecer o texto, o sistema pode realizar a leitura em voz utilizando:

```python
pyttsx3
```

---

# 📌 Melhorias Futuras

- [ ] Exportar texto para PDF
- [ ] Melhorar OCR para textos inclinados
- [ ] Reconhecimento automático de idioma
- [ ] Interface mais moderna
- [ ] Detecção automática da melhor câmera

---

# 👨‍💻 Autor

Desenvolvido por Hyago Rhenan Lopes da Silva

Universidade do Estado de Mato Grosso - UNEMAT

---

# 📜 Licença

Este projeto é destinado para fins acadêmicos e educacionais.