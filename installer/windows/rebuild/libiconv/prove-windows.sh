#!/usr/bin/env bash
# Metadata-only proof for libcharset-1.dll and libiconv-2.dll. MIT.
set -euo pipefail
if [[ ${MSYSTEM:-} != CLANG64 || $# != 2 ]]; then
  echo 'Usage (CLANG64): prove-windows.sh NEW_WORK NEW_EVIDENCE' >&2; exit 64
fi
proof_here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
proof_work=$(cygpath -au -- "$1")
proof_evidence=$(cygpath -au -- "$2")
proof_python=/clang64/bin/python.exe
export LANG=C.UTF-8 LC_ALL=C.UTF-8 MINGW_ARCH=clang64
export PACKAGER='Local PixelQuay retained-LGPL libiconv proof'
"$proof_python" "$proof_here/proof_driver.py" prepare --work "$proof_work" --evidence "$proof_evidence"
trap 'printf "Native command failed at line %s (exit %s)\n" "$LINENO" "$?" >> "$proof_evidence/failure.txt"' ERR
"$proof_python" "$proof_here/proof_driver.py" environment --msys "$(cygpath -w /)" --output "$proof_evidence/environment-before.json"
pacman -Q > "$proof_evidence/installed-packages-before.txt"
mapfile -t proof_packages < <(pacman -Qq)
mkdir "$proof_work/package-cache"
pacman -Sw --noconfirm --cachedir "$proof_work/package-cache" "${proof_packages[@]}" > "$proof_evidence/package-download.txt" 2>&1
"$proof_python" "$proof_here/proof_driver.py" archives --work "$proof_work" --evidence "$proof_evidence"
for proof_variant in original modified; do
  set +e
  (
    set -e; cd -- "$proof_work/$proof_variant"; export PKGDEST="$proof_work/$proof_variant/packages"
    # Exact signature bytes were independently verified in NativeSignatureVerification.json.
    # makepkg still verifies every declared content hash here; no network source is used.
    makepkg-mingw --verifysource --skippgpcheck
    makepkg-mingw --cleanbuild --log --skippgpcheck
  ) > "$proof_evidence/$proof_variant-build.txt" 2>&1
  proof_status=$?; set -e
  if [[ $proof_status != 0 ]]; then
    test_log="$proof_work/$proof_variant/src/build-CLANG64/tests/test-suite.log"
    if [[ -f $test_log ]]; then cp -- "$test_log" "$proof_evidence/$proof_variant-test-suite.log.txt"; fi
    exit "$proof_status"
  fi
done
/clang64/bin/clang.exe -std=c11 -Wall -Wextra -Werror -municode "$proof_here/iconv_probe.c" -o "$proof_work/iconv_probe.exe" > "$proof_evidence/probe-compile.txt" 2>&1
for proof_variant in original modified; do
  root="$proof_work/$proof_variant/pkg/mingw-w64-clang-x86_64-libiconv/clang64/bin"
  "$proof_work/iconv_probe.exe" "$(cygpath -w "$root/libcharset-1.dll")" "$(cygpath -w "$root/libiconv-2.dll")" "$proof_variant" > "$proof_evidence/$proof_variant-probe.json" 2> "$proof_evidence/$proof_variant-probe-stderr.txt"
  wrong=modified; [[ $proof_variant == modified ]] && wrong=original
  if "$proof_work/iconv_probe.exe" "$(cygpath -w "$root/libcharset-1.dll")" "$(cygpath -w "$root/libiconv-2.dll")" "$wrong" > "$proof_evidence/$proof_variant-negative-stdout.txt" 2> "$proof_evidence/$proof_variant-negative-stderr.txt"; then
    echo 'Wrong marker mode unexpectedly passed' >&2; exit 1
  else
    status=$?; printf '%s\n' "$status" > "$proof_evidence/$proof_variant-negative-exit.txt"
    [[ $status == 4 ]] || { echo 'Expected marker rejection exit 4' >&2; exit 1; }
  fi
done
"$proof_python" "$proof_here/proof_driver.py" environment --msys "$(cygpath -w /)" --output "$proof_evidence/environment-after.json"
"$proof_python" "$proof_here/proof_driver.py" verify --work "$proof_work" --evidence "$proof_evidence"
