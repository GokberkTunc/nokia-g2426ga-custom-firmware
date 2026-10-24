# -*- coding: utf-8 -*-
"""Nokia G-2426G-A HDR2 Firmware Repacker.

Reconstructs an un-signed HDR2 firmware image accepted by U-Boot:
- Original Header (HDR2 magic, 0x118 bytes)
- Original Kernel (LZMA, untouched)
- Modified SquashFS (Squashfs v4.0, LZMA, 128K block size)
- Original Extra Region (LZMA-compressed U-Boot bootram)

Checksum:
- JAMCRC over (body = kernel + rootfs + extra)
- Algorithm: zlib.crc32(body) ^ 0xFFFFFFFF
"""

import argparse
import hashlib
import os
import struct
import sys
import zlib

HDRLEN = 0x118


def repack(pkg_path, sqfs_path, out_path):
    if not os.path.isfile(pkg_path):
        print(f"[-] Base firmware package not found: {pkg_path}")
        sys.exit(1)
    if not os.path.isfile(sqfs_path):
        print(f"[-] SquashFS rootfs not found: {sqfs_path}")
        sys.exit(1)

    print(f"[*] Reading base package: {pkg_path}")
    d = open(pkg_path, "rb").read()

    hdrlen, totalsz, oldck = struct.unpack_from("<III", d, 4)
    klen, rlen = struct.unpack_from("<II", d, 0x50)
    extra_len = struct.unpack_from("<I", d, 0x9C)[0]

    if hdrlen != HDRLEN:
        print(f"[-] Invalid header length: {hdrlen:#x} (expected {HDRLEN:#x})")
        sys.exit(1)

    hdr = bytearray(d[:HDRLEN])
    kernel = d[HDRLEN : HDRLEN + klen]
    extra = d[HDRLEN + klen + rlen : HDRLEN + klen + rlen + extra_len]
    new_sq = open(sqfs_path, "rb").read()

    print(
        f"[*] Kernel: {klen:#x} bytes ({klen} B), Old RootFS: {rlen:#x} B, New RootFS: {len(new_sq):#x} B, Extra: {extra_len:#x} B"
    )

    new_len = HDRLEN + klen + len(new_sq) + extra_len
    body = kernel + new_sq + extra
    crc = zlib.crc32(body) ^ 0xFFFFFFFF

    # Update header metadata
    struct.pack_into("<I", hdr, 0x08, new_len)
    struct.pack_into("<I", hdr, 0x0C, crc)
    struct.pack_into("<I", hdr, 0x54, len(new_sq))

    out = bytes(hdr) + body
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    open(out_path, "wb").write(out)
    md5 = hashlib.md5(out).hexdigest()

    print(f"[+] Successfully wrote: {out_path} ({len(out)} bytes)")
    print(
        f"    Length: {new_len:#x}, JAMCRC: {crc:#010x}, RootFS Size: {len(new_sq):#x}"
    )
    print(f"    MD5: {md5}")

    # Self-verification
    v = open(out_path, "rb").read()
    h2, t2, c2 = struct.unpack_from("<III", v, 4)
    k2, r2 = struct.unpack_from("<II", v, 0x50)
    assert h2 == HDRLEN and t2 == len(v) and r2 == len(new_sq)
    assert v[h2 : h2 + k2] == kernel
    assert (zlib.crc32(v[HDRLEN:]) ^ 0xFFFFFFFF) == c2
    sqofs = v.find(b"hsqs")
    assert sqofs == HDRLEN + klen
    print(f"[+] Verification PASSED: Header, CRC, and SquashFS offset {sqofs:#x}")


def main():
    p = argparse.ArgumentParser(
        description="Nokia G-2426G-A HDR2 Firmware Repacker"
    )
    p.add_argument(
        "--pkg", required=True, help="Path to base stock firmware .bin package"
    )
    p.add_argument(
        "--sqfs",
        required=True,
        help="Path to new/modified rootfs.sqfs (Squashfs v4, LZMA)",
    )
    p.add_argument(
        "--out", required=True, help="Output destination path for repacked .bin"
    )
    args = p.parse_args()
    repack(args.pkg, args.sqfs, args.out)


if __name__ == "__main__":
    main()
