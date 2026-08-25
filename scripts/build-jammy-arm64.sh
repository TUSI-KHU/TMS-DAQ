#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
script_dir="$repo_root/scripts"
kernel_release=${JAMMY_KERNEL_RELEASE:-5.15.0-1105-raspi}

kernel_dir=$("$script_dir/prepare-jammy-raspi-headers.sh")

if [[ ${USB4704_USE_SYSTEM_CROSS_GCC:-0} == 1 ]] && command -v aarch64-linux-gnu-gcc >/dev/null; then
  compiler=aarch64-linux-gnu-gcc
  cross_prefix=aarch64-linux-gnu-
else
  tool_root=$("$script_dir/bootstrap-cross-toolchain.sh")
  compiler_bin=$(find "$tool_root/usr/bin" -maxdepth 1 -type f -name 'aarch64-linux-gnu-gcc-[0-9]*' | sort -V | tail -n 1)
  assembler=$(command -v aarch64-linux-gnu-as || true)
  if [[ -z "$assembler" ]]; then
    echo "Install binutils-aarch64-linux-gnu on the build host." >&2
    exit 1
  fi
  cross_prefix="$(dirname "$assembler")/aarch64-linux-gnu-"
  compiler="$compiler_bin -B$cross_prefix"
fi

KERNEL_RELEASE="$kernel_release" \
KERNEL_DIR="$kernel_dir" \
ARCH=arm64 \
CROSS_COMPILE="$cross_prefix" \
CC="$compiler" \
OUT_DIR="$repo_root/dist/$kernel_release" \
  "$script_dir/build-modules.sh"
