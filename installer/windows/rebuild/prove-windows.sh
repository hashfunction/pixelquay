#!/usr/bin/env bash
# Isolated library-only proof. No app publish, package registration, or signing.
# Copyright 2026 Trieflow LLC; MIT.
set -euo pipefail
if [[ ${MSYSTEM:-} != CLANG64 || $# != 2 ]]; then
  echo 'Usage (CLANG64 shell): prove-windows.sh NEW_WORK_DIRECTORY NEW_EVIDENCE_DIRECTORY' >&2
  exit 64
fi
proof_here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
proof_work=$(cygpath -au -- "$1")
proof_evidence=$(cygpath -au -- "$2")
proof_python=/clang64/bin/python.exe
proof_driver="$proof_here/proof_driver.py"
export LANG=C.UTF-8
export LC_ALL=C.UTF-8
export MINGW_ARCH=clang64
export PACKAGER='Local PixelQuay retained-LGPL library proof'
"$proof_python" "$proof_driver" prepare --work "$proof_work" --evidence "$proof_evidence"
# Preserve a clear failure outcome even if a later native command fails.
trap 'printf "Native command failed at line %s (exit %s)\n" "$LINENO" "$?" >> "$proof_evidence/failure.txt"' ERR
"$proof_python" "$proof_driver" environment --msys "$(cygpath -w /)" --output "$proof_evidence/environment-before.json"
pacman -Q > "$proof_evidence/installed-packages-before.txt"
pacman -Qi > "$proof_evidence/installed-package-metadata.txt"
mapfile -t proof_packages < <(pacman -Qq)
mkdir "$proof_work/package-cache"
# Download/verify the exact currently installed packages. A repository update
# between setup and this step is rejected by the final set/version comparison.
pacman -Sw --noconfirm --cachedir "$proof_work/package-cache" "${proof_packages[@]}" > "$proof_evidence/package-download.txt" 2>&1
"$proof_python" "$proof_driver" archives --work "$proof_work" --evidence "$proof_evidence"
for proof_variant in original modified; do
  (
    cd -- "$proof_work/$proof_variant"
    export PKGDEST="$proof_work/$proof_variant/packages"
    # All source inputs already exist locally. Never skip source verification,
    # tests, or install/update build dependencies during either build.
    makepkg-mingw --verifysource
    makepkg-mingw --cleanbuild --log
  ) > "$proof_evidence/$proof_variant-build.txt" 2>&1
done
/clang64/bin/clang.exe -std=c11 -Wall -Wextra -Werror -municode \
  -I"$proof_work/source/upstream/libdatrie-0.2.14" "$proof_here/datrie_probe.c" -o "$proof_work/datrie_probe.exe" \
  > "$proof_evidence/probe-compile.txt" 2>&1
for proof_variant in original modified; do
  proof_dll="$proof_work/$proof_variant/pkg/mingw-w64-clang-x86_64-libdatrie/clang64/bin/libdatrie-1.dll"
  "$proof_work/datrie_probe.exe" "$(cygpath -w "$proof_dll")" "$proof_variant" "$(cygpath -w "$proof_work/$proof_variant/probe-work")" \
    > "$proof_evidence/$proof_variant-probe.json" 2> "$proof_evidence/$proof_variant-probe-stderr.txt"
  proof_wrong_mode=modified
  if [[ $proof_variant == modified ]]; then proof_wrong_mode=original; fi
  if "$proof_work/datrie_probe.exe" "$(cygpath -w "$proof_dll")" "$proof_wrong_mode" "$(cygpath -w "$proof_work/$proof_variant/negative-probe-work")" \
    > "$proof_evidence/$proof_variant-negative-stdout.txt" 2> "$proof_evidence/$proof_variant-negative-stderr.txt"; then
    echo 'Wrong library variant unexpectedly passed' >&2; exit 1
  else
    proof_status=$?
    printf '%s\n' "$proof_status" > "$proof_evidence/$proof_variant-negative-exit.txt"
    if [[ $proof_status != 4 ]]; then echo 'Expected precise marker rejection exit 4' >&2; exit 1; fi
  fi
done
"$proof_python" "$proof_driver" environment --msys "$(cygpath -w /)" --output "$proof_evidence/environment-after.json"
"$proof_python" "$proof_driver" verify --work "$proof_work" --evidence "$proof_evidence"
