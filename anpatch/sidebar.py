"""Sidebar backgrounds (INTERFACE<width>) for the extra resolutions.

The game looks up the right-hand sidebar background as INTERFACE<screen width> in
Data/<race>/interface.gd. Only INTERFACE800 (192x600) and INTERFACE1024 (192x768) ship with it.
New ones are made from INTERFACE1024 by repeating (taller) or cutting (shorter) a band of the
lower panel, picked where the rows on both sides of the seam match best.

Sprite format (RLE, 4 bytes per pixel BGRA as u32), stream of u16 commands, type = low 4 bits,
n = cmd >> 4:
    0  literal: n+1 pixels follow        2  next line(s): move down n+1 rows, back to x=0
    1  fill: n+2 pixels of one u32        3  skip n+1 pixels
    4  end
Blob = 52-byte header + [0, F] + stream (padded to 4) + [0, F], F = size after the header.
"""
import struct

from . import exe
from .gdfile import GD

WIDTH = 192


def decode_rows(blob, height):
    rows = [[0] * WIDTH for _ in range(height)]
    p = 60
    x = y = 0
    while True:
        c = struct.unpack('<H', blob[p:p + 2])[0]
        t, n = c & 15, c >> 4
        if t == 4:
            break
        if t == 0:
            rows[y][x:x + n + 1] = struct.unpack('<%dI' % (n + 1), blob[p + 2:p + 6 + 4 * n])
            x += n + 1
            p += 2 + 4 * (n + 1)
        elif t == 1:
            v = struct.unpack('<I', blob[p + 2:p + 6])[0]
            rows[y][x:x + n + 2] = [v] * (n + 2)
            x += n + 2
            p += 6
        elif t == 2:
            y += n + 1
            x = 0
            p += 2
        elif t == 3:
            x += n + 1
            p += 2
        else:
            raise ValueError('unknown RLE command %d' % t)
    if any(len(r) != WIDTH for r in rows):
        raise ValueError('sprite is not %d px wide' % WIDTH)
    return rows


def encode_rows(rows):
    out = bytearray()
    for r in rows:
        i = 0
        while i < len(r):
            j = i
            while j < len(r) and r[j] == r[i] and j - i < 4097:
                j += 1
            if j - i >= 3:                                      # fill run
                out += struct.pack('<HI', ((j - i - 2) << 4) | 1, r[i])
                i = j
            else:                                               # literal run
                k = i
                while k < len(r) and k - i < 4096:
                    if k + 2 < len(r) and r[k] == r[k + 1] == r[k + 2]:
                        break
                    k += 1
                if k == i:
                    k = i + 1
                out += struct.pack('<H', (k - i - 1) << 4) + struct.pack('<%dI' % (k - i), *r[i:k])
                i = k
        out += struct.pack('<H', 2)                             # next line
    out += struct.pack('<H', 4)                                 # end
    while len(out) % 4:
        out += b'\0'
    return bytes(out)


def make_blob(header52, rows):
    stream = encode_rows(rows)
    size = 8 + len(stream) + 8
    hdr = list(struct.unpack('<13I', header52))
    hdr[2] = 52 + size
    return struct.pack('<13I', *hdr) + struct.pack('<2I', 0, size) + stream + struct.pack('<2I', 0, size)


def _rowdiff(a, b):
    t = 0
    for u, v in zip(a, b):
        t += (abs((u >> 16 & 255) - (v >> 16 & 255)) + abs((u >> 8 & 255) - (v >> 8 & 255))
              + abs((u & 255) - (v & 255)))
    return t


def _seam(rows, a, b):
    """Cost of continuing at row b after row a-1."""
    return sum(_rowdiff(rows[a + k], rows[b + k]) for k in (-2, -1, 0, 1))


def resize(rows, height, lo=440, hi=720):
    """Change the height by repeating/removing a band between rows lo and hi."""
    extra = height - len(rows)
    if extra == 0:
        return [r[:] for r in rows]
    if extra < 0:
        p = -extra
        a = min(range(lo, hi - p), key=lambda a: _seam(rows, a, a + p))
        return rows[:a] + rows[a + p:]
    best = None
    for m in range(1, 20):                  # band height p with extra == m * p repeats cleanly
        if extra % m:
            continue
        p = extra // m
        if not 40 <= p <= hi - lo - 4:
            continue
        for a in range(lo, hi - p):
            c = _seam(rows, a, a + p)
            if best is None or c < best[0]:
                best = (c, a, p, m)
    if best is None:
        raise ValueError('cannot build a %d px tall sidebar' % height)
    _, a, p, m = best
    return rows[:a + p] + rows[a:a + p] * m + rows[a + p:]


def extra_resolutions():
    """Resolutions from the exe patch that need a new sidebar."""
    return [(w, h) for w, h in exe.resolutions() if w not in (800, 1024)]


def apply(original):
    """Return interface.gd bytes with INTERFACE<width> added for every extra resolution."""
    g = GD(original)
    targets = extra_resolutions()
    for w, _ in targets:
        if b'INTERFACE%d' % w in g.names():
            raise ValueError('INTERFACE%d already present (file already patched?)' % w)
    rec, blob = g.get(b'INTERFACE1024')
    rows = decode_rows(blob, rec[9])
    for w, h in targets:
        new_rows = resize(rows, h)
        new_rec = list(rec)
        new_rec[7] = new_rec[9] = h
        g.add(b'INTERFACE%d' % w, new_rec, make_blob(blob[:52], new_rows))
    out = g.build()
    # self-check: everything that was there is unchanged, new sprites decode back correctly
    g2, g0 = GD(out), GD(original)
    for name in g0.names():
        if g2.get(name)[1] != g0.get(name)[1]:
            raise AssertionError('entry %r changed' % name)
    for w, h in targets:
        r2, b2 = g2.get(b'INTERFACE%d' % w)
        if r2[7] != h or len(decode_rows(b2, h)) != h:
            raise AssertionError('INTERFACE%d broken' % w)
    return out
