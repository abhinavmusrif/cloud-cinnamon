#!/usr/bin/env python3
"""Configure only the isolated build, without changing packaged configuration."""
import pathlib
import re
import shutil


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
    gfx = p/'etc/xrdp/gfx.toml'; text = gfx.read_text()
    for key, value in [('fps_num','30'), ('threads','2'), ('vbv_max_bitrate','6_000'), ('vbv_buffer_size','600')]:
        text = re.sub(rf'(?m)^(\s*){key}\s*=.*$', rf'\g<1>{key} = {value}', text)
    gfx.write_text(text)


if __name__ == '__main__':
    configure('/opt/cloud-cinnamon/rdp-0.10.6.1')
