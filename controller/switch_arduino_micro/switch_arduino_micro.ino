#include "src/SwitchJoystick.h"
#include <stdlib.h>

// Protocol v2: ASCII payload, comma, CRC-16/CCITT-FALSE, newline.
// Lease and partial-line limits use unsigned elapsed time to tolerate millis wrap.
SwitchJoystick_ pad;
char line[160]; uint8_t length = 0; bool discard = false;
unsigned long started = 0, renewed = 0;
const unsigned long LEASE_MS = 2000, LINE_MS = 500;
uint32_t session = 0, retired = 0, sequence = 0;
bool active = false, haveSequence = false, expired = false;
char lastState[96] = "";
char lastOperation[6] = "";
bool timedRunning = false;
unsigned long timedStarted = 0, timedDuration = 0;
uint8_t timedRelease[7];
// Fixed-size, saturating diagnostics; reset only on Arduino restart.
uint32_t diagReceived = 0, diagRejected = 0, diagReplies = 0;
uint32_t diagCrc = 0, diagMalformed = 0, diagTimeout = 0, diagOverflow = 0;
uint32_t diagTimedSession = 0, diagTimedSequence = 0;
uint8_t diagTimedResult = 0;  // 0 none, 1 running, 2 done, 3 USB error, 4 expired
void increment(uint32_t &value) { if (value != 0xffffffffUL) ++value; }
void rejectMalformed() { increment(diagRejected); increment(diagMalformed); }
const char *timedResult() {
  switch (diagTimedResult) {
    case 1: return "RUNNING";
    case 2: return "DONE";
    case 3: return "USB";
    case 4: return "EXPIRED";
    default: return "NONE";
  }
}

uint16_t crc(const char *s) {
  uint16_t c = 0xffff;
  while (*s) { c ^= (uint16_t)(uint8_t)*s++ << 8; for (uint8_t i=0;i<8;i++) c = (c & 0x8000) ? (c << 1) ^ 0x1021 : c << 1; }
  return c;
}
void reply(const char *s) {
  increment(diagReplies);
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
  if (!sum || strlen(sum+1)!=4) { rejectMalformed(); return; }
  for (char *p=sum+1; *p; ++p) if (!((*p>='0'&&*p<='9')||(*p>='A'&&*p<='F'))) { rejectMalformed(); return; }
  uint16_t received = strtoul(sum+1, NULL, 16); *sum='\0'; if (crc(line)!=received) { increment(diagRejected); increment(diagCrc); return; }
  char *parts[17]; uint8_t count=0; char *p=line;
  while (p && count<17) { parts[count++]=p; char *comma=strchr(p, ','); if (comma) { *comma='\0'; p=comma+1; } else p=NULL; }
  if (p || count<4 || strcmp(parts[0],"2")) { rejectMalformed(); return; }
  uint32_t sid, seq; if (!number(parts[1], 4294967295UL, sid) || !sid || !number(parts[2], 4294967295UL, seq)) { rejectMalformed(); return; }
  // Responses may be echoed back into Serial1. Never answer a response or
  // a malformed/unknown command: answering it can create an endless loop.
  bool validShape = (count==4 && (!strcmp(parts[3],"DIAG") || !strcmp(parts[3],"STATUS") ||
                     !strcmp(parts[3],"HELLO") || !strcmp(parts[3],"KEEP"))) ||
                    (count==10 && !strcmp(parts[3],"SET")) ||
                    (count==17 && !strcmp(parts[3],"TIMED"));
  if (!validShape) { rejectMalformed(); return; }
  increment(diagReceived);
  char response[128], diagnostic[96]; const char *result="ERROR";
  if (count==4 && !strcmp(parts[3],"DIAG")) {
    // The snapshot includes this request, but not its own reply.
    snprintf(diagnostic,sizeof(diagnostic),"%lu:%lu:%lu:%lu:%lu:%lu:%lu:%lu:%lu:%s",
             diagReceived,diagRejected,diagReplies,diagCrc,diagMalformed,diagTimeout,diagOverflow,
             diagTimedSession,diagTimedSequence,timedResult());
    snprintf(response,sizeof(response),"2,%lu,%lu,DIAG,%s",sid,seq,diagnostic);
    reply(response); return;
  }
  if (count==4 && !strcmp(parts[3],"STATUS")) result=active ? "ACTIVE" : (expired ? "EXPIRED" : "READY");
  else if (count==4 && !strcmp(parts[3],"HELLO")) {
    if (active && sid==session) result="ACTIVE";
    else if (!active && sid!=retired) { neutral(); session=sid; active=true; expired=false; haveSequence=false; timedRunning=false; renewed=millis(); result="ACTIVE"; }
    else result="SESSION";
  } else if (!active || sid!=session) result="SESSION";
  else if (count==4 && !strcmp(parts[3],"KEEP")) { renewed=millis(); result="ACTIVE"; }
  else if ((count==10 && !strcmp(parts[3],"SET")) || (count==17 && !strcmp(parts[3],"TIMED"))) {
    bool timed = !strcmp(parts[3], "TIMED");
    uint32_t values[13] = {}; bool valid=true;
    uint8_t n = timed ? 13 : 6;
    for (uint8_t i=0; i<n; i++) {
      uint8_t field = i % 6;
      uint32_t limit = i==12 ? 3000 : (field==0 ? 65535 : (field==1 ? 8 : 255));
      if (!number(parts[i+4], limit, values[i])) valid=false;
    }
    if (timed && !values[12]) valid=false;
    char state[96] = "";
    for (uint8_t i=0; i<n; i++) {
      size_t used = strlen(state);
      snprintf(state+used, sizeof(state)-used, i ? ",%lu" : "%lu", values[i]);
    }
    if (!valid) result="VALUE";
    else if (haveSequence && (seq<sequence || (seq==sequence && (strcmp(state,lastState) || strcmp(parts[3],lastOperation))))) result="SEQUENCE";
    else if (haveSequence && seq==sequence) result=timed ? (timedRunning ? "RUNNING" : "DONE") : "APPLIED";
    else if (timedRunning) result="BUSY";
    else {
      uint8_t data[]={(uint8_t)values[0],(uint8_t)(values[0]>>8),(uint8_t)values[1],(uint8_t)values[2],(uint8_t)values[3],(uint8_t)values[4],(uint8_t)values[5]};
      if (pad.sendState(data) == 8) {
        sequence=seq; haveSequence=true; strcpy(lastState,state); strcpy(lastOperation,parts[3]); renewed=millis();
        if (timed) {
          timedRelease[0]=values[6]; timedRelease[1]=values[6]>>8;
          for (uint8_t i=1;i<6;i++) timedRelease[i+1]=values[i+6];
          timedDuration=values[12]; timedStarted=millis(); timedRunning=true; result="RUNNING";
          diagTimedSession=sid; diagTimedSequence=seq; diagTimedResult=1;
        } else result="APPLIED";
      } else { neutral(); retired=session; active=false; expired=true; timedRunning=false; result="USB"; }
    }
  }
  snprintf(response,sizeof(response),"2,%lu,%lu,%s,%s",sid,seq,parts[3],result); reply(response);
}
void setup() { Serial1.begin(115200); pad.begin(false); neutral(); }
void loop() {
  unsigned long now=millis();
  if (active && now-renewed>=LEASE_MS) { if (timedRunning) diagTimedResult=4; neutral(); retired=session; active=false; expired=true; timedRunning=false; }
  if (active && timedRunning && now-timedStarted>=timedDuration) {
    if (pad.sendState(timedRelease) != 8) { diagTimedResult=3; neutral(); retired=session; active=false; expired=true; }
    else diagTimedResult=2;
    timedRunning=false;
  }
  // A timed-out prefix is already irrecoverable.  Reset immediately so the
  // following request need not donate its terminating newline to the discard.
  if (length && now-started>=LINE_MS) { increment(diagRejected); increment(diagTimeout); length=0; }
  if (Serial1.available()) {
    char c=Serial1.read();
    if (c=='\n') { if (!discard && length) { line[length]='\0'; command(); } length=0; discard=false; }
    else if (!discard) {
      // Seek a protocol-version prefix while idle.  This resynchronizes after
      // bytes that precede a complete request, without scanning inside one.
      if (!length) {
        if (c=='2') { line[length++]=c; started=millis(); }
        else rejectMalformed();
      } else if (length==1 && line[0]=='2' && c!=',') {
        rejectMalformed(); length=0;
        if (c=='2') { line[length++]=c; started=millis(); }
      } else if (length<sizeof(line)-1) line[length++]=c;
      else { increment(diagRejected); increment(diagOverflow); length=0; discard=true; }
    }
  }
}
