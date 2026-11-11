# TUSI TMS 현재 기능·데이터 규격

기준일: **2026-11-11**. 이 문서는 현재 소스와 실장비 검증을 기술한다.
기존 Raspberry Pi 전용 구현 요청서를 대체하며, 과거 검증 이력은
[복구 이력](daq-session-recovery-20261104.md)에 분리한다.

## 실행 구조와 운영 모드

실행 단위는 Nano 펌웨어, `tms-agent`, GUI 세 가지다.

```text
USB-4704 → buffered-AI → DAQ 서비스 → HDF5 원본
                            ├→ loopback → DAQ PC 로컬 GUI
                            └→ SSH 터널 → 노트북 원격 GUI
Nano → GUI를 실행하는 PC의 USB serial → DAQ 서비스의 상태·점화 이벤트
```

현재 DAQ PC는 Ubuntu 22.04.5 x86_64, 커널 `6.8.0-138-generic`이다.
Raspberry Pi ARM64도 소스로 지원하며 현재 운영 PC와 구분한다.
`pi/`와 `pi_host`, `pi_directory` 같은 이름은 호환성을 위해 유지한다.

| 항목 | 원격 모드 | DAQ PC 로컬 모드 |
|---|---|---|
| 실행 | `scripts/run-tms-dashboard.sh` | `tusi-tms-local` |
| GUI 옵션 | 기본 SSH | `--local-daq` |
| 연결 | `10.47.0.2:22` SSH → loopback telemetry | `127.0.0.1:29100` 직접 |
| GUI 설정 | 프로젝트 `config.yaml` | `~/.config/tusi-tms/dashboard-local.yaml` |
| GUI 저장 | 노트북 선택 폴더 | DAQ PC 선택 폴더 |
| 보정 원본 | DAQ PC `/etc/tusi-tms/config.yaml` | 동일 |
| Nano 연결 | 노트북 USB | DAQ PC USB |
| 초기화 | 독립 SSH/sudo | `pkexec` OS 인증 |

단독 모드는 주소를 loopback으로 고정하고 SSH 연결을 만들지 않는다.
원격 모드는 ID/Password 인증만 사용하며 기본 현장 주소·계정은
`laptop/operator_defaults.py`가 적용한다. 개발용 `--direct-telemetry`와 구별한다.

## 수집과 기록 우선순위

- AI0 로드셀·AI1 압력 고정. 기본 5,000 samples/s/channel, 10 ms 블록(50 samples).
- USB-4704 native buffered-AI ioctl, 사용자 버퍼, mmap 상태를 사용한다.
  단일 샘플 polling 루프로 대체하지 않는다.
- 인접 채널 스캔 총 속도는 `47,619 samples/s`를 넘지 않도록 설정을 검증한다.
- 취득·logger·GUI 통신을 분리한다. 링 버퍼 기본 길이는 5초다.
- GUI·SSH·Ethernet·Nano 장애가 DAQ 원본 기록을 중지하지 않는다.
- logger 큐 손실은 실패로 기록한다. telemetry 큐 손실은 표시 경로의 손실이며
  sample index의 간격으로 드러난다.
- 측정 준비 시 파일과 취득을 시작한다. 점화 신호는 기록 시작 명령이 아니다.
- 측정 종료는 logger를 마감한 뒤 USB close를 수행한다. STOP watchdog 실패 시
  복구 필요 상태를 유지하고 다음 취득을 차단한다.

세션 파일은 날짜·시험명·session ID로 구분하며 기존 파일을 덮어쓰지 않는다.
새 세션과 재접속에서 오래된 블록을 새 세션으로 표시하지 않는다.

## 기본 표시 필터

최근 80샘플 이동평균을 후행 방식으로 계산한다.

```text
y[n] = mean(x[max(구간 시작, n-79) : n+1])
```

입력은 보정된 추력·압력이며 LPF 출력에 이동평균을 겹쳐 적용하지 않는다.
초기는 확보된 샘플 수로 평균내고 0을 채우지 않는다. 각 입력 샘플에 출력 하나가
생기므로 CSV 행 수와 시간축을 바꾸지 않는다. 5 kHz 창 길이는 16 ms이고 시간
지연을 별도로 보정하지 않는다.

`common/filtering.py::MovingAverage`가 공통 구현이다. `TmsAgent`가 logger·통신
큐로 나누기 전에 한 번 계산해 `DaqBlock.moving_average_values`에 담는다.
logger와 모든 telemetry client는 같은 float32 배열을 사용한다. 늦게 접속한
client도 자체 이력으로 다시 계산하지 않는다. 블록 경계는 유지하고 새 측정,
불연속 index, 비정상 값에서 창을 초기화한다.

`FirstOrderLowPass`와 `low_pass` 설정은 보관용 `_lpf` 열을 위해 남아 있으며,
현재 기본 표시·분석 필터가 아니다.

## 영구 보정

로드셀·압력은 각각 원시 ADC에 대한 affine 변환이다.

```text
thrust_N = raw_thrust * scale + offset
pressure_bar = raw_pressure * scale + offset
```

- 2점 또는 3점의 알려진 질량(g)/압력(bar)과 취득 원시값을 사용한다.
- 원시값의 평균·표준편차·샘플 수를 표시하고 RMSE·잔차·R²로 계산 결과를 보여준다.
- **설정 저장**은 DAQ PC의 파일 저장 성공 후 메모리에 적용하고 ACK를 보낸다.
  파일 쓰기 실패를 성공처럼 표시하지 않는다.
- 채널별 최신 scale·offset 한 개를 유지한다. 다른 센서의 보정을 바꾸지 않는다.
- **프로파일 불러오기**는 CONFIG 조회로 서버의 현재 계수를 가져온다.
- 닫힌 보정 창의 늦은 불러오기 응답을 다른 창에 적용하지 않는다.
- 계수 저장은 `/etc/tusi-tms/config.yaml`, GUI 사본은 각 PC의 설정 파일에 저장한다.
- 과거 파일에는 측정 당시 계수를 보존한다. 새 보정은 다음 측정에 적용한다.

압력 션트 기본값은 100 Ω, 4–20 mA → 0.4–2.0 V다.
기계·전기적 정확도는 별도 기준계측으로 확인해야 한다.

## GUI와 저장 위치

주요 화면은 실시간 계측, 수집·연결, 시스템 점검, 시험 로그다. 로드셀·압력 보정은
별도 창으로 연다. 실시간 그래프는 채널 선택·단위·현재값·피크를 표시하며 최근
10초를 유지한다. 화면용 min/max envelope는 그리는 점 수만 줄이고 저장 샘플을
삭제하지 않는다.

측정 화면·시험 로그의 **저장 폴더 선택**, 설정의 **저장 위치 적용**을 제공한다.
선택한 경로를 절대 경로로 정규화하고 디렉터리 생성·실제 쓰기 검사를 수행한다.
설정 저장이 성공한 뒤 GUI와 runtime의 불변 설정 사본을 교체한다.

- 수집·SSH 연결을 종료하거나 다시 만들지 않는다.
- 이미 진행 중인 파일 저장은 기존 경로에 HDF5·CSV를 함께 완료한다.
- 다음 저장은 새 폴더를 사용한다. 재실행 후에도 유지된다.
- 취소·권한·설정 저장 실패는 이전 유효 설정을 유지한다.
- GUI 목적지 변경은 DAQ 원본 경로를 바꾸거나 기존 파일을 이동하지 않는다.

측정 종료 후 정확한 세션의 HDF5를 회수/복사하고 CSV를 자동 생성한다.
원본이 정상인데 GUI 저장만 실패하면 측정 실패와 구분하고 파일명을 유지해
재시도한다. 원격은 SFTP, 로컬은 동일 PC 파일 복사를 사용한다.

## HDF5와 CSV

```text
/metadata  test_name, session_id, start_time, end_time, sample_rate, sample_count,
           daq_configuration, sensor_calibration, display_filter,
           moving_average_window_samples, software_version
/samples/sample_index
/samples/raw_thrust
/samples/raw_pressure
/samples/thrust_N
/samples/pressure_bar
/samples/thrust_N_ma
/samples/pressure_bar_ma
/samples/thrust_N_lpf
/samples/pressure_bar_lpf
/events
/health
```

모든 `/samples` 데이터셋의 길이는 같다. MA metadata는
`display_filter=moving_average`, `moving_average_window_samples=80`이다.

CSV는 다음을 포함한다.

- index·시간: `sample_index`, `time_s`, `acquisition_time_s`
- 원본: `raw_thrust`, `raw_pressure`, `thrust_N`, `pressure_bar`
- 필터: `thrust_N_ma`, `pressure_bar_ma`, `moving_average_window_samples`,
  `thrust_N_lpf`, `pressure_bar_lpf`
- 점화: `ignition`, `ignition_recorded`, `time_reference`, `ignition_source`,
  `ignition_receive_time_utc`, `nano_sequence`, `nano_uptime_ms`, `ignition_timing_basis`
- 상태: `nano_gpio`, `nano_gpio_valid`, `nano_gpio_observed`

CSV 내보내기는 chunk 사이에 이동평균 이력을 유지한다. 과거 HDF5에 MA가 없으면
환산 원본으로 계산한다. 내보내기는 임시 파일 완성 후 목적지에 반영한다.

## 결과 분석

시험 로그 선택 후 **결과 분석**, 로그 더블클릭 또는 파일 선택으로 HDF5·CSV를 연다.
`laptop/analysis.py`가 두 PC에서 같은 데이터를 생성하고
`laptop/gui/analysis_dialog.py`가 이동평균 추력·압력과 최대·평균을 표시한다.
점화 기록이 있으면 수신 기준 T=0, 없으면 수집 시작 기준이다.
저장된 MA80을 우선 사용하고 과거 파일에만 원본에서 계산한다.
누락 구간을 연속 그래프로 잇지 않는다. 확대·이동은 pyqtgraph 조작을 사용한다.

## Nano와 점화 시각

현재 펌웨어는 `firmware/nano/nano_trigger.ino`다.

| 항목 | 값 |
|---|---|
| 입력 | D5, `INPUT`, 외부 4.7 kΩ pull-down |
| 의미 | LOW=비활성, HIGH=신호 감지 |
| debounce | 20 ms |
| Serial | 115200 baud |
| heartbeat | 500 ms |
| GUI 상태 만료 | 기본 2초 |

ASCII 메시지: `HELLO`, `HB,<sequence>,<uptime_ms>,<gpio>`,
`STATE,<sequence>,<uptime_ms>,<gpio>`, `TRIGGER,<sequence>,<uptime_ms>`,
`ARM,<session_id>`, `ARMED,<session_id>`.
GPIO HIGH/LOW 상태 기록은 ARM 확인이나 첫 점화 여부와 독립적으로 유지한다.
처음부터 HIGH라면 상태만 기록하고 과거 점화 에지를 만들지 않는다.

서비스는 신호를 처리하는 시점의 최신 로깅 샘플에 이벤트를 연결하고 flush 후 ACK한다.
`ignition_timing_basis=pi_latest_sample_on_receipt`는 x86_64에서도 유지하는 호환 이름이다.
Nano uptime은 UTC나 DAQ clock이 아니며 hardware trigger/PTP 동기화는 구현하지 않는다.

CSV 점화 행의 시간은 `(sample_index-trigger_sample)/sample_rate`다.
점화가 없으면 수집 시작 기준이며 점화 시점을 임의로 추정하지 않는다.
유효한 마지막 GPIO 상태를 보고 사이에 유지하되 수신 전·단절·만료는 빈칸으로 쓴다.

## 통신·상태·복구

TCP 프로토콜은 길이 헤더와 제어 메시지, float32 DAQ payload를 사용한다.
주요 명령은 HELLO, PING, CONFIG, START_SESSION, STOP_SESSION, CALIBRATION_SAMPLE,
SET_THRUST_CALIBRATION, SET_PRESSURE_CALIBRATION, NANO_STATE, TRIGGER다.
서버는 HEALTH·DAQ_DATA와 request ID에 대응하는 ACK/ERROR를 반환한다.

서비스 세션 상태는 READY, RECORDING, TRIGGERED, COMPLETE다. 보정 취득 중에는
세션 상태를 유지하고 DAQ health를 CALIBRATING으로 표시한다. GUI의 DISCONNECTED와 복구 진행 상태를 별도로 관리한다.
logger·DAQ·storage health, logger/telemetry dropped block 수, session ID를 표시한다.

원격 재연결은 정상 SSH 터널을 유지하고 반복 실패 때만 교체한다. 초기화는 PING이
응답하지 않아도 별도 제어 경로로 수행하며 중복 실행은 파일 잠금으로 막는다.
정상 서비스 시작은 이미 있는 `/dev/daq0`를 건드리지 않는다. 노드가 없을 때만
재인가·재열거를 시도한다. 수동 초기화는 서비스 중지·장치 복구·서비스 재시작 후
실제 buffered-AI 취득/종료 두 번과 GUI 재연결을 확인한다.

`USBDEVFS_RESET`은 이 장치에서 장시간 block된 이력이 있어 사용하지 않는다.
일부 펌웨어가 `GET_USB_FLAG`에 STALL을 반환하면 반복 요청을 중단한다. 이 경우
장치 내부 FIFO 초과 상태를 읽을 수 없지만 호스트 버퍼·샘플 index 검사는 유지한다.

## 설정·설치 경계

설정 schema는 `common/config.py`, 예제는 `config.example.yaml`이 기준이다.
`daq.sample_rate=5000`, `daq.block_ms=10`, `logging.ring_buffer_sec=5`,
`logging.flush_interval_sec=1`이 기본이다. 비밀번호를 포함하는 실제 설정·로그·
가상환경은 소스 관리에서 제외한다.

설치된 서비스는 `tms:plugdev`로 실행하고 `/var/lib/tusi-tms`와 `/etc/tusi-tms`에
쓰기 권한을 갖는다. 로컬 GUI는 일반 사용자로 실행하며 초기화 때만 OS 인증한다.
드라이버 모듈은 실행 중인 아키텍처·커널과 일치해야 한다.

## 검증 기준과 현재 결과

2026-11-11 자동 테스트 **196개 통과**. 주요 근거:

- MovingAverage의 정확한 80샘플 창·시작·블록 경계·누락 구간 검증.
- 늦은 client와 logger의 이동평균 배열 일치.
- 신규·과거 HDF5/CSV 분석과 chunk 내보내기 일치.
- 서비스 재시작 후 센서별 보정 유지·프로파일 조회.
- 원격/로컬 저장 폴더 선택·재실행 유지·취소·권한 오류·저장 중 경로 변경.
- 실장비 16,100샘플의 화면/HDF5/CSV/분석 일치와 두 PC CSV의 바이트 일치.
- 실장비 폴더 선택 후 HDF5·CSV 저장 및 설정 복원 확인.

센서 기준계에 의한 정확도, 실제 점화 배선, 장시간·최대 속도, 60 m 케이블 전체
장애 시험, AO/DO·counter와 이번 변경의 Windows 실기기 시험은 완료로 간주하지 않는다.
