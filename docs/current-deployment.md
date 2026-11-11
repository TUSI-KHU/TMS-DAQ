# 현재 장비·설치·관리

기준일: **2026-11-11**. 패키지 버전은 `tusi-tms 0.1.0`이며 아래 기능을 포함한
현재 작업본을 설치했다. 예전 Pi 전용 프로그램이나 홈의 임시 배포본을 실행하지 않는다.

## 현재 배포

| 역할 | 현재 값 |
|---|---|
| 노트북 | `sb-ThinkPad-X1-Carbon-Gen-9`, 원격 GUI |
| DAQ PC | hostname `tms`, Ubuntu 22.04.5, x86_64 |
| DAQ 커널 | `6.8.0-138-generic` |
| 노트북 유선 | `10.47.0.1/24`, `enx00e04c3607a2` |
| DAQ PC 유선 | `10.47.0.2/24`, `enx00e04c3603ee` |
| SSH | `tms@10.47.0.2:22`, 현장 ID/Password 인증 |
| telemetry | DAQ PC `127.0.0.1:29100` |
| DAQ | USB `1809:4704`, `/dev/daq0`, AI0·AI1, 5 kHz |
| DKMS | `advantech-usb4704/20260306`, x86_64 현재 커널에 설치 |
| GUI 기능 | 원격/로컬, 센서별 보정 저장·불러오기, MA80, 결과 분석, 저장 폴더 선택 |

인터페이스 이름은 이 장비의 실측값이다. 다른 장비에서는 이름을 확인하고 사용한다.
현재 PC에서는 Pi 전용 `eth0`/`wlan0` Wi-Fi failover를 활성화하지 않는다.

## 실행·파일 위치

| 내용 | 위치 |
|---|---|
| 현재 유지보수 소스 | DAQ PC `~/TMS-DAQ/` |
| 설치된 Python 실행본 | `/opt/tusi-tms/.venv/` |
| 서비스 | `tms-agent.service` |
| 로컬 GUI 명령 | `/usr/local/bin/tusi-tms-local` |
| 앱 메뉴 | `/usr/share/applications/tusi-tms-local.desktop` |
| 영구 센서 보정·서비스 설정 | `/etc/tusi-tms/config.yaml` |
| 로컬 GUI 설정 | `~/.config/tusi-tms/dashboard-local.yaml` |
| 원본 HDF5 | `/var/lib/tusi-tms/logs/` |
| GUI HDF5·CSV 기본 폴더 | `~/TUSI-TMS/logs/` |
| DKMS 유지보수 소스 | `/usr/src/advantech-usb4704-20260306/` |
| 모듈 자동 적재 | `/etc/modules-load.d/advantech-usb4704.conf` |

`~/TUSI-TMS`는 측정·검증 데이터 폴더이며 이전 프로그램이 아니다.
GUI에서 선택한 별도 저장 폴더도 데이터로 보존한다. GUI 목적지를 바꿔도
서비스 원본 경로는 위 위치에 유지한다.

## 실행과 상태 확인

DAQ PC의 앱 메뉴 **TUSI TMS (DAQ PC 로컬)** 또는:

```bash
tusi-tms-local
```

노트북 프로젝트 루트:

```bash
./scripts/run-tms-dashboard.sh
```

DAQ PC에서 확인:

```bash
systemctl is-active tms-agent.service
systemctl is-enabled tms-agent.service
journalctl -u tms-agent.service -n 80 --no-pager
ls -l /dev/daq0
lsusb -d 1809:4704
dkms status
/opt/tusi-tms/.venv/bin/python -m pi.recovery_probe
```

`pi.recovery_probe`는 AI0·AI1의 실제 입력 취득/종료를 두 번 수행한다.
측정 중이 아닌 상태에서 실행한다. GUI는 일반 앱이며 상시 user service가 아니다.
작업 중 `systemd-run --user`로 실행한 GUI unit이 이후 사라져도 앱 설치 삭제를 뜻하지 않는다.

## 신규 x86_64 장치 설치

현재 PC에는 설치가 끝났다. 다음은 같은 종류의 새 Ubuntu 장치에 적용하는 절차다.
기존 DKMS 등록이 있으면 먼저 `dkms status`를 확인하고 중복 등록하지 않는다.

```bash
sudo apt update
sudo apt install dkms build-essential gcc-12 linux-headers-$(uname -r) \
  python3-venv python3-numpy python3-h5py python3-serial python3-yaml
```

`Makefile`, `vendor/`, `packaging/`를 포함한 현재 소스 루트에서:

```bash
sudo install -d /usr/src/advantech-usb4704-20260306
sudo cp Makefile /usr/src/advantech-usb4704-20260306/
sudo cp -a vendor /usr/src/advantech-usb4704-20260306/
sudo cp packaging/dkms.conf /usr/src/advantech-usb4704-20260306/
sudo sed -i 's/MAKE\[0\]="make /MAKE[0]="env make /' /usr/src/advantech-usb4704-20260306/dkms.conf
sudo sed -i 's/ modules"/ CC=gcc-12 modules"/' /usr/src/advantech-usb4704-20260306/dkms.conf
sudo dkms add -m advantech-usb4704 -v 20260306
sudo dkms build -m advantech-usb4704 -v 20260306 -k "$(uname -r)"
sudo dkms install -m advantech-usb4704 -v 20260306 -k "$(uname -r)"
sudo install -m 0644 packaging/71-advantech-usb4704.rules /etc/udev/rules.d/
printf 'biokernbase\nbio4704\n' | sudo tee /etc/modules-load.d/advantech-usb4704.conf
sudo depmod -a
sudo udevadm control --reload-rules
sudo modprobe biokernbase
sudo modprobe bio4704
```

이 장치의 커널은 GCC 12로 빌드됐다. 다른 커널이면 해당 커널의 빌드 도구와
헤더를 확인한다. `env make`는 DKMS가 추가하는 `KERNELRELEASE`가 공급사
중첩 Makefile의 Kbuild 경로를 잘못 선택하지 않게 하는 현재 장치의 설정이다.
이 설정은 설치된 `/usr/src/.../dkms.conf`에 반영되어 있다. 저장소의
`scripts/install-dkms.sh`와 prebuilt installer에는 AArch64 제한이 남아 있으므로
x86_64에 그대로 실행하지 않는다.

`tms` 로그인 사용자를 준비한 뒤 agent를 설치한다.

```bash
sudo ./scripts/install-tms-agent.sh
```

Ubuntu의 오래된 setuptools가 프로젝트 이름을 `UNKNOWN`으로 만드는 환경에서는
venv의 `pip`, `setuptools>=68`, `wheel`을 갱신한 뒤 현재 소스를
`--no-build-isolation`으로 다시 설치한다. 현재 로컬 GUI 설치기는 이를 처리한다.

```bash
sudo apt install libxcb-cursor0 libxkbcommon-x11-0 libopengl0 libegl1
sudo ./scripts/install-local-dashboard.sh
```

PC의 네트워크 인터페이스가 `eth0`/`wlan0`가 아니면 Pi 전용 failover는 사용하지 않는다.
기존 설치 스크립트가 이를 등록한 신규 PC에서는 다음으로 끈다.

```bash
sudo systemctl disable --now tms-network-failover.service
```

## 현재 실행본 갱신

`~/TMS-DAQ`를 최신 소스로 맞춘 후, 측정을 종료하고 GUI를 닫은 상태에서 실행한다.
의존성을 포함해 설치할 때는 위 로컬 GUI 설치기를 사용한다. 이미 의존성이 준비된
같은 환경에서 코드만 갱신할 때:

```bash
sudo /opt/tusi-tms/.venv/bin/python -m pip install \
  --no-deps --no-build-isolation --force-reinstall /home/tms/TMS-DAQ
```

서비스 코드가 바뀌었으면 `sudo systemctl restart tms-agent.service` 후 입력 검증을
수행하고 GUI를 다시 연다. 문서만 바뀌면 서비스 재시작이 필요 없다.
NumPy만 올려 apt의 오래된 h5py와 섞지 않는다. GUI 설치기는 NumPy·h5py를 함께
맞추며, 현재 장치는 NumPy 2.2.6 / h5py 3.16.0 조합으로 검증했다.

노트북의 소스와 `dist/TUSI-TMS`를 같은 변경으로 빌드하고 GUI를 재실행한다.

## 네트워크와 SSH 복구

`nmcli device status`, `ip -br addr`, `ip route get 10.47.0.2`로 실제 유선 경로를 확인한다.
새 장치가 DHCP 주소를 받지 못하고 NetworkManager 로그에 `no address available`이
반복되면 단일 주소 `.2` 풀이 과거 임대에 묶였을 수 있다. 현재 유선 프로필에서
임시로 풀을 `.2`~`.10`으로 넓혀 접속하고 DAQ PC를 `.2/24` 고정으로 설정한 후
운영 프로필을 확인한다. 현재 PC는 `.2` 고정이며 `.3` 임시 주소는 제거했다.

호스트 키 변경은 `StrictHostKeyChecking`을 끄는 대신 기존 신뢰 경로나 장치
콘솔에서 공개 키 fingerprint를 대조한 뒤 해당 주소의 `known_hosts`만 갱신한다.
2026-11-11 현재 DAQ PC ED25519 fingerprint:

```text
SHA256:YBRHvZMp0uKpf/KF7SG/TlsXxjAh/PKKjUNylGtfFXQ
```

이 값은 현재 장치 확인용 기록이며 다른 장치·재설치 후 키를 자동 신뢰하는 값이 아니다.

## 홈 폴더 정리 기준

2026-11-11 유지보수에서 홈의 이전 임시 배포본 네 개를 제거하고
`~/TMS-DAQ`를 현재 소스로 통합한다.

- 제거 대상: `tms-slave-source-20261111`, `tms-local-gui-source`,
  `tms-ma80-source`, `tms-folder-source`, 코드 백업 `tms-before-ma80.tar.gz`.
- 유지: `/opt/tusi-tms`, `/usr/src/advantech-usb4704-20260306`, 현재 소스 `~/TMS-DAQ`.
- 데이터 유지: `~/TUSI-TMS`, `/var/lib/tusi-tms/logs`, 사용자가 선택한 저장 폴더.
- 설정 유지: `/etc/tusi-tms/config.yaml`, `~/.config/tusi-tms/dashboard-local.yaml`.
- 이전 소스의 `config.yaml.backup-f18f5f41`은 보정 참고 자료로
  `~/.config/tusi-tms/legacy-calibration-backups/`에 따로 보존한다.

설치된 패키지는 소스 폴더를 직접 import하는 editable 설치가 아니다. 유지보수
소스는 한 위치에 두고, 임시 배포 폴더를 실제 실행 경로로 사용하지 않는다.
