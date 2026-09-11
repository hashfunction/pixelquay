"""Materialize the exact retained libiconv 1.19 source without executing it.

Copyright 2026 Trieflow LLC. MIT. Upstream files retain their own licenses.
"""
import gzip
import hashlib
import io
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
import tarfile
import unicodedata

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from libdatrie_source import checked_parents, digest, write_json, write_new, _regular_stream
from msix_qualification import _checked_path

ARCHIVE_SHA = "74428280c17094da5b702c29b2e1a0abae59556ea5dfdd65705cc8ccc1e000fb"
ARCHIVE_SIZE = 5131029
MEMBERS = {
    ".SRCINFO": (1638, "0a6eaca4b054fbc935d8f66e0432a5e29abed083d25707d47938ca009947015f"),
    "0002-fix-cr-for-awk-in-configure.all.patch": (415, "89d5c0f666e50a0186cfb142ba7b77e8fe1ac4d65bdfd9ae14ae8d2f0045a87c"),
    "0003-add-cp65001-as-utf8-alias.patch": (518, "cb2b1cca44c9b9bd11c3bd33997c10d22dff263542275324c88f34b59910ef87"),
    "fix-pointer-buf.patch": (1664, "6b6e2393840f4dc6067587165777b1a07978f4c05247d7c1010a45ad251bbeeb"),
    "iconv.pc": (240, "56e7ec406bf42eb66b1d972f20d229f7a76ba00c38c7b4403bf348875704baae"),
    "libiconv-1.19.tar.gz": (5921103, "88dd96a8c0464eca144fc791ae60cd31cd8ee78321e67397e25fc095c4a19aa6"),
    "libiconv-1.19.tar.gz.sig": (228, "30374a9cf2846418fc34977eb2b92094c3edb76021d57de541699e2b5e32dc9b"),
    "PKGBUILD": (4906, "9b3212d06910560fb59e017e0b73a29d392a5082d3a47a613e61509bd7dcd475"),
}
LICENSE_HASHES = {
    "COPYING": "8ceb4b9ee5adedde47b31e975c1d90c73ad27b6b165a1dcd80c7c545eb65b903",
    "COPYING.LIB": "20e50fe7aae3e56378ebf0417d9de904f55a0e61e4df315333e632a4d3555d95",
    "README": "4ae66e61d1c6593c84c47105b368d579bcee1af566dbb959ec63a0c48425dcf4",
    "libcharset/COPYING.LIB": "20e50fe7aae3e56378ebf0417d9de904f55a0e61e4df315333e632a4d3555d95",
}


def read_tar(data, root, max_bytes, max_members):
    if len(data) > max_bytes + 2 * 1024 * 1024:
        raise ValueError("Archive expanded byte limit exceeded")
    files, directories, aliases = {}, set(), {}
    total = 0
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as archive:
        for index, member in enumerate(archive):
            if index >= max_members or member.pax_headers:
                raise ValueError("Unreviewed archive member count or extension")
            name = member.name.rstrip("/") if member.isdir() else member.name
            _checked_path(name)
            if name != root and not name.startswith(root + "/"):
                raise ValueError("Archive member outside expected root")
            for count in range(1, len(name.split("/")) + 1):
                prefix = "/".join(name.split("/")[:count])
                key = unicodedata.normalize("NFC", prefix).casefold()
                if key in aliases and aliases[key] != prefix:
                    raise ValueError("Case/Unicode archive alias")
                aliases[key] = prefix
            if name in files or name in directories:
                raise ValueError("Duplicate archive member")
            if member.isdir():
                if member.size: raise ValueError("Directory member has data")
                directories.add(name)
            elif member.isreg():
                total += member.size
                if member.size < 0 or total > max_bytes: raise ValueError("Archive byte bound")
                stream = archive.extractfile(member); body = stream.read(member.size + 1)
                if len(body) != member.size: raise ValueError("Truncated archive member")
                files[name] = body
            else:
                raise ValueError("Archive links/devices refused")
    for name in set(files) | directories:
        if any(str(parent) in files for parent in PurePosixPath(name).parents):
            raise ValueError("Archive file/directory collision")
    return files


def materialize(archive, output, zstd="zstd"):
    archive, output = checked_parents(archive), checked_parents(output)
    if os.path.lexists(output): raise FileExistsError(f"Output already exists: {output}")
    with _regular_stream(archive) as stream: compressed = stream.read(ARCHIVE_SIZE + 1)
    if digest(compressed) != {"bytes": ARCHIVE_SIZE, "sha256": ARCHIVE_SHA}:
        raise ValueError("Exact libiconv source archive hash/size mismatch")
    decoded = subprocess.run([zstd, "-dc"], input=compressed, capture_output=True, check=True, timeout=30).stdout
    outer = read_tar(decoded, "mingw-w64-libiconv", 7 * 1024 * 1024, 32)
    expected = {"mingw-w64-libiconv/" + name for name in MEMBERS}
    if set(outer) != expected: raise ValueError("Source wrapper member set differs")
    for short, expected_digest in MEMBERS.items():
        if digest(outer["mingw-w64-libiconv/" + short]) != {"bytes": expected_digest[0], "sha256": expected_digest[1]}:
            raise ValueError(f"Source wrapper member mismatch: {short}")
    upstream_tar = gzip.decompress(outer["mingw-w64-libiconv/libiconv-1.19.tar.gz"])
    if len(upstream_tar) > 32 * 1024 * 1024: raise ValueError("Upstream decompression bound")
    upstream = read_tar(upstream_tar, "libiconv-1.19", 24 * 1024 * 1024, 2048)
    for name, sha in LICENSE_HASHES.items():
        if digest(upstream["libiconv-1.19/" + name])["sha256"] != sha:
            raise ValueError(f"Original license differs: {name}")
    outputs = {"recipe/" + name.split("/", 1)[1]: body for name, body in outer.items()}
    outputs.update({"upstream/" + name: body for name, body in upstream.items()})
    receipt = {
        "schemaVersion": 1, "purpose": "libiconv-two-dll-source-rebuild-proof",
        "archive": digest(compressed), "upstreamFileCount": len(upstream),
        "files": {name: digest(body) for name, body in sorted(outputs.items())},
        "executedRecipe": False, "licenseConversionApplied": False,
        "sourceUrl": "https://mirror.msys2.org/mingw/sources/mingw-w64-libiconv-1.19-1.src.tar.zst",
    }
    output.mkdir()
    for name, body in outputs.items(): write_new(output / name, body)
    write_json(output / "source-receipt.json", receipt)
    return receipt
