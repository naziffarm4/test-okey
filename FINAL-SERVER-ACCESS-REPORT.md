# FINAL SERVER ACCESS REPORT — OKEY MUHABBET (`sistem.okeymuhabbet.com`)

- **Tarih:** 2026-11-17 (`09:53:57 UTC`)
- **Başlangıç `main` Commit SHA:** `d0687710adf4fd669ebbfc7f2d7d553a73a345b5` (Birleştirilen test tabanı: `4ef3635c68a60f8e185bf9a28489b37888683e81`)
- **Hedef Uygulama:** `com.adnc.okeymuhabbet` `v3.1.33` (`versionCode: 118`, 4 Kişilik Düz Okey)
- **Birincil Kanıt Dosyaları:**
  - Canlı salt okunur HTTP ölçümü: `live-test/reports/faz2_live_http_probe.json`
  - Pasif TCP `:4082` + Mock WS ölçümü: `live-test/reports/faz3_websocket_validation.json`
  - Çalıştırma defteri: `live-test/reports/test_execution_ledger.json`
  - Statik bağlantı kanıtları: `SERVER-CONNECTION-EVIDENCE.md`, `AUTHENTICATION-FLOW-TRACE.md`

---

## 1. Sekiz Erişim Kaleminin Doğrudan Bulguları (Bölüm 4)

| # | Araştırma Konusu | Kanıt Kaynağı | Somut Bulgu | Durum |
|---|---|---|---|---|
| 1 | **Sunucu DNS çözümlemesi** | Canlı DNS (`LIVE-HTTP-01-DNS`) | `sistem.okeymuhabbet.com` doğrudan `185.33.130.138` (IPv4) adresine çözümlendi (`34.584 ms`). | **`KANITLANDI`** |
| 2 | **HTTPS uç noktasının TCP/TLS erişilebilirliği** | Canlı TCP/TLS (`LIVE-HTTP-02-TCP-TLS`) | `185.33.130.138:443` TCP bağlantısı `26.165 ms`, `TLSv1.3` (`TLS_AES_256_GCM_SHA384`, 256-bit) el sıkışması `20.681 ms` içinde tamamlandı. | **`KANITLANDI`** |
| 3 | **HTTPS sertifika zinciri ve HTTP yanıt davranışı** | Canlı HTTPS (`LIVE-HTTP-03-SAFE-GET`) | Sertifika: `CN=*.okeymuhabbet.com` (`SAN: *.okeymuhabbet.com, okeymuhabbet.com`), Makam: `Go Daddy Secure Certificate Authority - G2`, Geçerlilik: `16 Oca 2026 – 4 Şub 2027` (`verified=true`). Parametresiz salt okunur `HEAD /` (`91.851 ms`) ve `GET /` (`63.215 ms`) istekleri `HTTP 200 OK`, `server: nginx/1.21.5`, `cache-control: no-store, no-cache, must-revalidate`, `Set-Cookie: [REDACTED]` ve `0 byte` boş gövde döndürdü; Cloudflare/CAPTCHA/WAF engeli yok. | **`KANITLANDI`** |
| 4 | **WebSocket portu `4082` TCP erişilebilirliği** | Canlı Pasif TCP (`LIVE-WS-01-TCP4082`) | `185.33.130.138:4082` TCP 3-yollu el sıkışmayı `14.174 ms` içinde kabul etti (`0` uygulama baytı gönderildi). | **`KANITLANDI`** |
| 5 | **WebSocket el sıkışma davranışı** | Statik İkili Kod + Yerel Mock (`MOCK-WS-03`) | İstemci `ws://sistem.okeymuhabbet.com:4082/socket.io/?EIO=4&transport=websocket` adresine şifresiz (`ws://`) RFC 6455 `HTTP 101` yükseltmesi yapar. Yerel mock sunucuda `HTTP 101` (`2.46 ms`) + `Sec-WebSocket-Accept` doğrulandı; üretim `:4082` üzerinde yetkisiz `HTTP 101` başlatılmadı. | Mock/Statik: **`KANITLANDI`** / Canlı: **`ENGELLENDİ`** |
| 6 | **Engine.IO v4 ve Socket.IO protokol uyumluluğu** | `SocketIOPlus.dll` + `MOCK-SIO4-06` | HTTP long-polling yoktur (`Tranceiver.Connect @ RVA 0x01ACF57C`). Engine.IO v4 (`0{sid}`, `2`/`3` ping-pong) üstünde Socket.IO v4 (Protocol v5: `40{id,...}` -> `40{"sid":"..."}` @ `RVA 0x01ACA854` ve tekil `'i'` olay zarfı) çalışır. | Mock/Statik: **`KANITLANDI`** / Canlı: **`ENGELLENDİ`** |
| 7 | **Resmi veya izinli misafir oturumu imkânı** | `resources.assets+0x70315C` + `RVA 0x019B2B0C` | Orijinal APK arayüzünde aktif `MisafirGirisi` (`_e: "giris-misafir"`) butonu vardır; ancak üçüncü taraf bağımsız bir istemcinin üretimde misafir oturumu açmasına izin veren halka açık/resmi bir API politikası **bulunmamaktadır**. | Canlı Kabul: **`ENGELLENDİ`** / **`BİLİNMİYOR`** |
| 8 | **Geliştirici test ortamı, test hesabı veya dokümantasyon gereksinimi** | Mimari & Hukuki Sınır Analizi | İstek imzalama tuzu (`lit#1429`), WS el sıkışma dizgisi (`lit#399`), sosyal giriş OAuth (`SHA-1`/Key Hash) ve canlı kabul testleri için sunucu sahibinden (`ADNC` / `Manc Games`) **yazılı test izni ve/veya staging ortamı + test hesabı** alınması zorunludur. | **`KANITLANDI`** |

---

## 2. Zorunlu Kanıt Katmanı Ayrımı

### 2.1 Statik Kod Kanıtı (`libil2cpp.so` + `data.unity3d`)
- Komut kanalı adresi `level1+0x7DBC` konumunda `"https://sistem.okeymuhabbet.com/"`, gerçek zamanlı kanal adresi `level1+0x7879` konumunda `"ws://sistem.okeymuhabbet.com:4082"` olarak serileştirilmiştir.
- Ağ katmanında Google Play Integrity, SafetyNet, Firebase App Check, mTLS istemci sertifikası veya `Application.identifier` paket adı doğrulaması (`PackNameFinder` `0` çağrıcıya sahiptir) bulunmamaktadır. PAIRIP (`libpairipcore.so`) yalnızca orijinal APK'nın yerel açılış kilididir.

### 2.2 Yerel Mock Test Kanıtı (`live-test/`)
- `LocalMockHttpServer` üzerinde `?h=MD5(d+salt)&d=<JSON>` imzalama doğrulaması (`200 OK` vs hatalı tuz `403 Forbidden`), `LocalEngineIOWebSocketServer` ve `LocalOkeyProtocolMockStack` üzerinde `HTTP 101` yükseltmesi, `EIO=4` `0{sid}`, `40{id}` -> `40{sid}`, `2`/`3` + `42["ping"]`/`42["pong"]`, `42["i", ...]` olay yönlendirmesi ve kopma sonrası 2. denemede otomatik yeniden bağlanma (`64.275 ms`) doğrulanmıştır.

### 2.3 Canlı Sunucu Kanıtı (`PRODUCTION_SAFE_READONLY`)
- `sistem.okeymuhabbet.com` (`185.33.130.138`) üzerinde hem `:443` (`TLSv1.3`, `nginx/1.21.5`, `HTTP 200`, `0 byte` gövde) hem `:4082` (`14.174 ms` TCP açık) uç noktalarının dış ağdan doğrudan erişilebilir olduğu canlı olarak kanıtlanmıştır.
- **Önemli Uyarı:** Taşıma katmanının (`DNS + TCP + TLS + HTTP 200`) açık olması, sunucunun bağımsız istemciden gelen oturum ve oyun komutlarını kabul ettiğinin kanıtı **değildir**.

### 2.4 Yetki Nedeniyle Yapılamayan Testler (`ENGELLENDİ`)
- Üretim sunucusuna `_e: "giris-misafir"` veya `_e: "giris-GirisYap"` isteği gönderilmemiştir.
- Üretim `:4082` portunda RFC 6455 `HTTP 101` yükseltmesi, `40{id}` kimlik doğrulaması, masa listeleme (`masayakatil-masalistesi`), masaya oturma, taş çekme/atma veya `masaoyunbitir-oyunbitirbeta` çağrısı yapılmamıştır.

### 2.5 Çözülmemiş Riskler
1. **Sunucu Tarafı Misafir Kısıtı Riski:** Üretim sunucusu `v3.1.33` için yeni `giris-misafir` kayıtlarını kapatmış veya `MisafirGirisBildirim` ile sosyal hesaba zorluyor olabilir (`BİLİNMİYOR`).
2. **Paylaşımlı Sabitlerin Kullanım İzni ve Rotasyon Riski:** İstemci ikilisindeki MD5 imzalama tuzu ve WS el sıkışma dizgisi sunucu sahibinin izni olmadan kullanılırsa ToS ihlali ve hesap/IP engeli (`BanMesaj`) doğurur; ayrıca sunucu güncellemesinde bu sabitler değiştirildiğinde bağımsız istemci anında bağlantı kaybeder.
3. **OAuth Sertifika Kilidi:** Google Play Games ve Facebook girişleri geliştirici konsolunda yeni APK imzası tanımlanmadan bağımsız istemcide çalışmaz.
