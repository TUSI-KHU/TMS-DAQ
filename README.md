# TUSI TMS / USB-4704

문서 기준: **2026-11-11**, Python 패키지 `tusi-tms 0.1.0`의 현재 작업본.

USB-4704로 추력·압력을 수집하는 프로그램이다. 노트북에서 DAQ PC를 원격으로 조작하거나, DAQ PC에서 같은 GUI를 실행해 독립적으로 측정·저장한다. 

## 실행 방법

### 노트북에서 원격 실행

프로젝트 루트에서 실행한다.

```
./scripts/run-tms-dashboard.sh
```

노트북은 `10.47.0.1/24`, DAQ PC는 `10.47.0.2/24`를 사용한다. 실행기는 유선 경로와 DAQ 서비스를 확인하고 GUI가 ID/Password 기반 SSH 터널을 연다. 폐쇄형 현장망 기본 계정은 `tms`이며 연결 설정은 `config.yaml`에 둔다. DAQ 서비스는 `127.0.0.1:29100`만 수신한다.

유선 인터페이스는 현재 주소로 탐색하므로 USB Ethernet의 `enx…` 이름도 지원한다. 고정 DHCP 풀이 과거 장치에 묶여 새 장치가 주소를 받지 못하는 경우와 SSH 키 변경은 [장치 관리 문서](docs/current-deployment.md)의 네트워크 복구 절차를 따른다.

### DAQ PC에서 단독 실행

설치된 DAQ PC의 앱 메뉴에서 \*\*TUSI TMS (DAQ PC 로컬)\*\*를 선택하거나 실행한다.

```
tusi-tms-local
```

로컬 모드는 같은 서비스에 `127.0.0.1`로 직접 연결한다. 노트북·SSH·Ethernet 없이 그래프, 측정, 보정, 결과 분석, HDF5·CSV 저장을 사용한다. 수집 서비스는 부팅 시 자동 시작하며 GUI는 로그인 후 실행한다. 운영 단독 실행은 `--local-daq`, `--direct-telemetry`는 개발용이다.

Nano 점화 신호를 쓰려면 **GUI를 실행하는 PC에 Nano USB를 연결**한다. 로컬 GUI 설치 시 `tms`를 `dialout` 그룹에 추가하므로 기존 로그인은 로그아웃 후 다시 로그인해야 새 권한이 반영된다. 두 GUI가 같은 장치를 공유하므로 한 측정의 시작·종료는 한쪽에서 조작한다.

## 운영 순서

1. DAQ PC와 센서·앰프 전원을 켜고 USB-4704를 연결한다.
2. 원격 또는 로컬 GUI를 실행한다. 원격이면 Ethernet도 연결한다.
3. Nano를 사용할 때 GUI가 실행되는 PC에 USB로 연결한다.
4. **저장 폴더 선택**으로 위치를 확인하고 전체 시스템 점검을 실행한다.
5. 필요하면 로드셀·압력을 보정하거나 저장 프로파일을 불러온다.
6. **측정 준비**를 눌러 점화 전부터 수집을 시작한다.
7. **측정 종료** 후 HDF5·CSV를 확인한다.
8. 시험 로그에서 파일을 선택해 **결과 분석**을 연다.

GUI·Nano·Ethernet 연결이 끊겨도 DAQ 서비스의 수집·원본 기록은 계속된다. 점화 이벤트는 수집 시작 명령이 아니라 이미 기록 중인 데이터의 시간 기준이다.

## 저장 위치

측정 화면과 시험 로그 화면의 **저장 폴더 선택**은 선택 즉시 설정을 저장한다. **설정 → 수집·연결 → 저장**에서 경로 입력 후 **저장 위치 적용**도 가능하다. 현재 경로는 시험 로그 상단에 표시되며 앱을 다시 실행해도 유지된다.

- 원격 모드: 노트북의 선택 폴더에 HDF5 복사본·CSV 저장.
- 로컬 모드: DAQ PC의 선택 폴더에 HDF5 복사본·CSV 저장.
- DAQ 서비스 원본: `/var/lib/tusi-tms/logs/`에 별도 보관.

폴더 변경 때문에 수집을 재연결하지 않는다. 진행 중인 저장은 기존 폴더에 HDF5·CSV를 함께 완료하고 다음 저장부터 새 위치를 쓴다. 쓰기 검사·설정 저장 실패 시 기존 설정을 유지한다. 기존 파일을 이동하거나 덮어쓰지 않는다. 회수 실패는 시험 로그의 **Pi 로그 가져오기**(원격) 또는 **DAQ 원본 로그 가져오기**(로컬)로 재시도한다.

## 보정 프로파일

AI0는 로드셀, AI1은 압력으로 고정한다. 측정을 종료한 상태에서 각 보정 화면을 연다.

1. 기준점 2개 또는 3개를 입력하고 각 점의 원시값을 취득한다.
2. **보정값 계산**으로 scale·offset과 잔차를 확인한다.
3. **설정 저장**으로 DAQ PC의 `/etc/tusi-tms/config.yaml`에 영구 저장한다.

**프로파일 불러오기**는 DAQ PC에 마지막 저장된 해당 센서의 계수를 읽는다. 센서별 최신 프로파일 한 개이며 이름별 이력·기준점 데이터는 저장하지 않는다. 서비스 재시작 후에도 유지되고 다음 측정과 HDF5 메타데이터에 적용된다. 노트북 설정도 저장 응답으로 갱신한다.

로드셀 기준 질량은 g, 환산 추력은 N, 압력은 bar 단위다. 압력 입력은 기본 100 Ω 션트, 4–20 mA, 0.4–2.0 V이다. 예제 계수는 실제 센서 교정값이 아니다.

## 기본 필터와 결과 분석

기본 화면·CSV·결과 분석은 **현재 샘플을 포함한 최근 80개의 산술평균**을 사용한다. 5 kHz에서 16 ms 구간이며 처음 79개는 확보된 샘플만 평균낸다. 시간축 이동이나 샘플 수 감소는 하지 않는다. 블록 경계에서는 이력을 유지하고 샘플 번호 누락, 비정상 값, 새 측정에서는 창을 초기화한다.

DAQ 수집 단계에서 한 번 계산한 float32 값을 파일과 모든 GUI에 전달하므로 원격/로컬, 재접속 시점, 전송 묶음 크기에 따라 값이 달라지지 않는다.

| 데이터 | HDF5·CSV 이름 |
| --- | --- |
| ADC 원본 | `raw_thrust`, `raw_pressure` |
| 환산 원본 | `thrust_N`, `pressure_bar` |
| 기본 표시 이동평균 | `thrust_N_ma`, `pressure_bar_ma` |
| 보관용 LPF | `thrust_N_lpf`, `pressure_bar_lpf` |

CSV에는 `moving_average_window_samples=80`도 저장한다. `low_pass` 설정은 보관용 `_lpf`에만 적용한다. 이동평균이 없는 과거 HDF5·CSV는 환산 원본에서 계산해 분석하며, 저장된 이동평균에 필터를 중복 적용하지 않는다.

시험 로그의 **결과 분석** 또는 로그 더블클릭으로 추력·압력 그래프를 연다. 로그를 선택하지 않으면 HDF5·CSV 파일을 직접 선택할 수 있다.

## 점화·Nano 데이터

펌웨어는 `firmware/nano/nano_trigger.ino`이다. Nano는 D5 입력을 읽으며 점화를 제어하지 않는다. 외부 4.7 kΩ pull-down, `INPUT`, 20 ms debounce, 펌웨어 1.2, 115200 baud, 500 ms heartbeat를 사용한다.

첫 유효 LOW→HIGH 전환을 점화 기준으로 기록한다. 처음부터 HIGH이면 과거 에지 시각을 만들지 않는다. 서비스 기록·flush 응답 후에만 GUI가 점화를 확정한다.

- `ignition=1`: 점화에 연결된 한 행. `time_s=0`이다.
- `ignition_recorded=0`: 점화 기록 없음. `time_reference=acquisition_start`.
- `acquisition_time_s`: 수집 시작 기준 시간.
- `nano_gpio`: 마지막 유효 LOW/HIGH. 미확인·만료는 빈칸이며 LOW가 아니다.
- `nano_gpio_valid`, `nano_gpio_observed`: 유효 상태와 실제 보고 행 구분.
- 점화 행의 출처·수신 정보: `ignition_source`, `nano_sequence`, `nano_uptime_ms`, `ignition_receive_time_utc`, `ignition_timing_basis`.

`pi_latest_sample_on_receipt`는 서비스가 신호를 처리할 때의 최신 기록 샘플을 뜻하는 호환 이름이며 x86\_64에서도 유지한다. debounce·USB·통신 지연을 포함하므로 하드웨어 동기화된 에지 시각은 아니다. 실시간 그래프는 수집 표시 구간 기준이며, CSV·결과 분석은 점화가 있으면 점화 수신 기준, 없으면 수집 시작 기준이다.

## 설치·복구

현재 장치의 설치 경로와 x86\_64 DKMS 절차는 [설치·관리](docs/current-deployment.md)를 따른다. 현재 `scripts/install-dkms.sh`, `packaging/install-prebuilt.sh`는 AArch64 전용이다. 실행 중인 x86\_64 장치에 ARM64 모듈을 설치하지 않는다.

DAQ 서비스가 설치된 Ubuntu 장치의 로컬 GUI 설치:

```
sudo apt install python3-venv libxcb-cursor0 libxkbcommon-x11-0 libopengl0 libegl1
sudo ./scripts/install-local-dashboard.sh
```

설치기는 NumPy·h5py를 함께 갱신해 호환성을 맞춘다. 보정 파일은 유지한다. DAQ 초기화는 원격에서 별도 SSH/sudo, 로컬에서 OS 인증 창(`pkexec`)을 사용한다. 서비스 정지·USB 복구·재시작 후 AI0·AI1 취득/종료 두 번과 GUI 재연결로 판정한다. 자세한 종료·복구 정책은 [기술 규격](docs/system-requirements.md)을 참고한다.

## 개발·빌드·테스트

```
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dashboard,test]'
python -m pytest
```

외부 ROS pytest 플러그인이 수집에 개입하는 환경:

```
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 QT_QPA_PLATFORM=offscreen python -m pytest -q
```

2026-11-11 전체 테스트는 **196개 통과**다. 실장비에서 5 kHz 수집, 원격/로컬 연결, 보정 유지, MA80 화면·HDF5·CSV·분석 일치, 두 PC의 CSV 바이트 일치, 저장 폴더와 재실행 후 경로 유지를 확인했다. 센서 물리 교정, Nano 실제 점화 배선, AO/DO, 최대 속도·장시간 운용은 별도 검증 대상이다.

Linux: `./scripts/build-dashboard.sh` → `dist/TUSI-TMS`. Windows: `scripts/build-dashboard.ps1` → `dist/TUSI-TMS.exe`. Windows에서 이번 기능의 실기기 검증은 수행하지 않았다.

```
./dist/TUSI-TMS --self-test
```

개발용 모의 경로는 두 터미널에서 실행한다.

```
tms-agent --simulate --config config.example.yaml --bind 127.0.0.1
tusi-tms --config config.example.yaml --direct-telemetry
```

Nano 빌드: `./scripts/build-nano.sh`; 업로드 시 `NANO_PORT=/dev/ttyUSB0` 지정. 기본 FQBN은 `arduino:avr:nano:cpu=atmega328old`이며 `NANO_FQBN`으로 변경한다.

## 소스 구조

```
common/       설정·프로토콜·공통 필터·압력 환산
pi/           DAQ PC/Pi 수집 서비스·드라이버 ABI·HDF5 기록
laptop/       원격/로컬 GUI·Nano·CSV·결과 분석·저장 폴더 검증
firmware/     Nano 점화 감지 펌웨어
vendor/       공급사 커널 소스와 Linux 호환 수정
scripts/      설치·빌드·네트워크·복구 실행기
packaging/    systemd·udev·DKMS·GUI 패키징
tests/        자동 검증
docs/         현재 규격·배포·검증 이력
```

`config.yaml`, 가상환경, `build/`, `dist/`, 측정 로그는 장치 설정 또는 생성물이다. DAQ PC의 유지보수 소스는 `~/TMS-DAQ`, 설치된 실행본은 `/opt/tusi-tms`에 둔다.
