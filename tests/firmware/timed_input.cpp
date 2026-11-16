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
  std::string input;
  size_t position = 0;
  void begin(int) {}
  void print(const char* s) { output += s; }
  void print(char c) { output += c; }
  int available() { return position < input.size(); }
  char read() { return input[position++]; }
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
  length = strlen(line);
  command();
  length = 0;
}
std::string frame(const char* payload) {
  char encoded[180];
  snprintf(encoded, sizeof(encoded), "%s,%04X\n", payload, crc(payload));
  return encoded;
}
void receive(const std::string &bytes, unsigned long interval=1) {
  Serial1.input += bytes;
  while (Serial1.available()) { loop(); currentTime += interval; }
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
  assert(diagTimedResult == 4 && diagTimedSequence == 2);
  auto receivedBefore = diagReceived, repliesBefore = diagReplies;
  request("2,99,0,DIAG");
  assert(Serial1.output.find("DIAG,") != std::string::npos);
  assert(Serial1.output.find(":1:2:EXPIRED") != std::string::npos);
  assert(diagReceived == receivedBefore + 1 && diagReplies == repliesBefore + 1);
  // An echoed reply is never accepted as a request or answered again.
  std::string echoed = Serial1.output;
  assert(!echoed.empty() && echoed.back() == '\n');
  echoed.pop_back();
  snprintf(line, sizeof(line), "%s", echoed.c_str());
  Serial1.output.clear();
  auto repliesAfterDiag = diagReplies;
  auto rejectedEcho = diagRejected;
  length = strlen(line);
  command();
  length = 0;
  assert(Serial1.output.empty() && diagReplies == repliesAfterDiag);
  assert(diagRejected == rejectedEcho + 1);
  strcpy(line, "bad,0000");
  auto rejectedBefore = diagRejected;
  length = strlen(line);
  command();
  length = 0;
  assert(diagRejected == rejectedBefore + 1);
  diagReceived = 0xffffffffUL;
  increment(diagReceived);
  assert(diagReceived == 0xffffffffUL);

  // Feed the real loop one byte at a time, as Serial1 does on hardware.
  diagReceived = diagRejected = diagCrc = diagMalformed = diagTimeout = diagOverflow = diagNoise = 0;
  Serial1.output.clear();
  receive("x" + frame("2,77,0,STATUS"));
  assert(Serial1.output.find("2,77,0,STATUS,") != std::string::npos);
  assert(diagReceived == 1 && diagRejected == 0 && diagNoise == 1);

  // A partial line expires without consuming the newline of the next request.
  Serial1.output.clear();
  receive("2");
  currentTime += LINE_MS;
  loop();
  receive(frame("2,77,1,STATUS"));
  assert(Serial1.output.find("2,77,1,STATUS,") != std::string::npos);
  assert(diagReceived == 2 && diagTimeout == 1);

  // A normally split request remains valid, while a bad CRC is counted alone.
  Serial1.output.clear();
  receive(frame("2,77,2,STATUS"), 10);
  assert(diagReceived == 3 && diagTimeout == 1);
  std::string badCrc = frame("2,77,3,STATUS");
  badCrc[badCrc.size()-2] = '0';
  receive(badCrc);
  assert(diagReceived == 3 && diagCrc == 1);

  // An overlong line recovers after its deadline even when its newline is lost.
  receive("2," + std::string(158, 'x'));
  assert(diagOverflow == 1);
  currentTime += LINE_MS;
  loop();
  Serial1.output.clear();
  receive(frame("2,77,4,STATUS"));
  assert(Serial1.output.find("2,77,4,STATUS,") != std::string::npos);
  assert(diagReceived == 4);

  // Capture the raw frame before comma tokenization, including embedded NUL.
  std::string corrupt = frame("2,77,5,STATUS");
  corrupt[7] = '\0';
  auto idBefore = rejectedId;
  Serial1.output.clear();
  receive(corrupt);
  assert(Serial1.output.empty() && rejectedId == idBefore + 1);
  assert(rejectedLength == corrupt.size()-1);
  assert(!memcmp(rejectedBytes, corrupt.data(), rejectedLength));
  auto savedId = rejectedId;
  request("2,77,6,DUMP,0,0");
  assert(Serial1.output.find(",DUMP,") != std::string::npos);
  assert(Serial1.output.find("00") != std::string::npos);
  assert(rejectedId == savedId);
  std::string dumpEcho = Serial1.output;
  Serial1.output.clear(); receive(dumpEcho);
  assert(Serial1.output.empty());

  // A maximum-size captured line can be reconstructed across five chunks.
  std::string longBad = "2," + std::string(152, 'A') + ",0000\n";
  receive(longBad);
  assert(rejectedLength == 159);
  std::string reconstructed;
  savedId = rejectedId;
  for (unsigned offset=0; offset<159; offset+=32) {
    char payload[80];
    snprintf(payload,sizeof(payload),"2,4294967295,4294967295,DUMP,%lu,%u",(unsigned long)savedId,offset);
    request(payload);
    assert(Serial1.output.size() <= 160);
    size_t begin = Serial1.output.find(",DUMP,") + 6;
    for (int i=0; i<3; ++i) begin=Serial1.output.find(':',begin)+1;
    size_t end=Serial1.output.find(',',begin);
    for (size_t i=begin; i<end; i+=2) reconstructed += (char)strtoul(Serial1.output.substr(i,2).c_str(),NULL,16);
  }
  assert(reconstructed == longBad.substr(0,159));
  receive(corrupt);
  char stale[80];
  snprintf(stale,sizeof(stale),"2,77,10,DUMP,%lu,32",(unsigned long)savedId);
  request(stale);
  assert(Serial1.output.find(",DUMP,STALE,") != std::string::npos);
  request("2,77,11,DUMP,0,1");
  assert(Serial1.output.find(",DUMP,STALE,") != std::string::npos);
  savedId = rejectedId;
  // CRC-valid embedded NUL is malformed and cannot execute the prefix command.
  std::string binaryPayload("2,77,12,STATUS\0ignored", 22);
  char checksum[8];
  snprintf(checksum,sizeof(checksum),",%04X\n",crcBytes(binaryPayload.data(),binaryPayload.size()));
  Serial1.output.clear(); receive(binaryPayload + checksum);
  assert(Serial1.output.empty() && rejectedId == savedId);
  // Saturation freezes the record rather than reusing its identifier.
  rejectedId = 0xffffffffUL;
  std::string oldRecord((char*)rejectedBytes,rejectedLength);
  receive(longBad);
  assert(rejectedId == 0xffffffffUL);
  assert(std::string((char*)rejectedBytes,rejectedLength) == oldRecord);
}
