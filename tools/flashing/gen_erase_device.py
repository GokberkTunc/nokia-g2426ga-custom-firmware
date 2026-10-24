import struct, sys
from keystone import Ks, KS_ARCH_MIPS, KS_MODE_MIPS32, KS_MODE_LITTLE_ENDIAN

# sys.argv[1]: device path (e.g. "/dev/mtd2")
# sys.argv[2]: output binary (e.g. "erase_mtd2")
dev_path = sys.argv[1].encode('ascii') + b'\x00'
out_file = sys.argv[2]

src = r"""
    lui  $a0, PATH_HI
    ori  $a0, $a0, PATH_LO
    li   $a1, 0x12
    move $a2, $zero
    li   $v0, 4005
    syscall
    bltz $v0, FAIL
    nop
    move $s0, $v0
    move $s1, $zero          # offset = 0
LOOPBLK:
    lui  $t0, TOTAL_HI
    ori  $t0, $t0, TOTAL_LO
    sltu $t1, $s1, $t0
    beqz $t1, DONE
    nop
    # MEMUNLOCK (0x80084D7E)
    sw   $s1, 0($sp)
    lui  $t0, ERASE_HI
    ori  $t0, $t0, ERASE_LO
    sw   $t0, 4($sp)
    move $a0, $s0
    lui  $a1, 0x8008
    ori  $a1, $a1, 0x4d7e
    move $a2, $sp
    li   $v0, 4054
    syscall
    # MEMERASE (0x80084D02)
    move $a0, $s0
    lui  $a1, 0x8008
    ori  $a1, $a1, 0x4d02
    move $a2, $sp
    li   $v0, 4054
    syscall
    # advance offset by 0x40000
    lui  $t0, ERASE_HI
    ori  $t0, $t0, ERASE_LO
    addu $s1, $s1, $t0
    b LOOPBLK
    nop
DONE:
    li   $a0, 1
    lui  $a1, MSG_HI
    ori  $a1, $a1, MSG_LO
    li   $a2, 3
    li   $v0, 4004
    syscall
    move $a0, $zero
    li   $v0, 4001
    syscall
FAIL:
    li   $a0, 1
    li   $v0, 4001
    syscall
"""
base = 0x00400000
EHDR, PHDR = 52, 32
CODE_OFF = EHDR + PHDR
data = dev_path + b"OK!\x00"
path_rel = 0
msg_rel = len(dev_path)

ks = Ks(KS_ARCH_MIPS, KS_MODE_MIPS32 | KS_MODE_LITTLE_ENDIAN)
s0 = src.replace('PATH_HI','0').replace('PATH_LO','0').replace('MSG_HI','0').replace('MSG_LO','0').replace('ERASE_HI','0').replace('ERASE_LO','0').replace('TOTAL_HI','0').replace('TOTAL_LO','0')
enc0, _ = ks.asm(s0)
enc0 = bytes(enc0)
data_off = CODE_OFF + len(enc0)
pathaddr = base + data_off + path_rel
msgaddr = base + data_off + msg_rel

s = src.replace('PATH_HI', str((pathaddr>>16)&0xffff)).replace('PATH_LO', str(pathaddr&0xffff))
s = s.replace('MSG_HI', str((msgaddr>>16)&0xffff)).replace('MSG_LO', str(msgaddr&0xffff))
s = s.replace('ERASE_HI', str((0x40000>>16)&0xffff)).replace('ERASE_LO', str(0x40000&0xffff))
s = s.replace('TOTAL_HI', str((0x2980000>>16)&0xffff)).replace('TOTAL_LO', str(0x2980000&0xffff))
enc, _ = ks.asm(s)
enc = bytes(enc)
assert len(enc) == len(enc0)

image = enc + data
ehdr = struct.pack('<16sHHIIIIIHHHHHH', b'\x7fELF' + bytes([1,1,1,0]) + bytes(8), 2, 8, 1, base + CODE_OFF, EHDR, 0, 0, EHDR, PHDR, 1, 0, 0, 0)
phdr = struct.pack('<IIIIIIII', 1, 0, base, base, len(image), len(image), 7, 0x1000)
open(out_file, 'wb').write(ehdr + phdr + image)
print('yazildi:', out_file, len(ehdr + phdr + image))
