import pyttsx3
import json
import random
import unicodedata
import pyaudio
from vosk import Model, KaldiRecognizer
import time
import queue
import threading
import sys
import traceback
import socket
import difflib

# -----------------------
# Configurações de rede
# -----------------------
HOST = "127.0.0.1"
PORT_BOCA = 5000       # para enviar comando de boca ao ControlaTudo.py
PORT_BOTAO = 5001      # para receber estado do botão do ControlaTudo.py

# -----------------------
# Variáveis globais
# -----------------------
tts_queue = queue.Queue()
falando_event = threading.Event()
botao_pressionado = False  # atualizado via socket do servidor do botão

# -----------------------
# Função para enviar comando de boca
# -----------------------
def envia_comando_boca(comando):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT_BOCA))
            s.sendall(comando.encode())
    except ConnectionRefusedError:
        print("[ERRO] Servidor de boca não está rodando.")

# -----------------------
# Cliente para receber estado do botão
# -----------------------
def escuta_botao_cliente():
    global botao_pressionado
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((HOST, PORT_BOTAO))
                print(f"[BOTÃO CLIENTE] Conectado ao servidor do botão em {HOST}:{PORT_BOTAO}")
                while True:
                    data = s.recv(1024).decode().strip()
                    if data == "BOTAO:1":
                        botao_pressionado = True
                    elif data == "BOTAO:0":
                        botao_pressionado = False
        except ConnectionRefusedError:
            print("[BOTÃO CLIENTE] Servidor do botão não disponível. Tentando novamente em 1s...")
            time.sleep(1)
        except Exception as e:
            print("[BOTÃO CLIENTE] Erro:", e)
            time.sleep(1)

threading.Thread(target=escuta_botao_cliente, daemon=True).start()

# -----------------------
# Carrega falas JSON
# -----------------------
with open("falas.json", "r", encoding="utf-8") as f:
    respostas = json.load(f)

def normalizar(texto):
    return "".join(
        c for c in unicodedata.normalize("NFD", texto.lower().strip())
        if unicodedata.category(c) != "Mn"
    )

respostas_normalizadas = {normalizar(k): v for k, v in respostas.items()}

def melhor_resposta(frase, respostas_normalizadas, limite=0.4):
    melhor_chave = None
    melhor_score = 0
    for chave in respostas_normalizadas.keys():
        score = difflib.SequenceMatcher(None, chave, frase).ratio()
        if score > melhor_score:
            melhor_score = score
            melhor_chave = chave
    if melhor_score >= limite:
        return random.choice(respostas_normalizadas[melhor_chave])
    return None

# -----------------------
# Thread TTS
# -----------------------
def tts_worker():
    try:
        import pythoncom
        pythoncom.CoInitialize()
    except Exception:
        pass

    while True:
        texto = tts_queue.get()
        if texto is None:
            tts_queue.task_done()
            break

        try:
            falando_event.set()
            envia_comando_boca("B:1")  # abre boca
            print("[SINAL] Boca ABERTA (B:1)")

            engine = pyttsx3.init()
            engine.setProperty('rate', 170)
            engine.setProperty('volume', 1.0)

            voices = engine.getProperty("voices")
            selecionada = None
            for v in voices:
                if "DANIEL" in v.name.upper():
                    selecionada = v.id
                    break
            if not selecionada:
                for v in voices:
                    if "MARIA" in v.name.upper():
                        selecionada = v.id
                        break
            if selecionada:
                engine.setProperty("voice", selecionada)

            engine.say(texto)
            engine.runAndWait()
            try:
                engine.stop()
            except Exception:
                pass
            del engine

        except Exception as e:
            print("Erro no TTS:", e, file=sys.stderr)
            traceback.print_exc()
        finally:
            falando_event.clear()
            envia_comando_boca("B:0")  # fecha boca
            print("[SINAL] Boca FECHADA (B:0)")
            tts_queue.task_done()

threading.Thread(target=tts_worker, daemon=True).start()

# -----------------------
# Inicializa Vosk
# -----------------------
model = Model("vosk-model-small-pt-0.3")
p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=2048)
stream.start_stream()

print("Assistente pronto. Pressione e segure o BOTÃO.")

# -----------------------
# Loop principal
# -----------------------
try:
    while True:
        if not falando_event.is_set() and botao_pressionado:
            print("[Ouvindo...]")
            audio_data = []
            while botao_pressionado:
                try:
                    data = stream.read(2048, exception_on_overflow=False)
                    audio_data.append(data)
                except OSError:
                    pass

            print("[Processando...]")
            if audio_data:
                rec = KaldiRecognizer(model, 16000)
                for frame in audio_data:
                    rec.AcceptWaveform(frame)
                resultado = rec.FinalResult()
                try:
                    texto_reconhecido = json.loads(resultado).get("text", "")
                except:
                    texto_reconhecido = ""

                if texto_reconhecido:
                    print(f"[Você disse]: {texto_reconhecido}")
                    frase_normalizada = normalizar(texto_reconhecido)
                    resposta = melhor_resposta(frase_normalizada, respostas_normalizadas)
                    if not resposta:
                        resposta = "Não entendi"
                    print(f"[Fila de fala]: {resposta}")
                    tts_queue.put(resposta)

        time.sleep(0.05)

except KeyboardInterrupt:
    print("\nFinalizando Assistente de Voz...")

finally:
    stream.stop_stream()
    stream.close()
    p.terminate()
    tts_queue.put(None)
    tts_queue.join()
