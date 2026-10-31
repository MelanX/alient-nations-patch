"""Binary patch for Bin/AN.exe (GOG v2.05, German).

Every patch checks the original bytes before it writes anything; if a byte differs
(other game version, already patched, ...) PatchError is raised and nothing is written.
"""
import os
import struct

# Mapping VA -> file offset: all sections of AN.exe have file offset == RVA, image base 0x400000.
IMAGE_BASE = 0x400000

CAVE_VA = 0x4a4690           # start of unused zero padding at the end of .text
CAVE_END_VA = 0x4a5000
# entry points in cave.bin (pinned with .org in cave/cave.s)
CAVE_NEXT_RES = 0x4a4690
CAVE_LABEL = 0x4a46e0
CAVE_RESTAB = 0x4a4720       # dword count, then (width, height) pairs
CAVE_SCROLL_MOVE = 0x4a47c0
CAVE_ZERO_VX = 0x4a4800
CAVE_ZERO_VY = 0x4a4850
CAVE_KEY_DOWN_MAP = 0x4a48a0
CAVE_KEY_UP_MAP = 0x4a48c0

TEXT_VSIZE_OFFSET = 0x1f0 + 8    # section header .text, VirtualSize field
DATA_VSIZE_OFFSET = 0x240 + 8    # section header .data, VirtualSize field

# Scroll speed in 1/16 px per 8 ms tick (original: 4 px acceleration, 32 px max per 25 ms tick).
SCROLL_ACCEL = 3
SCROLL_MAX = 104

CAVE_BIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cave.bin')


class PatchError(Exception):
    pass


def _rel32(frm, to):
    """rel32 operand of a 5-byte call/jmp at address frm."""
    return struct.pack('<i', to - (frm + 5))


def _call(frm, to):
    return b'\xe8' + _rel32(frm, to)


def _hex(s):
    return bytes.fromhex(s) if isinstance(s, str) else s


def patches():
    """List of (virtual address, original bytes, new bytes, description).

    New bytes shorter than the original are padded with NOPs.
    """
    return [
        # --- resolution toggle in the graphics settings -----------------------------------
        (0x42b0fd,
         '57 3b c6 bb db 01 00 00 bd 7c 01 00 00 75 0c be 00 04 00 00 bf 00 03 00 00 eb 05 bf 58 02 00 00',
         b'\x57\xbb\x90\x01\x00\x00\xbd\x7c\x01\x00\x00' + _call(0x42b108, CAVE_NEXT_RES),
         'toggle: cycle through the resolution table instead of 800x600 <-> 1024x768; '
         'also moves the label left edge 0x1db -> 0x190 so "2560 X 1440" fits'),
        (0x42b12e, '74 2a', '90 90',
         'toggle: ignore the DirectDraw mode list check (cnc-ddraw accepts any size)'),
        (0x42b151, '0f 94 c1', 'b1 01 90',
         'toggle: always set the "resolution changed" flag (the original flipped it, '
         'which only works with two modes)'),
        (0x42b15a,
         '81 3d a4 f3 4a 00 20 03 00 00 75 11 8b 15 08 39 4b 00 8b 42 04 8b b8 88 04 00 00 eb 0f',
         _call(0x42b15a, CAVE_LABEL) + b'\xeb' + bytes([0x42b186 - 0x42b161]),
         'toggle: label text "<w> X <h>" instead of the two fixed strings'),
        (0x42b644,
         'a1 a4 f3 4a 00 3d 20 03 00 00 75 10 a1 08 39 4b 00 8b 48 04 8b b9 88 04 00 00 eb 0f',
         _call(0x42b644, CAVE_LABEL) + b'\xeb' + bytes([0x42b66f - 0x42b64b]),
         'graphics settings menu: label text "<w> X <h>"'),
        (0x42b6a5, 'b8 db 01 00 00', 'b8 90 01 00 00',
         'graphics settings menu: label left edge 0x1db -> 0x190'),
        # --- switch to the selected mode -------------------------------------------------
        (0x484158, '3d 00 04 00 00 74', '3d 20 03 00 00 75',
         'starting a game: switch mode if width != 800 (was: width == 1024)'),
        (0x484173, '3d 00 04 00 00 75', '3d 20 03 00 00 74',
         'starting a game: same condition, second branch'),
        (0x484181, '68 00 03 00 00 68 00 04 00 00', 'ff 35 a8 f3 4a 00 50',
         'starting a game: use the configured width/height instead of 1024x768'),
        (0x4298d6, '81 f9 00 04 00 00 74 16', '81 f9 20 03 00 00 75 16',
         'closing the options menu in-game: re-apply mode if width != 800 (was: == 1024)'),
        # --- smooth scrolling -------------------------------------------------------------
        (0x44453d, '8b 73 1c 8b 53 20 03 f7 89 73 1c 8b 0d ec 44 4b 00 03 d1 89 53 20',
         _call(0x44453d, CAVE_SCROLL_MOVE),
         'scrolling: move by velocity/16 with sub-pixel remainder'),
        (0x444520, '83 e8 19', '83 e8 08', 'scrolling: 8 ms update step (was 25 ms)'),
        (0x4445f7, '83 c1 19', '83 c1 08', 'scrolling: 8 ms update step (was 25 ms)'),
        (0x4afc08, struct.pack('<4I', 4, 4, 32, 32),
         struct.pack('<4I', SCROLL_ACCEL, SCROLL_ACCEL, SCROLL_MAX, SCROLL_MAX),
         'scrolling: acceleration and top speed (x, y) in the new 1/16 px units'),
        (0x486989, 'c7 05 e8 44 4b 00 00 00 00 00', _call(0x486989, CAVE_ZERO_VX),
         'scrolling: moving the mouse no longer cancels keyboard scrolling (x)'),
        (0x4869e8, 'c7 05 ec 44 4b 00 00 00 00 00', _call(0x4869e8, CAVE_ZERO_VY),
         'scrolling: moving the mouse no longer cancels keyboard scrolling (y)'),
        # --- WASD -------------------------------------------------------------------------
        (0x44008c, '8b 46 0c 83 c0 df', _call(0x44008c, CAVE_KEY_DOWN_MAP),
         'keys: W/A/S/D act as arrow keys (key down)'),
        (0x43ff06, '8b 46 0c 83 c0 ed', _call(0x43ff06, CAVE_KEY_UP_MAP),
         'keys: W/A/S/D act as arrow keys (key up)'),
        # --- version text -----------------------------------------------------------------
        (0x486d5e, '68 b0 3a 4b 00', '68 60 72 4b 00',
         'version text: read into a 260-byte buffer (was char[8]; longer values '
         'overwrote the next variable)'),
        (0x428561, '68 b0 3a 4b 00', '68 60 72 4b 00',
         'version text: display from the new buffer'),
    ]


def apply(original, cave=None):
    """Return the patched AN.exe bytes for the original AN.exe bytes."""
    if cave is None:
        with open(CAVE_BIN, 'rb') as f:
            cave = f.read()
    d = bytearray(original)

    def off(va):
        return va - IMAGE_BASE

    # section sizes
    for name, pos, old, new in (('.text', TEXT_VSIZE_OFFSET, 0xa368a, 0xa4000),
                                ('.data', DATA_VSIZE_OFFSET, 0x8248, 0x8400)):
        cur = struct.unpack('<I', d[pos:pos + 4])[0]
        if cur != old:
            raise PatchError('%s VirtualSize is 0x%x, expected 0x%x' % (name, cur, old))
        # .text: covers the code cave; .data: 0x4b7250 scroll remainders, 0x4b7260 version text
        d[pos:pos + 4] = struct.pack('<I', new)

    # code cave
    if len(cave) > CAVE_END_VA - CAVE_VA:
        raise PatchError('cave.bin is too large')
    o = off(CAVE_VA)
    if d[o:o + len(cave)] != bytes(len(cave)):
        raise PatchError('code cave area at 0x%x is not empty' % CAVE_VA)
    d[o:o + len(cave)] = cave

    for va, old, new, desc in patches():
        old, new = _hex(old), _hex(new)
        if len(new) > len(old):
            raise PatchError('patch at 0x%x is longer than the original code' % va)
        o = off(va)
        if d[o:o + len(old)] != old:
            raise PatchError('unexpected bytes at 0x%x (%s): %s' % (va, desc, d[o:o + len(old)].hex(' ')))
        d[o:o + len(old)] = new + b'\x90' * (len(old) - len(new))
    return bytes(d)


def resolutions(cave=None):
    """(width, height) list from the resolution table in cave.bin."""
    if cave is None:
        with open(CAVE_BIN, 'rb') as f:
            cave = f.read()
    o = CAVE_RESTAB - CAVE_VA
    n = struct.unpack('<I', cave[o:o + 4])[0]
    return [struct.unpack('<II', cave[o + 4 + 8 * i:o + 12 + 8 * i]) for i in range(n)]
