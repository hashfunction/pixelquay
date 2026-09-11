"""Focused source and receipt rejection tests for the two libiconv DLLs."""
import copy
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import libiconv_source as source
import receipt


def pair():
    originals = {
        "libcharset-1.dll": {
            "sha256": "1" * 64,
            "machine": "x64",
            "exports": ["libcharset_set_relocation_prefix", "locale_charset"],
            "imports": ["kernel32.dll"],
            "probe": {"apiChecks": 2, "libraryPathMatched": True, "markerPresent": False},
            "libraryUnchangedByTests": True,
        },
        "libiconv-2.dll": {
            "sha256": "2" * 64,
            "machine": "x64",
            "exports": ["_libiconv_version", "iconv_canonicalize", "libiconv", "libiconv_close", "libiconv_open", "libiconv_open_into", "libiconv_set_relocation_prefix", "libiconvctl", "libiconvlist", "locale_charset"],
            "imports": ["kernel32.dll"],
            "probe": {"apiChecks": 6, "libraryPathMatched": True, "markerPresent": False},
            "libraryUnchangedByTests": True,
        },
    }
    modified = copy.deepcopy(originals)
    for name, marker in receipt.MARKERS.items():
        modified[name]["sha256"] = "3" * 64 if name.startswith("libcharset") else "4" * 64
        modified[name]["exports"] = sorted(modified[name]["exports"] + [marker])
        modified[name]["probe"]["markerPresent"] = True
    return originals, modified


class LibiconvProofTests(unittest.TestCase):
    def test_exact_retained_source_materializes_and_preserves_licenses(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp).resolve() / "source"
            record = source.materialize(HERE / "inputs/mingw-w64-libiconv-1.19-1.src.tar.zst", output)
            self.assertEqual(record["archive"], {"bytes": 5131029, "sha256": source.ARCHIVE_SHA})
            self.assertEqual(record["upstreamFileCount"], 1109)
            self.assertEqual(source.digest((output / "upstream/libiconv-1.19/COPYING.LIB").read_bytes())["sha256"], source.LICENSE_HASHES["COPYING.LIB"])
            self.assertFalse(record["executedRecipe"])
            license_before = (output / "upstream/libiconv-1.19/COPYING.LIB").read_bytes()
            # Match PKGBUILD prepare(): it enters libiconv-1.19 before -p1.
            subprocess.run(["patch", "-p1", "-i", str(HERE / "001-local-markers.patch")], cwd=output / "upstream/libiconv-1.19", check=True, capture_output=True)
            changed = ["include/iconv.h.in", "lib/iconv.c", "libcharset/include/localcharset.h.in", "libcharset/lib/localcharset.c"]
            for name in changed:
                self.assertIn("Modified 2026-09-11 by Trieflow LLC", (output / "upstream/libiconv-1.19" / name).read_text())
            self.assertEqual((output / "upstream/libiconv-1.19/COPYING.LIB").read_bytes(), license_before)

    def test_corrupt_archive_and_existing_output_are_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            bad = root / "bad.zst"; bad.write_bytes(b"wrong")
            output = root / "out"; output.mkdir(); sentinel = output / "keep"; sentinel.write_bytes(b"old")
            with self.assertRaises(ValueError): source.materialize(bad, root / "new")
            with self.assertRaises(FileExistsError): source.materialize(HERE / "inputs/mingw-w64-libiconv-1.19-1.src.tar.zst", output)
            self.assertEqual(sentinel.read_bytes(), b"old")

    def test_pair_requires_both_changed_dlls_tests_and_exact_exports(self):
        original, modified = pair()
        self.assertTrue(receipt.validate_pair(original, modified, tests_passed=True, copying_hashes=source.LICENSE_HASHES))
        mutations = [
            ("tests", False),
            ("unchanged", False),
            ("extra-export", True),
            ("same-hash", True),
            ("shipped-hash", True),
            ("missing-license", True),
        ]
        for kind, tests in mutations:
            bad = copy.deepcopy(modified); licenses = dict(source.LICENSE_HASHES)
            if kind == "unchanged": bad["libcharset-1.dll"]["libraryUnchangedByTests"] = False
            if kind == "extra-export": bad["libiconv-2.dll"]["exports"].append("unexpected")
            if kind == "same-hash": bad["libiconv-2.dll"]["sha256"] = original["libiconv-2.dll"]["sha256"]
            if kind == "shipped-hash": bad["libiconv-2.dll"]["sha256"] = receipt.SHIPPED_HASHES["libiconv-2.dll"]
            if kind == "missing-license": licenses.pop("COPYING.LIB")
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                receipt.validate_pair(original, bad, tests_passed=tests, copying_hashes=licenses)

    def test_post_test_hashes_bind_both_build_dlls(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = root / "libcharset-1.dll"; b = root / "libiconv-2.dll"
            a.write_bytes(b"a"); b.write_bytes(b"b")
            hashes = root / "hashes.txt"
            hashes.write_text(f"{receipt.sha256(a)}  libcharset-1.dll\n{receipt.sha256(b)}  libiconv-2.dll\n", encoding="ascii", newline="\n")
            self.assertEqual(set(receipt.verify_post_test_hashes({a.name: a, b.name: b}, hashes)), {a.name, b.name})
            b.write_bytes(b"changed")
            with self.assertRaises(ValueError): receipt.verify_post_test_hashes({a.name: a, b.name: b}, hashes)

    def test_probe_record_requires_exact_typed_variant_and_both_libraries(self):
        value = {"schemaVersion": 1, "mode": "original", "libraryPathMatched": True,
                 "markersPresent": False, "libraries": {"libcharset-1.dll": {"apiChecks": 2}, "libiconv-2.dll": {"apiChecks": 6}}}
        self.assertEqual(receipt.parse_probe(value, "original")["libiconv-2.dll"]["apiChecks"], 6)
        for bad in (
            {**value, "mode": "modified"},
            {**value, "schemaVersion": True},
            {**value, "libraryPathMatched": 1},
            {**value, "extra": False},
            {**value, "libraries": {"libiconv-2.dll": {"apiChecks": 6}}},
            {**value, "libraries": {**value["libraries"], "libiconv-2.dll": {"apiChecks": "6"}}},
        ):
            with self.assertRaises(ValueError): receipt.parse_probe(bad, "original")

    def test_recipes_make_native_tests_fail_closed_and_preserve_split_runtime(self):
        for mode in ("original", "modified"):
            text = (HERE / "recipes" / mode / "PKGBUILD").read_text()
            self.assertIn("make check\n", text)
            self.assertNotIn('make check ||', text)
            self.assertIn("source-tests-before.sha256", text)
            self.assertIn("cmp source-tests-before.sha256 source-tests-passed.sha256", text)
            self.assertIn('rm -fr "${pkgdir}${MINGW_PREFIX}"/bin/*.exe', text)
        modified = (HERE / "recipes/modified/PKGBUILD").read_text()
        self.assertIn("001-local-markers.patch", modified)
        self.assertIn("pkgrel=1.1", modified)
        prepare = modified[modified.index("prepare()"):modified.index("build()") ]
        self.assertLess(prepare.index("001-local-markers.patch"), prepare.index("regenerate_files"))


if __name__ == "__main__":
    unittest.main()
