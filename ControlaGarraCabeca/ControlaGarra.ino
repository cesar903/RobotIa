// #include "Meccanoid.h"

// const int chainPin = 9;
// Chain chain(chainPin);
// MeccanoServo garra = chain.getServo(0);

// int ultimoAngulo = -1;

// void setup() {
//   Serial.begin(9600);
//   chain.update();
// }

// void loop() {
//   chain.update();

//   if (Serial.available() > 0) {
//     String angStr = Serial.readStringUntil('\n');
//     angStr.trim();

//     if (garra.isConnected()) {
//       int angulo = angStr.toInt();
//       if (angulo >= 0 && angulo <= 180 && angulo != ultimoAngulo) {
//         garra.setPosition(angulo);
//         ultimoAngulo = angulo;

//         if (angulo < 90)
//           garra.setColor(0,1,0);  // verde (aberto)
//         else
//           garra.setColor(1,0,0);  // vermelho (fechado)
//       }
//     }
//   }
// }
