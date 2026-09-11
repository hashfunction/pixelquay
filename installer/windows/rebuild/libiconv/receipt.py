"""Fail-closed acceptance for the libcharset/libiconv replacement pair. MIT."""
import hashlib
from pathlib import Path
import re

from libiconv_source import LICENSE_HASHES

MARKERS = {
    "libcharset-1.dll": "pixelquay_libcharset_rebuild_marker",
    "libiconv-2.dll": "pixelquay_libiconv_rebuild_marker",
}
ORIGINAL_EXPORTS = {
    "libcharset-1.dll": ["libcharset_set_relocation_prefix", "locale_charset"],
    "libiconv-2.dll": ["_libiconv_version", "iconv_canonicalize", "libiconv", "libiconv_close", "libiconv_open", "libiconv_open_into", "libiconv_set_relocation_prefix", "libiconvctl", "libiconvlist", "locale_charset"],
}
API_CHECKS = {"libcharset-1.dll": 2, "libiconv-2.dll": 6}
SHIPPED_HASHES = {
    "libcharset-1.dll": "6e7794de2d9caa32e78f3685b69b01bb278f27e748ce447e41188bb00d0136a8",
    "libiconv-2.dll": "c9f9b9addeac620eeccb6a23fc5a423fa1244e18431c00e1219db00d479ea332",
}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_post_test_hashes(libraries, evidence):
    lines = Path(evidence).read_text(encoding="ascii").splitlines()
    actual = {}
    for line in lines:
        match = re.fullmatch(r"([0-9a-f]{64})  (libcharset-1\.dll|libiconv-2\.dll)", line)
        if not match or match.group(2) in actual: raise ValueError("Malformed/duplicate post-test hash")
        actual[match.group(2)] = match.group(1)
    if set(actual) != set(libraries): raise ValueError("Both post-test DLL hashes required")
    records = {}
    for name, path in libraries.items():
        value = sha256(path)
        if value != actual[name]: raise ValueError(f"Tests changed or did not bind {name}")
        records[name] = {"sha256": value, "bytes": Path(path).stat().st_size}
    return records


def parse_probe(value, mode):
    expected_keys = {"schemaVersion", "mode", "libraryPathMatched", "markersPresent", "libraries"}
    if set(value) != expected_keys or type(value["schemaVersion"]) is not int or value["schemaVersion"] != 1:
        raise ValueError("Malformed probe schema")
    if mode not in ("original", "modified") or value["mode"] != mode:
        raise ValueError("Probe variant mismatch")
    if type(value["libraryPathMatched"]) is not bool or value["libraryPathMatched"] is not True:
        raise ValueError("Exact loaded library paths not proven")
    if type(value["markersPresent"]) is not bool or value["markersPresent"] is not (mode == "modified"):
        raise ValueError("Probe marker mode mismatch")
    if type(value["libraries"]) is not dict or set(value["libraries"]) != set(API_CHECKS):
        raise ValueError("Probe must cover exactly both DLLs")
    result = {}
    for name, expected_checks in API_CHECKS.items():
        row = value["libraries"][name]
        if type(row) is not dict or set(row) != {"apiChecks"} or type(row["apiChecks"]) is not int or row["apiChecks"] != expected_checks:
            raise ValueError("Probe API check count mismatch")
        result[name] = {"apiChecks": expected_checks, "libraryPathMatched": True, "markerPresent": mode == "modified"}
    return result


def validate_pair(original, modified, tests_passed, copying_hashes):
    if tests_passed is not True: raise ValueError("Native make check must pass")
    if copying_hashes != LICENSE_HASHES: raise ValueError("All exact upstream license files required")
    if set(original) != set(MARKERS) or set(modified) != set(MARKERS): raise ValueError("Both DLLs required")
    for name, marker in MARKERS.items():
        left, right = original[name], modified[name]
        for row, is_modified in ((left, False), (right, True)):
            if row.get("machine") != "x64" or not re.fullmatch(r"[0-9a-f]{64}", row.get("sha256", "")):
                raise ValueError("Missing x64/hash evidence")
            if row.get("libraryUnchangedByTests") is not True: raise ValueError("Post-test DLL integrity missing")
            probe = row.get("probe", {})
            if probe != {"apiChecks": API_CHECKS[name], "libraryPathMatched": True, "markerPresent": is_modified}:
                raise ValueError("Wrong dynamic API probe evidence")
            expected = sorted(ORIGINAL_EXPORTS[name] + ([marker] if is_modified else []))
            if row.get("exports") != expected: raise ValueError("Unexpected native export set")
        if left.get("imports") != right.get("imports"): raise ValueError("Modified DLL imports changed")
        if right["sha256"] in (left["sha256"], SHIPPED_HASHES[name]): raise ValueError("Modified DLL did not change from original/shipped")
    return True
