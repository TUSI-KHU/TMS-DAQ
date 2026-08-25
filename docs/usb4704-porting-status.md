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
- Pi `192.168.0.214`에서 두 모듈을 실제 적재하고 USB `1809:4704`,
  `/sys/class/daq/daq0`, `/dev/daq0`, description ioctl smoke test 통과
- `tms-agent`가 `tms:plugdev` systemd 서비스로 설치되어 `127.0.0.1:29100`만
  수신하도록 확인
- 실제 USB-4704 native buffered-AI를 5 kS/s로 수집하여 HDF5에 18,950개
  연속 sample index를 기록하고, 원격과 SFTP 회수본의 SHA-256 일치 확인
- 실제 password SSH local forwarding을 끊고 다시 연결한 뒤에도 Pi 수집이
  계속되고 session을 정상 종료하는지 확인
- 재설치 후 systemd restart 경로로 5 kS/s data block 수신과 HDF5 기록 재확인
- 로컬 자동 테스트 `24 passed`

Artifacts:

- `dist/5.15.0-1105-raspi/`
- `dist/usb4704-5.15.0-1105-raspi-arm64.tar.gz`

## Remaining hardware gates

The following require calibrated sensors, safe wiring, or a deliberate ground-test
procedure. No output or trigger command was issued during the completed tests.

1. Verify calibrated AI values against measurement equipment.
2. Verify DI/DO loopback, AO, and counter operation with safe loads.
3. Run a long-duration 5 kS/s buffered-AI overrun and USB hotplug/reconnect test.
4. Upload and verify Arduino Nano GPIO/pull-down/debounce wiring.
5. Perform the 60 m Ethernet disconnect/recovery and full ground-test acceptance.

## User-space boundary

The public Advantech package contains full kernel source but only x86-64
DAQNavi user-space libraries. This port therefore provides the kernel driver,
installation lifecycle, direct diagnostics, and a TMS-specific native
buffered-AI wrapper. Existing third-party applications which require the
DAQNavi `libbiodaq.so` API still need an Advantech AArch64 library package or
their own compatibility layer.
