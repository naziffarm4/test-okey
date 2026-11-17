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

### 1. HTTPS sunucusuna gerçek bağlantı kurulabiliyor mu?
- **Yanıt:** **EVET (`KANITLANDI`).** `https://sistem.okeymuhabbet.com/` DNS üzerinden `185.33.130.138` IPv4 adresine (`23.01 ms`) çözümlenmiş, TCP `:443` bağlantısı (`27.37 ms`) ve sistem CA deposuyla doğrulanan geçerli GoDaddy G2 `TLSv1.3` (`TLS_AES_256_GCM_SHA384`, `30.733 ms`) el sıkışması Cloudflare/CAPTCHA engeli olmadan doğrudan tamamlanmıştır (`LIVE-HTTP-01-DNS`, `LIVE-HTTP-02-TCP-TLS`).

### 2. HTTP yanıtı alınabiliyor mu?
- **Yanıt:** **EVET (`KANITLANDI`).** Kimlik doğrulamasız, parametresiz, salt okunur `HEAD /` (`79.405 ms`) ve `GET /` (`48.896 ms`) istekleri `HTTP 200 OK` durum kodu, `server: nginx/1.21.5`, `content-type: text/html; charset=UTF-8`, `cache-control: no-store, no-cache, must-revalidate` başlıkları ve `0 byte` boş gövdeyle yanıt dönmüştür (`LIVE-HTTP-03-SAFE-GET`; `Set-Cookie` değeri otomatik olarak `[REDACTED]` maskelenmiştir).

### 3. WebSocket sunucusu bağlantıyı kabul ediyor mu?
- **Yanıt:** **Taşıma katmanında (TCP `:4082`) EVET (`KANITLANDI`); uygulama katmanında (`HTTP 101 Upgrade`) üretimde `ENGELLENDİ`, yerel mock sunucuda EVET (`KANITLANDI`).** `sistem.okeymuhabbet.com:4082` (`185.33.130.138:4082`) pasif TCP bağlantısını `14.592 ms` içinde kabul etmektedir (`LIVE-WS-01-TCP4082`, `0` uygulama baytı gönderildi). Bölüm 4 yetki kuralı gereği üretim `:4082` servisine uygulama protokolü seviyesinde bağlanılmamış (`LIVE-WS-02-PROD-APP-GATE` -> `ENGELLENDİ`); RFC 6455 `HTTP 101 Switching Protocols`, `Sec-WebSocket-Accept` ve kopma sonrası yeniden bağlanma yerel `LocalEngineIOWebSocketServer` üzerinde doğrulanmıştır (`MOCK-WS-03`, `MOCK-WS-04`).

### 4. Engine.IO v4 handshake başarılı mı?
- **Yanıt:** **Yerel mock ortamında EVET (`KANITLANDI`); canlı üretim sunucusunda yazılı yetki yokluğu nedeniyle `ENGELLENDİ`.** İstemci ikili kodunun (`Tranceiver::Connect @ RVA 0x01ACF57C`) yalnızca `?EIO=4&transport=websocket` kullandığı kanıtlanmış; `0{"sid":...,"upgrades":[],"pingInterval":25000,"pingTimeout":20000}` açılış paketi ve `2`/`3` Ping/Pong (`0.459 ms` RTT) yerel mock sunucuda doğrulanmıştır (`MOCK-WS-03-EIO4-HANDSHAKE-PING`).

### 5. Socket.IO namespace bağlantısı başarılı mı?
- **Yanıt:** **Yerel çift kanallı mock ortamında EVET (`KANITLANDI`); canlı üretim sunucusunda `ENGELLENDİ`.** `SuWebRequest::Callback @ RVA 0x019C5090` varsayılan `/` ad alanında oyuncu `"id"` değerini ve el sıkışma dizgesini `40{...}` ile gönderir; `SocketIONamespace::Submit @ RVA 0x01ACA854` sunucu yanıtında `40{"sid":"..."}` zorunluluğunu denetler. Bu akış `MOCK-SIO4-06-DUAL-CHANNEL` testinde eksiksiz doğrulanmıştır (`passed = true`).

### 6. Sunucudan gerçek olay alınabiliyor mu?
- **Yanıt:** **Canlı üretim sunucusundan HAYIR (`ENGELLENDİ` — yazılı test yetkisi yok); yerel mock sunucudan `'i'` zarfı üzerinden EVET (`KANITLANDI`).** Üretim WebSocket servisine kimlik doğrulama ve olay dinleme oturumu açılmadığından canlı sunucu olayı yakalanmamıştır (`ENGELLENDİ`). İstemcinin `42["i", "{\"s\":[{\"i\":\"...\",\"d\":{...}}]}"]` zarfını `OnSocketGelen -> SuWebRequest::Receive -> SuKuyrukPool` zinciriyle işlediği ikili kodda ve `MOCK-SIO4-06-DUAL-CHANNEL` testinde kanıtlanmıştır.

### 7. HTTP komut ve yanıt yapısı doğrulanabiliyor mu?
- **Yanıt:** **İstemci ikili kodunda ve yerel mock üzerinde EVET (`KANITLANDI`); canlı üretim kabulü `ENGELLENDİ`.** Oturum öncesi `_e`, oturum içi `_i` + `_t`, 1 saniyelik MD5 tekrar gönderim kilidi (`SuWebRequest::Emit @ RVA 0x019C2C64`), `?h=MD5(d+salt)&d=<json>` imzalama yapısı (`RVA 0x019C6374`) ve `{"s":[{"i":...,"d":...}]}` yanıt zarfı (`RVA 0x019C5614`) statik analiz ve `MOCK-HTTP-05-SIGNING` (`200` / hatalı imza `403`) testleriyle doğrulanmıştır.

### 8. Misafir oturumu yetkili test ortamında açılabiliyor mu?
- **Yanıt:** **Proje sahibine tahsis edilmiş yetkili bir staging/üretim test ortamı veya yazılı sunucu izni bulunmadığından `ENGELLENDİ` (`BİLİNMİYOR`).** İstemci arayüzünde misafir giriş butonunun aktif olduğu (`resources.assets+0x70315C`) ve `SuNetwork::MisafirGirisi @ RVA 0x019B2B0C` -> `OnMisafirGirisi @ RVA 0x019B2CE8` zincirinin yerel mock üzerinde çalıştığı **`KANITLANDI`**; ancak gerçek sunucunun yeni misafir oturumu kabulü yetkili ortam sağlandığında test edilmelidir.

### 9. Gerçek taş ve istaka JSON yapıları doğrulanabiliyor mu?
- **Yanıt:** **İstemci ayrıştırıcı ve serileştirici kuralları düzeyinde EVET (`KANITLANDI`); canlı sunucu ham paket yakalaması düzeyinde `ENGELLENDİ`.** `Tas::TasOlustur @ RVA 0x01A1265C` (`<TasID>-<TasRenk>-<TasSayi>` ve `"Bos"`), `IsOkeyTile @ RVA 0x01A0A210` (aktif Okey joker vs `"53"`/`"106"` sahte Okey ayrımı), 28 yuvalı `OyunBitirBeta` dizgesi (`RVA 0x019FF938`) ve 7 masa/taş işleyicisinin JSON şemaları (`SIM-SCHEMA-07-ALL-EVENTS`, `SIM-ENGINE-08-AKILLI-DIZ-OKEY-BIT`) Ghidra C çıktısıyla birebir doğrulanmıştır (ek olarak `SiraGeldi`'nin ağ olayı değil yerel türetilmiş metot olduğu kanıtlanmıştır).

### 10. Bağımsız Android istemcisi geliştirmeye geçmek için gereken bütün ön koşullar karşılanmış mı?
- **Yanıt:** **HAYIR — Üretim sunucusuyla canlı çalışma ön koşulu (yetkili canlı oturum kabulü) karşılanmamıştır (`ENGELLENDİ`); bu nedenle karar `GO` değil `CONDITIONAL GO`'dur.**
  - **Karşılanan Ön Koşullar (`KANITLANDI`):** Taşıma erişilebilirliği (`:443` TLSv1.3 ve `:4082` TCP), Play Integrity / paket adı / mTLS engeli bulunmaması, çift kanallı protokol şemaları, `Akıllı Diz` motoru ve 28 yuvalı `Okey ile Bit` komut biçimi. Çevrimdışı/mock tabanlı Android istemci çekirdeği (`Akıllı Diz`, `Okey ile Bit`, 28 yuvalı ıstaka UI ve mock ağ adaptörü) hemen geliştirilebilir.
  - **Eksik Tek Ön Koşul (`ENGELLENDİ`):** Sunucu sahibinden (`ADNC` / `Manc Games`) alınacak yazılı izin veya yetkili test ortamı ile gerçek sunucunun `giris-misafir` + Socket.IO `40{id}` + masa olay akışını kabul ettiğinin canlı olarak kanıtlanması.
