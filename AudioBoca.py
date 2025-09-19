import pyttsx3
import json
import random
import unicodedata
import pyaudio
from vosk import Model, KaldiRecognizer
import keyboard
import time
import queue
import threading
import sys
import traceback
import serial
import socket

HOST = "127.0.0.1"
PORT = 5000

def envia_comando_boca(comando):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            s.sendall(comando.encode())
    except ConnectionRefusedError:
        print("[ERRO] Servidor de boca não está rodando.")



# -----------------------
# Fila para mensagens de voz
# -----------------------
tts_queue = queue.Queue()
falando_event = threading.Event()  # Event para sinalizar quando estiver falando

try:
    arduino = serial.Serial('COM10', 9600, timeout=1)
    time.sleep(2)  # espera a conexão serial se estabelecer
except serial.SerialException:
    print("ERRO: Não foi possível conectar na porta COM8. Verifique a porta e a conexão.")
    arduino = None


# -----------------------
# Thread TTS
# -----------------------
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
            envia_comando_boca("B:1")   # abre boca
            print("[SINAL ENVIADO] Boca ABERTA (B:1)")

            engine = pyttsx3.init()
            engine.setProperty('rate', 170)
            engine.setProperty('volume', 1.0)

            # Seleção de voz automática
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
            envia_comando_boca("B:0")   # fecha boca
            print("[SINAL ENVIADO] Boca FECHADA (B:0)")
            tts_queue.task_done()





# inicia thread TTS como daemon
threading.Thread(target=tts_worker, daemon=True).start()

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

# -----------------------
# Inicializa Vosk (modelo global)
# -----------------------
model = Model("vosk-model-small-pt-0.3")

p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=2048)
stream.start_stream()

print("Assistente pronto. Pressione e segure ESPAÇO para falar.")

try:
    while True:
        # só inicia captura quando não estivermos falando
        if not falando_event.is_set() and keyboard.is_pressed("space"):
            print("[Ouvindo...]")
            audio_data = []
            while keyboard.is_pressed("space"):
                try:
                    data = stream.read(2048, exception_on_overflow=False)
                    audio_data.append(data)
                except OSError:
                    # overflow de buffer — ignora esse frame
                    pass

            print("[Processando...]")
            if audio_data:
                # cria um recognizer local para cada captura (evita problemas com Reset())
                rec = KaldiRecognizer(model, 16000)
                for frame in audio_data:
                    rec.AcceptWaveform(frame)

                resultado = rec.FinalResult()
                try:
                    texto_reconhecido = json.loads(resultado).get("text", "")
                except Exception:
                    texto_reconhecido = ""

                if texto_reconhecido:
                    print(f"[Você disse]: {texto_reconhecido}")
                    frase_normalizada = normalizar(texto_reconhecido)

                    resposta = None
                    for chave, opcoes in respostas_normalizadas.items():
                        if chave in frase_normalizada:
                            resposta = random.choice(opcoes)
                            break
                    if not resposta:
                        resposta = "Desculpe, não entendi o que você disse."

                    print(f"[Fila de fala]: {resposta}")
                    tts_queue.put(resposta)  # adiciona na fila do TTS

        time.sleep(0.05)

except KeyboardInterrupt:
    print("\nFinalizando Assistente de Voz...")

finally:
    # encerra fluxos
    stream.stop_stream()
    stream.close()
    p.terminate()
    # sinaliza para TTS encerrar
    tts_queue.put(None)
    # opcional: aguarda a fila esvaziar (não obrigatório)
    tts_queue.join()
