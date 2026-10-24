# -*- coding: utf-8 -*-
"""Nokia G-2426G-A MTD Flashing Script.

Automates the safe firmware deployment process over local Telnet:
1. Uploads and executes custom MTD hardware eraser on target partition.
2. Downloads repacked firmware image to device RAM (/tmp).
3. Writes image to target partition block device (/dev/mtdblockX).
4. Verifies written bytes using MD5 checksum against the local image.
5. Switches active boot slot via Imagetool switch.
6. Triggers safe system reboot into new firmware.
"""

import argparse
import hashlib
import os
import socket
import sys
import time


def sh(sock, cmd, wait=90):
    print(f">>> {cmd}")
    sock.sendall((cmd + "\n").encode())
    time.sleep(0.8)
    out = b""
    t0 = time.time()
    while time.time() - t0 < wait:
        try:
            sock.settimeout(2.0)
            d = sock.recv(4096)
            if not d:
                break
            out += d
            if b"/ # " in out:
                break
        except Exception:
            pass
    res = out.decode("latin-1", errors="replace")
    print(res)
    return res


def main():
    p = argparse.ArgumentParser(
        description="Nokia G-2426G-A Safe Firmware Flasher"
    )
    p.add_argument(
        "--ip", default="192.168.1.1", help="Router IP address (default: 192.168.1.1)"
    )
    p.add_argument(
        "--port",
        type=int,
        default=2324,
        help="Telnet root shell port (default: 2324)",
    )
    p.add_argument(
        "--image", required=True, help="Path to local repacked firmware .bin"
    )
    p.add_argument(
        "--http-server",
        required=True,
        help="Local PC IP and port for HTTP server (e.g. 192.168.1.8:8000)",
    )
    p.add_argument(
        "--target-slot",
        choices=["image0", "image1"],
        required=True,
        help="Target inactive image slot to flash (image0 = mtd2, image1 = mtd4)",
    )
    args = p.parse_args()

    if not os.path.isfile(args.image):
        print(f"[-] Image file not found: {args.image}")
        sys.exit(1)

    img_data = open(args.image, "rb").read()
    img_len = len(img_data)
    img_md5 = hashlib.md5(img_data).hexdigest()
    img_filename = os.path.basename(args.image)

    mtd_num = "2" if args.target_slot == "image0" else "4"
    print(
        f"[*] Target: {args.target_slot} (/dev/mtd{mtd_num}, /dev/mtdblock{mtd_num})"
    )
    print(f"[*] Image Size: {img_len} bytes, Expected MD5: {img_md5}")

    sock = socket.create_connection((args.ip, args.port), timeout=15)
    time.sleep(0.5)
    sock.recv(1024)

    # 1. Hardware Erase
    print(f"\n--- 1. Erasing /dev/mtd{mtd_num} ---")
    sh(
        sock,
        f"wget -q -O /tmp/erase_mtd http://{args.http_server}/erase_mtd{mtd_num} && chmod 755 /tmp/erase_mtd && /tmp/erase_mtd",
    )
    sh(sock, f"dd if=/dev/mtd{mtd_num} bs=32 count=1 2>/dev/null | hexdump")

    # 2. Download Image
    print("\n--- 2. Downloading Firmware to Device RAM ---")
    sh(
        sock,
        f"rm -f /tmp/img.bin; wget -q -O /tmp/img.bin http://{args.http_server}/{img_filename}; md5sum /tmp/img.bin",
        wait=180,
    )

    # 3. Write to block device
    print(f"\n--- 3. Writing to /dev/mtdblock{mtd_num} ---")
    sh(sock, f"dd if=/tmp/img.bin of=/dev/mtdblock{mtd_num} bs=65536; sync; echo WRITE_DONE", wait=180)

    # 4. Verification
    print("\n--- 4. Verifying Written Flash Blocks ---")
    blocks = (img_len + 65535) // 65536
    res = sh(
        sock,
        f"dd if=/dev/mtdblock{mtd_num} bs=65536 count={blocks} 2>/dev/null | head -c {img_len} | md5sum",
        wait=180,
    )
    if img_md5 not in res:
        print("[!] CRITICAL ERROR: Written MD5 checksum mismatch! DO NOT SWITCH!")
        sys.exit(1)
    print("[+] Checksum verified successfully!")

    # 5. Switch Slot
    print("\n--- 5. Switching Boot Slot ---")
    sh(sock, "/usr/exe/Imagetool show")
    sh(sock, "/usr/exe/Imagetool switch")
    sh(sock, "/usr/exe/Imagetool show")

    # 6. Reboot
    print("\n--- 6. Rebooting Device ---")
    sh(sock, "reboot")
    sock.close()
    print("[+] Flash completed. Device is restarting into new firmware.")


if __name__ == "__main__":
    main()
