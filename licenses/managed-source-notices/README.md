# Bound upstream notice texts

These source texts were already included by PixelQuay's project file. The new
`package-bindings.json` connects them to24 exact NuGet package versions and archive
SHA-256 values from the observed Windows restore. The inventory now verifies both
package and notice hashes and records the included text's provenance. It reuses
the existing managed-source-notices destination instead of copying duplicate texts.
Changed packages/texts fail; unmatched versions remain unresolved; conflicting
existing output is retained. No license text or copyright was rewritten.

The original `noticeReviewRequired` flag remains when a NuGet archive omits its
own notice. Text presence does not establish complete review of DLLs, assets,
runtime alternatives or native GTK/LGPL source delivery. See `sources.json` for
ParagonClipper's unavailable source repository and Mono.Addins sibling package
source-commit limitations. Their existing notices and limitations are preserved.

Six real-file/hash regression tests pass. Running against the current actual
restored assets records82 packages with24 hash-bound notice references. This is
local source-inventory validation, not Windows installation or final license
clearance. The next Windows restore must preserve the same provenance evidence.
