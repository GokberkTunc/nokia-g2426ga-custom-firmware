# -*- coding: utf-8 -*-
"""Nokia G-2426G-A Safe Firmware Flasher.

Automates the complete firmware flashing process:
1. Connects to the router's Telnet shell.
2. Automatically detects the currently active slot (image0 or image1) and selects
   the INACTIVE safe slot as the flash target.
3. Spawns an internal HTTP server to stream the firmware image and MTD erase tools.
4. Executes hardware MTD erase on the target partition using MIPS ioctl (0x80084D02 / 0x80084D7E).
5. Writes the HDR2 firmware image to the MTD block device (/dev/mtdblockX).
6. Verifies flash integrity with MD5 checksum.
7. Switches boot slot (Imagetool switch) and triggers a clean system reboot.
"""

import argparse
import hashlib
import http.server
import os
import re
import socket
import socketserver
import sys
import threading
import time


def get_local_ip(target_ip):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect((target_ip, 80))
        return s.getsockname()[0]
    except Exception:
        return "192.168.1.5"
    finally:
        s.close()


class CustomFileHandler(http.server.BaseHTTPRequestHandler):
    files_map = {}  # URL path -> Local file path

    def do_GET(self):
        url_path = self.path.split("?")[0].lstrip("/")
        if url_path in self.files_map and os.path.isfile(self.files_map[url_path]):
            filepath = self.files_map[url_path]
            filesize = os.path.getsize(filepath)
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(filesize))
            self.end_headers()
            with open(filepath, "rb") as f:
                while chunk := f.read(65536):
                    self.wfile.write(chunk)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress noisy HTTP logs


def start_http_server(files_map, host_ip):
    class ThreadingServer(
        socketserver.ThreadingMixIn, http.server.HTTPServer
    ):
        allow_reuse_address = True

    CustomFileHandler.files_map = files_map
    server = ThreadingServer((host_ip, 0), CustomFileHandler)
    port = server.server_port
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, port


def sh(sock, cmd, wait=90, echo=True):
    if echo:
        print(f">>> {cmd}")
    sock.sendall((cmd + "\n").encode())
    time.sleep(0.5)
    out = b""
    t0 = time.time()
    while time.time() - t0 < wait:
        try:
            sock.settimeout(2.0)
            d = sock.recv(4096)
            if not d:
                break
            out += d
            if b"/ # " in out or b"# " in out:
                break
        except Exception:
            pass
    res = out.decode("latin-1", errors="replace")
    if echo:
        print(res.strip())
    return res


def main():
    p = argparse.ArgumentParser(
        description="Nokia G-2426G-A Safe Automated Firmware Flasher"
    )
    p.add_argument(
        "--image", required=True, help="Path to local HDR2 firmware image (.bin)"
    )
    p.add_argument(
        "--ip", default="192.168.1.1", help="Router IP address (default: 192.168.1.1)"
    )
    p.add_argument(
        "--port",
        type=int,
        default=2324,
        help="Telnet port (default: 2324 for custom firmware, or 2360 for initial exploit)",
    )
    p.add_argument(
        "--target-slot",
        choices=["image0", "image1"],
        help="Target slot to flash (if omitted, automatically selects the inactive slot)",
    )
    p.add_argument(
        "--http-server",
        help="Optional external HTTP server (e.g. 192.168.1.8:8000). If omitted, an internal server is used automatically.",
    )
    args = p.parse_args()

    image_path = os.path.abspath(args.image)
    if not os.path.isfile(image_path):
        print(f"[-] Firmware image not found: {image_path}")
        sys.exit(1)

    img_data = open(image_path, "rb").read()
    img_len = len(img_data)
    img_md5 = hashlib.md5(img_data).hexdigest()
    print(f"[*] Loaded Firmware Image: {os.path.basename(image_path)}")
    print(f"    Size: {img_len:,} bytes | MD5: {img_md5}")

    print(f"\n[*] Connecting to router Telnet at {args.ip}:{args.port}...")
    try:
        sock = socket.create_connection((args.ip, args.port), timeout=15)
        time.sleep(0.5)
        sock.recv(1024)
    except Exception as e:
        print(f"[-] Could not connect to Telnet at {args.ip}:{args.port} ({e}).")
        print("    If this is your first time, run the initial exploit first:")
        print("    python tools/initial_access/get_initial_shell.py")
        sys.exit(1)

    print("[+] Telnet connected successfully!")

    # 1. Determine Target Slot
    target_slot = args.target_slot
    if not target_slot:
        print("[*] Detecting active boot slot from router...")
        info = sh(sock, "/usr/exe/Imagetool show", wait=5, echo=False)
        m = re.search(r"active\s*=\s*\[([01])\]", info)
        if m:
            active_slot = int(m.group(1))
            inactive_slot = 1 if active_slot == 0 else 0
            target_slot = f"image{inactive_slot}"
            print(
                f"[+] Active slot is 'image{active_slot}'. Selected safe target: '{target_slot}'"
            )
        else:
            print("[-] Could not determine active slot automatically.")
            print("    Please specify --target-slot image0 or --target-slot image1")
            sys.exit(1)

    mtd_num = "2" if target_slot == "image0" else "4"
    erase_bin_name = f"erase_mtd{mtd_num}"
    erase_bin_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), erase_bin_name
    )

    if not os.path.isfile(erase_bin_path):
        print(f"[-] Erase tool not found: {erase_bin_path}")
        sys.exit(1)

    # 2. HTTP Server setup
    http_srv = None
    if args.http_server:
        http_base = f"http://{args.http_server}"
    else:
        local_ip = get_local_ip(args.ip)
        files_map = {
            erase_bin_name: erase_bin_path,
            "firmware.bin": image_path,
        }
        http_srv, srv_port = start_http_server(files_map, local_ip)
        http_base = f"http://{local_ip}:{srv_port}"
        print(f"[+] Started internal HTTP transfer server at {http_base}")

    try:
        # 3. Hardware MTD Erase
        print(
            f"\n--- [1/4] Erasing Flash Partition /dev/mtd{mtd_num} ({target_slot}) ---"
        )
        erase_url = f"{http_base}/{erase_bin_name}"
        sh(
            sock,
            f"wget -q -O /tmp/erase_mtd {erase_url} && chmod 755 /tmp/erase_mtd && /tmp/erase_mtd",
        )

        # 4. Download Image to RAM
        print(f"\n--- [2/4] Downloading Firmware to Router RAM (/tmp) ---")
        firmware_url = (
            f"{http_base}/firmware.bin"
            if not args.http_server
            else f"{http_base}/{os.path.basename(image_path)}"
        )
        sh(
            sock,
            f"rm -f /tmp/img.bin; wget -q -O /tmp/img.bin {firmware_url}; md5sum /tmp/img.bin",
            wait=180,
        )

        # 5. Write to Block Device
        print(
            f"\n--- [3/4] Writing to NAND Block Device /dev/mtdblock{mtd_num} ---"
        )
        sh(
            sock,
            f"dd if=/tmp/img.bin of=/dev/mtdblock{mtd_num} bs=65536; sync",
            wait=180,
        )

        # 6. Checksum Verification
        print(f"\n--- [4/4] Verifying Flash Integrity ---")
        blocks = (img_len + 65535) // 65536
        res = sh(
            sock,
            f"dd if=/dev/mtdblock{mtd_num} bs=65536 count={blocks} 2>/dev/null | head -c {img_len} | md5sum",
            wait=180,
        )
        if img_md5 not in res:
            print(
                "\n[!] CRITICAL ERROR: Written MD5 does not match expected image!"
            )
            print("    DO NOT REBOOT THE ROUTER. Re-try writing.")
            sys.exit(1)

        print("[+] Checksum verified successfully! Written blocks are 100% authentic.")

        # 7. Switch Active Slot & Reboot
        print("\n[*] Switching boot slot to newly flashed image...")
        sh(sock, "/usr/exe/Imagetool show", echo=False)
        sh(sock, "/usr/exe/Imagetool switch")
        sh(sock, "/usr/exe/Imagetool show")

        print("\n[*] Triggering system reboot into new custom firmware...")
        sh(sock, "reboot")
        sock.close()
        print("\n" + "=" * 65)
        print("🎉 TEBRİKLER! Flaşlama başarıyla tamamlandı.")
        print(
            "   Modem yeniden başlatılıyor. Yaklaşık 60 saniye içinde açılacaktır."
        )
        print(
            "   Açıldığında şifresiz root için: telnet 192.168.1.1 2324"
        )
        print("=" * 65 + "\n")

    finally:
        if http_srv:
            http_srv.shutdown()


if __name__ == "__main__":
    main()
