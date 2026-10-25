#!/usr/bin/env python3
"""Apply a reversible profile to one existing non-root Cinnamon user."""
import argparse
import datetime
import json
import os
import pathlib
import pwd
import re
import shutil
import subprocess


def session_environment(uid):
    env = os.environ.copy()
    env.pop('DBUS_SESSION_BUS_ADDRESS', None)
    env.pop('DISPLAY', None)
    env.pop('XAUTHORITY', None)
    sessions = {}
    for proc in sorted(pathlib.Path('/proc').iterdir()):
        try:
            if not proc.name.isdigit() or proc.stat().st_uid != uid:
                continue
            if (proc / 'comm').read_text().strip() != 'cinnamon':
                continue
            pairs = (proc / 'environ').read_bytes().split(b'\0')
            values = dict(x.decode().split('=', 1) for x in pairs if b'=' in x)
            if values.get('DBUS_SESSION_BUS_ADDRESS') and values.get('DISPLAY'):
                sessions[(values['DISPLAY'], values['DBUS_SESSION_BUS_ADDRESS'])] = values
        except (OSError, ValueError, UnicodeError):
            continue
    if len(sessions) > 1:
        raise SystemExit('Multiple Cinnamon sessions found. Log out unused sessions before applying settings.')
    if not sessions:
        raise SystemExit('Log into Cinnamon first; no live session for this user. No settings changed.')
    values = next(iter(sessions.values()))
    env.update({k: values[k] for k in ('DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS') if k in values})
    env['XDG_RUNTIME_DIR'] = '/run/user/' + str(uid)
    return env


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--user', required=True)
    ap.add_argument('--scale', type=float, default=1.35)
    ap.add_argument('--no-idle-lock', action='store_true', help='Opt in: no automatic idle lock; manual lock stays available')
    ap.add_argument('--restore', type=pathlib.Path, help='Restore a snapshot created by this tool')
    ap.add_argument('--check', action='store_true', help='Read-only current settings and session check')
    args = ap.parse_args()
    account = pwd.getpwnam(args.user)
    if account.pw_uid == 0:
        raise SystemExit('Never run the desktop as root')
    if os.geteuid() == 0:
        command = ['runuser', '-u', account.pw_name, '--', 'python3', str(pathlib.Path(__file__).resolve()), '--user', account.pw_name, '--scale', str(args.scale)]
        if args.no_idle_lock: command += ['--no-idle-lock']
        if args.restore: command += ['--restore', str(args.restore.resolve())]
        if args.check: command += ['--check']
        raise SystemExit(subprocess.run(command, check=False).returncode)
    if os.getuid() != account.pw_uid or not 1 <= args.scale <= 2:
        raise SystemExit('Wrong user or scale outside [1,2]')
    env = session_environment(account.pw_uid)
    env.update(HOME=account.pw_dir, USER=account.pw_name, LOGNAME=account.pw_name)

    def gs(*items):
        return subprocess.check_output(['gsettings', *items], env=env, text=True, timeout=15).strip()

    schemas = set(gs('list-schemas').splitlines())
    settings = [
        ('org.cinnamon.desktop.interface', 'text-scaling-factor', str(args.scale)),
        ('org.gnome.desktop.interface', 'text-scaling-factor', str(args.scale)),
        ('org.cinnamon.desktop.interface', 'font-name', "'Ubuntu 11'"),
        ('org.gnome.desktop.interface', 'font-name', "'Ubuntu 11'"),
        ('org.gnome.desktop.interface', 'monospace-font-name', "'Ubuntu Mono 13'"),
        ('org.cinnamon.desktop.wm.preferences', 'titlebar-font', "'Ubuntu Medium 11'"),
        ('org.cinnamon', 'panels-height', "['1:58']"),
        ('org.cinnamon', 'panel-zone-icon-sizes', "'[{\"panelId\":1,\"left\":48,\"center\":48,\"right\":24}]'"),
        ('org.cinnamon', 'panel-zone-symbolic-icon-sizes', "'[{\"panelId\":1,\"left\":32,\"center\":32,\"right\":22}]'"),
        ('org.nemo.desktop', 'font', "'Ubuntu Medium 11'"),
        ('org.cinnamon.settings-daemon.plugins.xsettings', 'antialiasing', "'rgba'"),
        ('org.cinnamon.settings-daemon.plugins.xsettings', 'hinting', "'slight'"),
    ]
    theme = next((t for t in ('Yaru-cinnamon-dark', 'Yaru-dark') if pathlib.Path('/usr/share/themes', t, 'gtk-3.0').is_dir()), None)
    if theme:
        settings += [('org.cinnamon.desktop.interface', 'gtk-theme', repr(theme)), ('org.cinnamon.desktop.wm.preferences', 'theme', repr(theme))]
    shell = next((t for t in ('Yaru-cinnamon-dark', 'Ubuntu-Cinnamon') if pathlib.Path('/usr/share/themes', t, 'cinnamon').is_dir()), None)
    if shell: settings += [('org.cinnamon.theme', 'name', repr(shell))]
    icons = next((t for t in ('Yaru-cinnamon-dark', 'Yaru-dark', 'Papirus-Dark') if pathlib.Path('/usr/share/icons', t, 'index.theme').exists()), None)
    if icons: settings += [('org.cinnamon.desktop.interface', 'icon-theme', repr(icons))]
    wallpaper = pathlib.Path('/usr/share/backgrounds/ubuntucinnamon/Ubuntu_Cinnamon_Gray.jpg')
    if wallpaper.exists(): settings += [('org.cinnamon.desktop.background', 'picture-uri', repr(wallpaper.as_uri())), ('org.cinnamon.desktop.background', 'picture-options', "'zoom'")]
    if args.no_idle_lock:
        settings += [('org.cinnamon.desktop.screensaver', 'idle-activation-enabled', 'false'), ('org.cinnamon.desktop.session', 'idle-delay', 'uint32 0')]
    # Only installed schema keys. Missing components are explicitly reported.
    ready = []
    for schema, key, value in settings:
        if schema not in schemas or key not in gs('list-keys', schema).splitlines():
            print('Unavailable setting:', schema, key)
        else:
            ready.append((schema, key, value))
    if args.check:
        print(json.dumps({'live_session': True, 'settings': [{'schema': s, 'key': k, 'value': gs('get', s, k)} for s, k, _ in ready]}, indent=2))
        return
    if args.restore:
        data = json.loads(args.restore.read_text())
        for item in data['settings']:
            gs('set', item['schema'], item['key'], item['value'])
        for item in data['files']:
            path = pathlib.Path(item['path'])
            if not path.resolve().is_relative_to(pathlib.Path(account.pw_dir).resolve()):
                raise SystemExit('Snapshot contains a path outside the desktop home')
            if item['before'] is None: path.unlink(missing_ok=True)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(item['before'])
        print('Restored snapshot; no session restart requested.')
        return
    state = pathlib.Path(account.pw_dir) / '.local/state/cloud-cinnamon'
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    snapshot = state / (datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ') + '.json')
    data = {'settings': [{'schema': s, 'key': k, 'value': gs('get', s, k)} for s, k, _ in ready], 'files': []}
    configs = pathlib.Path(account.pw_dir) / '.config/cinnamon/spices'
    changes = []
    for cfg in configs.glob('grouped-window-list@cinnamon.org/*.json'):
        before = cfg.read_text()
        obj = json.loads(before)
        pins = obj.get('pinned-apps', {}).get('value')
        if isinstance(pins, list):
            for name in ('nemo.desktop', 'org.gnome.Terminal.desktop', 'google-chrome.desktop'):
                if pathlib.Path('/usr/share/applications', name).exists() and name not in pins: pins.append(name)
            changes.append((cfg, before, json.dumps(obj, indent=2)))
    menu_icon = pathlib.Path('/usr/share/icons/Papirus/96x96/apps/distributor-logo-ubuntu.svg')
    if menu_icon.exists():
        for cfg in configs.glob('menu@cinnamon.org/*.json'):
            before = cfg.read_text(); obj = json.loads(before)
            if 'menu-icon' in obj and isinstance(obj['menu-icon'], dict):
                obj['menu-icon']['value'] = str(menu_icon)
                changes.append((cfg, before, json.dumps(obj, indent=2)))
    nemo = pathlib.Path(account.pw_dir) / '.config/nemo/desktop-metadata'
    if nemo.exists():
        before = nemo.read_text()
        after = re.sub(r'(?m)^nemo-icon-view-zoom-level=.*$', 'nemo-icon-view-zoom-level=4', before)
        changes.append((nemo, before, after))
    data['files'] = [{'path': str(p), 'before': before} for p, before, _ in changes]
    snapshot.write_text(json.dumps(data, indent=2)); snapshot.chmod(0o600)
    try:
        for schema, key, value in ready: gs('set', schema, key, value)
        for path, _, after in changes: path.write_text(after)
    except Exception:
        print('Apply failed; restore with --restore', snapshot)
        raise
    print('Profile applied. Snapshot:', snapshot)
    print('No shell replacement, logout, password or account changes.')


if __name__ == '__main__':
    main()
