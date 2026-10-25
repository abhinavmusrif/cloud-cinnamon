#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 ]] || { echo 'Run with sudo'; exit 1; }
if pgrep -x cinnamon >/dev/null; then echo 'Log out first to preserve desktop work.' >&2; exit 1; fi
BACKUP=$(cat /var/lib/cloud-cinnamon/last-activation)
[[ $BACKUP == /var/lib/cloud-cinnamon/activation-* && -d $BACKUP ]] || exit 1
systemctl stop xrdp xrdp-sesman
for unit in xrdp xrdp-sesman; do
  dropin="/etc/systemd/system/$unit.service.d/90-cloud-cinnamon.conf"
  if [[ -f $BACKUP/$unit.conf ]]; then cp "$BACKUP/$unit.conf" "$dropin"; else rm -f -- "$dropin"; fi
done
systemctl daemon-reload
systemctl start xrdp-sesman xrdp
echo 'Previous RDP unit definitions restored. Source/build artifacts retained.'
