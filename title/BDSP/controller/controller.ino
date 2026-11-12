#include "src/SwitchJoystick.h"

SwitchJoystick_ pad;
char line[32];
uint8_t length = 0;
bool overflow = false;

struct Button { const char *name; int8_t button; int16_t hat; };
const Button buttons[] = {
  {"Y", 0, -1}, {"B", 1, -1}, {"A", 2, -1}, {"X", 3, -1},
  {"L", 4, -1}, {"R", 5, -1}, {"ZL", 6, -1}, {"ZR", 7, -1},
  {"MINUS", 8, -1}, {"PLUS", 9, -1}, {"HOME", 12, -1},
  {"CAPTURE", 13, -1}, {"UP", -1, 0}, {"RIGHT", -1, 90},
  {"DOWN", -1, 180}, {"LEFT", -1, 270}
};

void command() {
  if (strcmp(line, "PING") == 0) { Serial1.println(F("PONG")); return; }
  for (const auto &b : buttons) {
    if (strcmp(line, b.name) != 0) continue;
    if (b.button >= 0) pad.pressButton(b.button); else pad.setHatSwitch(b.hat);
    delay(150);
    if (b.button >= 0) pad.releaseButton(b.button); else pad.setHatSwitch(-1);
    Serial1.println(F("OK"));
    return;
  }
  Serial1.println(F("ERR"));
}

void setup() {
  Serial1.begin(115200);
  pad.begin(false);
  pad.setXAxis(128); pad.setYAxis(128); pad.setZAxis(128); pad.setRzAxis(128);
  pad.sendState();
  // Send subsequent changes immediately; no button is pressed at startup.
  pad.begin(true);
}

void loop() {
  while (Serial1.available()) {
    char c = Serial1.read();
    if (c == '\r') continue;
    if (c == '\n') {
      if (overflow) Serial1.println(F("ERR"));
      else { line[length] = '\0'; command(); }
      length = 0; overflow = false;
    } else if (!overflow) {
      if (length < sizeof(line) - 1) line[length++] = c;
      else overflow = true;
    }
  }
}
