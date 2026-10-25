# Nokia G-2426G-A — Derinlemesine Teknik İnceleme ve Mimari Kılavuzu

Bu belge, **Nokia G-2426G-A** (MediaTek EcoNet MT7528/EN7528 MIPS32 mimarisi) GPON ONT / Router cihazının donanım, önyükleyici, çekirdek, MTD depolama, konfigürasyon veri modeli ve web arayüzü alt sistemlerinin teknik incelemesini içerir.

---

## 1. Donanım ve Sistem Mimarisi

- **Yonga Seti (SoC):** MediaTek / EcoNet MT7528 (EN7528 ailesi)
- **İşlemci (CPU):** MIPS 1004Kc (32-bit Little-Endian, 4 Sanal İş Parçacığı / Çift Çekirdek)
- **Çekirdek (Kernel):** Linux 3.18.21 SMP
- **Önyükleyici (Bootloader):** U-Boot 2016 (MediaTek tclinux / tcboot dalı)
- **Bellek (RAM):** 512 MB DDR3 (~417.928 KB sistem tarafından erişilebilir)
- **Depolama (Flash):** 256 MB NAND Flash (Çift imajlı A/B slot mimarisi)
- **Optik Alıcı (GPON):** Entegre MediaTek BOSA alıcı-verici (`bosa_m02180.ko`, `xpon.ko`, `DSPCore.ko`, `omciMgr`)
- **Kablosuz Ağ (Wi-Fi):** MediaTek MT7915 / MT7592 (Wi-Fi 6 802.11ax 5 GHz + 802.11b/g/n 2.4 GHz, `mt_whnat` donanım hızlandırıcılı)

---

## 2. MTD Flaş Bölüm Haritası (Flash Partition Layout)

Nokia G-2426G-A, güncelleme sırasında elektrik kesintisi gibi durumlara karşı çift yuvalı (**Dual-Bank A/B**) yedekli bölümleme mimarisi kullanır:

| MTD Aygıtı | Boyut | Silme Boyutu | Bölüm Adı | İşlevi / İçeriği |
|---|---|---|---|---|
| `/dev/mtd0` | 256 KB (`0x00040000`) | 256 KB | `bootloader` | U-Boot önyükleyici |
| `/dev/mtd1` | 256 KB (`0x00040000`) | 256 KB | `romfile` | Fabrika başlangıç konfigürasyon şablonu |
| `/dev/mtd2` | 41.5 MB (`0x02980000`) | 256 KB | `image0` | **Slot 0 Firmware:** Header + Kernel + RootFS + Extra |
| `/dev/mtd3` | 41.5 MB (`0x02980000`) | 256 KB | `linux` | Aktif imajın çekirdek ve dosya sistemi alanı |
| `/dev/mtd4` | 37.3 MB (`0x02563e6d`) | 256 KB | `rootfs` / `image1` | **Slot 1 Firmware:** İkincil imaj yuvası |
| `/dev/mtd5` | 8 MB (`0x00800000`) | 256 KB | `config` | Kalıcı kullanıcı ayarları (UBIFS: `/configs`) |
| `/dev/mtd6` | 12 MB (`0x00c00000`) | 256 KB | `log` | Hata günlükleri ve çekirdek dökümleri (UBIFS: `/logs`) |
| `/dev/mtd7` | 6 MB (`0x00600000`) | 256 KB | `extfs` | İlave sistem eklentileri (UBIFS: `/flash`) |
| `/dev/mtd8` | 256 KB (`0x00040000`) | 256 KB | `bosa` | Optik lazer kalibrasyon parametreleri |
| `/dev/mtd9` | 256 KB (`0x00040000`) | 256 KB | `flag` | Yuva yönetim bayrakları (`commit`, `next_active`, `boot_fail`) |
| `/dev/mtd10` | 256 KB (`0x00040000`) | 256 KB | `flagback` | Yuva bayraklarının ikincil kopyası |
| `/dev/mtd11` | 256 KB (`0x00040000`) | 256 KB | `ri` | Üretici ve operatör kimliği (`OperatorID`, seri no, MAC) |
| `/dev/mtd12` | 256 KB (`0x00040000`) | 256 KB | `riback` | `ri` bölümünün ikincil yedeği |
| `/dev/mtd13` | ~337 MB (`0x15140000`) | 256 KB | `data` | Kullanıcı veri alanı / önbellek |

---

## 3. HDR2 Firmware Paket Mimarisi ve İmza Bypass Analizi

### 3.1. Paket Dosya Anatomisi
Firmware imaj dosyası Nokia'ya tescilli `HDR2` başlığıyla başlar:

```text
Ofset      Uzunluk    Alan Adı        Açıklama
-----------------------------------------------------------------------------------------------------
0x000000   4 B        Magic           "HDR2" (0x32524448 Little-Endian)
0x000004   4 B        hdrlen          0x118 (280 bayt)
0x000008   4 B        totalsz         Header + Kernel + RootFS + Extra toplam boyutu
0x00000C   4 B        crc32           JAMCRC (zlib.crc32 ^ 0xFFFFFFFF)
0x000010   16 B       version         Sürüm dizesi (örn. "3FE49226IJKI11")
0x000050   4 B        kernel_len      Çekirdek (LZMA) sıkıştırılmış uzunluğu (örn. 0x41c07b)
0x000054   4 B        rootfs_len      Kök dosya sistemi (SquashFS) uzunluğu (örn. 0x18ac000)
0x00007C   4 B        kernel_load     Çekirdek RAM yüklenme adresi (0x80002000)
0x00009C   4 B        extra_len       Extra bölgesi uzunluğu (U-Boot bootram, 0x1436d)
-----------------------------------------------------------------------------------------------------
0x000118   klen       KERNEL          MIPS Linux Çekirdeği (LZMA sıkıştırmalı)
0x118+klen rlen       ROOTFS          Squashfs v4.0 (LZMA, 128 KB blok boyutu)
Sonrası    extra_len  EXTRA           U-Boot Bootram (LZMA)
Paket Sonu 1.720 B    TRAILER         PKCS#7 İmzası (Sadece dağıtım paketinde bulunur, flaşa YAZILMAZ)
```

### 3.2. Sağlama (Checksum) Algoritması
Sağlama algoritması `libupgradeimpl.so` içerisindeki `getCrc32(buf, len, crc)` fonksiyonu deasamble edilerek çözülmüştür:
```c
while (len--) crc = (crc >> 8) ^ table[(crc ^ *buf++) & 0xff];
return crc;
```
Bu algoritma **CRC-32 / JAMCRC** (init `0xFFFFFFFF`, yansımalı polinom `0xEDB88320`, xorout `0`) standardıdır. Python karşılığı:
$$\text{JAMCRC} = \text{zlib.crc32}(\text{body}) \oplus \text{0xFFFFFFFF}$$

### 3.3. U-Boot İmza Denetimi Bypassı
Resmî güncelleme mekanizmaları (`libupgrade.so`, web `upgrade.cgi`, OMCI uzaktan güncelleme), `/usr/etc/buildinfo` içindeki `SIGN=y` bayrağı nedeniyle PKCS#7 dijital imzasını şart koşar. Üreticinin özel anahtarı taklit edilemeyeceğinden modifiye imaj resmî yoldan geçemez.

Ancak önyükleyici (U-Boot) incelendiğinde:
- Normal açılış rutininde çekirdek üzerinde hiçbir RSA veya PKCS#7 imza doğrulaması **yapmadığı**,
- Yalnızca `HDR2` başlığındaki magic numarası ve **JAMCRC** değerini kontrol ettiği kanıtlanmıştır.
- **Sonuç:** MTD blok katmanına doğrudan yazılan ve JAMCRC'si doğru hesaplanmış modifiye imajlar, U-Boot tarafından sorunsuz önyüklenir.

---

## 4. Donanımsal MTD Flaşlama ve Sürücü ioctl Keşfi

### 4.1. Neden Standart `dd` ve `flash_eraseall` Başarısız Oldu?
1. **Mimari Uyumsuzluğu:** Vendor tarafından `/opt/mtdtools/` altına bırakılan `flash_eraseall` ikilisi x86 ELF formatındaydı; MIPS Linux çekirdeğinde `syntax error` vererek çalışmadı.
2. **Karakter Sürücüsü Hizalaması:** Karakter aygıtı `/dev/mtdX` üzerinden yapılan `dd` yazımları `EINVAL (Invalid argument)` döndürdü. MediaTek NAND sürücüsü sayfa hizalamasız ve blok silme kilidi açılmamış tampon yazımlarını doğrudan engellemektedir.
3. **MIPS ioctl Yön Kodlaması:** MIPS mimarisinde ioctl numaraları standart x86'dan farklı bit alanlarıyla kodlanır:
   - Standart Linux `MEMERASE`: `0x40084D02` -> MIPS'te `ENOTTY` verdi.
   - MIPS Çekirdeğinde `MEMERASE`: **`0x80084D02`**
   - MIPS Çekirdeğinde `MEMUNLOCK`: **`0x80084D7E`**

### 4.2. Blok Aygıtı Katmanı
NAND blok aygıtı (`/dev/mtdblock2` ve `/dev/mtdblock4`), çekirdeğin blok önbellek katmanı (block buffer layer) ile entegredir. Hedef bölüm `0x80084D7E` (unlock) ve `0x80084D02` (erase) ile temizlendikten sonra `/dev/mtdblockX` üzerine yapılan `dd` yazımları donanımsal sayfa boyutlarına tam sadakatle yazılır.

---

## 5. Sistem Kararlılığı ve `cfgmgr` Çökme Mekanizması (RCA)

### 5.1. Sorunun Tespiti
İlk modifiye imaj denemelerinde cihazın her ~11 dakikada bir kendini yeniden başlattığı görüldü. Hata günlüğü:
```text
File Name   : src/diag_monitor.c
Line Number : 232
Error Info  : cfgmgr crashed, restart system.
```

### 5.2. Kök Neden
1. Web açıkları veya geçici betiklerle parametre enjeksiyonu yapıldığında (örneğin kullanıcı adı alanına `\n` ve kabuk komutları konulduğunda), bu kirli veri `cfgmgr`'ın veri modeline (`FtpUserName` vb.) kaydediliyordu.
2. `cfgmgr`, periyodik olarak veri tabanını flash'a (`/configs`) XML formatında yazmaya çalışırken kontrolsüz satır sonları nedeniyle XML sözdizim hatası alarak `SIGABRT (sig 6)` ile çöküyordu.
3. Bekçi köpeği (`diag_monitor`), sistemin ana yönetim sürecinin düştüğünü görünce cihazı reboot döngüsüne sokuyordu.
4. Ayrıca `cfgmgr` her açılışta `killall utelnetd` komutunu çalıştırarak varsayılan `utelnetd` süreçlerini sonlandırıyordu.

### 5.3. Supervisor Çözümü
- `utelnetd` ikilisi `/bin/rr_telnetd` adıyla bağımsız bir dosyaya kopyalandı. Böylece `killall utelnetd` komutu port 2324 servisine asla dokunamaz hale geldi.
- `/etc/rcS.d/S99rr.sh` başlangıç kancası içine her 3 saniyede bir çalışan supervisor döngüsü eklendi:
  ```sh
  (
      while true; do
          if ! netstat -ltn | grep -q ':2324 '; then
              /bin/rr_telnetd -p 2324 -l /configs/w.sh -d 2>/dev/null
          fi
          sleep 3
      done
  ) &
  ```
- Sistem hesapları (`passwd`, `shadow`) kurcalanmayarak `cfgmgr`'ın veri modeli temiz tutuldu; böylece sistem çökmesiz kararlılığa ulaştı.

---

## 6. Web Arayüzü Mimarisi ve RBAC Çözümü

### 6.1. Operatör Profili (`OperatorID`)
Cihaz kimlik bölümündeki `OperatorID: TRCL` (Turkcell Superonline) değeri `ritool set OperatorID ALCL` komutuyla Nokia'nın küresel fabrika standardı olan `ALCL` profiline geçirildi. Böylece:
- Sabit VLAN 100 kilidi kalktı (tüm VLAN'lar serbest bırakıldı).
- Köprü (Bridge) modu açıldı.
- Kullanıcı adı ve şifre kutuları düzenlenebilir hale geldi.
- DNS ezme (`DNSOverrideAllowed = true`) serbest kaldı.

### 6.2. Rol Tabanlı Yetkilendirme (RBAC) ve Menü Üretimi
- Web motoru (`libcgi.so`), çağrılan her CGI isteğini `/etc/configs/rbac/{AdminUser,NormalUser}/` altındaki `authorizedcgi` listesinde denetler. Listede olmayan sayfalar `"Bad request for invalid parameter in the coookie."` sahte çerez hatasıyla reddedilir.
- Tüm `Adminuser.json` ve `Normaluser.json` dosyalarına **2.702 adet CGI yetki girdisi** işlendi ve tüm `"visibility": -1` kısıtlamaları `1` yapıldı.
- `menu.cgi` ikilisindeki `0x400fbc` rol seçici fonksiyonu daima `ADMIN` döndürecek şekilde 16 baytlık makine koduyla yamalandı. Böylece 66 gelişmiş menü hedefi sol gezinme çubuğunda kalıcı olarak görünür kılındı.

---

## 7. Konfigürasyon Kasası: `config_encryption.cfg` Analizi

Cihazın tüm kalıcı ayarları `/dev/mtd5` (`UBIFS`, `/configs`) üzerindeki
`/configs/config_encryption.cfg` dosyasında tutulur. Bu dosya iki katmanlı korunur.

### 7.1. Katman 1 — Dosya Kapsayıcısı

Dosya 52 baytlık bir başlık ve ardından gelen tek bir gövdeden oluşur:

```text
Ofset   Boyut   İçerik
--------------------------------------------------------------------------
0x00    4 B     Ayırılan tampon kapasitesi (ör. 0x124124)
0x04    4 B     Gövde (ciphertext) uzunluğu
0x08    4 B     Düz metnin CRC32 sağlaması
0x0C    4 B     Açılmış (deflate sonrası) uzunluk, NUL dahil
0x10   36 B     KDF/şifre parametreleri (anahtar kaynağı türevi)
0x34    n B     Deflate sıkıştırılmış + şifrelenmiş XML gövdesi
```

Gözlemler (canlı cihazdan alınan 139.197 baytlık dosya üzerinde):

- Gövde entropisi **7.999 bit/bayt**, 256 farklı bayt değeri → gerçek şifreleme.
- 8 ve 16 baytlık bloklarda **hiç tekrar yok** → ECB değil (CBC/CFB/CTR benzeri).
- Gövde uzunluğu blok boyutunun katı değil → akış (stream) modu veya sıkıştırma sonrası
  hizalama yok.
- `cfgmgr` ikilisinde `des3_encrypt`, `CS_crypt`, `CS_cryptFile`, `CS_getCryptOutLen`
  sembolleri; `libsec_engine.so` içinde `EVP_CIPHER`, `PKCS5_PBKDF2_HMAC`, `EVP_sha256`,
  `AES_set_*_key`, `AES_cbc_encrypt` bağımlılıkları bulunur.

**Pratik sonuç:** Dosya kapsayıcısını çözmek için anahtar kırmaya gerek yoktur. `libcfg.so`
üzerinden `cfgcli`'ye "dump dbfile" isteği gönderildiğinde, çözme işlemini **cfgmgr kendi
belleğinde** yapar ve sonucu düz XML olarak verir:

```sh
cfgcli dump dbfile 3      # 3 = config_encryption.cfg, 4 = .bak, 1/2 = confignew.cfg(.bak)
# -> "the uncompress db file in /tmp/dump.xml"
```

Çıktı: ~999 KB, `<?xml version="1.0"?>` ile başlayan, `InternetGatewayDevice.` kökü altında
düğümleri `t=`, `rw=`, `ml=`, `dv=`, `v=` öznitelikleriyle taşıyan XML.

### 7.2. Katman 2 — Düğüm Seviyesinde Şifreleme

Düz XML'e ulaştıktan sonra bile hassas düğümler açık metin değildir:

```xml
<Password ml="64" rw="RW" t="string"
          v="AbCdEf0123456789+/ZzYyXx=="
          ealgo="sab" kn="key11" ckn="key3"></Password>
```

| Öznitelik | Anlamı |
|---|---|
| `ealgo="sab"` | Değerin "secure algorithm B" ile şifreli olduğunu belirtir |
| `kn="key11"` | Şifreleme anahtarının adı (sec-engine anahtar deposundan) |
| `ckn="key3"` | Bütünlük/checksum anahtarının adı |
| `v="<base64>"` | 24 baytlık blok → base64 (32 karakter) |

Bu nedenle `cfgcli -g ...Password` çıktısı `******`, web arayüzü ise
`!!!@@@###$$$^^$&&&***` benzeri bir "değiştirme" yer tutucusu döndürür.

### 7.3. Anahtar Kaynağı Zinciri

```text
/configs/se.conf  [keys]
    keysrc0 = <firmware sürüm dizesi>      (tüm cihazlarda ortak)
    keysrc1 = <cihaza özgü 8 haneli tohum> (cihaza bağlı)
    keysrc2 = <üretim/sürüm kodu>
        │
        ▼  (önyüklemede se_engine tarafından)
/tmp/secKeySrc.conf   +   sedbfile=/tmp/sedb.conf
        │
        ▼  libsec_engine.so
SE_deriveKey / SE_deriveKeyStr / CS_getSha256Key
    PBKDF2-HMAC-SHA256 + salt  →  AES/3DES anahtar materyali
        │
        ├─► CS_cryptFile / CS_cryptFileProdKey  → dosya kapsayıcısı
        └─► CS_crypt / CS_cryptString           → düğüm değerleri (key11)
```

**Sonuç:** Anahtar malzemesi cihaza bağlıdır (`keysrc1`). Bir cihazdan alınan
`config_encryption.cfg` dosyası **başka bir cihazda** kendi başına çözülemez; aynı cihaz
üzerinde ise `cfgcli` ve `ndk_wand` gibi bileşenler çözmeyi zaten yapabilir. Bu yüzden
yayımlanan araçlarda **anahtar malzemesi yoktur**; çözme işi her zaman cihazın kendisine
yaptırılır.

### 7.4. PPPoE Kimlik Bilgileri Nerede?

- **Kullanıcı adı:** Veri modelinde açık metin (`...WANPPPConnection.1.Username`), ayrıca
  `/etc/ppp/options_ppp<N>` içinde `user "..."` satırı olarak bulunur.
- **Şifre:** `kn="key11"` ile düğüm seviyesinde şifreli. Açık metin yalnızca `ndk_wand`
  pppd'yi başlatırken üretilir ve `/etc/ppp/options_ppp<N>` dosyasına `password "..."` satırı
  olarak yazılır. Oturum kapalıyken bu satır dosyada bulunmaz (yalnızca `user` satırı kalır).
- **Kalıcılık:** PPPoE profili `/dev/mtd5` içinde olduğu için `image0`/`image1` arasında
  firmware değiştirmek bu bilgileri **silmez**.

