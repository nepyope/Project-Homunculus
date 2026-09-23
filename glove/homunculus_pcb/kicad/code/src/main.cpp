#include <Adafruit_NeoPixel.h>
#include <Arduino.h>
#include <SSD1306Wire.h>
#include <Wire.h>

#define NUM_LEDS 1
#define DATA_PIN 2

Adafruit_NeoPixel pixels(NUM_LEDS, DATA_PIN, NEO_GRB + NEO_KHZ800);

SSD1306Wire display(0x3c, /* SDA */ 7, /* SCL */ 6, GEOMETRY_128_32);

void setup() {
  Serial.begin(9600);

  pinMode(3, INPUT);

  pixels.begin();
  display.init();
}

void loop() {
  display.drawRect(12, 12, 20, 20);
  display.display();

  if (digitalRead(3) == LOW) {
    pixels.setPixelColor(0,
                         pixels.Color(random(255), random(255), random(255)));
    pixels.show();
  }
}