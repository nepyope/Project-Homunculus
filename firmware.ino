#include <Arduino.h>

#define S0 5
#define S1 6
#define S2 8
#define S3 7
#define SENSOR_INPUT 4
#define SENSOR_COUNT 16

int rawVals[SENSOR_COUNT];
uint8_t scanOrder[SENSOR_COUNT] = {7,6,5,4,3,2,1,0, 15,14,13,12,11,10,9,8};

void selectMuxChannel(uint8_t ch) {
  digitalWrite(S0, ch & 1);
  digitalWrite(S1, (ch >> 1) & 1);
  digitalWrite(S2, (ch >> 2) & 1);
  digitalWrite(S3, (ch >> 3) & 1);
}

void setup() {
  Serial.begin(115200);
  pinMode(S0, OUTPUT);
  pinMode(S1, OUTPUT);
  pinMode(S2, OUTPUT);
  pinMode(S3, OUTPUT);
}

void loop() {
  for (uint8_t i = 0; i < SENSOR_COUNT; i++) {
    selectMuxChannel(scanOrder[i]);
    delayMicroseconds(100);
    rawVals[i] = analogRead(SENSOR_INPUT);
  }
  for (uint8_t i = 0; i < SENSOR_COUNT; i++) {
    Serial.print(rawVals[i]);
    Serial.print(' ');
  }
  Serial.println();
  delay(1);
}
