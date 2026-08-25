#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "Usage: $0 <biokernbase.ko> <bio4704.ko> <kernel-release>" >&2
  exit 2
fi

base_module=$1
device_module=$2
kernel_release=$3

for module in "$base_module" "$device_module"; do
  test -f "$module"
  file "$module"
  readelf -h "$module" | grep -Eq 'Machine:[[:space:]]+AArch64'
  vermagic=$(modinfo -F vermagic "$module")
  [[ "$vermagic" == "$kernel_release "* ]] || {
    echo "Unexpected vermagic for $module: $vermagic" >&2
    exit 1
  }
done

depends=$(modinfo -F depends "$device_module")
[[ ",$depends," == *,biokernbase,* ]] || {
  echo "bio4704.ko does not depend on biokernbase: $depends" >&2
  exit 1
}

modinfo -F alias "$device_module" | grep -q 'usb:v1809p4704'

echo "Verified AArch64 modules for $kernel_release"
echo "USB-4704 alias: $(modinfo -F alias "$device_module" | grep 'usb:v1809p4704' | head -n 1)"

