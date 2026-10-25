# Cloud Cinnamon

**Your own Ubuntu desktop, recoverable on another cloud machine.**

A real Cinnamon desktop over RDP: readable Ubuntu fonts, dark orange-accented
themes, a useful bottom panel, LibreOffice, and repaired Windows/Linux clipboard
integration. This is an open-source setup and recovery kit, not a new Linux ISO.

Built from an actual daily-use cloud desktop. The reusable scripts replace
machine-specific commands; account credentials and personal files are never part
of this repository.

## What you get

| Area | Included |
| --- | --- |
| Desktop | Cinnamon, Ubuntu fonts, Yaru/Papirus icons, charcoal Ubuntu Cinnamon wallpaper when its package is available |
| Readability | 1.35× text, 58 px panel, 48 px application icons; adjustable and reversible |
| Applications | Terminal, Files and LibreOffice Writer; existing Chrome gets pinned if installed |
| Remote desktop | Checksum-pinned xrdp 0.10.6.1 + xorgxrdp 0.10.5, CPU H.264, conservative 6 Mbps / 30 fps settings |
| Image clipboard | Windows bitmap → lossless PNG transport → Linux PNG/BMP applications, with bounded native decoding |
| Text history | Optional Linux text → Windows local Win+V history, with cloud clipboard roaming disabled |
| Access | Provider-independent SSH tunnel; optional AWS Systems Manager tunnel |
| Recovery | Package setup, profile snapshots, private settings backup, health checks and RDP rollback |

**Supported setup target:** Ubuntu 24.04 LTS, x86-64, systemd, an existing non-root
user. The original live machine used 4 CPU cores and 32 GB RAM with no GPU.
Other cloud providers can supply the same OS; their networking and identity
setup differ. ARM, other distributions and a completely fresh provider recovery
have not yet been certified. See [verification](docs/verification.md).

## Start on a new cloud machine

Keep the provider console or SSH/SSM access working throughout installation.
**Do not expose TCP 3389 publicly.** Use your cloud firewall to block it before
installing; RDP is configured to listen only on localhost. Allow SSH only from
your own network, or use your provider's private access mechanism.

```bash
sudo apt-get update
sudo apt-get install -y git
git clone https://github.com/Amretra-Dynamics/cloud-cinnamon.git
cd cloud-cinnamon
# Inspect scripts before running them with sudo. Use your existing Linux user:
sudo bash setup.sh --user "$(id -un)"
sudo bash linux/build-rdp.sh
```

The build downloads official sources, verifies their pinned SHA-256 values,
applies the reviewed clipboard patch, runs native tests, and stages the binaries.
It does **not** disconnect existing desktops. Once desktop work is saved and all
Cinnamon sessions are logged out:

```bash
sudo bash linux/activate-rdp.sh --activate
```

Connect from Windows using an authenticated SSH host:

```powershell
git clone https://github.com/Amretra-Dynamics/cloud-cinnamon.git
cd cloud-cinnamon
# First establish normal SSH access and verify the server's host key:
ssh your-linux-user@your-cloud-host
# Exit that shell, then:
powershell.exe -NoProfile -File .\windows\Connect-Desktop.ps1 `
  -Transport SSH -SshHost your-linux-user@your-cloud-host
```

Use the Linux desktop user's password at the RDP login. Cloud images may ship
with a locked password; set your own with `sudo passwd YOUR_USER` through your
existing authorized administration session. No password is supplied or stored
by this kit. Review the RDP certificate against the server fingerprint; see
[access and security](docs/access.md).

After the first Cinnamon login, apply the desktop profile from SSH/SSM or its
terminal. It discovers the **actual user's live Cinnamon D-Bus session**, rather
than guessing UID 1000 or a display number:

```bash
sudo python3 linux/desktop.py --user "$(id -un)"
# Read-only check:
sudo python3 linux/desktop.py --user "$(id -un)" --check
```

Snapshots are saved privately under `~/.local/state/cloud-cinnamon/`. No shell
replacement or forced logout is used for appearance settings. The profile's
panel layout targets Cinnamon's default panel 1; review custom panel layouts
before applying it.

## Daily use and options

* **Windows + Print Screen:** stays on Windows and saves a screenshot using
  Windows' normal settings. The clipboard helper adds a lossless PNG format
  when an image reaches the clipboard; it does not capture screenshots or
  enable Windows clipboard history itself.
* **Paste commands into a Linux terminal:** use **Ctrl+Shift+V** (or Shift+Insert).
  Ctrl+V has a different meaning inside most terminal applications.
* **Paste screenshots into Writer:** use Ctrl+V after copying/selecting the
  Windows screenshot. Both the Windows helper and patched Linux stack are
  needed for the optimized image path.
* **Linux text in Windows clipboard history:** explicitly opt in by adding
  `-EnableTextHistory` to the Windows connection command. This permits ordinary
  remote text in your local history, preserves explicit exclusion markers and
  leaves cloud roaming disabled. Read [clipboard behavior](docs/clipboard.md).
* **Idle locking:** default locking policy is retained. For a personally
  controlled desktop, explicitly add `--no-idle-lock` to `desktop.py`.
  Manual locking remains available.
* **Fewer software-installation prompts:** the optional
  `sudo python3 linux/desktop-admin.py --user YOUR_USER --enable` policy grants
  listed ordinary Flatpak operations to that one active sudo user and retains
  temporary approval for listed PackageKit actions. It is not blanket root
  access; review [security](SECURITY.md) first.

## Recover this environment later

1. Keep a copy or fork of this repository and note the commit/tag you used.
2. Keep documents, application data and credentials in **separate private
   backups**. This public repo cannot recover data it never stores.
3. Provision another supported Ubuntu machine with enough CPU/RAM/storage.
4. Run the setup/build/activation steps, establish a private tunnel, then apply
   the same desktop profile. Set your account password and log into applications
   yourself.
5. Restore private documents and reviewed settings. Run the health and clipboard
   checks before retiring the previous machine.

Full steps, rollback and old-account cleanup guidance:
**[Recovery runbook](docs/recovery.md)**.

## Development and provenance

No GitHub Actions runner is required. [Local checks](docs/verification.md) include
patch applicability, Python/PowerShell/Bash validation, and native PNG codec
tests with address/undefined-behavior sanitizers. Builds run locally on the target
Linux machine; no prebuilt executable is substituted for source.

The RDP engine is [upstream xrdp](https://github.com/neutrinolabs/xrdp/releases/tag/v0.10.6.1)
with [xorgxrdp](https://github.com/neutrinolabs/xorgxrdp/releases/tag/v0.10.5).
Our source patch is provided explicitly in `patches/`, not hidden in an installer.
Original setup code is MIT licensed. Upstream patch portions retain Apache-2.0;
see [third-party notices](THIRD_PARTY_NOTICES.md).

This infrastructure kit does not package or replace the MegasMoves application
or its embedded MCP operator. It can host your usual Linux applications.
