# -*- coding: utf-8 -*-
"""lls ciktisindan mksquashfs pseudo-file uret (mod/uid/gid birebir geri yukle)."""
import re, sys

PERM_BITS = {'r': 4, 'w': 2, 'x': 1, '-': 0}


def mode_from_ls(perm):
    # ornek: -rwsr-xr-- / drwxr-xr-x / lrwxrwxrwx
    special = 0
    out = 0
    for tri in range(3):
        chunk = perm[1 + tri * 3:4 + tri * 3]
        val = 0
        for i, ch in enumerate(chunk):
            bit = PERM_BITS.get(ch, 0)
            if ch in 'sS':
                bit = 1 if ch == 's' else 0
                special |= 0o4000 if tri == 0 else 0o2000  # setuid / setgid
            if ch in 'tT':
                bit = 1 if ch == 't' else 0
                special |= 0o1000  # sticky
            val |= bit
        out |= val << ((2 - tri) * 3)
    return special | out


def main():
    lls_path, out_path = sys.argv[1], sys.argv[2]
    raw = open(lls_path, 'rb').read()
    txt = raw.decode('utf-16', errors='replace') if raw[:2] in (b'\xff\xfe', b'\xfe\xff') else raw.decode('utf-8', errors='replace')
    n = 0
    with open(out_path, 'w', newline='\n') as o:
        for line in txt.splitlines():
            m = re.match(r'^(\S+)\s+(\d+)/(\d+)\s+(\d+)\s+\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}\s+(.+)$', line.rstrip())
            if not m:
                continue
            perm, uid, gid, size, rest = m.groups()
            path = rest.split(' -> ', 1)[0]
            if path.startswith('squashfs-root'):
                path = path[len('squashfs-root'):]
            if not path or path == '/':
                continue
            path = path.lstrip('/')
            mode = mode_from_ls(perm)
            o.write('%s m 0%o %s %s\n' % (path, mode, uid, gid))
            n += 1
    print('pseudo kural: %d satir -> %s' % (n, out_path))


if __name__ == '__main__':
    main()
