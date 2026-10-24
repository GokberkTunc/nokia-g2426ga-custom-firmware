#!/bin/sh
# S99rr.sh v2 — kalici ve cokmesiz root hook
# rcS.d dongusunde source edilir; exit KULLANMA.

# 1) wrapper (sifresiz root shell icin)
if [ ! -f /configs/w.sh ]; then
    echo '#!/bin/sh' > /configs/w.sh
    echo 'exec /bin/sh' >> /configs/w.sh
    chmod 755 /configs/w.sh
fi

# 2) telnet bayraklari
touch /tmp/no_telnet_session_idle_time
touch /configs/factory_telnet_enable

# 3) firewall: LAN'dan 2324'e izin ver
iptables -C INPUT_LAN_ACCESS -p tcp -i br+ --dport 2324 -j ACCEPT 2>/dev/null || iptables -I INPUT_LAN_ACCESS 1 -p tcp -i br+ --dport 2324 -j ACCEPT 2>/dev/null

# 4) rr_telnetd supervisor dongusu (cfgmgr'nin killall utelnetd'sinden etkilenmez)
(
    while true; do
        if ! netstat -ltn | grep -q ':2324 '; then
            /bin/rr_telnetd -p 2324 -l /configs/w.sh -d 2>/dev/null
        fi
        sleep 3
    done
) &

# 5) boot saglikli: aktif slotu dinamik belirle ve commit et (150 sn sonra)
(
    sleep 150
    /usr/exe/Imagetool update >/dev/null 2>&1
    if cat /proc/mtd | grep -q 'mtd2.*image0'; then
        act=1
    else
        act=0
    fi
    /usr/exe/Imagetool commit $act >/dev/null 2>&1
) &

sync
