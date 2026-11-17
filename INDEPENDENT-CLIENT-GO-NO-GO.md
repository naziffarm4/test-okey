# INDEPENDENT CLIENT GO / NO-GO DECISION — OKEY MUHABBET

- **Tarih:** 2026-11-17
- **Hedef Sürüm:** `com.adnc.okeymuhabbet` `v3.1.33` (`versionCode: 118`)
- **Nihai Mühendislik Kararı:** **`CONDITIONAL GO` (Koşullu Devam — Canlı Sunucu Kabulü Yazılı İzin Kapısında Bekliyor; Kesin `GO` Verilmedi)**

---

## 1. Karar Özeti ve Gerekçesi

Görev kuralları gereği **gerçek sunucu kabulü canlı olarak kanıtlanmadan `GO` kararı verilemez** ve salt TCP/TLS erişilebilirliği çalışan bir oyun oturumu gibi sunulamaz.

1. **Neden `NO-GO` Değil?**
   - İstemci ikili kodunda (`libil2cpp.so` + `level1` + `resources.assets`) bağımsız istemciyi imkânsız kılacak **Google Play Integrity**, **SafetyNet**, **mTLS / istemci sertifikası** veya giriş akışında aktif **paket adı (`PackNameFinder`) kontrolü** bulunmadığı **`KANITLANDI`**.
   - PAIRIP (`libpairipcore.so`) yalnızca orijinal APK paketini koruyan yerel bir sarmalayıcıdır; sıfırdan yazılacak bağımsız bir Android istemcisinde çalışmaz (**`KANITLANDI`**).
   - Sunucunun her iki uç noktası (`https://sistem.okeymuhabbet.com:443` ve `sistem.okeymuhabbet.com:4082` -> `185.33.130.138`) Cloudflare/CAPTCHA engeli olmadan doğrudan erişilebilirdir (**`KANITLANDI`**).
   - Çift kanallı protokol (`HTTPS GET ?h=MD5&d=JSON` + `Engine.IO v4 / Socket.IO v4 'i'` kanalı), taş tel biçimi (`<TasID>-<TasRenk>-<TasSayi>`), `Akıllı Diz` algoritması ve 28 yuvalı `Okey ile Bit` (`masaoyunbitir-oyunbitirbeta`) serileştirmesi Ghidra dekompilasyonu ve yerel mock testleriyle (`11/11` birim testi + `12/12` kanıt senaryosu) eksiksiz doğrulanmıştır (**`KANITLANDI`**).
2. **Neden Doğrudan `GO` Değil (`CONDITIONAL GO`)?**
   - Sunucu sahibinden (`ADNC` / `Manc Games`) açık yazılı test izni bulunmadığından üretim sunucusuna `giris-misafir` komutu gönderilmemiş ve `:4082` üzerinde canlı `EIO=4 / Socket.IO v4` oturumu açılmamıştır (**`ENGELLENDİ`**).
   - Dolayısıyla üretim sunucusunun canlı ortamda misafir oturumu açıp masa olaylarını döndürdüğü henüz kanıtlanmamıştır (**`BİLİNMİYOR` / `ENGELLENDİ`**).

---

## 2. Nihai Başarı Kriterleri — 10 Temel Sorunun Kanıtlı Yanıtları (Bölüm 13)

### 1. HTTP sunucusu dışarıdan güvenli şekilde erişilebilir mi?
- **Yanıt:** **Evet (`KANITLANDI`).** `https://sistem.okeymuhabbet.com/` (`185.33.130.138:443`) DNS (`23.01 ms`), TCP (`27.37 ms`), geçerli GoDaddy G2 `TLSv1.3` (`TLS_AES_256_GCM_SHA384`, `30.733 ms`) ve salt okunur `HEAD /` ile `GET /` (`HTTP 200 OK`, `nginx/1.21.5`, `48.896 ms`) kontrollerini doğrudan ve WAF/CAPTCHA engeli olmaksızın geçmiştir (`LIVE-HTTP-01..03`).

### 2. WebSocket servisi erişilebilir mi?
- **Yanıt:** **Taşıma katmanında Evet (`KANITLANDI`), uygulama katmanında yetki bekliyor (`ENGELLENDİ`).** `sistem.okeymuhabbet.com:4082` (`185.33.130.138:4082`) TCP 3-yollu el sıkışmaya `14.592 ms` içinde yanıt vermektedir (`LIVE-WS-01-TCP4082`, `0` uygulama baytı gönderildi). Üretim üzerinde `HTTP 101` / `EIO=4` yükseltmesi yazılı izin kuralı gereği çalıştırılmamış (`ENGELLENDİ`), yerel `LocalEngineIOWebSocketServer` üzerinde `HTTP 101` + `EIO=4` + yeniden bağlanma tam olarak doğrulanmıştır (`MOCK-WS-03`, `MOCK-WS-04`).

### 3. Engine.IO v4 ve Socket.IO v4 el sıkışması çalışıyor mu?
- **Yanıt:** **İstemci ikili kodunda ve yerel mock yığınında Evet (`KANITLANDI`), canlı üretim sunucusunda yetki bekliyor (`ENGELLENDİ`).** `SocketIOPlus.dll` (`Tranceiver::Connect @ 0x01ACF57C`, `SocketIONamespace::Submit @ 0x01ACA854`) WebSocket-only `?EIO=4&transport=websocket` bağlantısı kurar, `0{sid}` açılış paketini alır, `40{"id":...}` gönderip `40{"sid":...}` bekler, `2`/`3` ve `42["ping"]`/`42["pong"]` kalp atışlarını yürütür. Bu tam akış `MOCK-SIO4-06-DUAL-CHANNEL` testinde `45.705 ms` içinde uçtan uca doğrulanmıştır.

### 4. Misafir giriş akışı gerçek ortamda çalışıyor mu?
- **Yanıt:** **İstemci kodunda ve UI sahnesinde aktif (`KANITLANDI`), gerçek üretim sunucusundaki canlı kabulü test edilmedi (`ENGELLENDİ` / `BİLİNMİYOR`).** `resources.assets+0x70315C` içindeki aktif misafir butonu `SuNetwork::MisafirGirisi @ 0x019B2B0C` üzerinden `_e: "giris-misafir"` isteğini üretir ve `OnMisafirGirisi @ 0x019B2CE8` yanıtından `id`, `token_id`, `session_id` değerlerini kaydeder. Yazılı izin olmadan üretim sunucusunda hesap/oturum oluşturulmamıştır.

### 5. Oturum açıldıktan sonra Socket.IO bağlantısı kabul ediliyor mu?
- **Yanıt:** **Mimari bağlama kuralı `KANITLANDI`, canlı üretim kabulü `ENGELLENDİ`.** İstemci HTTP girişinden aldığı oyuncu `id` değerini ve `StringLiteral #399` içindeki 10 karakterlik el sıkışma dizgesini `SuWebRequest::Callback @ 0x019C5090` ile `40{...}` içinde gönderir. Yerel çift kanallı mock üzerinde doğrulandı (`MOCK-SIO4-06-DUAL-CHANNEL`); üretim sunucusundaki canlı doğrulama yazılı izin bekliyor.

### 6. Gerçek masa ve taş olaylarının JSON şeması doğrulandı mı?
- **Yanıt:** **İstemci olay işleyicilerinin beklediği kesin alan adları ve türleri `KANITLANDI` (`SIM-SCHEMA-07-ALL-EVENTS`); canlı sunucu ham yükleri `ENGELLENDİ`.** `OnIstakayiGuncelle`, `OnMasaTaslariGuncelle`, `OnTasCek`, `OnTasAt`, `OnOyunBitir` ve `OnOyunBitirHata` işleyicilerinin okuduğu tüm JSON anahtarları Ghidra C çıktısıyla çıkarılmış ve şema doğrulayıcıdan `7/7` geçmiştir. Ayrıca `SiraGeldi`'nin ağ olayı değil, `TasCek`/`TasAt` sonunda çağrılan yerel bir metot (`0x01A0E0A4`) olduğu kanıtlanmıştır.

### 7. Sunucu bağımsız istemciyi engelleyen ek bir kontrol uyguluyor mu?
- **Yanıt:** **İstemci ikili kodunda engelleyici Play Integrity / imza / paket adı kontrolü YOK (`KANITLANDI`); sunucu tarafındaki olası gizli WAF/rate-limit kuralları `BİLİNMİYOR`.** İstemci yalnızca `Versiyon = "3.1.33"`, `os = "ANDROID"`, HTTP MD5 imzası ve WS el sıkışma dizgesi göndermektedir.

### 8. `Akıllı Diz` özelliği bağımsız istemcide uygulanabilir mi?
- **Yanıt:** **Evet, %100 uygulanabilir (`KANITLANDI`).** `Akıllı Diz` (`MasaPerHesaplayici @ 0x01A09D98`) tamamen istemci belleğindeki 14/15 taş üzerinde çalışan yerel bir per optimizasyon algoritmasıdır; sunucu izni veya özel API gerektirmez ve `OkeyRackEngine.akilli_diz` ile çalışır durumda doğrulanmıştır (`SIM-ENGINE-08-AKILLI-DIZ-OKEY-BIT`).

### 9. `Okey ile Bit` özelliği sunucu protokolüyle uyumlu şekilde uygulanabilir mi?
- **Yanıt:** **Protokol serileştirme biçimi %100 `KANITLANDI`, canlı sunucu masa kabulü `CONDITIONAL` (`ENGELLENDİ`).** `Masa::OyunBitir @ 0x019FF938` -> `SuNetwork::OyunBitirBeta @ 0x019B7BEC` akışının 28 ıstaka yuvasını `"-<id_veya_Bos>..."` biçiminde `taslar` alanına yazdığı, atılan aktif Okey taşının `TasID` değerini `bitentas` alanında gönderdiği ve `_i: "masaoyunbitir-oyunbitirbeta"` komutunu kullandığı kanıtlanmış ve `OkeyRackEngine.build_okey_ile_bit_command` ile doğrulanmıştır.

### 10. Bağımsız Android istemci geliştirmeye başlanmalı mı?
- **Yanıt:** **`CONDITIONAL GO` — Çevrimdışı/Mock tabanlı çekirdek modüller için EVET, üretim sunucusuna bağlama için YAZILI YETKİ SONRASI EVET.**
  - **Hemen Başlanabilecek İşler (Sıfır Risk):** Bağımsız Android UI (28 yuvalı ıstaka + masa görünümü), `Tas` tel ayrıştırıcısı, `Akıllı Diz` ve `Okey ile Bit` motoru, `live-test` yerel mock sunucusuna karşı çalışan çift kanallı ağ katmanı (`HTTPS GET` + `Socket.IO v4 WS` + `network_security_config.xml` açık metin `:4082` izni).
  - **`GO` Kararı İçin Tek Zorunlu Kapı:** Sunucu sahibinden (`ADNC` / `Manc Games`) yazılı test izni (veya test/staging ortamı) alınarak **tek bir yetkili `giris-misafir` + `:4082` `40{id}` bağlantısı + örnek masa taş dağıtımı** canlı olarak doğrulandığında proje doğrudan tam **`GO`** durumuna geçer.
