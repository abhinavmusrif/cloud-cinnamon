#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "$0")" && pwd)
[[ $EUID == 0 && $# == 2 && $1 == --user ]] || { echo 'Usage: sudo bash setup.sh --user EXISTING_LINUX_USER'; exit 1; }
USER_NAME=$2
[[ $USER_NAME =~ ^[a-z_][a-z0-9_-]*$ && $USER_NAME != root ]] || exit 1
id "$USER_NAME" >/dev/null
bash "$HERE/linux/bootstrap.sh"
python3 - "$USER_NAME" <<'PY'
import datetime,os,pathlib,pwd,shutil,sys
user=pwd.getpwnam(sys.argv[1]);p=pathlib.Path(user.pw_dir)/'.xsession'
if p.exists() or p.is_symlink():
    if p.is_symlink(): raise SystemExit('Review existing .xsession symlink manually')
    backup=p.with_name('.xsession.before-cloud-cinnamon-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    shutil.copy2(p,backup);os.chown(backup,user.pw_uid,user.pw_gid)
p.write_text('#!/bin/sh\nexec cinnamon-session\n');p.chmod(0o700);os.chown(p,user.pw_uid,user.pw_gid)
PY
echo 'Base setup complete. Desktop password and secure tunnel are your own account settings.'
echo 'After connecting once: sudo python3 linux/desktop.py --user YOUR_USER'
echo 'For the tested modern clipboard stack: sudo bash linux/build-rdp.sh'
