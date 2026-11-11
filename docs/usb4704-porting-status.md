# USB-4704 드라이버 지원·검증 현황

기준일: **2026-11-11**. 현재 운영 PC와 이전 Raspberry Pi 검증을 구분한다.

## 현재 운영: Ubuntu x86_64 DAQ PC

| 항목 | 확인 값 |
|---|---|
| 장치 | hostname `tms`, `10.47.0.2` |
| OS/CPU | Ubuntu 22.04.5, x86_64 |
| 커널 | `6.8.0-138-generic` |
| 컴파일러 | GCC 12 |
| DKMS | `advantech-usb4704/20260306` 설치 |
| 모듈 | `biokernbase`, `bio4704` |
| USB/노드 | `1809:4704`, `/dev/daq0`, plugdev 권한 |
| 서비스 | `tms-agent`, `127.0.0.1:29100` |

현재 장치는 공급사 커널 소스를 실행 중인 커널에 맞춰 직접 빌드했다.
설치된 DKMS의 MAKE는 `env make ... CC=gcc-12 modules`를 사용한다.
재현 절차와 저장소 installer의 AArch64 제한은
[설치·관리](current-deployment.md)에 명시한다.

## 현재 검증 결과

- AI0·AI1 native buffered-AI, 5 kHz 수집·종료·재취득 두 번 확인.
- 노트북의 ID/Password SSH 터널과 DAQ PC의 로컬 loopback GUI 확인.
- 보정 저장 후 재시작 유지 및 서버 프로파일 조회 확인.
- 실장비 MA80 검증: 16,100샘플, 표시 배열과 HDF5 저장값 정확히 일치.
- HDF5/CSV 결과 분석 값 일치, 노트북과 DAQ PC의 CSV 바이트 일치.
- GUI 저장 폴더 선택, 지정 위치의 HDF5·CSV, 재실행 후 경로 유지 확인.
- 전체 자동 테스트 196개 통과, Linux frozen 실행 파일 자체 검사 통과.

보정 프로그램의 저장·조회 검증은 센서의 기준계 정확도 검증과 다르다.
위 수치는 해당 입력 시험 결과이며 최대 속도·장시간·출력 기능의 완료 판정이 아니다.

## Raspberry Pi ARM64 경로와 이전 검증

현재 소스는 ARM64 호환 코드와 다음 빌드 도구를 유지한다.

- `scripts/build-jammy-arm64.sh`: 기본 `5.15.0-1105-raspi` 크로스 빌드.
- `JAMMY_KERNEL_RELEASE`로 대상 커널 선택.
- `scripts/build-native-arm64.sh`: 대상 ARM64에서 네이티브 빌드.
- `packaging/install-prebuilt.sh`: 커널 vermagic과 AArch64를 확인하는 설치기.
- `scripts/install-dkms.sh`: AArch64 전용 설치기.

예전 검증 환경은 Ubuntu 22.04 ARM64 / Raspberry Pi 4 / `5.15.0-1105-raspi`와
후속 `5.15.0-1110-raspi`였다. 모듈 적재, 장치 설명, buffered-AI, SSH 단절 후
수집 유지, 로그 회수 및 종료·복구 반복 시험을 수행했다.
[2026-11-04 이력](daq-session-recovery-20261104.md)은 당시 환경과 수치를 보존한다.
그 문서의 테스트 개수를 현재 전체 테스트 개수로 해석하지 않는다.

기본 ARM64 크로스 빌드:

```bash
./scripts/build-jammy-arm64.sh
```

다른 Pi 커널:

```bash
JAMMY_KERNEL_RELEASE=5.15.0-1110-raspi ./scripts/build-jammy-arm64.sh
```

생성물은 `dist/<kernel>/`와 `dist/usb4704-<kernel>-arm64.tar.gz`다.
현재 x86_64 PC에는 ARM64 생성물을 설치하지 않는다. 모듈은 대상의 실행 커널과
정확히 일치해야 한다.

## 드라이버·사용자 공간 범위

공통 모듈 `biokernbase`와 USB-4702/4704 모듈 `bio4704`를 제공한다.
TMS의 Python wrapper는 vendor FAI ABI, ioctl, mmap 상태·사용자 버퍼를 직접 사용한다.
공개 공급사 패키지의 독점 x86_64 DAQNavi 사용자 라이브러리·데몬은 이 프로젝트의
필수 런타임이 아니며 ARM64 호환 라이브러리를 제공한다고 주장하지 않는다.
소스 출처는 [SOURCE.md](../vendor/advantech-daqnavi/SOURCE.md)를 참고한다.

`GET_USB_FLAG` STALL 펌웨어에서는 내부 FIFO 초과 상태 조회를 중단한다.
호스트 버퍼·샘플 누락 검사는 유지되지만 내부 FIFO 상태의 증명은 아니다.
USB 종료·복구 수정은 [기술 규격](system-requirements.md)에 정리했다.

## 남은 실장비 검증

1. 센서 기준 전압·하중·압력에 의한 정확도.
2. 실제 Nano D5/pull-down/점화 신호 배선과 debounce.
3. 최대 취득 속도와 장시간 overrun·hotplug 반복.
4. 새 커널로의 DKMS 자동 재빌드와 재부팅 후 확인.
5. 60 m Ethernet 장애·복구와 전체 시험 절차.
6. 안전한 부하에서 AO·DI/DO·counter 시험.
7. 현재 GUI 기능의 Windows 실기기 검증.

Pi에서 확인했던 저전압 경고는 당시 환경의 기록이다. x86_64 현재 장치에서 같은
경고가 확인됐다는 뜻이 아니다. 전원·허브 조건은 장치별로 검증한다.
