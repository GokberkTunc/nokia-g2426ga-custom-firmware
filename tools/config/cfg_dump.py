# -*- coding: utf-8 -*-
"""Nokia G-2426G-A config database dumper / decoder.

The router keeps its configuration in an encrypted container:
    /configs/config_encryption.cfg

This tool asks the router's own config manager (`cfgcli`) to decode it, pulls
the resulting plain XML back to the PC and turns it into a flat
"full.path = value" listing.

Notes
-----
* The file container (52-byte header + deflate + cipher) is decoded by the
  router itself, so no key material is required on the PC.
* Individual *sensitive* nodes stay encrypted even inside the decoded XML:
  they carry ``ealgo="sab"`` and a key name (``kn="key11"``). Their values are
  shown as <ENCRYPTED> instead of the ciphertext.
* Everything happens over the root telnet shell. Nothing is written outside
  /tmp on the router.

Usage
-----
    python tools/config/cfg_dump.py                     # full config, masked
    python tools/config/cfg_dump.py --grep ppp         # only matching paths
    python tools/config/cfg_dump.py --out config.xml   # keep the raw XML
    python tools/config/cfg_dump.py --show-secrets      # also print plaintext
"""

import argparse
import json
import re
import socket
import sys
import time
import xml.etree.ElementTree as ET

CHUNK = 16384


class Router:
    def __init__(self, ip, port, timeout=10):
        self.sock = socket.create_connection((ip, port), timeout=timeout)
        self.sock.settimeout(1.0)
        time.sleep(0.4)
        try:
            self.sock.recv(8192)
        except Exception:
            pass

    def cmd(self, command, wait=1.0, timeout=60):
        self.sock.sendall((command + '\n').encode())
        time.sleep(wait)
        data = b''
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                d = self.sock.recv(65536)
                if not d:
                    break
                data += d
                if data.rstrip().endswith(b'/ #'):
                    break
            except socket.timeout:
                if data:
                    break
        return data.decode('latin-1', 'replace')

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass


def clean(b):
    """Strip telnet IAC negotiation bytes."""
    out = bytearray()
    i = 0
    while i < len(b):
        if b[i] == 0xFF and i + 1 < len(b):
            i += 3 if b[i + 1] in (0xFA, 0xFB, 0xFC, 0xFD, 0xFE) else 2
            continue
        out.append(b[i])
        i += 1
    return bytes(out)


def download(r, remote, max_bytes=0, chunk=CHUNK):
    size_txt = r.cmd('wc -c < %s' % remote, timeout=10)
    nums = re.findall(r'\d+', size_txt.split('\n', 1)[-1])
    total = int(nums[0]) if nums else 0
    if max_bytes:
        total = min(total, max_bytes)
    if not total:
        return b''
    print('[*] Downloading %s (%d bytes) in %d KiB chunks...' % (remote, total, chunk // 1024))
    out = bytearray()
    while len(out) < total:
        piece = min(chunk, total - len(out))
        skip = len(out) // chunk
        txt = r.cmd(
            "dd if=%s bs=%d skip=%d count=1 2>/dev/null | hexdump -v -e '1/1 \"%%02x\"'"
            % (remote, chunk, skip),
            wait=0.3,
            timeout=120,
        )
        line = txt.rsplit('\n', 1)[-1]
        hexs = re.sub(r'[^0-9a-f]', '', line)
        if len(hexs) % 2:
            hexs = hexs[:-1]
        blob = bytes.fromhex(hexs)[:piece]
        if not blob:
            break
        out += blob
        sys.stdout.write('\r    %d / %d bytes' % (len(out), total))
        sys.stdout.flush()
    print()
    return bytes(out)


def localname(tag):
    return tag


def walk(node, prefix='', out=None):
    """Flatten the Tr-069 style XML into full paths."""
    if out is None:
        out = {}
    for child in list(node):
        name = child.tag
        if name.endswith('.'):
            name = name[:-1]
        path = (prefix + '.' + name) if prefix else name
        value = child.get('v')
        kn = child.get('kn')
        ealgo = child.get('ealgo')
        if value is None:
            value = ''
        if len(child) == 0:
            if value == '' and not ealgo:
                continue
            out[path] = {
                'value': value,
                'encrypted': bool(ealgo),
                'key': kn or '',
            }
        else:
            walk(child, path, out)
    return out


def main():
    p = argparse.ArgumentParser(description='Nokia G-2426G-A config DB dumper')
    p.add_argument('--ip', default='192.168.1.1')
    p.add_argument('--port', type=int, default=2324,
                   help='2324 = permanent root shell, 2360 = temporary exploit shell')
    p.add_argument('--dbfile', type=int, default=3, choices=[1, 2, 3, 4],
                   help='1=confignew.cfg 2=confignew.cfg.bak 3=config_encryption.cfg 4=config_encryption.cfg.bak')
    p.add_argument('--out', help='write the decoded XML to this local file')
    p.add_argument('--grep', help='only show paths matching this regex (case-insensitive)')
    p.add_argument('--show-secrets', action='store_true',
                   help='print node-encrypted ciphertext instead of <ENCRYPTED>')
    p.add_argument('--json', dest='json_out', help='write flattened key/values as JSON')
    p.add_argument('--max-bytes', type=int, default=0, help='debug: only fetch the first N bytes')
    args = p.parse_args()

    r = Router(args.ip, args.port)
    try:
        print('[*] Asking cfgcli to decode dbfile %d on the router...' % args.dbfile)
        out = r.cmd('cfgcli dump dbfile %d' % args.dbfile, wait=1.5, timeout=120)
        if 'uncompress db file' not in out:
            print('[-] cfgcli did not produce a dump. Raw answer:')
            print(out.strip())
            return 1

        size_txt = r.cmd('ls -l /tmp/dump.xml', timeout=10)
        print('[*] Router-side decoded file: %s' % size_txt.strip().split('\n')[-2:][0].strip())

        blob = download(r, '/tmp/dump.xml', args.max_bytes)
        if not blob:
            print('[-] Download failed.')
            return 1
        r.cmd('rm -f /tmp/dump.xml', timeout=5)
    finally:
        r.close()

    if args.out:
        open(args.out, 'wb').write(blob)
        print('[+] Decoded XML written to %s (%d bytes)' % (args.out, len(blob)))

    try:
        root = ET.fromstring(blob)
    except ET.ParseError as e:
        print('[-] XML parse error: %s' % e)
        return 1

    flat = walk(root)
    print('[+] %d populated nodes found.' % len(flat))

    rx = re.compile(args.grep, re.I) if args.grep else None
    shown = 0
    for path in sorted(flat):
        if rx and not rx.search(path):
            continue
        item = flat[path]
        if item['encrypted'] and not args.show_secrets:
            val = '<ENCRYPTED kn=%s>' % item['key']
        else:
            val = item['value']
        if len(val) > 110:
            val = val[:107] + '...'
        print('%-78s %s' % (path, val))
        shown += 1
        if rx and shown >= 400:
            print('... (use a narrower --grep)')
            break

    if args.json_out:
        with open(args.json_out, 'w', encoding='utf-8') as f:
            json.dump(flat, f, indent=2)
        print('[+] Flattened JSON written to %s' % args.json_out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
