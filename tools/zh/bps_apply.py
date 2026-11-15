#!/usr/bin/env python3
"""Apply a BPS (beat) patch to a file.

Command bytes are themselves BPS varints, so a read can carry any length.
"""
import struct
import sys
import zlib
from pathlib import Path


def read_varint(data, p):
    value, shift = 0, 1
    while True:
        x = data[p]
        p += 1
        value += (x & 0x7f) * shift
        if x & 0x80:
            return value, p
        shift <<= 7
        value += shift


def apply(source, patch, verify=True):
    if patch[:4] != b'BPS1':
        raise ValueError('not a BPS patch')
    p = 4
    src_size, p = read_varint(patch, p)
    dst_size, p = read_varint(patch, p)
    meta, p = read_varint(patch, p)
    p += meta
    if src_size != len(source):
        raise ValueError('source is %d bytes, patch wants %d' % (len(source), src_size))
    out = bytearray()
    s_rel = t_rel = 0
    end = len(patch) - 12
    while p < end:
        cmd, p = read_varint(patch, p)
        length, mode = (cmd >> 2) + 1, cmd & 3
        if mode == 0:
            out += source[len(out):len(out) + length]
        elif mode == 1:
            out += patch[p:p + length]
            p += length
        else:
            delta, p = read_varint(patch, p)
            delta = -(delta >> 1) if delta & 1 else delta >> 1
            if mode == 2:
                s_rel += delta
                out += source[s_rel:s_rel + length]
                s_rel += length
            else:
                t_rel += delta
                for _ in range(length):
                    out.append(out[t_rel])
                    t_rel += 1
    if len(out) != dst_size:
        raise ValueError('produced %d bytes, patch wants %d' % (len(out), dst_size))
    if verify:
        src_crc, dst_crc, patch_crc = struct.unpack_from('<III', patch, len(patch) - 12)
        if zlib.crc32(patch[:-4]) != patch_crc:
            raise ValueError('patch CRC mismatch')
        if zlib.crc32(out) != dst_crc:
            raise ValueError('target CRC mismatch')
    return bytes(out)


if __name__ == '__main__':
    src = Path(sys.argv[1]).read_bytes()
    pat = Path(sys.argv[2]).read_bytes()
    result = apply(src, pat)
    Path(sys.argv[3]).write_bytes(result)
    print('%s: %d bytes (CRC32 %08x)' % (sys.argv[3], len(result), zlib.crc32(result)))
