import cv2
import mediapipe as mp
import serial
import time
import math
import socket
import threading

HOST = "127.0.0.1"
PORT = 5000
PORT_BOTAO = 5001  # nova porta só para o botão
botao_clients = []
botao_pressionado = False  # variável global do botão

# -----------------------
# Conecta ao Arduino
# -----------------------
try:
    arduino = serial.Serial('COM10', 9600, timeout=1)
    time.sleep(2)
except serial.SerialException:
    print("ERRO: Não foi possível conectar na porta COM8.")
    arduino = None

# -----------------------
# Envia estado do botão para todos os clientes conectados
# -----------------------
def envia_estado_botao(estado):
    global botao_clients
    for client in botao_clients[:]:
        try:
            client.sendall(estado.encode())
        except:
            botao_clients.remove(client)

# -----------------------
# Leitura do botão via Arduino
# -----------------------
def ler_botao_serial():
    global botao_pressionado
    while arduino:
        if arduino.in_waiting > 0:
            linha = arduino.readline().decode(errors='ignore').strip()
            if linha == "BOTAO:1":
                if not botao_pressionado:
                    print("[BOTÃO] Pressionado")
                botao_pressionado = True
                envia_estado_botao("BOTAO:1")
            elif linha == "BOTAO:0":
                if botao_pressionado:
                    print("[BOTÃO] Solto")
                botao_pressionado = False
                envia_estado_botao("BOTAO:0")
        time.sleep(0.02)

if arduino:
    threading.Thread(target=ler_botao_serial, daemon=True).start()

# -----------------------
# Servidor de sockets para receber comandos (da boca ou TTS)
# -----------------------
def servidor_boca():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"[SERVIDOR BOCA] Aguardando em {HOST}:{PORT}")
        while True:
            conn, addr = s.accept()
            with conn:
                data = conn.recv(1024).decode().strip()
                if data:
                    print(f"[SERVIDOR BOCA] Recebi: {data}")
                    if arduino:
                        arduino.write((data + "\n").encode())

threading.Thread(target=servidor_boca, daemon=True).start()

# -----------------------
# Servidor de sockets exclusivo do botão
# -----------------------
def servidor_botao():
    global botao_clients
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT_BOTAO))  # corrigido de HOST_BOTAO para HOST
        s.listen()
        print(f"[SERVIDOR BOTÃO] Aguardando conexão em {HOST}:{PORT_BOTAO}")
        while True:
            conn, addr = s.accept()
            print(f"[SERVIDOR BOTÃO] Conectado: {addr}")
            botao_clients.append(conn)

threading.Thread(target=servidor_botao, daemon=True).start()

# -----------------------
# Funções de visão (câmera + MediaPipe)
# -----------------------
cap = cv2.VideoCapture(0)
mp_drawing = mp.solutions.drawing_utils
mp_hands = mp.solutions.hands
mp_face_mesh = mp.solutions.face_mesh

def calcular_distancia(p1, p2):
    return math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2)

ultimo_angulo_garra = None
ultimo_angulo_olho = None
ultimo_angulo_cabeca = None
distancia_minima = 0.015
distancia_maxima = 0.12

# -----------------------
# Loop principal
# -----------------------
with mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7) as hands, \
     mp_face_mesh.FaceMesh(min_detection_confidence=0.7, min_tracking_confidence=0.7) as face_mesh:

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        hands_results = hands.process(rgb_frame)
        face_results = face_mesh.process(rgb_frame)

        angulo_garra = None
        angulo_cabeca = None
        angulo_olho = None

        # --- Controle da garra ---
        if hands_results.multi_hand_landmarks:
            for hand_landmarks in hands_results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                polegar = hand_landmarks.landmark[4]
                indicador = hand_landmarks.landmark[8]
                distancia = calcular_distancia(polegar, indicador)
                distancia_clamped = max(distancia_minima, min(distancia, distancia_maxima))
                proporcao = (distancia_clamped - distancia_minima) / (distancia_maxima - distancia_minima)
                angulo_garra = int(180 - proporcao * (180 - 100))
                angulo_garra = max(100, min(180, angulo_garra))
                cv2.putText(frame, f'Garra: {angulo_garra}', (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)

        # --- Controle da cabeça e olhos ---
        if face_results.multi_face_landmarks:
            face_landmarks = face_results.multi_face_landmarks[0]
            ponto_esquerdo = face_landmarks.landmark[33]
            ponto_direito = face_landmarks.landmark[263]
            ponto_central = face_landmarks.landmark[1]
            dist_esquerdo = ponto_central.x - ponto_esquerdo.x
            dist_direito = ponto_direito.x - ponto_central.x
            soma = dist_esquerdo + dist_direito
            angulo_cabeca = 90 if soma == 0 else int((dist_direito / soma)*(100-70)+70)
            angulo_cabeca = max(70, min(100, angulo_cabeca))
            cv2.putText(frame, f'Cabeca: {angulo_cabeca}', (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,0,0), 2)

            for face_landmarks in face_results.multi_face_landmarks:
                pos_x = face_landmarks.landmark[1].x
                angulo_olho = int(pos_x * 100)
                angulo_olho = max(0, min(100, angulo_olho))

        # --- Envio para Arduino ---
        if arduino:
            if angulo_garra is not None and (ultimo_angulo_garra is None or abs(angulo_garra - ultimo_angulo_garra) > 2):
                arduino.write(f"G:{angulo_garra}\n".encode())
                ultimo_angulo_garra = angulo_garra
            if angulo_cabeca is not None and (ultimo_angulo_cabeca is None or abs(angulo_cabeca - ultimo_angulo_cabeca) > 2):
                arduino.write(f"C:{angulo_cabeca}\n".encode())
                ultimo_angulo_cabeca = angulo_cabeca
            if angulo_olho is not None and (ultimo_angulo_olho is None or abs(angulo_olho - ultimo_angulo_olho) > 2):
                arduino.write(f"O:{angulo_olho}\n".encode())
                ultimo_angulo_olho = angulo_olho

        cv2.imshow('Controle Total', frame)

        if cv2.waitKey(1) & 0xFF == 27:
            break

print("Finalizando...")
cap.release()
cv2.destroyAllWindows()
if arduino:
    arduino.close()
