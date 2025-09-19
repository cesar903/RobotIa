#include "Meccanoid.h"
#include <Servo.h>

// --- Cabeça e Garra ---
const int chainPin = 9;
Chain chain(chainPin);

MeccanoServo garra = chain.getServo(0);
MeccanoServo cabeca = chain.getServo(1);

int ultimoAnguloGarra = -1;
int ultimoAnguloCabeca = -1;

// --- Olhos ---
Servo olhoEsquerdo;
Servo olhoDireito;
int pinOlhoEsq = 3;
int pinOlhoDir = 5;
int ultimoAnguloOlho = -1;

// --- Pálpebra ---
Servo palpebra;
int pinPalpebra = 6;
unsigned long ultimoPiscar = 0;
bool piscando = false;

// --- Boca ---
Servo boca;
int pinBoca = 4;        // boca conectada no pino D12
int bocaAberta = 100;    // ajuste se necessário
int bocaFechada = 60;    // ajuste se necessário

void setup() {
  Serial.begin(9600);
  chain.update();

  olhoEsquerdo.attach(pinOlhoEsq);
  olhoDireito.attach(pinOlhoDir);

  palpebra.attach(pinPalpebra);
  palpebra.write(90); // começa aberta

  boca.attach(pinBoca);
  boca.write(bocaFechada); // começa fechada

  Serial.println("Sistema iniciado. Boca pronta!");
}

void loop() {
  chain.update();

  // --- Leitura do Serial ---
  if (Serial.available() > 0) {
    String comando = Serial.readStringUntil('\n');
    comando.trim();

    // Garra
    if (comando.startsWith("G:") && garra.isConnected()) {
      int angGarra = comando.substring(2).toInt();
      if (angGarra >= 0 && angGarra <= 180 && angGarra != ultimoAnguloGarra) {
        garra.setPosition(angGarra);
        ultimoAnguloGarra = angGarra;
        if (angGarra < 90)
          garra.setColor(0, 1, 0);
        else
          garra.setColor(1, 0, 0);
      }
    }
    // Cabeça
    else if (comando.startsWith("C:") && cabeca.isConnected()) {
      int angCabeca = comando.substring(2).toInt();
      if (angCabeca >= 0 && angCabeca <= 180 && angCabeca != ultimoAnguloCabeca) {
        cabeca.setPosition(angCabeca);
        ultimoAnguloCabeca = angCabeca;
      }
    }
    // Olhos
    else if (comando.startsWith("O:")) {
      int angOlho = comando.substring(2).toInt();
      angOlho = constrain(angOlho, 0, 100);
      if (angOlho != ultimoAnguloOlho) {
        olhoEsquerdo.write(angOlho);
        olhoDireito.write(angOlho);
        ultimoAnguloOlho = angOlho;
      }
    }
    // Boca
    // Boca
    else if (comando == "B:1") {
      // faz a boca "mexer" umas 3 vezes
      for (int i = 0; i < 3; i++) {
        boca.write(bocaAberta);
        delay(800);
        boca.write(bocaFechada);
        delay(800);
      }
    }
    else if (comando == "B:0") {
      boca.write(bocaFechada);  // garante fechada no fim
    }
  }

  // --- Pálpebra piscando a cada 5 segundos ---
  unsigned long agora = millis();
  if (agora - ultimoPiscar >= 5000) {
    piscando = true;
    palpebra.write(150); // fecha
    delay(200);          // tempo do piscar
    palpebra.write(0);   // abre
    ultimoPiscar = agora;
    piscando = false;
  }
}
