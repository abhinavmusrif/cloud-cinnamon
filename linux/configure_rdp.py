#!/usr/bin/env python3
"""Configure only the isolated build, without changing packaged configuration."""
import json
import pathlib
import re
import shutil
import tomllib


INTERACTIVE = {
    "default": ("superfast", 20_000, 2_000),
    "lan": ("superfast", 20_000, 2_000),
    "wan": ("veryfast", 15_000, 1_500),
}


def configure_gfx(text):
    """Scope interactive encoder tuning to named x264 profiles."""
    expected = tomllib.loads(text)
    if not isinstance(expected.get("x264", {}).get("default"), dict):
        raise ValueError("Missing x264.default table")
    text = text.rstrip() + "\n"
    for name, (preset, rate, buffer) in INTERACTIVE.items():
        values = dict(preset=preset, tune="zerolatency", profile="main",
                      fps_num=60, fps_den=1, threads=2,
                      vbv_max_bitrate=rate, vbv_buffer_size=buffer)
        header = re.compile(rf"(?m)^[ \t]*\[x264\.{name}\][ \t]*(?:#[^\n]*)?\n")
        match = header.search(text)
        if match is None:
            if name in expected["x264"]:
                raise ValueError("Unsupported x264 table representation")
            text = text.rstrip() + f"\n\n[x264.{name}]\n"
            match = header.search(text)
        following = re.search(r"(?m)^[ \t]*\[", text[match.end():])
        end = match.end() + following.start() if following else len(text)
        body = text[match.end():end]
        for key, value in values.items():
            line = f"{key} = {json.dumps(value)}"
            pattern = re.compile(rf"(?m)^[ \t]*{key}[ \t]*=[^\n]*$")
            if pattern.search(body):
                body = pattern.sub(line, body, count=1)
            else:
                body = body.rstrip("\n") + "\n" + line + "\n"
        text = text[:match.end()] + body.rstrip("\n") + "\n\n" + text[end:]
        expected["x264"].setdefault(name, {}).update(values)
    text = text.rstrip() + "\n"
    if tomllib.loads(text) != expected:
        raise ValueError("Unexpected graphics configuration change")
    return text


def configure(prefix):
    p = pathlib.Path(prefix)
    ini = p/'etc/xrdp/xrdp.ini'
    text = ini.read_text()
    for key, value in {'port': 'tcp://127.0.0.1:3389', 'security_layer': 'tls',
                       'certificate': '/etc/xrdp/cert.pem', 'key_file': '/etc/xrdp/key.pem',
                       'LogFile': '/var/log/cloud-cinnamon-xrdp.log', 'autorun': 'Xorg'}.items():
        text, count = re.subn(rf'(?m)^{key}=.*$', f'{key}={value}', text, count=1)
        if count != 1: raise ValueError('Missing config key '+key)
    text = text.replace('#runtime_user=xrdp', 'runtime_user=xrdp').replace('#runtime_group=xrdp', 'runtime_group=xrdp')
    ini.write_text(text)
    ini = p/'etc/xrdp/sesman.ini'; text = ini.read_text()
    text = text.replace('#SessionSockdirGroup=xrdp', 'SessionSockdirGroup=xrdp')
    text = text.replace('param=Xorg', 'param=/usr/lib/xorg/Xorg', 1)
    text = text.replace('param=xrdp/xorg.conf', 'param='+str(p/'etc/X11/xrdp/xorg.conf'), 1)
    text = re.sub(r'(?m)^LogFile=.*$', 'LogFile=/var/log/cloud-cinnamon-sesman.log', text)
    ini.write_text(text)
    conf = p/'etc/X11/xrdp/xorg.conf'; text = conf.read_text()
    marker = '# cloud-cinnamon module paths\n'
    if not text.startswith(marker):
        text = marker + f'Section "Files"\n ModulePath "{p}/lib/xorg/modules"\n ModulePath "/usr/lib/xorg/modules"\nEndSection\n' + text
    conf.write_text(text)
    for name in ('startwm.sh', 'reconnectwm.sh'):
        shutil.copy2('/etc/xrdp/'+name, p/'etc/xrdp'/name)
    gfx = p/'etc/xrdp/gfx.toml'
    gfx.write_text(configure_gfx(gfx.read_text()))


if __name__ == '__main__':
    configure('/opt/cloud-cinnamon/rdp-0.10.6.1')
