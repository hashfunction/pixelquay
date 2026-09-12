# TintFable screenshot package binding

Capture uses the unchanged unsigned Store package from successful Windows run
[34691151615](https://github.com/hashfunction/pixelquay/actions/runs/34691151615),
public source `194094371299bc3afda2dd08af483997abd96149`, attempt 1.
Both installed identities passed image edit, recipe save/reload, export, reopen,
normal close, uninstall and cleanup before Store export.

The package is 104,350,689 bytes, SHA-256
`f4296d6cd1e38cb58b6196c450bf46cfb6e093dc8849ae669969c26190f20074`.
The original readiness record is 53,710 bytes, SHA-256
`1cff010c85d27e45f21217b1a2d34226c8a3cba3c1d03b69f5dbf22e782ed280`.
Store artifact ID: 10297154356. Qualification artifact ID: 10297635046.

Root independently replayed the complete capture input verifier against the
original downloaded metadata, all 3,845 MSIX payload files and exact qualified
source. A fresh Git checkout used the original Windows autocrlf/eol policy to
match all six recorded helper hashes; no evidence was changed or normalized.
Native-source records and both installed workflow/lifecycle checks passed.

This change only binds the separate screenshot workflow. It does not rebuild,
resign or change the upload package. Screenshot completion remains pending.
