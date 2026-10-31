"""Reader/writer for the game's .gd graphics archives (as used by Data/<race>/interface.gd).

Layout (all little-endian uint32):
    header      6 x u32: names_offset(=24), 24, index_offset, records_offset, data_offset, count
    names       NUL-terminated strings, byte-sorted (string pool)
    index       count x u32: offset of entry i's name in the string pool
    records     count x 64 bytes; record i belongs to entry count-1-i:
                  [2] entry index, [6..9] width/height (twice), [12] frame count,
                  [13] 0x00040004 (RLE, 4 bytes/pixel), [14] blob offset relative to data_offset
    data        sprite blobs; blob size is stored at blob+8

Existing data is kept byte-for-byte; new blobs are appended 4 KiB aligned.
"""
import struct


class GD:
    def __init__(self, data):
        self.raw = bytes(data)
        d = self.raw
        h = struct.unpack('<6I', d[:24])
        if h[0] != 24 or h[1] != 24:
            raise ValueError('not a .gd archive')
        n = h[5]
        name_offsets = struct.unpack('<%dI' % n, d[h[2]:h[2] + 4 * n])
        names = [d[24 + o:d.index(b'\0', 24 + o)] for o in name_offsets]
        recs = {}
        for i in range(n):
            rec = list(struct.unpack('<16I', d[h[3] + 64 * i:h[3] + 64 * i + 64]))
            if rec[2] != n - 1 - i:
                raise ValueError('unexpected record order')
            recs[rec[2]] = rec
        # entries in index order: [name, record]
        self.entries = [[names[j], recs[j]] for j in range(n)]
        self.data = bytearray(d[h[4]:])

    @classmethod
    def load(cls, path):
        with open(path, 'rb') as f:
            return cls(f.read())

    def names(self):
        return [e[0] for e in self.entries]

    def get(self, name):
        """(record, blob) of an entry."""
        rec = next(e[1] for e in self.entries if e[0] == name)
        o = rec[14]
        size = struct.unpack('<I', self.data[o + 8:o + 12])[0]
        return list(rec), bytes(self.data[o:o + size])

    def add(self, name, rec, blob):
        if name in self.names():
            raise ValueError('%r already exists' % name)
        while len(self.data) % 4096:
            self.data += b'\0'
        rec = list(rec)
        rec[14] = len(self.data)
        self.data += blob
        # keep the shipped order, insert before the first name that sorts after the new one
        idx = next((k for k, e in enumerate(self.entries) if e[0] > name), len(self.entries))
        self.entries.insert(idx, [name, rec])

    def build(self):
        n = len(self.entries)
        pool, pos = b'', {}
        for name in sorted(e[0] for e in self.entries):
            pos[name] = len(pool)
            pool += name + b'\0'
        index_off = 24 + len(pool)
        records_off = index_off + 4 * n
        data_off = records_off + 64 * n
        out = bytearray(struct.pack('<6I', 24, 24, index_off, records_off, data_off, n))
        out += pool
        out += struct.pack('<%dI' % n, *[pos[e[0]] for e in self.entries])
        for i in range(n):
            j = n - 1 - i
            rec = list(self.entries[j][1])
            rec[2] = j
            out += struct.pack('<16I', *rec)
        return bytes(out + self.data)
