#!/usr/bin/env bash
# Read-only diagnostics: no credentials, clipboard contents or user documents.
set -u
printf 'OS\n'; cat /etc/os-release
printf '\nResources\n'; nproc; free -h; df -h /
printf '\nRDP services\n'; systemctl is-active xrdp xrdp-sesman
printf '\nRDP listeners (should be loopback)\n'; ss -ltn '( sport = :3389 )'
printf '\nInstalled desktop packages\n'
dpkg-query -W -f='${binary:Package} ${Version}\n' cinnamon xrdp xorgxrdp libpng16-16t64 2>/dev/null
printf '\nCinnamon sessions\n'; pgrep -a -x cinnamon || true
printf '\nPrivate build\n'
if [[ -f /opt/cloud-cinnamon/rdp-0.10.6.1/build-tested ]]; then
  cat /opt/cloud-cinnamon/rdp-0.10.6.1/source-lock.json
  sha256sum -c /opt/cloud-cinnamon/rdp-0.10.6.1/artifact-sha256.txt
else printf 'No kit-built RDP stack. Distro or another installation may be active.\n'; fi

printf '\nRDP update/session safeguards\n'
python3 "$(dirname "$0")/session_safety.py" --check || true
printf '\nSession displays and lifecycle state\n'
while read -r session _; do
  [[ -n $session ]] || continue
  loginctl show-session "$session" -p Display -p State -p Service 2>/dev/null || true
done < <(loginctl list-sessions --no-legend 2>/dev/null)
