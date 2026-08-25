# TUSI TMS Software — Codex 구현 인수인계 문서

## 0. 문서 목적

본 문서는 TUSI 로켓 엔진 지상시험용 TMS(Test/Telemetry Measurement System) 소프트웨어의 구현 지침이다.

이번 단계에서 전체 시스템 구조와 요구사항은 이미 결정되어 있다. Codex는 새로운 아키텍처를 제안하거나 시스템을 불필요하게 복잡하게 만들지 말고, 아래 설계를 그대로 구현하는 것을 목표로 한다.

특히 SSH 인증은 **SSH Key를 사용하지 않고 ID/Password 기반 인증을 사용한다.**

본 시스템의 Raspberry Pi는 시험장 내부의 Laptop과 60 m Ethernet으로 직접 연결되는 폐쇄형 네트워크에서 사용되며 인터넷이나 외부 네트워크에 공개할 목적이 없다.

---

# 1. 시스템 구성

하드웨어 구성:

```text
Ignition Box
    │
    ├──> Rocket Engine Ignition
    │
    └──> 5V Stepdown
              │
              ▼
         Arduino Nano
              │
          USB Serial
              │
              ▼
           Laptop
              │
              │ 60 m Ethernet
              │ SSH Tunnel
              ▼
       Raspberry Pi 4B
        Ubuntu 22.04
              │
              │ USB
              ▼
         Advantech
          USB-4704
           /     \
          /       \
      Thrust     Pressure
      Sensor      Sensor
```

Raspberry Pi용 USB-4704 DAQ 드라이버 포팅은 이미 완료되어 있다.

Codex는 드라이버 포팅 작업을 다시 하지 않는다.

---

# 2. 최종 소프트웨어 구성

실행 단위는 최대한 단순하게 유지한다.

```text
1. nano_trigger
   Arduino Nano firmware

2. tms-agent
   Raspberry Pi acquisition/logging/telemetry daemon

3. tms-dashboard
   Laptop GUI application
```

사용자가 실제로 직접 실행해야 하는 프로그램은 원칙적으로:

```text
TUSI TMS Dashboard
```

하나뿐이어야 한다.

Pi에서는 `tms-agent`를 systemd service로 자동 실행한다.

---

# 3. 핵심 설계 원칙

다음 원칙을 반드시 지킨다.

### 3.1 KISS

시스템을 필요 이상으로 추상화하거나 서비스 수를 늘리지 않는다.

금지 예:

```text
ManagerFactory
ControllerInterface
ServiceRegistry
EventBus framework
microservice architecture
database server
message broker
Docker orchestration
```

이 프로젝트에는 필요 없다.

읽기 쉬운 Python/C/C++ 코드와 명확한 module 분리 정도면 충분하다.

---

### 3.2 Pi Local Logging이 최우선

시험 중 데이터의 authoritative copy는 Raspberry Pi의 로그다.

```text
DAQ
 ↓
Pi acquisition
 ↓
Pi local logging
```

이 경로는 다음과 독립적이어야 한다.

```text
Nano
Laptop
GUI
SSH
Ethernet
Telemetry
```

따라서:

```text
Nano disconnect     → logging 계속
Laptop crash        → logging 계속
GUI crash           → logging 계속
Ethernet disconnect → logging 계속
SSH disconnect      → logging 계속
```

이어야 한다.

---

### 3.3 Trigger 전에 이미 Logging 중이어야 한다

점화 Trigger는 DAQ 시작 명령이 아니다.

정상 흐름:

```text
측정 준비
   ↓
DAQ acquisition 시작
   ↓
Pi logging 시작
   ↓
계속 기록
   ↓
Nano Trigger
   ↓
점화 시점 기록
   ↓
계속 기록
```

Nano가 동작하지 않더라도 측정 데이터는 끝까지 남아야 한다.

---

# 4. 점화 시점 정의

점화 시점의 기준은 **Arduino Nano에서 감지한 ignition GPIO rising edge**로 한다.

별도의 USB-4704 trigger channel이나 PTP/NTP hardware synchronization은 추가하지 않는다.

수 ms 수준의 serial/network latency는 본 시스템의 허용 범위이다.

흐름:

```text
Ignition Switch
      ↓
Nano GPIO HIGH
      ↓
Nano detects rising edge
      ↓
USB Serial
      ↓
Laptop TMS Dashboard
      ↓
TRIGGER message
      ↓
SSH tunnel
      ↓
Pi tms-agent
      ↓
현재 DAQ sample index를 trigger_sample로 기록
```

시간축:

```text
t = (sample_index - trigger_sample) / sample_rate
```

Pi가 Trigger packet을 받은 시점에서 가장 가까운 acquisition sample index를 `trigger_sample`로 기록한다.

GUI 또한 해당 `trigger_sample`을 T=0으로 사용한다.

---

# 5. Arduino Nano Firmware

Nano firmware의 역할은 최대한 단순하게 한다.

```text
GPIO input
    ↓
debounce
    ↓
rising edge detection
    ↓
serial trigger
```

추가로 Nano 연결 상태 확인을 위한 heartbeat를 제공한다.

Nano는 ignition을 제어하지 않는다.

Nano는 ignition switch의 상태만 읽는다.

---

## 5.1 GPIO

외부 4.7 kΩ pull-down을 사용하는 구조다.

따라서 GPIO는 일반 `INPUT`으로 사용한다.

```text
LOW  = ignition inactive
HIGH = ignition signal detected
```

---

## 5.2 Trigger latch

한 시험 session에서는 Trigger를 한 번만 발생시킨다.

개념:

```text
armed = true

if rising_edge and armed:
    send_trigger()
    armed = false
```

새로운 measurement session이 시작되면 다시 armed 상태가 된다.

---

## 5.3 Serial Protocol

프로토콜은 사람이 터미널에서도 읽을 수 있는 ASCII 기반으로 한다.

예:

```text
HELLO,1.0
HB,101,50000,0
HB,102,50500,0
TRIGGER,103,50731
HB,104,51000,1
```

Heartbeat format:

```text
HB,<sequence>,<uptime_ms>,<gpio_state>
```

Trigger format:

```text
TRIGGER,<sequence>,<uptime_ms>
```

Baudrate:

```text
115200
```

Heartbeat 주기:

```text
500 ms
```

정도를 기본값으로 한다.

---

# 6. Raspberry Pi — tms-agent

환경:

```text
Raspberry Pi 4B
Ubuntu 22.04
USB-4704 driver already ported
```

`tms-agent`가 다음 기능을 담당한다.

```text
DAQ acquisition
buffer management
logging
telemetry
trigger handling
health monitoring
configuration
```

---

# 7. DAQ Acquisition

USB-4704에서 sample 하나씩 polling하지 않는다.

금지:

```text
read()
sleep()
read()
sleep()
```

반드시 포팅된 driver가 제공하는 buffered acquisition / DMA 경로를 이용한다.

전체 흐름:

```text
USB-4704
    │
hardware sampling
    │
    ▼
Driver DMA / USB Buffer
    │
    ▼
Acquisition Worker
    │
    ▼
Application Ring Buffer
    │
    ├──> Logger
    │
    └──> Telemetry
```

---

## 7.1 Block acquisition

DAQ data는 block 단위로 처리한다.

예:

```text
Sample rate = 5000 Hz

Block:
    50 samples
    10 ms
```

각 block metadata 예:

```text
sequence
first_sample_index
sample_count
sample_rate
channel_count
raw sensor data
```

실제 block size는 configuration에서 조절 가능하게 하되 일반 사용자는 수정할 필요가 없어야 한다.

기본:

```text
block_ms = 10
```

정도를 사용한다.

---

# 8. Buffer 정책

application-level ring buffer를 둔다.

권장:

```text
5 seconds
```

정도의 raw acquisition data를 유지한다.

역할:

```text
1. Disk writer 순간 지연 흡수
2. Network 순간 지연 흡수
3. Trigger 이전 데이터 GUI 표시
```

우선순위:

```text
DAQ Acquisition
    >
Local Logging
    >
Network Telemetry
    >
GUI Rendering
```

Network 또는 GUI가 느려지는 경우 acquisition thread를 기다리게 하면 안 된다.

Telemetry frame은 필요한 경우 drop 가능하지만 local log는 최대한 보존한다.

---

# 9. Thread 구조

처음에는 단순한 thread architecture를 사용한다.

```text
Main
 │
 ├── Acquisition Thread
 ├── Logger Thread
 ├── Network Thread
 └── Health Thread
```

대략적인 data flow:

```text
             USB4704
                │
                ▼
       Acquisition Thread
                │
                ▼
           Ring Buffer
             /     \
            /       \
           ▼         ▼
       Logger      Network
       Thread      Thread
```

필요하지 않으면 multiprocessing을 사용하지 않는다.

---

# 10. Raspberry Pi Logging

한 시험은 하나의 session으로 관리한다.

권장 파일:

```text
YYYY-MM-DD_TESTNAME_NUMBER.h5
```

예:

```text
2026-08-23_KNSB_TEST_003.h5
```

HDF5를 기본 저장 포맷으로 사용한다.

---

## 10.1 HDF5 기본 구조

```text
/metadata

/samples
    raw_thrust
    raw_pressure
    thrust_N
    pressure_bar

/events

/health
```

metadata에는 최소한 다음을 기록한다.

```text
test_name
session_id
start_time
sample_rate
DAQ configuration
sensor calibration
software version
```

Trigger event에는:

```text
event_type = ignition
trigger_sample
receive_time
```

등을 기록한다.

---

# 11. Measurement Session

`tms-agent` 자체는 Pi boot 시 자동 실행한다.

하지만 실제 DAQ recording은 Dashboard에서:

```text
측정 준비
```

를 눌렀을 때 시작한다.

흐름:

```text
Pi Boot
 ↓
tms-agent.service
 ↓
READY
 ↓

Laptop:
[측정 준비]

 ↓

START_SESSION

 ↓

DAQ acquisition
+
HDF5 logging

 ↓

RECORDING
```

이후 Laptop이 죽어도 session은 Pi에서 계속 진행되어야 한다.

---

# 12. Laptop — TMS Dashboard

지원 OS:

```text
Windows
Linux
```

가능한 한 동일한 Python codebase를 사용한다.

GUI:

```text
PySide6
```

실시간 graph:

```text
pyqtgraph
```

Serial:

```text
pyserial
```

SSH:

```text
asyncssh
```

등을 사용할 수 있다.

---

# 13. SSH 정책 — 중요

## SSH Key를 사용하지 않는다.

본 시스템의 SSH는 반드시:

```text
IP
Username
Password
```

기반으로 접속할 수 있어야 한다.

예:

```text
Pi IP:       192.168.50.2
SSH Port:    22
SSH ID:      tms
SSH Password: ********
```

SSH key generation, ssh-agent, public key installation 등을 사용자에게 요구하지 않는다.

---

# 14. Raspberry Pi SSH Server

Ubuntu 22.04의 OpenSSH server를 사용한다.

Pi에는 TMS 전용 user를 하나 사용하는 것을 권장한다.

예:

```text
username: tms
```

해당 계정에 password를 설정한다.

SSH server는 password login을 허용하도록 구성한다.

필요 설정 예:

```text
PasswordAuthentication yes
```

설정 변경 후 sshd를 restart한다.

인터넷에 공개할 시스템이 아니므로 본 프로젝트에서는 password authentication을 정상적인 운용 방식으로 취급한다.

---

# 15. Laptop SSH Client

Dashboard 내부에서 SSH 연결을 자동으로 수행한다.

사용자가 command line에서:

```text
ssh ...
```

를 입력하게 만들지 않는다.

전체 과정:

```text
Dashboard
   ↓
read SSH settings
   ↓
connect using username + password
   ↓
create SSH tunnel
   ↓
connect telemetry socket
```

---

# 16. SSH Tunnel

Pi의 `tms-agent` telemetry server는 가능하면:

```text
127.0.0.1:<TMS_PORT>
```

에만 bind한다.

예:

```text
Pi:
127.0.0.1:29100
```

Laptop Dashboard가 SSH local forwarding을 생성한다.

논리적으로:

```text
Laptop
127.0.0.1:29100
      │
      │ SSH Tunnel
      ▼
Pi
127.0.0.1:29100
```

Dashboard의 telemetry client는 항상 localhost를 사용한다.

이를 통해 Windows/Linux networking 차이를 최소화한다.

---

# 17. SSH Authentication 구현

`asyncssh` 등을 사용할 경우 반드시 password 기반 인증을 사용한다.

개념적으로 필요한 값:

```text
host
port
username
password
```

SSH private key를 요구하지 않는다.

다음 기능도 필요하다.

```text
connect
disconnect
keepalive
automatic reconnect
connection timeout
authentication failure reporting
```

---

# 18. SSH Password GUI

Setup 화면에 다음 항목을 제공한다.

```text
Raspberry Pi

IP Address      [ 192.168.50.2 ]
SSH Port        [ 22           ]
SSH ID          [ tms          ]
SSH Password    [ ************ ]
```

Password field는 반드시 GUI에서 masked input으로 표시한다.

추가 옵션:

```text
[✓] 비밀번호 저장
```

을 둘 수 있다.

비전공자가 매 시험마다 SSH password를 다시 입력할 필요가 없도록 기본적으로 저장 기능을 지원하는 것이 좋다.

---

# 19. Password 저장 정책

시스템을 불필요하게 복잡하게 만들기 위해 OS keyring 같은 별도 credential framework를 필수화하지 않는다.

간단한 local configuration 방식으로 충분하다.

단:

* GUI에는 password를 masked 처리한다.
* 일반 log에 password를 절대 출력하지 않는다.
* exception message에도 password를 포함하지 않는다.
* debug dump에도 password를 넣지 않는다.
* Linux에서는 config file permission을 가능한 경우 user-only로 제한한다.
* Git repository에 실제 password가 들어간 config 파일을 commit하지 않는다.

repository에는:

```text
config.example.yaml
```

만 둔다.

실제:

```text
config.yaml
```

은 `.gitignore`에 포함한다.

---

# 20. SSH 오류 표시

GUI에는 technical traceback 대신 사람이 이해할 수 있는 메시지를 보여준다.

예:

```text
SSH 연결 실패

Raspberry Pi에 로그인할 수 없습니다.

확인:
1. LAN 케이블 연결
2. Raspberry Pi 전원
3. Pi IP 주소
4. SSH ID
5. SSH Password
```

인증 실패라면:

```text
SSH 인증 실패

ID 또는 Password를 확인하십시오.
```

등으로 명확히 구분한다.

Python traceback은 Advanced Log에서만 보여준다.

---

# 21. SSH Reconnect

Ethernet cable이 순간적으로 끊길 수 있으므로 자동 reconnect를 구현한다.

예:

```text
connection lost
 ↓
1 sec
 ↓
retry

failure
 ↓
2 sec
 ↓
retry

failure
 ↓
5 sec
 ↓
retry
```

최대 backoff는 약 10초 정도면 충분하다.

SSH reconnect가 진행되는 동안에도:

```text
Pi DAQ
Pi logging
```

은 계속되어야 한다.

GUI:

```text
SSH ● Reconnecting
```

정도로 표시한다.

---

# 22. Nano Serial Manager

Laptop Dashboard 내부 module로 구현한다.

기능:

```text
serial port detection
connection
heartbeat parsing
trigger parsing
automatic reconnect
Nano health
```

Windows:

```text
COMx
```

Linux:

```text
/dev/ttyUSBx
/dev/ttyACMx
```

차이는 pyserial layer에서 처리한다.

GUI에서는:

```text
Nano Port: AUTO
```

를 기본값으로 한다.

필요한 경우 manual selection도 가능하게 한다.

---

# 23. Trigger 처리

Nano trigger 수신 시:

```text
Nano
 ↓
SerialManager
 ↓
TriggerManager
 ↓
GUI trigger latch
 ↓
Pi에 TRIGGER message 즉시 전송
 ↓
Pi current sample index 기록
 ↓
Pi ACK
 ↓
Dashboard T=0 설정
```

Trigger는 한 session에 한 번만 인정한다.

---

# 24. Pi ↔ Laptop Protocol

SSH tunnel 위의 TCP connection 하나를 사용한다.

불필요하게 여러 socket/service를 만들지 않는다.

message type:

```text
HELLO
HEALTH
START_SESSION
STOP_SESSION
DAQ_DATA
TRIGGER
TRIGGER_ACK
CONFIG
ACK
ERROR
```

정도면 충분하다.

---

# 25. DAQ Data 전송

sample 하나씩 network packet으로 보내지 않는다.

block 단위로 보낸다.

예:

```text
DAQ_DATA

sequence
first_sample
sample_rate
sample_count
thrust data
pressure data
```

control message는 사람이 이해하기 쉬운 구조를 사용하되 대량 sample data는 binary array로 전송한다.

JSON float array로 수천 개 sample을 문자열화하지 않는다.

---

# 26. Dashboard UI

Dashboard는 비전공자에게 인수인계할 수 있는 수준으로 단순해야 한다.

첫 화면 예:

```text
┌─────────────────────────────────────────────┐
│                TUSI TMS                     │
├─────────────────────────────────────────────┤
│ SYSTEM STATUS                               │
│                                             │
│ Nano        ● Connected                     │
│ LAN         ● Connected                     │
│ SSH         ● Connected                     │
│ Raspberry   ● Connected                     │
│ DAQ         ● Running                       │
│ Logger      ● Recording                     │
│ Storage     ● OK                            │
├─────────────────────────────────────────────┤
│                                             │
│ Test Name [ KNSB_TEST_003              ]    │
│                                             │
│       [ 측정 준비 ]   [ 측정 종료 ]        │
│                                             │
│             STATUS : ARMED                  │
│                                             │
├─────────────────────────────────────────────┤
│                 THRUST                      │
│                                             │
│              realtime graph                 │
│                                             │
├─────────────────────────────────────────────┤
│                PRESSURE                     │
│                                             │
│              realtime graph                 │
│                                             │
├────────────────────┬────────────────────────┤
│ Current Thrust     │ Current Pressure       │
│ Peak Thrust        │ Peak Pressure          │
│                    │                        │
│ T+                 │ Sample Rate            │
└────────────────────┴────────────────────────┘
```

---

# 27. GUI Tabs

최대 4개 정도로 유지한다.

```text
Dashboard
Setup
System Test
Logs
```

---

## Dashboard

실제 시험 운용 화면.

표시:

```text
Nano
LAN
SSH
Pi
DAQ
Logger
Disk

Thrust graph
Pressure graph

Current thrust
Peak thrust
Current pressure
Peak pressure
T+
Sample rate
```

---

## Setup

일반 설정:

```text
Nano Port

Pi IP
SSH Port
SSH ID
SSH Password

Sample Rate

Thrust Channel
Thrust Scale
Thrust Offset

Pressure Channel
Pressure Scale
Pressure Offset

Log Directory
```

일반 사용자가 YAML을 직접 수정할 필요가 없어야 한다.

---

## System Test

버튼 하나:

```text
[ 전체 시스템 점검 ]
```

결과:

```text
Nano ............. PASS
LAN .............. PASS
SSH .............. PASS
Pi Agent ......... PASS
USB4704 .......... PASS
DAQ Stream ....... PASS
Thrust Channel ... PASS
Pressure Channel . PASS
Storage .......... PASS
```

SSH 검사에는:

```text
TCP port 22 reachable
username/password authentication successful
SSH tunnel successful
```

을 포함한다.

---

## Logs

시험 session 목록과 최소 기능만 제공한다.

```text
시험 선택

[폴더 열기]
[CSV 내보내기]
[Pi 로그 가져오기]
```

---

# 28. Health 상태

색상 의미:

```text
GREEN   정상
YELLOW  주의 / reconnecting
RED     오류
GRAY    비활성
```

예:

```text
Nano      ● Connected
SSH       ● Connected
Pi        ● Connected
DAQ       ● 5.00 kS/s
Logger    ● Recording
```

오류 시:

```text
Nano      ● Disconnected
SSH       ● Reconnecting
```

처럼 보여준다.

---

# 29. State Machine

불필요하게 많은 상태를 만들지 않는다.

```text
DISCONNECTED
      ↓
READY
      ↓
RECORDING
      ↓
TRIGGERED
      ↓
COMPLETE
```

세부 장치 오류는 state를 늘리지 말고 health flag로 관리한다.

예:

```text
state = RECORDING

health.nano = FAILED
health.ssh = OK
health.daq = OK
health.logger = OK
```

Nano failure 때문에 전체 state를 ERROR로 바꾸면 안 된다.

---

# 30. Configuration

개념적인 configuration:

```yaml
system:
  pi_host: 192.168.50.2

ssh:
  port: 22
  username: tms
  password: ""
  remember_password: true

nano:
  port: auto
  baudrate: 115200

daq:
  sample_rate: 5000
  block_ms: 10

channels:
  thrust:
    channel: 0
    scale: ...
    offset: ...

  pressure:
    channel: 1
    scale: ...
    offset: ...

logging:
  ring_buffer_sec: 5
```

실제 password가 들어간 파일은 repository에 commit하지 않는다.

---

# 31. Repository 구조

과도하게 파일을 분리하지 않는다.

```text
tusi-tms/
│
├── firmware/
│   └── nano/
│       └── nano_trigger.ino
│
├── pi/
│   ├── tms_agent.py
│   ├── daq.py
│   ├── logger.py
│   ├── telemetry.py
│   └── service/
│
├── laptop/
│   ├── main.py
│   ├── nano.py
│   ├── ssh_client.py
│   ├── telemetry.py
│   ├── health.py
│   └── gui/
│
├── common/
│   ├── protocol.py
│   └── config.py
│
├── tests/
│
├── config.example.yaml
├── README.md
└── .gitignore
```

---

# 32. Pi systemd

Pi 설치 후:

```text
tms-agent.service
```

를 등록한다.

Pi boot:

```text
Ubuntu boot
 ↓
network
 ↓
tms-agent.service
 ↓
READY
```

사용자가 Pi terminal을 직접 조작할 필요가 없어야 한다.

---

# 33. Windows / Linux 지원

Laptop code는 가능한 한 완전히 동일하게 사용한다.

OS-specific 부분을 최소화한다.

특히 SSH는 external command:

```text
ssh
plink
powershell
```

등에 의존하지 말고 Python SSH library를 사용하는 것을 우선한다.

그러면 Windows/Linux 모두:

```text
host
username
password
```

만으로 동일한 connection code를 사용할 수 있다.

---

# 34. Packaging

최종적으로 일반 운영자는 Python 환경을 직접 관리하지 않는 방향을 목표로 한다.

Windows:

```text
TUSI-TMS.exe
```

Linux:

```text
tusi-tms
```

또는 간단한 launcher.

사용자 절차는:

```text
1. Raspberry Pi 전원 ON
2. Nano USB 연결
3. Ethernet 연결
4. TUSI TMS 실행
5. 전체 시스템 점검
6. 측정 준비
7. 점화
8. 측정 종료
```

이면 충분해야 한다.

---

# 35. Fault Requirement

반드시 자동 테스트 또는 수동 acceptance test를 만든다.

| Fault               | Required behavior             |
| ------------------- | ----------------------------- |
| Nano unplug         | Pi logging 계속                 |
| Nano firmware crash | Pi logging 계속                 |
| Laptop GUI crash    | Pi logging 계속                 |
| Laptop shutdown     | Pi logging 계속                 |
| Ethernet unplug     | Pi logging 계속                 |
| SSH disconnect      | Pi logging 계속 + reconnect     |
| Wrong SSH password  | GUI에 명확한 인증 오류                |
| Telemetry delay     | acquisition 영향 없음             |
| DAQ buffer pressure | health warning                |
| DAQ overrun         | DATA_GAP event 기록             |
| USB4704 disconnect  | DAQ error + reconnect attempt |
| Disk low            | GUI warning                   |
| Logger failure      | Critical RED                  |

---

# 36. 구현 순서

## Phase 1 — DAQ backend

먼저 Pi에서:

```text
USB4704
 ↓
buffer/DMA acquisition
 ↓
ring buffer
 ↓
HDF5 logging
```

을 완성한다.

GUI부터 만들지 않는다.

---

## Phase 2 — Nano

```text
GPIO
 ↓
debounce
 ↓
rising-edge
 ↓
TRIGGER serial
```

* heartbeat.

---

## Phase 3 — Pi telemetry

```text
DAQ
 ↓
tms-agent
 ↓
TCP telemetry server
```

---

## Phase 4 — Laptop connectivity

순서:

```text
Nano serial
 ↓

Pi LAN connection
 ↓

SSH ID/PASSWORD authentication
 ↓

SSH tunnel
 ↓

Telemetry
```

CLI 수준으로 먼저 검증한다.

---

## Phase 5 — Trigger integration

```text
Nano GPIO HIGH
 ↓
Laptop
 ↓
Pi
 ↓
trigger_sample
```

이 실제 DAQ log에 정확히 기록되는지 검증한다.

---

## Phase 6 — Dashboard

검증된 backend 위에 GUI를 붙인다.

GUI에서 transport 또는 acquisition logic을 직접 구현하지 않는다.

---

## Phase 7 — Packaging / handover

Windows/Linux package 생성.

README에는 비전공자용 운용법을 최상단에 작성한다.

상세 개발 정보는 뒤쪽에 둔다.

---

# 37. Codex가 하지 말아야 하는 것

다음 변경은 하지 않는다.

```text
SSH Key authentication으로 변경
PKI 도입
OAuth 도입
TLS 인증서 관리 추가
PTP/NTP 동기화 시스템 추가
별도 DAQ trigger channel 추가
데이터베이스 서버 추가
Redis/Kafka/RabbitMQ 추가
Docker/Kubernetes 추가
ROS2 추가
microservice architecture 변경
```

또한 현재 Raspberry Pi USB-4704 driver가 이미 준비된 상태이므로 자체 driver를 새로 개발하지 않는다.

---

# 38. Coding Style

코드는 다른 TUSI 구성원이 읽고 수정할 수 있어야 한다.

우선순위:

```text
Readability
>
Reliability
>
Performance
>
Architectural elegance
```

단, DAQ hot path에 대해서는 buffer/DMA/block processing을 사용하여 성능과 데이터 유실 방지를 보장한다.

명확한 이름을 사용한다.

좋음:

```text
read_daq_block()
save_samples()
connect_ssh()
handle_trigger()
update_health()
```

불필요:

```text
DataAcquisitionAbstractFactory
TransportStrategyProvider
TriggerEventDispatcherSingleton
```

---

# 39. Acceptance Criteria

최종 구현 완료의 기준은 다음이다.

### 기본 동작

```text
Dashboard 실행
→ Nano 자동 연결
→ ID/PW로 Pi SSH 자동 연결
→ SSH tunnel 생성
→ DAQ 상태 확인
→ 측정 준비
→ 지속 logging
→ Nano Trigger
→ T=0 생성
→ 실시간 그래프 표시
→ 측정 종료
→ 로그 정상 저장
```

### 장애 시험

시험 도중 Ethernet cable을 뽑는다.

```text
Dashboard:
SSH RED/YELLOW

Pi:
DAQ 계속
Logging 계속
```

Ethernet을 다시 연결한다.

```text
Dashboard:
SSH 자동 reconnect
Telemetry 자동 복구
```

시험 도중 Nano를 뽑는다.

```text
Nano RED
DAQ 정상
Logger 정상
```

시험 도중 Dashboard를 강제 종료한다.

```text
Pi DAQ 정상
Pi Logger 정상
```

Dashboard를 다시 실행하면 Pi에 다시 로그인할 수 있어야 한다.

---

# 40. 최종 설계 철학

TUSI TMS 내부에는:

```text
Serial
SSH
TCP
DMA
Buffer
Threads
DAQ
HDF5
```

등이 존재하지만 운영자는 이를 알 필요가 없어야 한다.

운영자에게 보여야 하는 것은:

```text
Nano       ●
Pi         ●
DAQ        ●
Logger     ●
SSH        ●

[전체 시스템 점검]

[측정 준비]

      THRUST
       graph

      PRESSURE
       graph

[측정 종료]
```

정도여야 한다.

특히 SSH는 다음처럼 구현한다.

```text
사용자 관점:

Pi IP
SSH ID
SSH Password

        ↓

Dashboard 내부 자동 처리

        ↓

SSH Connected ●
```

**SSH Key는 사용하지 않는다.**

이 프로젝트의 최종 목표는 단순히 기능이 동작하는 것이 아니라, 다음 학기의 비전공자 또는 신규 TUSI 구성원이 README와 Dashboard만 보고도 시험을 수행할 수 있는 TMS를 만드는 것이다.
