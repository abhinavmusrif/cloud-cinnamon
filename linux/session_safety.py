#!/usr/bin/env python3
"""Preserve live RDP sessions across library updates; never restart services."""
import argparse
import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

NEEDRESTART = Path('etc/needrestart/conf.d/90-cloud-cinnamon-rdp.conf')
RELOAD = Path('etc/systemd/system/xrdp-sesman.service.d/95-cloud-cinnamon-reload.conf')
NEEDRESTART_TEXT = r'''# Cloud Cinnamon: keep active desktops during shared-library updates.
# Package updates remain enabled. Restart RDP in a planned, logged-out window.
# Extend existing exclusions instead of replacing the distro configuration.
$nrconf{override_rc}{qr(^xrdp(?:-sesman)?\.service$)} = 0;
1;
'''
RELOAD_TEXT = '''# Cloud Cinnamon: apply sesman configuration without ending desktops.
[Service]
ExecReload=
ExecReload=/bin/kill -HUP $MAINPID
'''
FILES = {NEEDRESTART: NEEDRESTART_TEXT, RELOAD: RELOAD_TEXT}


def atomic_write(path, data, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.session-safety-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, mode)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def check(root=Path('/')):
    return {str(relative): (root / relative).is_file() and not (root / relative).is_symlink()
            and (root / relative).read_text() == text for relative, text in FILES.items()}


def apply(root=Path('/'), run=subprocess.run):
    changed = {}
    for relative, text in FILES.items():
        path = root / relative
        if path.is_symlink():
            raise ValueError('Review managed configuration symlinks before applying')
        if path.exists() and not path.is_file():
            raise ValueError('Managed configuration must be a regular file')
        if not path.exists() or path.read_text() != text:
            changed[relative] = (path.read_bytes(), path.stat().st_mode & 0o777) if path.exists() else None
    if not changed:
        return {'changed': [], 'services_restarted': False, 'backup': None}
    # Persistent backup of only this feature's files, never personal/session data.
    directory = root / 'var/lib/cloud-cinnamon/session-safety'
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    backup = Path(tempfile.mkdtemp(prefix=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ-'), dir=directory))
    for relative, previous in changed.items():
        if previous is not None:
            atomic_write(backup / relative, previous[0], previous[1])
    atomic_write(backup / 'manifest.json', json.dumps({str(path): previous is not None for path, previous in changed.items()}, indent=2).encode(), 0o600)
    try:
        for relative in changed:
            atomic_write(root / relative, FILES[relative].encode())
        if RELOAD in changed:
            run(['systemctl', 'daemon-reload'], check=True, timeout=30)
    except BaseException:
        for relative, previous in changed.items():
            if previous is None:
                (root / relative).unlink(missing_ok=True)
            else:
                atomic_write(root / relative, previous[0], previous[1])
        if RELOAD in changed:
            run(['systemctl', 'daemon-reload'], check=False, timeout=30)
        raise
    return {'changed': [str(path) for path in changed], 'services_restarted': False, 'backup': str(backup)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check', action='store_true')
    group.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if args.check:
        result = check()
        print(json.dumps({'checks': result, 'ready': all(result.values())}, indent=2))
        return 0 if all(result.values()) else 1
    if os.geteuid() != 0:
        parser.error('--apply needs sudo; no configuration changed')
    result = apply()
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
