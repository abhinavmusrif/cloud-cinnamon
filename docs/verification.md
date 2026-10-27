# Verification record and limits

## Original desktop evidence — 2026-10-25

The original Ubuntu 24.04 x64 cloud machine ran Cinnamon 6.0.4 on a CPU-only
4-core/32 GB instance. Before this repository was assembled:

* xrdp 0.10.6.1 / xorgxrdp 0.10.5 were built from upstream source and activated.
* The xrdp native suite passed 215 checks. The separate PNG codec suite passed
  11 checks with address and undefined-behavior sanitizers, including malformed
  and oversized inputs and exact RGB conversion through 3840×2160.
* Real Windows screenshots pasted into Linux GTK/Writer. The user confirmed
  image paste and RDP responsiveness. PNG/BMP representations matched pixels.
* An RDP window responsiveness probe had 0 timeouts over 120 samples during
  clipboard activity. This is a sample, not a promise of zero future stalls.
* Linux multiline Unicode text including Hindi, Telugu and emoji reached Windows
  and local clipboard history. Local Windows history still worked afterward.
* Actual live D-Bus settings, panel sizes, theme and pinned apps were checked.
* Narrow remote software-installation authorization was checked against the
  intended active administrator; an unrelated user/untrusted operation was denied.

The public native patch was exported as an exact diff from that installation
against its original source tarball. Personal logs, screen captures, credentials
and account-specific manifests were excluded.

## Repository checks

The repository's isolated validation build completed successfully on the existing
Ubuntu 24.04 host: freshly downloaded checksum-pinned sources, zero-fuzz patch
application, both native builds/test targets, the 11 ASan/UBSan PNG checks, and
ELF validation of installed staging files. No live RDP service was activated or
replaced by this validation. The five repository tests passed on Windows and
Linux; all three Windows helper scripts parsed successfully, and Bash scripts
passed syntax checks. All four patched source hashes match the original live
implementation after LF normalization. The new Windows connection wrapper was
parsed and reviewed, not exercised through a new interactive login.

On Windows:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tests\check.ps1
```

On Linux, after fetching clean sources into an empty build directory:

```bash
python3 -m unittest discover -s tests -p test_repository.py -v
python3 linux/fetch_sources.py .cache/sources
cd .cache/sources/xrdp-0.10.6.1
patch --batch --fuzz=0 -p1 < ../../../patches/xrdp-0.10.6.1-clipboard.patch
cd ../../..
python3 tests/test_clipboard_codec.py --header .cache/sources/xrdp-0.10.6.1/sesman/chansrv/clipboard_png.h
```

Install compiler/libpng development files and Python Pillow for the native codec
test. `bash -n` accepts one input script at a time; to check every script use:

```bash
for script in setup.sh linux/*.sh; do bash -n "$script" || exit; done
```

For a full clean source build and staging test on an already provisioned Ubuntu
24.04 build host with dependencies present:

```bash
sudo bash linux/build-rdp.sh --validate-only
```

This runs both upstream builds/tests plus codec checks and verifies installed
ELF files in a staging directory, without activating/replacing a live RDP stack.
Without `--validate-only`, dependencies are installed and the tested build is
copied to its isolated `/opt/cloud-cinnamon` prefix. Activation stays separate.

## What remains outside certification

The new provider-neutral bootstrap, recovery procedure and Windows connection
wrapper are extracted/generalized from the original machine's engineering.
Do not equate original live tests or static validation with a complete fresh-VM
recovery test. No new billable VM was created for this repository. The project
does not certify other Ubuntu releases, ARM, arbitrary providers' identity
configuration, all office applications or every Windows version.

Nothing in this repository claims a hardware GPU, universally instant RDP,
unlimited agents, automatic application logins or recovery of unbacked-up data.

### RDP tunnel readiness

`windows/Connect-Desktop.ps1` waits for a valid RDP negotiation response selecting
TLS before opening the desktop client. A TCP listener by itself is insufficient.
The probe uses loopback only, bounded connection/read timeouts, and never sends
credentials or starts a desktop session. It does not validate the server's TLS
certificate or authenticate a user; the normal RDP client retains those steps.

On Windows, run the six protocol regression checks:

```powershell
python -m unittest discover -s tests -p test_rdp_readiness.py -v
```

These cover successful and fragmented responses, protocol mismatch, explicit
RDP failure, silent sockets, and immediate connection closure. They do not
certify reboot recovery. For your own tunnel supervisor, configure sign-in
startup, failure restart, a single-instance guard and repeated protocol probes;
verify an actual reboot separately before claiming before-sign-in availability.

### Update-time session safety — 2026-10-27

The isolated session-safety tests exercise actual Perl policy matching, retaining
existing exclusions, unrelated-service behavior, idempotence, prior-file backup,
symlink refusal and rollback after a failed systemd metadata reload. They never
restart a live RDP service. Run:

```bash
python3 -m unittest discover -s tests -p test_session_safety.py -v
```

Use `session_safety.py --check` to inspect installed managed files. The apply
command needs root and only invokes `systemctl daemon-reload`; it cannot certify
an interactive disconnect/reconnect cycle. After applying it on a live host,
verify unchanged daemon PIDs and session IDs, then perform a normal client
**disconnect/reconnect** and verify the same desktop. Avoid deliberately
restarting sesman during unsaved work to reproduce this bug.

This is not crash-proof session persistence, automatic orphan recovery, or a
replacement for logged-out maintenance after RDP binary/security updates.

Live follow-up on Ubuntu 24.04 x86-64 passed after applying the safeguard:
managed-file checks matched, the effective Perl configuration excluded both RDP
services while retaining existing exclusions, and `CanReload=yes` was exposed
for sesman. The RDP daemon PIDs, desktop session identity and session leader
remained unchanged. The user disconnected/reconnected their actual RDP client
and confirmed that the same desktop and open applications returned. This verifies
one live reconnect after this configuration change, not recovery from a future
sesman crash or a guarantee against all causes of duplicate sessions.

The five repository checks and five session-safety checks passed. Six Windows
readiness tests were skipped on this Linux host because Windows PowerShell was
unavailable. Bash syntax, Python compilation and the installed merged systemd
unit passed validation. Native RDP/clipboard source did not change and was not
rebuilt for this configuration-only follow-up. The standalone native codec
harness takes explicit arguments and is not a unittest-discovery module; run
its documented command separately when native clipboard code changes.
