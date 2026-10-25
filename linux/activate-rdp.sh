#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 && ${1:-} == --activate ]] || { echo 'Save desktop work, log out, then sudo bash linux/activate-rdp.sh --activate'; exit 1; }
PREFIX=/opt/cloud-cinnamon/rdp-0.10.6.1
[[ -f $PREFIX/build-tested ]] || { echo 'No verified build.' >&2; exit 1; }
sha256sum -c "$PREFIX/artifact-sha256.txt"
# Refuse to disconnect anybody. Only activate after the user has logged out.
if pgrep -x cinnamon >/dev/null; then echo 'Log out of Cinnamon first; existing sessions will not be killed.' >&2; exit 1; fi
for unit in xrdp xrdp-sesman; do
  if systemctl cat "$unit" | grep -E '^ExecStart=' | grep -vE '^ExecStart=$|/usr/sbin/|/opt/cloud-cinnamon/' >/dev/null; then
    echo 'Another custom RDP installation exists. Review it before activation.' >&2; exit 1
  fi
done
python3 "$(dirname "$0")/configure_rdp.py"
test -r /etc/xrdp/cert.pem
test -r /etc/xrdp/key.pem
mkdir -p /var/lib/cloud-cinnamon
BACKUP=$(mktemp -d /var/lib/cloud-cinnamon/activation-XXXXXXXX)
for unit in xrdp xrdp-sesman; do
  systemctl cat "$unit" > "$BACKUP/$unit.unit.txt"
  dropin="/etc/systemd/system/$unit.service.d/90-cloud-cinnamon.conf"
  if [[ -f $dropin ]]; then cp "$dropin" "$BACKUP/$unit.conf"; fi
done
echo "$BACKUP" > /var/lib/cloud-cinnamon/last-activation
systemctl stop xrdp xrdp-sesman
rollback() { bash "$(dirname "$0")/rollback-rdp.sh"; }
trap rollback ERR
for unit in xrdp xrdp-sesman; do
  mkdir -p "/etc/systemd/system/$unit.service.d"
  cat > "/etc/systemd/system/$unit.service.d/90-cloud-cinnamon.conf" <<EOF
[Service]
Type=simple
PIDFile=
RuntimeDirectory=
RuntimeDirectory=cloud-cinnamon-rdp
RuntimeDirectoryPreserve=yes
ExecStartPre=
ExecStartPre=+/usr/bin/install -d -m 2775 -o root -g xrdp /run/cloud-cinnamon-rdp
ExecStart=
ExecStart=$PREFIX/sbin/$unit --nodaemon --config $PREFIX/etc/xrdp/${unit/xrdp-sesman/sesman}.ini
ExecStop=
Restart=on-failure
RestartSec=3
EOF
done
install -m 640 -o xrdp -g xrdp /dev/null /var/log/cloud-cinnamon-xrdp.log
systemctl daemon-reload
systemctl enable xrdp xrdp-sesman
systemctl start xrdp-sesman xrdp
sleep 2
systemctl is-active --quiet xrdp xrdp-sesman
ss -ltn '( sport = :3389 )' | grep -q '127.0.0.1:3389'
trap - ERR
echo "Active on loopback only. Previous unit definitions saved at $BACKUP"
