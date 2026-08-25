# USB-4704 ARM64 porting status

Date: 2026-08-25

## Build result

Target:

- Ubuntu 22.04 LTS ARM64
- Raspberry Pi `linux-raspi`
- Kernel `5.15.0-1105-raspi`
- Header package `5.15.0-1105.108`
- GCC `11.4.0-1ubuntu1~22.04.3`

Completed:

- `biokernbase.ko` compiled as ELF64 AArch64
- `bio4704.ko` compiled as ELF64 AArch64
- both modules have `5.15.0-1105-raspi ... aarch64` vermagic
- `bio4704.ko` depends on `biokernbase`
- USB alias `1809:4704` is present
- module and deployment file checksums pass
- prebuilt installer and DKMS installation paths are prepared
- read-only AI/DI/DO-readback diagnostic source is included in the bundle
- TMS용 native buffered-AI wrapper가 vendor `FAI_CONFIG`/`FAI_STATUS` ABI,
  ioctl 번호, mmap 상태 페이지 및 pin된 사용자 원형 버퍼를 직접 사용하도록 구현됨
- ABI structure 크기/offset/ioctl 번호 자동 테스트와 장치 부재 안전 탐지 구현
- Pi `10.47.0.2`에서 두 모듈을 실제 적재하고 USB `1809:4704`,
  `/sys/class/daq/daq0`, `/dev/daq0`, description ioctl smoke test 통과
- `tms-agent`가 `tms:plugdev` systemd 서비스로 설치되어 `127.0.0.1:29100`만
  수신하도록 확인
- 실제 USB-4704 native buffered-AI를 5 kS/s로 수집하여 HDF5에 18,950개
  연속 sample index를 기록하고, 원격과 SFTP 회수본의 SHA-256 일치 확인
- 실제 password SSH local forwarding을 끊고 다시 연결한 뒤에도 Pi 수집이
  계속되고 session을 정상 종료하는지 확인
- 재설치 후 systemd restart 경로로 5 kS/s data block 수신과 HDF5 기록 재확인
- 정상 `/dev/daq0`가 존재하는 agent 재시작은 USB rebind 없이 완료되는 것을 확인
- Dashboard와 동일한 별도 SSH DAQ 초기화 경로로 VIA parent hub port 1을 실제
  전원 재인가한 뒤 `/dev/daq0`, `bio4704`, 100–500 ms calibration sample 및
  start/stop HDF5 session 복구를 확인
- USB-4704의 `USBDEVFS_RESET` fallback을 제거: 실제 장치에서 60초 이상
  block되어 systemd `ExecStartPre` timeout을 유발한 것이 확인됨
- 로컬 자동 테스트 `47 passed`

Artifacts:

- `dist/5.15.0-1105-raspi/`
- `dist/usb4704-5.15.0-1105-raspi-arm64.tar.gz`

## Remaining hardware gates

The following require calibrated sensors, safe wiring, or a deliberate ground-test
procedure. No output or trigger command was issued during the completed tests.

1. Raspberry Pi power path를 보강하고 재검증. USB-4704는 bus-powered 500 mA로
   보고하며, 실제 재연결 시 Pi kernel에 `Undervoltage detected`가 기록됐다.
   정격 Pi PSU 또는 외부 전원형 USB hub 적용 후 장시간 시험이 필요하다.
2. Verify calibrated AI values against measurement equipment.
3. Verify DI/DO loopback, AO, and counter operation with safe loads.
4. Run a long-duration 5 kS/s buffered-AI overrun and USB hotplug/reconnect test.
5. Upload and verify Arduino Nano GPIO/pull-down/debounce wiring.
6. Perform the 60 m Ethernet disconnect/recovery and full ground-test acceptance.

## User-space boundary

The public Advantech package contains full kernel source but only x86-64
DAQNavi user-space libraries. This port therefore provides the kernel driver,
installation lifecycle, direct diagnostics, and a TMS-specific native
buffered-AI wrapper. Existing third-party applications which require the
DAQNavi `libbiodaq.so` API still need an Advantech AArch64 library package or
their own compatibility layer.
