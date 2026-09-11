#!/usr/bin/env python3
"""Prepare and verify the native two-DLL libiconv proof. MIT."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(1, str(HERE.parent))
import libiconv_source
import receipt
from library_receipt import pe_inventory

_spec = importlib.util.spec_from_file_location("libdatrie_common_driver", HERE.parent / "proof_driver.py")
common = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(common)

PACKAGE = "mingw-w64-clang-x86_64-libiconv"
DLL_MEMBERS = {name: "clang64/bin/" + name for name in receipt.MARKERS}
LICENSE_MEMBERS = {
    "COPYING": "clang64/share/licenses/libiconv/COPYING",
    "COPYING.LIB": "clang64/share/licenses/libiconv/COPYING.LIB",
    "README": "clang64/share/licenses/libiconv/README",
    "libcharset/COPYING.LIB": "clang64/share/licenses/libiconv/libcharset/COPYING.LIB",
}


def prepare(work, evidence):
    work, evidence = common.checked_parents(work), common.checked_parents(evidence)
    if os.path.lexists(work) or os.path.lexists(evidence): raise FileExistsError("Fresh work/evidence required")
    commit = common.source_state(); inputs = common.tracked_inputs()
    work.mkdir(); evidence.mkdir()
    source_record = libiconv_source.materialize(HERE / "inputs/mingw-w64-libiconv-1.19-1.src.tar.zst", work / "source")
    recipe_files = ["libiconv-1.19.tar.gz", "libiconv-1.19.tar.gz.sig", "0002-fix-cr-for-awk-in-configure.all.patch", "0003-add-cp65001-as-utf8-alias.patch", "fix-pointer-buf.patch", "iconv.pc"]
    for variant in ("original", "modified"):
        root = work / variant; root.mkdir(); (root / "packages").mkdir()
        common.write_new(root / "PKGBUILD", (HERE / "recipes" / variant / "PKGBUILD").read_bytes())
        for name in recipe_files: common.write_new(root / name, (work / "source/recipe" / name).read_bytes())
        if variant == "modified": common.write_new(root / "001-local-markers.patch", (HERE / "001-local-markers.patch").read_bytes())
    common.write_json(evidence / "inputs.json", {"sourceCommit": commit, "inputs": inputs, "sourceReceipt": source_record})


def read_package(path, extracted):
    wanted = {".PKGINFO", ".BUILDINFO", *DLL_MEMBERS.values(), *LICENSE_MEMBERS.values()}
    found, seen, total = {}, set(), 0
    process = subprocess.Popen(["zstd", "-dc", str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        with tarfile.open(fileobj=process.stdout, mode="r|") as archive:
            for index, member in enumerate(archive):
                name = member.name.rstrip("/"); common._checked_path(name)
                if index > 4096 or name in seen: raise ValueError("Unbounded/duplicate package")
                seen.add(name); total += member.size
                if total > 64 * 1024 * 1024: raise ValueError("Package expansion bound")
                if name in wanted:
                    if not member.isreg() or member.size > 4 * 1024 * 1024: raise ValueError("Expected bounded regular member")
                    found[name] = archive.extractfile(member).read()
        common.drain_padding(process.stdout); process.stdout.close(); error = process.stderr.read()
        if process.wait(timeout=30): raise ValueError(error.decode(errors="replace"))
    finally:
        if process.poll() is None: process.kill(); process.wait()
        process.stdout.close(); process.stderr.close()
    if set(found) != wanted: raise ValueError("Missing package DLL/metadata/license member")
    for name, member in DLL_MEMBERS.items():
        if common.digest(found[member]) != common.file_record(extracted / member): raise ValueError(f"Package/stage mismatch: {name}")
    hashes = {name: hashlib.sha256(found[member]).hexdigest() for name, member in LICENSE_MEMBERS.items()}
    if hashes != libiconv_source.LICENSE_HASHES: raise ValueError("Packaged license bytes differ")
    return found, hashes


def verify(work, evidence):
    inputs = json.loads((evidence / "inputs.json").read_text())
    if inputs["sourceCommit"] != common.source_state() or inputs["inputs"] != common.tracked_inputs(): raise ValueError("Proof inputs changed")
    before = json.loads((evidence / "environment-before.json").read_text()); after = json.loads((evidence / "environment-after.json").read_text())
    common.validate_environment(before, after)
    archives = common.verify_archive_inputs(work / "package-cache", before, evidence / "package-inputs.json")
    if archives != json.loads((evidence / "package-inputs-before.json").read_text()): raise ValueError("Package inputs changed")
    results, licenses = {}, None
    probes = {mode: json.loads((evidence / f"{mode}-probe.json").read_text()) for mode in ("original", "modified")}
    for mode, version in (("original", "1.19-1"), ("modified", "1.19-1.1")):
        root = work / mode
        packages = list((root / "packages").glob(PACKAGE + "-[0-9]*.pkg.tar.zst"))
        if len(packages) != 1: raise ValueError("Expected one runtime package")
        extracted = root / "pkg" / PACKAGE
        members, current_licenses = read_package(packages[0], extracted)
        licenses = current_licenses if licenses is None else licenses
        if current_licenses != licenses: raise ValueError("Variant license files changed")
        pkginfo = members[".PKGINFO"].decode("utf-8"); buildinfo = members[".BUILDINFO"].decode("utf-8")
        required = [f"pkgname = {PACKAGE}", f"pkgver = {version}", "license = spdx:LGPL-2.1-or-later"]
        if not all(line in pkginfo.splitlines() for line in required): raise ValueError("Wrong package identity/license")
        if "pkgbuild_sha256sum = " + common.file_record(root / "PKGBUILD")["sha256"] not in buildinfo.splitlines(): raise ValueError("Recipe hash absent from BUILDINFO")
        if "buildenv = check" not in buildinfo.splitlines(): raise ValueError("Package build did not enable native checks")
        build = root / "src/build-CLANG64"
        libraries = {"libcharset-1.dll": build / "libcharset/lib/.libs/libcharset-1.dll", "libiconv-2.dll": build / "lib/.libs/libiconv-2.dll"}
        before_hashes = receipt.verify_post_test_hashes(libraries, build / "source-tests-before.sha256")
        after_hashes = receipt.verify_post_test_hashes(libraries, build / "source-tests-passed.sha256")
        if before_hashes != after_hashes: raise ValueError("Native tests changed a build DLL")
        mode_rows = {}; parsed_probe = receipt.parse_probe(probes[mode], mode)
        for name, member in DLL_MEMBERS.items():
            data = members[member]
            mode_rows[name] = {**common.digest(data), **pe_inventory(data), "libraryUnchangedByTests": True,
                "testedBuildLibrary": after_hashes[name], "probe": parsed_probe[name]}
        results[mode] = {"libraries": mode_rows, "package": {"name": packages[0].name, **common.file_record(packages[0])}, "nativeMakeCheckPassed": True}
        common.write_new(evidence / f"{mode}-PKGINFO.txt", pkginfo.encode()); common.write_new(evidence / f"{mode}-BUILDINFO.txt", buildinfo.encode())
        for candidate in (build / "config.log", build / "tests/test-suite.log"):
            if candidate.is_file(): common.write_new(evidence / f"{mode}-{candidate.name}.txt", candidate.read_bytes())
    receipt.validate_pair(results["original"]["libraries"], results["modified"]["libraries"], True, licenses)
    common.write_json(evidence / "library-proof.json", {"schemaVersion": 1, "sourceCommit": inputs["sourceCommit"], "variants": results,
        "nativeTwoDllReplacementProof": True, "environmentUnchanged": True, "historicalBinaryParityClaimed": False,
        "applicationReplacementVerified": False, "msixBuilt": False, "licenseConversionApplied": False, "licenseClearanceClaimed": False})


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("operation", choices=["prepare", "environment", "archives", "verify"])
    parser.add_argument("--work", type=Path); parser.add_argument("--evidence", type=Path); parser.add_argument("--msys", type=Path); parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if sys.platform != "win32": parser.error("Native proof requires Windows")
    if args.operation == "prepare": prepare(args.work, args.evidence)
    elif args.operation == "environment": common.environment(args.msys, args.output)
    elif args.operation == "archives":
        before = json.loads((args.evidence / "environment-before.json").read_text()); common.verify_archive_inputs(args.work / "package-cache", before, args.evidence / "package-inputs-before.json")
    else: verify(args.work, args.evidence)


if __name__ == "__main__": main()
