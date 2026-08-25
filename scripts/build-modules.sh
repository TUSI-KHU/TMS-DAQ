#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
kernel_release=${KERNEL_RELEASE:-$(uname -r)}
kernel_dir=${KERNEL_DIR:-/lib/modules/$kernel_release/build}
target_arch=${ARCH:-}
cross_prefix=${CROSS_COMPILE:-}
compiler=${CC:-}
out_dir=${OUT_DIR:-$repo_root/dist/$kernel_release}

test -d "$kernel_dir" || {
  echo "Kernel headers not found: $kernel_dir" >&2
  exit 1
}

stage=$(mktemp -d "${TMPDIR:-/tmp}/usb4704-build.XXXXXX")
cleanup() {
  if [[ ${KEEP_BUILD:-0} == 1 ]]; then
    echo "Build tree kept at $stage" >&2
  else
    rm -rf -- "$stage"
  fi
}
trap cleanup EXIT

cp -a "$repo_root/vendor" "$stage/"
cp "$repo_root/Makefile" "$stage/"
mkdir -p "$out_dir" "$stage/out"

# The vendor makefiles pass KSRC and M without shell quoting. Bridge the kernel
# headers through the no-space temporary tree so builds also work when the
# repository itself lives in a directory containing spaces.
ln -s "$kernel_dir" "$stage/kernel-headers"
effective_kernel_dir="$stage/kernel-headers"

make_args=(
  "KERNEL_RELEASE=$kernel_release"
  "KERNEL_DIR=$effective_kernel_dir"
  "OUT_DIR=$stage/out"
)

[[ -n "$target_arch" ]] && make_args+=("ARCH=$target_arch")
[[ -n "$cross_prefix" ]] && make_args+=("CROSS_COMPILE=$cross_prefix")
[[ -n "$compiler" ]] && make_args+=("CC=$compiler")

echo "Building USB-4704 modules for $kernel_release" | tee "$out_dir/build.log"
echo "Kernel headers: $kernel_dir" | tee -a "$out_dir/build.log"
echo "Compiler: ${compiler:-default}" | tee -a "$out_dir/build.log"

make -C "$stage" "${make_args[@]}" modules 2>&1 | tee -a "$out_dir/build.log"

install -m 0644 "$stage/out/biokernbase.ko" "$out_dir/biokernbase.ko"
install -m 0644 "$stage/out/bio4704.ko" "$out_dir/bio4704.ko"
install -m 0644 "$repo_root/packaging/71-advantech-usb4704.rules" "$out_dir/71-advantech-usb4704.rules"
install -m 0755 "$repo_root/packaging/install-prebuilt.sh" "$out_dir/install.sh"
install -m 0644 "$repo_root/tools/usb4704-smoke.c" "$out_dir/usb4704-smoke.c"
install -m 0644 "$repo_root/tools/usb4704-readonly-diag.c" "$out_dir/usb4704-readonly-diag.c"

"$repo_root/scripts/verify-modules.sh" \
  "$out_dir/biokernbase.ko" "$out_dir/bio4704.ko" "$kernel_release" | \
  tee "$out_dir/verification.txt"

(
  cd "$out_dir"
  sha256sum biokernbase.ko bio4704.ko 71-advantech-usb4704.rules install.sh usb4704-smoke.c usb4704-readonly-diag.c > SHA256SUMS
)

archive="$repo_root/dist/usb4704-$kernel_release-arm64.tar.gz"
tar -C "$(dirname "$out_dir")" -czf "$archive" "$(basename "$out_dir")"

echo "Artifacts: $out_dir"
echo "Deployment archive: $archive"
