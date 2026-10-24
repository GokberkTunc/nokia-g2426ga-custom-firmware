# Nokia G-2426G-A — Karşılaşılan Engeller, Başarısızlıklar ve Çözümler

Bu belgede, Nokia G-2426G-A üzerinde yürütülen özelleştirme ve donanım kontrolü sürecinde karşılaşılan tüm teknik engeller, denenen ancak başarısız olan yaklaşımlar, başarısızlıkların kök nedenleri ve bunların nasıl aşıldığı kronolojik ve şeffaf bir şekilde belgelenmiştir.

---

## 1. Başarısızlıklar ve Çözümler Tablosu

| # | Denenen Yaklaşım | Alınan Hata / Belirti | Kök Neden | Nihai Çözüm |
|---|---|---|---|---|
| **1** | Cihazdaki `/opt/mtdtools/flash_eraseall` ile silme | `syntax error` | Vendor ikiliyi x86 mimarisinde bırakmış; MIPS çekirdeğinde çalışmıyor. | Keystone ile 302 baytlık statik MIPS `erase_mtd` ikilisi üretildi. |
| **2** | Standart Linux ioctl (`0x40084D02`) ile silme | `ENOTTY (Inappropriate ioctl)` | MIPS mimarisinde ioctl yön ve boyut bitleri x86'dan farklıdır. | Canlı brute-force ile doğru MIPS kodları bulundu: Erase `0x80084D02`, Unlock `0x80084D7E`. |
| **3** | Karakter aygıtı `/dev/mtd4` üzerine doğrudan `dd` yazımı | `EINVAL (Invalid argument)` | MediaTek NAND sürücüsü sayfa hizalamasız tampon yazımlarını engelliyor. | Blok önbellek katmanını kullanan `/dev/mtdblock4` aygıtı kullanıldı. |
| **4** | Web komut enjeksiyonuyla geçici kabuk alma | 10 dk sonra `cfgmgr crashed (SIGABRT)` ve reboot | Enjeksiyon verisi `FtpUserName` alanına yazıldı; XML doğrulaması çöktü. | Web açığına bağımlılık sıfırlandı; firmware içine kalıcı supervisor konuldu. |
| **5** | Başlangıçta standart `utelnetd` çalıştırma | Boot sonrası port kapandı | `cfgmgr` başlangıçta `killall utelnetd` komutunu çalıştırıyor. | İkili `/bin/rr_telnetd` adıyla kopyalandı; isim çakışması önlendi. |
| **6** | Windows üzerinde düzenlenen `rrboot.sh` | Ash kabuğunda `syntax error` | Windows CRLF satır sonları Linux ash tarafından tanınmadı. | Dosyalar Python ile salt LF (`\n`) olarak üretildi. |
| **7** | `head.html` içine `<% ... ; ctcadmin = 1 ;%>` eklenmesi | `# 257 >>lex error->unknown token character` | `libcgi.so` lexer'ı noktalı virgül (`;`) atamasını desteklemiyor. | Lexer'ı bozan ifade kaldırıldı; arayüz kilitleri JavaScript ile açıldı. |
| **8** | `libcgi.so` içindeki çerez fonksiyonunu erken döndürme | Pointer hatası ve CGI çökmeleri | Fonksiyon çıktı göstericilerini doldurmadan dönünce bellek bozuldu. | Orijinal `libcgi.so` geri yüklendi; rol seçimi `menu.cgi` ikilisinde yapıldı. |
| **9** | `ONU_ALCL_ADMIN.t` dosyasını tek başına güncelleme | Menüde 66 yerine 34 sekme göründü | `menu.cgi` rol fonksiyonu oturumu `USER` görerek `ONU_ALCL_USER.t` açıyordu. | `menu.cgi` içinde `0x400fbc` fonksiyonu daima `"ADMIN"` dönecek şekilde yamalandı. |
| **10** | SmartHome sekmelerine tıklama | Boş beyaz sayfa | Cihaz kartında Zigbee/Z-Wave IoT yongası ve servisi fiziksel olarak yok. | Sayfaların donanım yokluğu nedeniyle boş döndüğü belgelendi. |

---

## 2. Teknik Detaylar ve Çıkarılan Dersler

### 2.1. Neden Çift Yuva (Dual-Bank A/B) Hayati Önem Taşıdı?
Cihazda `image0` ve `image1` olmak üzere iki ayrı bağımsız sistem bölümü bulunmaktadır. 
- Bir yuva üzerinde çalışırken (`active=1`), diğer yuva (`image0: /dev/mtd2`) tamamen boşta ve salt okunur durumdadır.
- Tüm yeni firmware derlemeleri ve denemeleri daima **boşta olan yuvaya** yazılmıştır.
- Yazılan imaj U-Boot tarafından onaylanmadığı veya açılamadığı takdirde, önyükleyicinin `boot_fail_num` sayacı devreye girerek sistemi otomatik olarak çalışan önceki yuvaya geri döndürmektedir.
- Bu mimari, onlarca flaşlama ve test boyunca cihazın hiçbir zaman "brick" (kullanılamaz) hale gelmemesini sağlamıştır.

### 2.2. Web Veri Tabanı Bütünlüğünün Korunması
Telekom modemlerindeki yönetim servisleri (`cfgmgr`, `cwmp`, `tr069`), katı XML şemaları kullanır. Konfigürasyon alanlarına kabuk enjeksiyonu veya satır sonu sokulması sistemin kısa vadede çalışmasını sağlasa bile, arka plandaki flash senkronizasyonunda ölümcül çökmelere (`SIGABRT`) yol açmaktadır. Bu nedenle kalıcı root erişimi, kullanıcı veritabanını kirletmeden dosya sistemindeki bağımsız sistem başlatma betikleri (`/etc/rcS.d/`) üzerinden kurulmalıdır.
