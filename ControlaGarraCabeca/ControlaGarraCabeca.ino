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

// --- Boca ---
Servo boca;
int pinBoca = 4;
int bocaAberta = 100;
int bocaFechada = 60;

// --- Botão ---
const int botaoPin = 7;  
int estadoBotao = HIGH;      // começa não pressionado (por causa do INPUT_PULLUP)
int ultimoEstadoBotao = HIGH;

void setup() {
  Serial.begin(9600);
  chain.update();

  olhoEsquerdo.attach(pinOlhoEsq);
  olhoDireito.attach(pinOlhoDir);

  palpebra.attach(pinPalpebra);
  palpebra.write(90);

  boca.attach(pinBoca);
  boca.write(bocaFechada);

  pinMode(botaoPin, INPUT_PULLUP); // botão entre pino e GND

  Serial.println("Sistema iniciado. Boca pronta!");
}

void loop() {
  chain.update();

  // --- Leitura do Botão ---
  estadoBotao = digitalRead(botaoPin);

  if (estadoBotao != ultimoEstadoBotao) {
    if (estadoBotao == LOW) {
      Serial.println("BOTAO:1"); // botão pressionado → começa ouvir
    } else {
      Serial.println("BOTAO:0"); // botão solto → para ouvir
    }
    delay(50); // anti-repique
    ultimoEstadoBotao = estadoBotao;
  }

  // --- Leitura do Serial ---
  if (Serial.available() > 0) {
    String comando = Serial.readStringUntil('\n');
    comando.trim();

    if (comando.startsWith("G:") && garra.isConnected()) {
      int angGarra = comando.substring(2).toInt();
      if (angGarra >= 0 && angGarra <= 180 && angGarra != ultimoAnguloGarra) {
        garra.setPosition(angGarra);
        ultimoAnguloGarra = angGarra;
        if (angGarra < 90) garra.setColor(0, 1, 0);
        else garra.setColor(1, 0, 0);
      }
    }
    else if (comando.startsWith("C:") && cabeca.isConnected()) {
      int angCabeca = comando.substring(2).toInt();
      if (angCabeca >= 0 && angCabeca <= 180 && angCabeca != ultimoAnguloCabeca) {
        cabeca.setPosition(angCabeca);
        ultimoAnguloCabeca = angCabeca;
      }
    }
    else if (comando.startsWith("O:")) {
      int angOlho = comando.substring(2).toInt();
      angOlho = constrain(angOlho, 0, 100);
      if (angOlho != ultimoAnguloOlho) {
        olhoEsquerdo.write(angOlho);
        olhoDireito.write(angOlho);
        ultimoAnguloOlho = angOlho;
      }
    }
    else if (comando == "B:1") {
      for (int i = 0; i < 3; i++) {
        boca.write(bocaAberta);
        delay(800);
        boca.write(bocaFechada);
        delay(800);
      }
    }
    else if (comando == "B:0") {
      boca.write(bocaFechada);
    }
  }

  // --- Pálpebra piscando ---
  unsigned long agora = millis();
  if (agora - ultimoPiscar >= 5000) {
    palpebra.write(150);
    delay(200);
    palpebra.write(0);
    ultimoPiscar = agora;
  }
}
