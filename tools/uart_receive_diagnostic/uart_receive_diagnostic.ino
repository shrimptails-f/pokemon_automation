// Forward every byte received from SH-U09C to the Arduino's USB serial port.
// Diagnostic only: this sketch does not operate the Switch.
void setup() {
  Serial.begin(115200);
  Serial1.begin(115200);
}

void loop() {
  // The PC can verify this diagnostic sketch over USB independently of UART.
  while (Serial.available()) {
    if (Serial.read() == '?') Serial.println("UART-DIAG-READY");
  }
  while (Serial1.available()) {
    Serial.write(Serial1.read());
  }
}
