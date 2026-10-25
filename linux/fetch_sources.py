#!/usr/bin/env python3
"""Fetch checksum-pinned upstream release tarballs; safe bounded extraction."""
import argparse
import hashlib
import json
import pathlib
import tarfile
import urllib.request


def fetch(destination):
    lock = json.loads((pathlib.Path(__file__).resolve().parents[1] / 'config/sources.json').read_text())
    destination.mkdir(parents=True, exist_ok=True)
    for name, item in lock.items():
        archive = destination / f'{name}-{item["version"]}.tar.gz'
        if not archive.exists():
            request = urllib.request.Request(item['url'], headers={'User-Agent': 'Cloud-Cinnamon-source-builder'})
            with urllib.request.urlopen(request, timeout=60) as response:
                data = response.read(32 * 1024 * 1024 + 1)
            if len(data) > 32 * 1024 * 1024: raise ValueError('Source archive too large')
            if hashlib.sha256(data).hexdigest() != item['sha256']: raise ValueError('Upstream checksum mismatch')
            archive.write_bytes(data)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != item['sha256']:
            raise ValueError(f'Checksum mismatch: {archive.name}')
        target = destination / f'{name}-{item["version"]}'
        if target.exists(): raise ValueError(f'Refusing to overwrite existing source tree: {target}')
        with tarfile.open(archive) as source:
            members = source.getmembers()
            if sum(m.size for m in members) > 256 * 1024 * 1024: raise ValueError('Expanded source too large')
            prefix = target.name + '/'
            for member in members:
                if member.name != target.name and not member.name.startswith(prefix): raise ValueError('Unexpected archive root')
            source.extractall(destination, filter='data')
        print('Verified and extracted', target.name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=pathlib.Path)
    fetch(parser.parse_args().destination)
