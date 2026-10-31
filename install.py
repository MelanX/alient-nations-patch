#!/usr/bin/env python3
"""Install / uninstall the Alien Nations (Die Völker) patch.

    python3 install.py "<game folder>"                 install
    python3 install.py "<game folder>" --ddraw         install, download cnc-ddraw if missing and set
                                                       the recommended cnc-ddraw options
    python3 install.py "<game folder>" --uninstall     restore the original files (and remove
                                                       cnc-ddraw if this script installed it)
    python3 install.py "<game folder>" --dry-run       check only, write nothing

<game folder> is the folder that contains Bin/ and Data/.
"""
import argparse
import hashlib
import io
import json
import os
import struct
import sys
import urllib.error
import urllib.request
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from anpatch import exe, sidebar  # noqa: E402

RACES = ('AMAZONS', 'PIMONS', 'SAJIKI')

# SHA-256 of the files shipped with the GOG release v2.05 (German).
ORIGINAL = {
    'Bin/AN.exe': 'd58e6b895944915cd6f8ced82f70f7c516f07ac92d567b369afe4982b6d5e060',
    'Data/AMAZONS/interface.gd': 'a49e3d7d979407a8e7834c700155ce3527712ac08744e84af23095dedc4e6fbe',
    'Data/PIMONS/interface.gd': 'cc3386b5c4249f47e002b47e142c62ae68d12fdd474ca0b5759caa8f4bd9e930',
    'Data/SAJIKI/interface.gd': '25f73e75d5dc8b549ca36298b27fd1340b5f16ed40b1dab5b3661237e7c5c4b7',
}
# SHA-256 of the patched files produced by this version of the patch.
PATCHED = {
    'Bin/AN.exe': '8abc8f5536a15d5b53eaa55ec790ca12300ebe8bc60a6d3f956f68504860dbe8',
    'Data/AMAZONS/interface.gd': '8d261dfd4dfc946734d2d67c2d77c482197c15466eda36fd0bc2eeedcb34e103',
    'Data/PIMONS/interface.gd': '52da308919748e098b458741bfcc06a4df27fd4a11de1b1732074553e9a59bf5',
    'Data/SAJIKI/interface.gd': '952ced3ed0709af70016e20a94239b841610054564ca46557e18d19d4ac370c3',
}

# cnc-ddraw (https://github.com/FunkyFr3sh/cnc-ddraw), downloaded with --ddraw if Bin/ddraw.dll is missing
CNC_DDRAW_RELEASE = 'https://api.github.com/repos/FunkyFr3sh/cnc-ddraw/releases/latest'
CNC_DDRAW_ASSET = 'cnc-ddraw.zip'
CNC_DDRAW_RECORD = 'cnc-ddraw.anpatch.json'   # in Bin/: files added by this script, used by --uninstall

# Recommended cnc-ddraw settings ([ddraw] section of Bin/ddraw.ini).
DDRAW_SETTINGS = [
    ('fullscreen', 'true'),       # with windowed=true: borderless fullscreen
    ('windowed', 'true'),
    ('maintas', 'true'),          # keep the aspect ratio when scaling
    ('border', 'false'),
    ('resolutions', '2'),         # accept every resolution
    ('renderer', 'opengl'),       # needed for .glsl shaders ("auto" picks Direct3D 9)
    ('shader', r'Shaders\interpolation\fsr.glsl'),
]


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    with open(path, 'rb') as f:
        return f.read()


def write_atomic(path, data):
    tmp = path + '.tmp'
    with open(tmp, 'wb') as f:
        f.write(data)
    os.replace(tmp, path)


def build(rel, original):
    if rel == 'Bin/AN.exe':
        return exe.apply(original)
    return sidebar.apply(original)


def find_original(game, rel):
    """Original bytes of a file, from the file itself or its .orig backup. Returns (bytes, state)."""
    path = os.path.join(game, rel)
    if not os.path.isfile(path):
        raise SystemExit('missing %s - is this the Alien Nations folder?' % path)
    cur = read(path)
    h = sha256(cur)
    if h == ORIGINAL[rel]:
        return cur, 'original'
    backup = path + '.orig'
    if os.path.isfile(backup):
        orig = read(backup)
        if sha256(orig) == ORIGINAL[rel]:
            return orig, 'patched' if h == PATCHED[rel] else 'modified'
        raise SystemExit('%s does not match the original GOG v2.05 file' % backup)
    raise SystemExit('%s is not the original GOG v2.05 file (SHA-256 %s) and there is no .orig backup.\n'
                     'This patch only supports the GOG release v2.05 (German).' % (path, h))


def install(game, dry_run):
    files = ['Bin/AN.exe'] + ['Data/%s/interface.gd' % r for r in RACES]
    plan = []
    for rel in files:
        orig, state = find_original(game, rel)
        backup = os.path.join(game, rel) + '.orig'
        if os.path.exists(backup) and sha256(read(backup)) != ORIGINAL[rel]:
            raise SystemExit('%s exists but is not the original file - move it away first' % backup)
        new = build(rel, orig)
        h = sha256(new)
        note = ''
        if PATCHED[rel] and h != PATCHED[rel]:
            note = ' (differs from the reference build - expected only if you changed the patch)'
        plan.append((rel, orig, new, state))
        print('%-27s %-9s -> patched%s' % (rel, state, note))
    if dry_run:
        print('dry run, nothing written')
        return
    for rel, orig, new, state in plan:
        path = os.path.join(game, rel)
        backup = path + '.orig'
        if not os.path.exists(backup):
            write_atomic(backup, orig)
        write_atomic(path, new)
    print('installed. Originals are kept as *.orig next to the patched files.')


def uninstall(game, dry_run):
    files = ['Bin/AN.exe'] + ['Data/%s/interface.gd' % r for r in RACES]
    for rel in files:
        path = os.path.join(game, rel)
        backup = path + '.orig'
        if os.path.isfile(path) and sha256(read(path)) == ORIGINAL[rel]:
            print('%-27s already original' % rel)
            continue
        if not os.path.isfile(backup) or sha256(read(backup)) != ORIGINAL[rel]:
            raise SystemExit('no valid backup %s - restore the file from GOG instead' % backup)
        print('%-27s restore from .orig' % rel)
        if not dry_run:
            write_atomic(path, read(backup))
            os.remove(backup)
    # The original game only knows 800x600 and 1024x768; reset a saved custom resolution.
    cfg = os.path.join(game, 'Savegames', 'an.cfg')
    if os.path.isfile(cfg):
        d = bytearray(read(cfg))
        if len(d) >= 0x2d:
            w, h = struct.unpack('<II', d[0x25:0x2d])
            if (w, h) not in ((800, 600), (1024, 768)):
                print('Savegames/an.cfg: resolution %dx%d -> 1024x768' % (w, h))
                if not dry_run:
                    d[0x25:0x2d] = struct.pack('<II', 1024, 768)
                    write_atomic(cfg, bytes(d))
    uninstall_cnc_ddraw(game, dry_run)
    print('dry run, nothing written' if dry_run else 'uninstalled.')


def http_get(url, accept=None):
    headers = {'User-Agent': 'alien-nations-patch'}
    if accept:
        headers['Accept'] = accept
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as r:
        return r.read()


def download_cnc_ddraw():
    """Latest cnc-ddraw release from GitHub. Returns (version, zip SHA-256, {path: bytes})."""
    try:
        release = json.loads(http_get(CNC_DDRAW_RELEASE, 'application/vnd.github+json'))
        asset = next(a for a in release['assets'] if a['name'] == CNC_DDRAW_ASSET)
        data = http_get(asset['browser_download_url'])
    except (urllib.error.URLError, OSError, ValueError, KeyError, StopIteration) as e:
        raise SystemExit('Could not download cnc-ddraw (%s).\n'
                         'Install it manually (see README) and run the installer again.' % e)
    if asset.get('size') and len(data) != asset['size']:
        raise SystemExit('cnc-ddraw download incomplete (%d of %d bytes)' % (len(data), asset['size']))
    digest = asset.get('digest') or ''
    if digest.startswith('sha256:') and digest[7:] != sha256(data):
        raise SystemExit('cnc-ddraw download does not match the SHA-256 published by GitHub')
    files = {}
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            name = info.filename.replace('\\', '/')
            if name.startswith('/') or ':' in name or '..' in name.split('/'):
                raise SystemExit('unexpected path in %s: %r' % (CNC_DDRAW_ASSET, info.filename))
            files[name] = z.read(info)
    if 'ddraw.dll' not in files or 'ddraw.ini' not in files:
        raise SystemExit('%s does not contain ddraw.dll and ddraw.ini' % CNC_DDRAW_ASSET)
    return release.get('tag_name', '?'), sha256(data), files


def install_cnc_ddraw(game, version, files, dry_run):
    bindir = os.path.join(game, 'Bin')
    added = []
    for name, data in sorted(files.items()):
        path = os.path.join(bindir, *name.split('/'))
        if os.path.exists(path):
            continue                         # never overwrite files that are already there
        added.append(name)
        if not dry_run:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            write_atomic(path, data)
    print('Bin/: cnc-ddraw %s, %d files added' % (version, len(added)))
    if not dry_run:
        with open(os.path.join(bindir, CNC_DDRAW_RECORD), 'w') as f:
            json.dump({'version': version, 'files': added}, f, indent=1)


def cnc_ddraw_record(game):
    path = os.path.join(game, 'Bin', CNC_DDRAW_RECORD)
    if not os.path.isfile(path):
        return None
    with open(path) as f:
        return json.load(f)


def apply_ddraw_settings(data):
    """Set DDRAW_SETTINGS in the [ddraw] section of a ddraw.ini (bytes -> bytes)."""
    lines = data.decode('latin-1').splitlines(keepends=True)        # keep each line's own ending
    try:
        start = next(i for i, l in enumerate(lines) if l.strip().lower() == '[ddraw]')
    except StopIteration:
        raise SystemExit('no [ddraw] section in Bin/ddraw.ini')
    end = next((i for i in range(start + 1, len(lines)) if lines[i].strip().startswith('[')), len(lines))
    eol = lines[start][len(lines[start].rstrip('\r\n')):] or '\r\n'
    insert_at = start + 1
    for key, value in DDRAW_SETTINGS:
        idx = next((i for i in range(start + 1, end)
                    if lines[i].split('=', 1)[0].strip().lower() == key), None)
        if idx is None:
            lines.insert(insert_at, '%s=%s%s' % (key, value, eol))
            insert_at += 1
            end += 1
        else:
            ending = lines[idx][len(lines[idx].rstrip('\r\n')):]
            lines[idx] = '%s=%s%s' % (key, value, ending)
        print('Bin/ddraw.ini: %s=%s' % (key, value))
    return ''.join(lines).encode('latin-1')


def configure_ddraw(game, dry_run, pending_ini=None):
    """pending_ini: ddraw.ini that would have been installed (dry run only)."""
    path = os.path.join(game, 'Bin', 'ddraw.ini')
    if pending_ini is not None and not os.path.isfile(path):
        apply_ddraw_settings(pending_ini)
        return
    if not os.path.isfile(path):
        print('Bin/ddraw.ini not found, skipping cnc-ddraw settings')
        return
    new = apply_ddraw_settings(read(path))
    if dry_run:
        return
    record = cnc_ddraw_record(game) or {'files': []}
    backup = path + '.orig'
    if 'ddraw.ini' not in record['files'] and not os.path.exists(backup):
        write_atomic(backup, read(path))     # only back up a ddraw.ini the user already had
    write_atomic(path, new)


def uninstall_cnc_ddraw(game, dry_run):
    bindir = os.path.join(game, 'Bin')
    record = cnc_ddraw_record(game)
    if record is not None:
        print('Bin/: remove cnc-ddraw %s (%d files added by the installer)'
              % (record.get('version', '?'), len(record['files'])))
        if not dry_run:
            dirs = set()
            for name in record['files']:
                path = os.path.join(bindir, *name.split('/'))
                if os.path.isfile(path):
                    os.remove(path)
                d = os.path.dirname(name)
                while d:
                    dirs.add(d)
                    d = os.path.dirname(d)
            for d in sorted(dirs, key=len, reverse=True):     # remove now-empty folders
                path = os.path.join(bindir, *d.split('/'))
                if os.path.isdir(path) and not os.listdir(path):
                    os.rmdir(path)
            os.remove(os.path.join(bindir, CNC_DDRAW_RECORD))
    backup = os.path.join(bindir, 'ddraw.ini.orig')
    if os.path.isfile(backup):
        print('Bin/ddraw.ini: restore from .orig')
        if not dry_run:
            write_atomic(os.path.join(bindir, 'ddraw.ini'), read(backup))
            os.remove(backup)


WINE_HINT = ('Wine/Proton: make sure the DLL override "ddraw=native,builtin" is set for this game '
             '(e.g. WINEDLLOVERRIDES="ddraw=n,b"), otherwise Wine ignores cnc-ddraw. See README.')


def main():
    ap = argparse.ArgumentParser(description='Alien Nations (Die Völker) GOG v2.05 patch')
    ap.add_argument('game', help='game folder (contains Bin/ and Data/)')
    ap.add_argument('--uninstall', action='store_true',
                    help='restore the original files and remove cnc-ddraw if this script installed it')
    ap.add_argument('--ddraw', action='store_true',
                    help='download cnc-ddraw if Bin/ddraw.dll is missing and set the recommended options')
    ap.add_argument('--dry-run', action='store_true', help='check only, write nothing')
    args = ap.parse_args()
    game = os.path.abspath(args.game)
    if args.uninstall:
        uninstall(game, args.dry_run)
        return
    package = None
    if args.ddraw:
        if os.path.isfile(os.path.join(game, 'Bin', 'ddraw.dll')):
            print('Bin/ddraw.dll found, keeping the existing cnc-ddraw')
        elif os.path.isdir(os.path.join(game, 'Bin')):
            print('downloading the latest cnc-ddraw release from GitHub ...')
            package = download_cnc_ddraw()     # before patching, so a failed download changes nothing
            print('cnc-ddraw %s, %s SHA-256 %s' % (package[0], CNC_DDRAW_ASSET, package[1]))
    install(game, args.dry_run)
    if args.ddraw:
        if package:
            install_cnc_ddraw(game, package[0], package[2], args.dry_run)
        configure_ddraw(game, args.dry_run, package[2]['ddraw.ini'] if package and args.dry_run else None)
        if os.name != 'nt':
            print(WINE_HINT)


if __name__ == '__main__':
    main()
