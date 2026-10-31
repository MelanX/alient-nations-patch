#!/usr/bin/env python3
"""Assemble cave/cave.s into anpatch/cave.bin and check the entry points match anpatch/exe.py.

Needs GNU binutils with i386 support (as, ld, objcopy). On Debian/Ubuntu/Mint: binutils.
"""
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from anpatch import exe  # noqa: E402

EXPECTED = {
    'next_res': exe.CAVE_NEXT_RES,
    'label': exe.CAVE_LABEL,
    'nres': exe.CAVE_RESTAB,
    'scroll_move': exe.CAVE_SCROLL_MOVE,
    'zero_vx': exe.CAVE_ZERO_VX,
    'zero_vy': exe.CAVE_ZERO_VY,
    'key_down_map': exe.CAVE_KEY_DOWN_MAP,
    'key_up_map': exe.CAVE_KEY_UP_MAP,
}


def run(*cmd):
    subprocess.run(cmd, check=True)


def main():
    src = os.path.join(ROOT, 'cave', 'cave.s')
    dst = os.path.join(ROOT, 'anpatch', 'cave.bin')
    with tempfile.TemporaryDirectory() as tmp:
        obj, elf, binf = (os.path.join(tmp, n) for n in ('cave.o', 'cave.elf', 'cave.bin'))
        run('as', '--32', '-o', obj, src)
        run('ld', '-m', 'elf_i386', '-Ttext=0x%x' % exe.CAVE_VA, '-e', '0x%x' % exe.CAVE_VA, '-o', elf, obj)
        run('objcopy', '-O', 'binary', '-j', '.text', elf, binf)
        syms = {}
        for line in subprocess.run(['nm', elf], check=True, capture_output=True, text=True).stdout.split('\n'):
            parts = line.split()
            if len(parts) == 3:
                syms[parts[2]] = int(parts[0], 16)
        bad = [(n, syms.get(n), a) for n, a in EXPECTED.items() if syms.get(n) != a]
        if bad:
            for n, got, want in bad:
                print('symbol %s at %s, anpatch/exe.py expects 0x%x' % (n, got and hex(got), want))
            sys.exit(1)
        with open(binf, 'rb') as f:
            data = f.read()
    if len(data) > exe.CAVE_END_VA - exe.CAVE_VA:
        sys.exit('cave.bin too large (%d bytes)' % len(data))
    with open(dst, 'wb') as f:
        f.write(data)
    print('%s: %d bytes, resolutions: %s' % (os.path.relpath(dst, ROOT), len(data),
          ', '.join('%dx%d' % r for r in exe.resolutions(data))))


if __name__ == '__main__':
    main()
