# -*- coding: utf-8 -*-
"""Nokia G-2426G-A Interactive Terminal & Command Runner.

Provides an instant, cross-platform terminal to the router over Telnet
without needing PuTTY or enabling Windows Telnet Client.

Usage:
    python tools/terminal.py                 # Interactive shell on port 2324
    python tools/terminal.py --port 2360     # Connect to temporary exploit port
    python tools/terminal.py --cmd "uptime"  # Run single command and exit
"""

import argparse
import socket
import sys
import time


def clean_telnet(b):
    """Filters out Telnet negotiation IAC sequences."""
    out = bytearray()
    i = 0
    n = len(b)
    while i < n:
        if b[i] == 0xFF:  # IAC
            if i + 1 < n and b[i + 1] in (0xFA, 0xFB, 0xFC, 0xFD, 0xFE):
                i += 3
                continue
            i += 2
            continue
        out.append(b[i])
        i += 1
    return bytes(out).decode("latin-1", errors="replace")


def run_single(ip, port, cmd):
    try:
        sock = socket.create_connection((ip, port), timeout=8)
    except Exception as e:
        print(f"[-] Could not connect to {ip}:{port} ({e})")
        sys.exit(1)

    sock.settimeout(1.0)
    time.sleep(0.3)
    try:
        sock.recv(4096)
    except Exception:
        pass

    sock.sendall((cmd + "\n").encode())
    data = b""
    t0 = time.time()
    while time.time() - t0 < 15:
        try:
            d = sock.recv(4096)
            if not d:
                break
            data += d
            if b"/ # " in data or b"# " in data:
                break
        except socket.timeout:
            pass
    sock.close()
    out = clean_telnet(data)
    print(out.strip())


def interactive(ip, port):
    print(f"[*] Connecting to {ip}:{port}...")
    try:
        sock = socket.create_connection((ip, port), timeout=10)
    except Exception as e:
        print(f"[-] Connection failed ({e}).")
        print("    If using Windows, you can also use PuTTY on port 2324.")
        sys.exit(1)

    sock.settimeout(0.5)
    time.sleep(0.4)
    init_data = b""
    try:
        while True:
            d = sock.recv(2048)
            if not d:
                break
            init_data += d
    except Exception:
        pass

    banner = clean_telnet(init_data).strip()
    if banner:
        print(banner)

    print("\n" + "=" * 55)
    print(" Nokia G-2426G-A Root Terminal (Type 'exit' to quit)")
    print("=" * 55 + "\n")

    try:
        while True:
            try:
                cmd = input("router # ")
            except EOFError:
                break
            cmd_s = cmd.strip()
            if not cmd_s:
                continue
            if cmd_s in ("exit", "quit"):
                break

            sock.sendall((cmd_s + "\n").encode())
            time.sleep(0.2)
            out_bytes = b""
            t0 = time.time()
            while time.time() - t0 < 30:
                try:
                    sock.settimeout(1.0)
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    out_bytes += chunk
                    if b"/ # " in out_bytes or b"# " in out_bytes:
                        break
                except socket.timeout:
                    if out_bytes:
                        break

            rendered = clean_telnet(out_bytes)
            # Remove prompt echo if duplicated
            lines = rendered.splitlines()
            if lines and cmd_s in lines[0]:
                lines = lines[1:]
            if lines and lines[-1].strip().endswith("#"):
                lines = lines[:-1]
            out_final = "\n".join(lines).strip()
            if out_final:
                print(out_final)
    except KeyboardInterrupt:
        print("\n[*] Disconnected.")
    finally:
        sock.close()


def main():
    p = argparse.ArgumentParser(
        description="Nokia G-2426G-A Telnet Terminal & Runner"
    )
    p.add_argument(
        "--ip", default="192.168.1.1", help="Router IP (default: 192.168.1.1)"
    )
    p.add_argument(
        "--port",
        type=int,
        default=2324,
        help="Telnet port (default: 2324 or 2360 for exploit)",
    )
    p.add_argument(
        "--cmd",
        help="Execute a single command on the router and exit",
    )
    args = p.parse_args()

    if args.cmd:
        run_single(args.ip, args.port, args.cmd)
    else:
        interactive(args.ip, args.port)


if __name__ == "__main__":
    main()
