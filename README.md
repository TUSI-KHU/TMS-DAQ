# TUSI TMS / USB-4704 Raspberry Pi project

이 저장소에는 두 작업이 함께 들어 있다.

1. USB-4704 Ubuntu 22.04 ARM64 커널 드라이버 포팅
2. 포팅된 드라이버를 이용할 TUSI 시험 계측 소프트웨어

전체 TMS 요구사항은 [시스템 요구사항](docs/system-requirements.md)에, ARM64
드라이버 포팅 결과와 남은 검증 항목은
[USB-4704 포팅 현황](docs/usb4704-porting-status.md)에 정리되어 있다.

## 저장소 구조

```text
common/     Pi agent와 Dashboard가 공유하는 설정·프로토콜
pi/         Raspberry Pi 수집·기록·telemetry agent
laptop/     노트북 Dashboard와 SSH tunnel client
firmware/   Arduino Nano trigger firmware
vendor/     USB-4704 커널 드라이버 원본 및 포팅 대상 소스
scripts/    빌드·설치·유선망 provision·실행 스크립트
packaging/  systemd, udev, DKMS, PyInstaller 패키징 파일
tools/      USB-4704 진단 도구
tests/      하드웨어 없이 실행 가능한 자동 테스트
docs/       시스템 요구사항과 포팅/검증 현황
```

`build/`, `dist/`, 가상환경, 측정 로그 및 로컬 `config.yaml`은 생성물 또는
현장별 설정이므로 Git에 포함하지 않는다.

## 현장 운영 순서

설치가 끝난 시스템의 운영자는 다음 순서만 따르면 된다.

```text
1. Raspberry Pi 전원 ON
2. Nano USB 연결
3. Ethernet 연결
4. TUSI TMS Dashboard 실행
5. Dashboard의 통합 상태 확인
6. 전체 시스템 점검
7. 측정 준비
8. 점화
9. 측정 종료
```

Dashboard가 password SSH 인증, local tunnel, Nano Serial 및 Pi telemetry를
내부에서 처리한다. SSH Key는 사용하지 않는다.

노트북에서 최신 GUI를 한 명령으로 실행하려면 다음을 사용한다.

```bash
./scripts/run-tms-dashboard.sh
```

실행 스크립트가 노트북 유선 NIC를 `10.47.0.1`, Pi `eth0`을
`10.47.0.2`로 설정하고 `tms-agent`가 실행 중인지 확인한다. 정상 실행 중인
agent는 재시작하지 않는다. Pi는 유선 링크가
살아 있는 동안 Wi-Fi를 내려 동일 IP 충돌을 막고, 케이블이 빠지면 저장된
`TUSI_wifi` 프로필로 자동 복귀한다.
접속 정보는 폐쇄망 고정값 `tms@10.47.0.2:22`이며, GUI가 Pi의
`tms-agent`에 SSH local tunnel로 연결한다. `--direct-telemetry`는 현장
운용에 사용하지 않는다.

## 현재 구현 상태

운용 소프트웨어와 실제 장치 연결 경로가 구현되어 있다.

- Arduino Nano 실제 펌웨어: GPIO debounce, rising-edge, latch, heartbeat, ARM
- USB-4704 실제 buffered-AI ioctl, 사용자 버퍼 pinning, mmap 상태 및 원형 버퍼 소비
- USB 분리 시 `DATA_GAP` 기록, backoff 재접속 및 저장 공간 부족 경고
- Nano `pyserial` 자동 포트 탐색, parser, heartbeat 감시 및 재접속
- password-only `asyncssh` 연결, local forwarding, keepalive 및 backoff
- 길이-prefixed TCP 제어 메시지와 binary float32 DAQ block
- Pi telemetry server와 Dashboard client
- Dashboard 종료·Ethernet 단절과 독립적인 Pi acquisition/HDF5 logging
- Dashboard, Setup, System Test, Logs 4개 화면
- Dashboard 2×2 통합 콘솔: 선택 가능한 실시간 데이터 graph 2개,
  프로그램/파이프라인 상태, 측정 시작·종료·설정 바로가기
- 각 실시간 graph의 데이터 상자에서 추력·압력 등 수신 channel을 선택하면
  단위, 현재값, 세션 피크, 최근 10초 범위와 graph가 함께 변경
- HDF5 session 조회, CSV 내보내기 및 SFTP Pi 로그 가져오기
- Pi systemd service, 설치 스크립트 및 Dashboard PyInstaller 설정

### 2026-08-25 실장비 검증 결과

Pi (`10.47.0.2`, Ubuntu 22.04 ARM64, `5.15.0-1105-raspi`)에서 다음을
실제 장치로 확인했다.

- `bio4704`/`biokernbase` 모듈 적재, USB `1809:4704`, `/dev/daq0` 및
  description ioctl
- `tms-agent` systemd 서비스가 `tms:plugdev` 권한으로 기동되고 telemetry를
  `127.0.0.1:29100`에만 bind
- USB-4704 native buffered-AI를 5 kS/s로 취득하여 HDF5에 연속 기록
- password SSH local forwarding으로 노트북 telemetry client를 연결, 수집 중
  터널을 완전히 끊었다가 재접속해도 Pi 수집과 HDF5 기록이 계속됨
- SFTP로 HDF5를 회수하고 원격 파일과 SHA-256이 일치함을 확인

이 검증에서는 `TRIGGER`, AO/DO write, Nano GPIO 제어를 실행하지 않았다.
센서의 실제 물리 단위 교정과 출력/점화 계통 시험은 아래 최종 게이트로 남긴다.

Pi 로그 파일에는 다음 구조가 생성된다.

```text
/metadata
/samples/sample_index
/samples/raw_thrust
/samples/raw_pressure
/samples/thrust_N
/samples/pressure_bar
/events
/health
```

설정은 `config.example.yaml`을 복사한 `config.yaml`에서 변경한다. 실제
비밀번호가 들어갈 수 있는 `config.yaml`, 시험 로그 및 가상환경은 Git에서
제외된다. 비밀번호는 일반/고급 로그나 exception에 출력하지 않는다.

## 개발 환경과 자동 테스트

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dashboard,test]'
python -m pytest
```

하드웨어 없는 전체 TCP/Dashboard 경로는 두 터미널에서 실행할 수 있다.
이때 시뮬레이터는 USB-4704 입력만 대체하며 나머지 session, TCP, binary
telemetry, logger와 Dashboard 코드는 실제 운용 코드다.

```bash
# Terminal 1: local Pi agent replacement
tms-agent --simulate --config config.example.yaml --bind 127.0.0.1

# Terminal 2: SSH만 우회하는 local Dashboard QA mode
tusi-tms --config config.example.yaml --direct-telemetry
```

`--direct-telemetry`는 로컬 개발 전용이며 현장 운용에서는 사용하지 않는다.

짧은 HDF5 self-test만 실행할 때:

```bash
tms-agent-selftest \
  --simulate \
  --duration 5 \
  --trigger-after 2 \
  --test-name LOCAL_SIM_001
```

## Raspberry Pi agent 설치

먼저 password login이 가능한 `tms` 사용자를 생성하고, 저장소에서 설치
스크립트를 실행한다. Ubuntu 22.04 ARM64에서는 수집 런타임을 먼저 apt로
설치한다. 스크립트는 사용자의 password를 만들거나 변경하지 않는다.

```bash
sudo adduser tms
sudo apt update
sudo apt install build-essential python3-venv python3-numpy python3-h5py python3-serial python3-yaml
sudo ./scripts/install-tms-agent.sh
systemctl status tms-agent.service
```

Pi telemetry server는 `127.0.0.1:29100`에만 bind되며 Dashboard가 SSH local
forwarding으로 접근한다.

`tms-agent`가 시작 또는 재시작될 때 `/dev/daq0`가 이미 있으면 systemd의
root 전용 pre-start 단계는 USB topology를 건드리지 않는다. 장치 노드가 없을
때만 USB `1809:4704`의 logical reauthorize를 먼저 시도하고, 실패했을 때만
USB core rebind를 마지막 수단으로 사용한다. `usbreset`은 이 장치의 실패한
control transfer를 장시간 block할 수 있어 사용하지 않는다.

Dashboard의 **DAQ 초기화** 버튼은 telemetry `PING`에 의존하지 않는 별도 SSH
복구 경로다. agent를 정지한 뒤 USB-4704의 상위 허브 포트를 전원 재인가하여
물리 재연결과 같은 재열거를 수행하고 agent를 다시 시작한다. 배포 Pi의 VIA
허브는 ganged power이므로 같은 허브의 다른 downstream USB 장치도 잠깐
재시작될 수 있다.

USB-4704는 USB bus-powered, 최대 500 mA 장치다. Pi kernel에
`Undervoltage detected`가 기록되면 소프트웨어 복구만으로는 안정성을 보장할 수
없다. 정격 Raspberry Pi 전원(5 V/3 A 이상)과 짧고 굵은 케이블을 사용하고,
전압 경고가 재발하면 USB-4704를 외부 전원형 USB hub에 연결한 뒤 재시험한다.

## Dashboard 패키징

Windows PowerShell:

```powershell
.\scripts\build-dashboard.ps1
```

Ubuntu/Debian Linux:

```bash
sudo apt install python3-venv \
  libxcb-cursor0 libxcb-image0 libxcb-icccm4 libxcb-keysyms1 libxcb-render-util0
./scripts/build-dashboard.sh
```

결과는 `dist/TUSI-TMS` 또는 `dist/TUSI-TMS.exe`에 생성된다.

## Nano firmware 빌드

`arduino-cli`와 `arduino:avr` core가 준비된 환경에서 다음 명령으로 컴파일한다.

```bash
./scripts/build-nano.sh
```

USB로 연결된 Nano에 업로드까지 수행할 때는 포트를 명시한다.

```bash
NANO_PORT=/dev/ttyUSB0 ./scripts/build-nano.sh
```

Windows에서는 `scripts\build-nano.ps1`을 사용한다. 기본 대상은 구형
bootloader Nano(`arduino:avr:nano:cpu=atmega328old`)이며 `NANO_FQBN` 환경 변수로
호환 보드를 바꿀 수 있다.

## 실장비가 필요한 최종 게이트

- `Usb4704DaqSource`의 실제 buffered-AI ioctl/mmap ABI와 채널 순서 검증
- Raspberry Pi에서 5 kS/s 장시간 취득 및 overrun/hotplug 시험
- 센서 기준 전압, scale/offset 및 실제 물리량 교정
- Nano firmware upload와 실제 GPIO/pull-down/debounce 시험
- Pi udev, systemd, password SSH 및 재부팅 시험
- 60 m Ethernet 단절/복구와 전체 지상시험 acceptance test

실장비 backend는 polling 방식으로 대체하지 않는다. `--simulate` 없이 agent를
실행하면 `/dev/daq0`의 실제 USB-4704 ioctl/mmap 경로를 사용하며, 장치 또는
드라이버가 없으면 해당 원인이 포함된 오류를 출력한다.

---

## USB-4704 Ubuntu 22.04 ARM64 port

이 프로젝트는 Advantech USB-4704의 Linux 커널 모듈을 Raspberry Pi 4용
Ubuntu 22.04 ARM64에서 빌드하고 배포하기 위한 작업 트리다.

현재 빌드 결과와 남은 실장비 게이트는
[USB-4704 포팅 현황](docs/usb4704-porting-status.md)에 정리되어 있다.

## 현재 범위

- 공급사 공통 모듈 `biokernbase.ko`
- USB-4702/4704 장치 모듈 `bio4704.ko`
- ARM64에서 x86 전용 DAQNavi 데몬을 호출하지 않는 udev 규칙
- 장치 설명 ioctl을 확인하는 최소 smoke test

공급사 DAQNavi 사용자 공간 라이브러리(`libbiodaq.so`,
`libbiodaqutil.so`, `libbio4704.so`)는 최신 공개 패키지에서 x86-64
바이너리로만 제공되므로 포함하지 않는다.

## 기준 대상

- OS: Ubuntu 22.04 LTS ARM64
- Board: Raspberry Pi 4
- 현재 배포 대상 Jammy `linux-raspi`: `5.15.0-1105-raspi`

커널 모듈은 실행 중인 커널과 정확히 일치해야 한다. 대상 장비의
`uname -r`이 다르면 해당 버전의 `linux-headers-$(uname -r)`로 다시
빌드해야 한다.

## 재현 빌드

x86-64 Ubuntu 빌드 머신에서 다음 한 명령으로 Jammy ARM64 헤더와 로컬
크로스 컴파일러를 준비하고 모듈을 만든다.

```bash
./scripts/build-jammy-arm64.sh
```

산출물은 `dist/5.15.0-1105-raspi/`와 배포용 tar.gz에 생성된다.

기존 `5.15.0-1061-raspi` 대상도 다음처럼 명시해서 계속 빌드할 수 있다.

```bash
JAMMY_KERNEL_RELEASE=5.15.0-1061-raspi ./scripts/build-jammy-arm64.sh
```

이미 준비된 다른 커널 헤더를 사용할 때:

```bash
KERNEL_RELEASE=5.15.0-xxxx-raspi \
KERNEL_DIR=/path/to/linux-headers-5.15.0-xxxx-raspi \
ARCH=arm64 \
CROSS_COMPILE=aarch64-linux-gnu- \
./scripts/build-modules.sh
```

## Raspberry Pi에 설치

배포 압축을 Pi에서 풀고, 실행 중인 커널이 일치하는지 확인한 뒤 설치한다.

```bash
uname -m
uname -r
tar -xzf usb4704-5.15.0-1105-raspi-arm64.tar.gz
cd 5.15.0-1105-raspi
sha256sum -c SHA256SUMS
sudo ./install.sh
```

장치를 연결한 뒤:

```bash
lsusb -d 1809:4704
lsmod | grep -E 'bio4704|biokernbase'
cat /sys/class/daq/daq0/desc
ls -l /dev/daq0
cc -O2 -Wall -Wextra -o usb4704-smoke usb4704-smoke.c
./usb4704-smoke
```

### 비파괴 실제 I/O 진단

다음 도구는 AI 0~7의 즉시 샘플, DI 포트 및 DO readback만 반복 읽는다.
AO나 DO에는 쓰지 않으므로 연결된 설비의 출력을 바꾸지 않는다. AI 값은
설정된 입력 범위에 따른 raw ADC 코드다.

```bash
cc -O2 -Wall -Wextra -Werror -o usb4704-readonly-diag usb4704-readonly-diag.c
./usb4704-readonly-diag /dev/daq0 200 50
```

DI 배선을 한 비트씩 바꾸거나 AI0에 기준 전압을 인가했을 때, 반복 출력의
`DI` 또는 해당 `AI` raw 값이 바뀌는지 확인한다. DO/AO loopback 시험은
출력 배선과 안전한 부하를 확인한 뒤에만 수행한다.

### DKMS 설치 권장

대상 Pi에서 소스 트리를 사용할 수 있다면 DKMS 설치가 권장된다. 이후
커널 업데이트 때 두 모듈을 자동으로 다시 빌드한다.

```bash
sudo apt update
sudo apt install dkms build-essential linux-headers-$(uname -r)
sudo ./scripts/install-dkms.sh
```

제거:

```bash
sudo ./scripts/uninstall-dkms.sh
```

Pi에서 현재 실행 중인 커널용 산출물을 직접 만들 수도 있다.

```bash
./scripts/build-native-arm64.sh
```

## 아직 필요한 실장비 검증

1. 모듈 로딩과 USB hotplug
2. AI 기준 전압 및 보정 정확도
3. AO 출력 전압
4. DI/DO loopback과 counter
5. 최대 샘플링 속도에서 장시간 buffered AI
6. 재부팅 및 커널 업데이트 후 모듈 재빌드
