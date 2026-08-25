#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
machine=$(uname -m)
kernel_release=${KERNEL_RELEASE:-$(uname -r)}
kernel_dir=${KERNEL_DIR:-/lib/modules/$kernel_release/build}

if [[ "$machine" != aarch64 ]]; then
  echo "Native build requires AArch64; this host is $machine." >&2
  exit 1
fi

KERNEL_RELEASE="$kernel_release" \
KERNEL_DIR="$kernel_dir" \
ARCH=arm64 \
OUT_DIR="$repo_root/dist/$kernel_release" \
  "$repo_root/scripts/build-modules.sh"

