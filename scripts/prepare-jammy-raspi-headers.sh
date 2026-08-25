#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)

kernel_release=${JAMMY_KERNEL_RELEASE:-5.15.0-1105-raspi}
kernel_abi=${kernel_release%-raspi}

case "$kernel_release" in
  5.15.0-1061-raspi)
    default_package_version=5.15.0-1061.64
    default_common_sha=799b2e434f34b6aa7132154896777880cc53670f7cecf80cb6aa621c21ed04d9
    default_flavour_sha=f8cc8d707e56c249c16c206998360a999b75ce91c93fc23f856950cd12d53136
    ;;
  5.15.0-1105-raspi)
    default_package_version=5.15.0-1105.108
    default_common_sha=2253092187c88e4f8ac6917b386dc368cc14043ec3f66fc5b2ca23380f0115f4
    default_flavour_sha=dbe58cdeba6eea578ba17f3d1d475a0d91c9f4f4c1fa7f6fec1a68c5701e59e3
    ;;
  *)
    echo "Unsupported pinned Jammy raspi kernel: $kernel_release" >&2
    echo "Set KERNEL_DIR directly when building a different installed Jammy kernel." >&2
    exit 2
    ;;
esac

package_version=${JAMMY_HEADER_PACKAGE_VERSION:-$default_package_version}
if [[ "$package_version" != "$default_package_version" ]]; then
  echo "Unsupported header package for $kernel_release: $package_version" >&2
  exit 2
fi

cache_dir="$repo_root/build/cache/jammy-raspi-headers/$kernel_release"
# Kbuild resolves symlinks and rejects a source path containing spaces. Keep
# extracted headers outside this repository because its workspace name may
# legitimately contain spaces.
extract_root="${USB4704_HEADER_EXTRACT_ROOT:-/tmp/usb4704-jammy-headers-$(id -u)/$kernel_release}"
base_url=https://ports.ubuntu.com/ubuntu-ports/pool/main/l/linux-raspi

common_deb="linux-raspi-headers-${kernel_abi}_${package_version}_arm64.deb"
flavour_deb="linux-headers-${kernel_release}_${package_version}_arm64.deb"
common_sha=$default_common_sha
flavour_sha=$default_flavour_sha

mkdir -p "$cache_dir" "$extract_root"

download() {
  local filename=$1
  if [[ ! -f "$cache_dir/$filename" ]]; then
    echo "Downloading $filename" >&2
    curl --fail --location --retry 3 --output "$cache_dir/$filename" "$base_url/$filename"
  fi
}

download "$common_deb"
download "$flavour_deb"

printf '%s  %s\n' "$common_sha" "$cache_dir/$common_deb" | sha256sum --check - >&2
printf '%s  %s\n' "$flavour_sha" "$cache_dir/$flavour_deb" | sha256sum --check - >&2

dpkg-deb --extract "$cache_dir/$common_deb" "$extract_root"
dpkg-deb --extract "$cache_dir/$flavour_deb" "$extract_root"

kernel_dir="$extract_root/usr/src/linux-headers-$kernel_release"
test -f "$kernel_dir/Makefile"

rebuild_host_helpers() {
  local host_cc=${HOSTCC:-cc}
  local mod_dir="$kernel_dir/scripts/mod"
  local genksyms_dir="$kernel_dir/scripts/genksyms"
  local -a modpost_sources=(
    "$mod_dir/modpost.c"
    "$mod_dir/file2alias.c"
    "$mod_dir/sumversion.c"
  )

  if [[ -f "$mod_dir/symsearch.c" ]]; then
    modpost_sources+=("$mod_dir/symsearch.c")
  fi

  echo "Rebuilding kernel host helpers for $(uname -m)" >&2
  "$host_cc" -O2 -o "$kernel_dir/scripts/basic/fixdep" \
    "$kernel_dir/scripts/basic/fixdep.c"
  "$host_cc" -O2 -I"$mod_dir" -o "$mod_dir/modpost" "${modpost_sources[@]}"
  "$host_cc" -O2 -I"$genksyms_dir" -o "$genksyms_dir/genksyms" \
    "$genksyms_dir/genksyms.c" \
    "$genksyms_dir/parse.tab.c" \
    "$genksyms_dir/lex.lex.c"

  if [[ -f "$kernel_dir/scripts/recordmcount.c" ]]; then
    "$host_cc" -O2 -I"$kernel_dir/scripts" -o "$kernel_dir/scripts/recordmcount" \
      "$kernel_dir/scripts/recordmcount.c"
  fi
}

if [[ $(uname -m) != aarch64 ]]; then
  rebuild_host_helpers
fi

printf '%s\n' "$kernel_dir"
