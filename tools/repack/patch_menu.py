import struct
src = r'C:\Users\gokbe\Desktop\a\router_recon\01_araclar\msys_portable\usr\bin\rootfs_sq\webs\menu.cgi'
dst = r'C:\Users\gokbe\Desktop\a\router_recon\01_araclar\menu_admin.cgi'
data = bytearray(open(src, 'rb').read())
off = 0xfbc
patch = bytes.fromhex('4000023ce44742240800e00300000000')
data[off:off+len(patch)] = patch
open(dst, 'wb').write(data)
print('patched', dst, len(data))
