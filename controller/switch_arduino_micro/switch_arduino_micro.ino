#include "src/SwitchJoystick.h"
#include <stdlib.h>

// Protocol v1: ASCII payload, comma, CRC-16/CCITT-FALSE, newline.
// Lease and partial-line limits use unsigned elapsed time to tolerate millis wrap.
SwitchJoystick_ pad;
char line[128]; uint8_t length = 0; bool discard = false;
unsigned long started = 0, renewed = 0;
const unsigned long LEASE_MS = 2000, LINE_MS = 500;
uint32_t session = 0, retired = 0, sequence = 0;
bool active = false, haveSequence = false, expired = false;
char lastState[48] = "";

uint16_t crc(const char *s) {
  uint16_t c = 0xffff;
  while (*s) { c ^= (uint16_t)(uint8_t)*s++ << 8; for (uint8_t i=0;i<8;i++) c = (c & 0x8000) ? (c << 1) ^ 0x1021 : c << 1; }
  return c;
}
void reply(const char *s) {
  char suffix[7]; snprintf(suffix, sizeof(suffix), ",%04X", crc(s));
  Serial1.print(s); Serial1.print(suffix); Serial1.print('\n');
}
void neutral() {
  uint8_t data[] = {0,0,8,128,128,128,128}; pad.sendState(data);
}
bool number(const char *s, uint32_t max, uint32_t &out) {
  if (!s || !*s) return false;
  uint32_t n=0; while (*s) { if (*s<'0'||*s>'9') return false; uint8_t d=*s++-'0'; if (n > max/10 || (n == max/10 && d > max%10)) return false; n=n*10+d; }
  out=n; return true;
}
void command() {
  char *sum = strrchr(line, ',');
  if (!sum || strlen(sum+1)!=4) return;
  for (char *p=sum+1; *p; ++p) if (!((*p>='0'&&*p<='9')||(*p>='A'&&*p<='F'))) return;
  uint16_t received = strtoul(sum+1, NULL, 16); *sum='\0'; if (crc(line)!=received) return;
  char *parts[10]; uint8_t count=0; char *p=line;
  while (p && count<10) { parts[count++]=p; char *comma=strchr(p, ','); if (comma) { *comma='\0'; p=comma+1; } else p=NULL; }
  if (p || count<3 || strcmp(parts[0],"1")) return;
  uint32_t sid, seq; if (!number(parts[1], 4294967295UL, sid) || !sid || !number(parts[2], 4294967295UL, seq)) return;
  char response[80]; const char *result="ERROR";
  if (count==4 && !strcmp(parts[3],"STATUS")) result=active ? "ACTIVE" : (expired ? "EXPIRED" : "READY");
  else if (count==4 && !strcmp(parts[3],"HELLO")) {
    if (active && sid==session) result="ACTIVE";
    else if (!active && sid!=retired) { neutral(); session=sid; active=true; expired=false; haveSequence=false; renewed=millis(); result="ACTIVE"; }
    else result="SESSION";
  } else if (!active || sid!=session) result="SESSION";
  else if (count==4 && !strcmp(parts[3],"KEEP")) { renewed=millis(); result="ACTIVE"; }
  else if (count==10 && !strcmp(parts[3],"SET")) {
    uint32_t values[6] = {}; bool valid=true;
    for (uint8_t i=0;i<6;i++) if (!number(parts[i+4], i==0 ? 65535 : (i==1 ? 8 : 255), values[i])) valid=false;
    char state[48]; snprintf(state,sizeof(state),"%lu,%lu,%lu,%lu,%lu,%lu",values[0],values[1],values[2],values[3],values[4],values[5]);
    if (!valid) result="VALUE";
    else if (haveSequence && (seq<sequence || (seq==sequence && strcmp(state,lastState)))) result="SEQUENCE";
    else { uint8_t data[]={(uint8_t)values[0],(uint8_t)(values[0]>>8),(uint8_t)values[1],(uint8_t)values[2],(uint8_t)values[3],(uint8_t)values[4],(uint8_t)values[5]}; if (pad.sendState(data) == 8) { sequence=seq; haveSequence=true; strcpy(lastState,state); renewed=millis(); result="APPLIED"; } else { neutral(); retired=session; active=false; expired=true; result="USB"; } }
  }
  snprintf(response,sizeof(response),"1,%lu,%lu,%s,%s",sid,seq,parts[3],result); reply(response);
}
void setup() { Serial1.begin(115200); pad.begin(false); neutral(); }
void loop() {
  unsigned long now=millis();
  if (active && now-renewed>=LEASE_MS) { neutral(); retired=session; active=false; expired=true; }
  if (length && now-started>=LINE_MS) { length=0; discard=true; }
  while (Serial1.available()) {
    char c=Serial1.read();
    if (c=='\n') { if (!discard && length) { line[length]='\0'; command(); } length=0; discard=false; }
    else if (!discard) { if (!length) started=millis(); if (length<sizeof(line)-1) line[length++]=c; else { length=0; discard=true; } }
  }
}
