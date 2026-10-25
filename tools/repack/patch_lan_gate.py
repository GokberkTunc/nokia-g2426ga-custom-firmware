# -*- coding: utf-8 -*-
"""Patch the operator gate in lan_ipv4.cgi (LAN IPv4 / DHCP save permission).

Stock behaviour
---------------
The LAN page submits its forms as:

    POST /lan_ipv4.cgi?config      (LAN IP + DHCP pool)
    POST /lan_ipv4.cgi?allbridge   (port mode)

For the ``config`` and ``allbridge`` handlers the binary first calls
``is_operatorId("PHRA")`` and, when the device OperatorID is anything else
(TRCL, ALCL, ...), it aborts with:

    <script>alert("The normal user do not have permission to do this!");</script>

This is an OEM gate, not a user-role problem: the same error appears for the
SuperUser account and even for a plain GET of ``?config``.

Patch
-----
Two ``bnez`` instructions that guard the "allowed" branch are turned into
unconditional ``b`` instructions, so the permission check result is ignored:

    0x406210 : 14 40 00 04  ->  10 40 00 04   (?config gate)
    0x4074c0 : 14 40 01 fc  ->  10 40 01 fc   (?allbridge gate)

Usage
-----
    python patch_lan_gate.py path/to/rootfs_sq/webs/lan_ipv4.cgi
    python patch_lan_gate.py --check path/to/rootfs_sq/webs/lan_ipv4.cgi
"""

import argparse
import shutil
import sys

PATCHES = [
    # (file offset = vaddr - 0x400000, original word, patched word, description)
    (0x6210, 0x14400004, 0x10000004, '?config permission gate'),
    (0x74C0, 0x144001FC, 0x100001FC, '?allbridge permission gate'),
]


def main():
    p = argparse.ArgumentParser(description='Patch lan_ipv4.cgi operator gate')
    p.add_argument('cgi', help='path to webs/lan_ipv4.cgi inside the extracted rootfs')
    p.add_argument('--check', action='store_true', help='only report, do not modify')
    p.add_argument('--no-backup', action='store_true', help='do not write a .orig copy')
    args = p.parse_args()

    data = bytearray(open(args.cgi, 'rb').read())
    if len(data) < 0x8000:
        print('[-] File looks too small to be lan_ipv4.cgi')
        return 1

    changed = False
    for off, orig, patched, desc in PATCHES:
        cur = int.from_bytes(data[off:off + 4], 'little')
        if cur == patched:
            print('[=] %-26s already patched (0x%08x)' % (desc, cur))
        elif cur == orig:
            print('[+] %-26s 0x%08x -> 0x%08x' % (desc, cur, patched))
            if not args.check:
                data[off:off + 4] = patched.to_bytes(4, 'little')
            changed = True
        else:
            print('[!] %-26s unexpected 0x%08x at 0x%x (expected 0x%08x)' % (desc, cur, off, orig))
            return 1

    if args.check or not changed:
        return 0

    if not args.no_backup:
        shutil.copyfile(args.cgi, args.cgi + '.orig')
        print('[*] Backup written to %s.orig' % args.cgi)
    open(args.cgi, 'wb').write(bytes(data))
    print('[+] Patched %s' % args.cgi)
    return 0


if __name__ == '__main__':
    sys.exit(main())
