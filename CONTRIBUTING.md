# Contributing

Keep changes reproducible, provider-independent where possible, and reversible.
Never submit machine exports, credentials, personal clipboard samples or private
chat databases. Use synthetic fixtures when reporting clipboard problems.

Before changing the RDP patch, start from the exact source versions in
`config/sources.json`, apply the patch with zero fuzz, and run native builds/tests
and `tests/test_clipboard_codec.py`. Update reviewed result hashes deliberately;
do not change them just to silence a mismatch. Review upstream security fixes
when updating release pins.

Keep software-installation authorization and text-history recording opt-in.
Preserve loopback binding and retain existing vendor authorization for unlisted
actions. Never add automatic user deletion, saved passwords or public RDP access.

Documentation must distinguish source/static checks, native builds, interactive
clipboard behavior and complete recovery on a new VM. Report the exact OS,
architecture and test scope rather than claiming universal cloud support.
