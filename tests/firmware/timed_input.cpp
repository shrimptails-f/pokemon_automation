#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <string>
#include <vector>

unsigned long currentTime = 0;
unsigned long millis() { return currentTime; }
struct SerialStub {
  std::string output;
  void begin(int) {}
  void print(const char* s) { output += s; }
  void print(char c) { output += c; }
  int available() { return 0; }
  char read() { return 0; }
} Serial1;
struct SwitchJoystick_ {
  std::vector<std::vector<uint8_t>> states;
  bool fail = false;
  void begin(bool) {}
  int sendState(uint8_t* data) {
    states.emplace_back(data, data + 7);
    return fail ? 0 : 8;
  }
};
#include <stdlib.h>

// SKETCH

void request(const char* payload) {
  snprintf(line, sizeof(line), "%s,%04X", payload, crc(payload));
  Serial1.output.clear();
  command();
}
int main() {
  request("2,1,0,HELLO");
  assert(active);
  request("2,1,1,TIMED,4096,8,128,128,128,128,0,8,128,128,128,128,150");
  assert(timedRunning && pad.states.back()[1] == 16);
  size_t count = pad.states.size();
  currentTime = 100;
  request("2,1,1,TIMED,4096,8,128,128,128,128,0,8,128,128,128,128,150");
  assert(Serial1.output.find("RUNNING") != std::string::npos && pad.states.size() == count);
  request("2,1,1,TIMED,4096,8,128,128,128,128,0,8,128,128,128,128,151");
  assert(Serial1.output.find("SEQUENCE") != std::string::npos);
  request("2,1,2,SET,0,8,128,128,128,128");
  assert(Serial1.output.find("BUSY") != std::string::npos);
  currentTime = 150; loop();
  assert(!timedRunning && pad.states.back()[1] == 0);
  count = pad.states.size();
  request("2,1,1,TIMED,4096,8,128,128,128,128,0,8,128,128,128,128,150");
  assert(Serial1.output.find("DONE") != std::string::npos && pad.states.size() == count);
  request("2,1,2,TIMED,4,8,128,128,128,128,0,8,128,128,128,128,3000");
  currentTime += 2001; loop();
  assert(expired && !active && !timedRunning && pad.states.back()[0] == 0);
}
