#!/usr/bin/env bash
# Install a real Cinnamon/Xorg desktop. Never change cloud identity or passwords.
set -euo pipefail
[[ $EUID == 0 ]] || { echo 'Run with sudo.' >&2; exit 1; }
. /etc/os-release
[[ $ID == ubuntu && $VERSION_ID == 24.04 ]] || { echo 'Supported target: Ubuntu 24.04.' >&2; exit 1; }
if pgrep -x cinnamon >/dev/null; then
  echo 'Base provisioning can restart packaged services. Save work and log out first.' >&2
  exit 1
fi
# A fresh package install must not start a public listener before configuration.
MASKED_BY_US=0
cleanup() {
  if [[ $MASKED_BY_US == 1 ]]; then systemctl unmask --runtime xrdp.service; fi
}
trap cleanup EXIT
if ! systemctl is-active --quiet xrdp; then
  case $(systemctl is-enabled xrdp 2>/dev/null || true) in
    masked*) echo 'xrdp was masked already. Review that policy before provisioning.' >&2; exit 1 ;;
    *) systemctl mask --runtime xrdp.service; MASKED_BY_US=1 ;;
  esac
fi
export DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=l
apt-get update
apt-get install -y --no-remove cinnamon-desktop-environment gnome-terminal \
  xrdp xorgxrdp dbus-x11 x11-xserver-utils xclip openssl \
  fonts-ubuntu papirus-icon-theme yaru-theme-gtk yaru-theme-icon \
  python3 python3-pil python3-gi gir1.2-gtk-3.0 git curl flatpak libreoffice-writer
# Ubuntu Cinnamon theme packaging differs from generic Yaru. Install available
# official packages, and let the user profile select only themes actually present.
for package in yaru-cinnamon-theme-gtk yaru-cinnamon-theme-icon ubuntucinnamon-wallpapers; do
  if apt-cache show "$package" >/dev/null 2>&1; then apt-get install -y --no-remove "$package"; fi
done
usermod -a -G ssl-cert xrdp
# Keep distro RDP private even before the optional modern stack is built.
python3 - <<'PY'
import pathlib, re, shutil, datetime
p=pathlib.Path('/etc/xrdp/xrdp.ini')
backup=p.with_name('xrdp.ini.cloud-cinnamon-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
shutil.copy2(p, backup)
s=p.read_text()
# Only the global listener, never the Xorg session's port=-1.
s,n=re.subn(r'(?m)^port=(?:3389|tcp://127\.0\.0\.1:3389)$', 'port=tcp://127.0.0.1:3389', s, count=1)
if n!=1: raise SystemExit('Unrecognized listener: review /etc/xrdp/xrdp.ini manually')
p.write_text(s)
PY
cleanup
MASKED_BY_US=0
trap - EXIT
systemctl enable xrdp xrdp-sesman
echo 'Base packages ready. No session was terminated or rebooted.'
echo 'Set a Linux desktop password locally if needed; then apply the user profile.'
echo 'Restart xrdp only when existing desktop work is saved.'
