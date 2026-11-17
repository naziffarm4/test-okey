# Okey Muhabbet Alternatif İstemci Projesi — Engeller ve Gereksinimler

**Tarih:** 17.11.2026  
**Karar Durumu:** **SONUÇ B — KOŞULLU MÜMKÜN** *(Aşağıdaki gereksinimler karşılanmadığı sürece geliştirme başlatılamaz -> **SONUÇ C**)*

---

## 1. Tespit Edilen Engeller (Blockers)

| # | Engel Başlığı | Kategori | Teknik Kanıt ve Açıklama | Güvenirlik |
|---|---|---|---|---|
| **B-01** | **Kullanım Koşulları ve Sunucu Yetkilendirme Eksikliği** | Hukuki / Politika | `data.unity3d` içinde `https://www.okeymuhabbet.com/tr/terms-of-service` bağlantısı ve `Assembly-CSharp.dll` içinde `BanMesaj` / `SetBanData` / `siparis-hile` modülleri mevcuttur. Geliştirici (`MANC` / `ADNC`) onayı olmadan üçüncü parti bir istemcinin (özellikle *Akıllı Diz* ve *Hamle Önerileri* ile) canlı sunucuya bağlanması kullanım koşullarına aykırıdır ve hesap/cihaz engellemesine (`isBanned`) yol açar. | `[KANITLANDI]` |
| **B-02** | **Google Play Games ve Facebook OAuth Sertifika Kilidi** | Kimlik Doğrulama | `giris-googlegirisyeni` ve `giris-facebookgiris` (`App ID: 1479949552201495`) akışları, Google Cloud ve Meta tarafında `com.adnc.okeymuhabbet` paket adına ve `1e9f627e...` üretim imzasına kilitlidir. Geliştirici yeni istemcinin SHA-1 / Key Hash bilgisini kendi konsoluna eklemeden mevcut oyuncu hesaplarına giriş yapılamaz. | `[KANITLANDI]` |
| **B-03** | **Tel-Üstü (Wire-Level) JSON Paket Şemalarının Eksikliği** | Protokol | `60+` sunucu komutu (`masatascek-tascek`, `masatasat-tasat`, `masaoyunbitir-oyunbitir` vb.) kesin olarak tespit edilmiş olsa da her komutun beklediği tam JSON alan adları, `SendServerCommand` zarf formatı ve `ws://` vs `wss://` geçiş kuralı statik analizle tek başına %100 doğrulanamaz; üretim APK'sında PAIRIP olduğu ve izinsiz sunucu yoklaması yasak olduğu için resmi protokol şeması gereklidir. | `[KANITLANDI]` |
| **B-04** | **Olası İstek Özeti (`MD5Hash`) ve Sürüm Kapısı (`versiyonkontrol`)** | Oturum Güvenliği | `OyunMotoru` içinde `MD5Hash`, `UnixTime`, `AppVersiyon`, `PackNameFinder` ve `versiyonkontrol-versiyonkontrol` bulunmaktadır. Sunucunun istemci isteklerinde gizli bir tuz (salt) ile üretilmiş MD5 özeti arayıp aramadığı veya sürüm yükseltildiğinde bağımsız istemciyi reddedip reddetmeyeceği geliştirici bilgisi olmadan bilinemez. | `[GÜÇLÜ İPUCU]` / `[BİLİNMİYOR]` |
| **B-05** | **Vivox Sesli Sohbet Yetkilendirmesi** | Ses / VoIP | Masa içi sesli sohbet (`VivoxControl`, `MisafirKonusma`), Unity Gaming Services (`Unity.Services.Authentication` / `Unity.Services.Vivox`) proje kimlik bilgilerine bağlıdır. Geliştirici erişim anahtarı olmadan bağımsız istemci sesli masalara bağlanamaz. | `[KANITLANDI]` |
| **B-06** | **`Yardimli` Masa Kuralı ve Adil Oyun Sınırı** | Oyun Kuralları | Masa modelinde `get_Yardimli` / `set_Yardimli` alanı yer almaktadır. Yardımsız masalarda veya turnuvalarda (`isTournament`) istemci tarafında hamle/olasılık önerisi gösterilmesi oyun dengesini bozar; sunucu politikasıyla uyumlu sınırların geliştiriciyle mutabık kalınması şarttır. | `[KANITLANDI]` |

---

## 2. Engel Olmadığı Kanıtlanan Noktalar (Yanlış Varsayımların Elenmesi)

Araştırma sonucunda aşağıdakilerin bağımsız istemci önünde **engel OLMADIĞI** kanıtlanmıştır:
1. **`[KANITLANDI]`** Sunucu tarafında **Google Play Integrity API** jeton kontrolü yoktur (`ev_bce20d9021b7e540...`).
2. **`[KANITLANDI]`** Sunucu tarafında **Firebase App Check** doğrulaması yoktur (`ev_887174815c0b126f...`).
3. **`[KANITLANDI]`** **PAIRIP (`com.pairip.licensecheck`)** yalnızca orijinal APK'nın cihaz üzerinde açılışını kontrol eder; oyun sunucusu (`sistem.okeymuhabbet.com:4082`) ile herhangi bir kriptografik bağı yoktur.
4. **`[KANITLANDI]`** Taşıma katmanı özel bir ikili (binary) protokol değil, standart **Socket.IO + JSON** protokolüdür (`Firesplash.GameDevAssets.SocketIOPlus.dll`).

---

## 3. Geliştirmeye Başlamak İçin Zorunlu Ön Koşullar Listesi (`SONUÇ B` -> Uygulama Geçiş Kriterleri)

Bağımsız Android istemcisinin kodlanmasına geçilebilmesi için uygulama sahibi / geliştirici ekipten (`MANC` / `ADNC`) aşağıdaki 5 maddenin temin edilmesi gerekmektedir:

- [ ] **Gereksinim 1 — Yazılı Geliştirici Onayı ve Sunucu İzni:** Alternatif Android istemcisinin `sistem.okeymuhabbet.com` (ve öncesinde bir test/staging sunucusu) ile çalışmasına ve hangi masa türlerinde (`Yardimli` vb.) yardımcı özelliklerin açık olabileceğine dair resmi izin.
- [ ] **Gereksinim 2 — OAuth İstemci Kaydı:** Alternatif istemcinin paket adı ve imzalama sertifikası özetinin (`SHA-1` / `SHA-256` / Key Hash) Google Play Games (Google Cloud Console) ve Facebook Login (Meta Developer Portal) projelerine eklenmesi.
- [ ] **Gereksinim 3 — Resmi Socket.IO Mesaj ve JSON Şema Dokümanı:** `SuNetwork.SendServerCommand` olay zarfı, `giris-*`, `masa*` ve `OnIstakayiGuncelle` mesajlarının tam JSON alan tanımları ve varsa `MD5Hash` doğrulama kuralı.
- [ ] **Gereksinim 4 — Sürüm Politikası (`versiyonkontrol`):** Alternatif istemcinin `versiyonkontrol-versiyonkontrol` adımında hangi istemci kimliği ve sürüm numarasıyla (`AppVersiyon`) kabul edileceğinin tanımlanması.
- [ ] **Gereksinim 5 — (İsteğe Bağlı) Vivox / Test Ortamı Erişimi:** Sesli sohbet özelliği de desteklenecekse Vivox kanal katılım jetonu (`VivoxLoginId`) üretim yetkisi ve üretim verisini etkilemeyen bir QA/Test sunucu uç noktası.

---

## 4. Kesin Sonuç ve Eylem Kararı

- Yukarıdaki 5 gereksinim geliştirici iş birliğiyle sağlandığında, [CLIENT-ARCHITECTURE-PROPOSAL.md](file:///e:/apk/test-okey/CLIENT-ARCHITECTURE-PROPOSAL.md) belgesindeki Kotlin + Jetpack Compose + Socket.IO istemcisi doğrudan geliştirilebilir (**SONUÇ B — KOŞULLU MÜMKÜN**).
- Geliştirici onayı ve istemci kaydı **bulunmadığı mevcut tek taraflı durumda** ise canlı sunucuya bağlanan bir istemci geliştirmek hem OAuth/protokol engellerine takılacak hem de yetkisiz erişim oluşturacaktır; bu nedenle ön koşullar sağlanana kadar **kod geliştirmeye geçilmemesi (SONUÇ C — Durdurma Kriteri)** mühendislik ve güvenlik kuralları gereği zorunludur.
