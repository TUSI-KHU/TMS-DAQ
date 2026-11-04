// TUSI TMS ignition signal monitor for Arduino Nano.
// The Nano only observes the externally pulled-down ignition signal.

#include <Arduino.h>

constexpr uint8_t IGNITION_PIN = 5;
constexpr unsigned long DEBOUNCE_MS = 20;
constexpr unsigned long HEARTBEAT_MS = 500;
constexpr size_t COMMAND_BUFFER_SIZE = 64;

bool armed = false;
bool rawState = LOW;
bool stableState = LOW;
unsigned long rawChangedAt = 0;
unsigned long lastHeartbeatAt = 0;
uint32_t sequenceNumber = 0;
char commandBuffer[COMMAND_BUFFER_SIZE];
size_t commandLength = 0;

void sendHeartbeat(unsigned long now) {
  Serial.print(F("HB,"));
  Serial.print(++sequenceNumber);
  Serial.print(',');
  Serial.print(now);
  Serial.print(',');
  Serial.println(stableState == HIGH ? 1 : 0);
}

void sendState(unsigned long now) {
  Serial.print(F("STATE,"));
  Serial.print(++sequenceNumber);
  Serial.print(',');
  Serial.print(now);
  Serial.print(',');
  Serial.println(stableState == HIGH ? 1 : 0);
}

void sendTrigger(unsigned long now) {
  Serial.print(F("TRIGGER,"));
  Serial.print(++sequenceNumber);
  Serial.print(',');
  Serial.println(now);
}

void handleCommand(const char *command) {
  constexpr char ARM_PREFIX[] = "ARM,";
  if (strncmp(command, ARM_PREFIX, sizeof(ARM_PREFIX) - 1) != 0) {
    return;
  }

  const char *sessionId = command + sizeof(ARM_PREFIX) - 1;
  if (*sessionId == '\0') {
    return;
  }

  armed = true;
  Serial.print(F("ARMED,"));
  Serial.println(sessionId);
  // Report the present level even if HIGH predates ARM. This is a snapshot,
  // not a newly observed rising edge and must not generate a TRIGGER.
  sendState(millis());
}

void readCommands() {
  while (Serial.available() > 0) {
    const char value = static_cast<char>(Serial.read());
    if (value == '\r') {
      continue;
    }
    if (value == '\n') {
      commandBuffer[commandLength] = '\0';
      if (commandLength > 0) {
        handleCommand(commandBuffer);
      }
      commandLength = 0;
      continue;
    }
    if (commandLength + 1 < COMMAND_BUFFER_SIZE) {
      commandBuffer[commandLength++] = value;
    } else {
      commandLength = 0;
    }
  }
}

void updateIgnition(unsigned long now) {
  const bool current = digitalRead(IGNITION_PIN);
  if (current != rawState) {
    rawState = current;
    rawChangedAt = now;
  }

  if (current != stableState && now - rawChangedAt >= DEBOUNCE_MS) {
    const bool previous = stableState;
    stableState = current;
    if (previous == LOW && stableState == HIGH && armed) {
      sendTrigger(now);
      armed = false;
    }
    // Continue reporting both edges after the legacy TRIGGER has latched.
    sendState(now);
  }
}

void setup() {
  pinMode(IGNITION_PIN, INPUT);  // External 4.7 kOhm pull-down.
  Serial.begin(115200);
  rawState = digitalRead(IGNITION_PIN);
  stableState = rawState;
  rawChangedAt = millis();
  lastHeartbeatAt = millis();
  Serial.println(F("HELLO,1.2"));
}

void loop() {
  readCommands();
  const unsigned long now = millis();
  updateIgnition(now);
  if (now - lastHeartbeatAt >= HEARTBEAT_MS) {
    lastHeartbeatAt = now;
    sendHeartbeat(now);
  }
}
