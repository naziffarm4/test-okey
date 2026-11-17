# LIVE HTTP TEST REPORT — OKEY MUHABBET (`sistem.okeymuhabbet.com`)

- **Tarih:** 2026-11-17 (`09:29:03 UTC`)
- **Hedef:** `https://sistem.okeymuhabbet.com/`
- **Uygulama Referansı:** `com.adnc.okeymuhabbet` `v3.1.33` (`versionCode: 118`, Unity `6000.5.0f1`, IL2CPP ARM64)
- **Kanıt Dosyaları:** `live-test/reports/faz2_live_http_probe.json`, `live-test/reports/faz4_5_protocol_and_engine.json`, `live-test/reports/test_execution_ledger.json`

---

## 1. Yönetici Özeti ve Doğruluk Etiketleri

| Kontrol Kalemi | Ortam | Sonuç | Durum Etiketi |
|---|---|---|---|
| DNS Çözümlemesi (`sistem.okeymuhabbet.com`) | `PRODUCTION_SAFE_READONLY` | `185.33.130.138` (`23.01 ms`) | **`KANITLANDI`** |
| TCP `443` Bağlantısı | `PRODUCTION_SAFE_READONLY` | Açık ve erişilebilir (`27.37 ms`) | **`KANITLANDI`** |
| TLS Protokol ve Sertifika Doğrulaması | `PRODUCTION_SAFE_READONLY` | `TLSv1.3` (`TLS_AES_256_GCM_SHA384`), GoDaddy G2 geçerli sertifika (`30.733 ms`) | **`KANITLANDI`** |
| Salt Okunur `HEAD /` ve `GET /` Yanıtı | `PRODUCTION_SAFE_READONLY` | `HTTP 200 OK`, `nginx/1.21.5`, `0 byte` boş gövde (`48.896 ms`) | **`KANITLANDI`** |
| İstemci Komut İletim Mimarisi (`?h=<md5>&d=<json>`) | Statik Binary + `LOCAL_MOCK` | `SuWebRequest.Emit -> Send` HTTPS GET + MD5 bütünlük zarfı (`200` / hatalı tuz `403`) | **`KANITLANDI`** (İstemci & Mock) |
| Üretim Sunucusunda Canlı Oyun/Giriş Komutu Kabulü | Üretim Uygulama Katmanı | Yazılı sunucu sahibi izni olmadığından imzalı komut gönderimi durduruldu (`0` komut gönderildi) | **`ENGELLENDİ`** |

---

## 2. Canlı Salt Okunur Taşıma ve HTTP Bulguları (`PRODUCTION_SAFE_READONLY`)

`live-test/src/http/probe.py` içindeki `run_safe_production_http_probe()` fonksiyonu ile hiçbir uygulama komutu (`_e`, `_i`), oturum belirteci (`_t`), sahte cihaz kimliği veya `?h=&d=` sorgu parametresi gönderilmeden gerçekleştirilen ölçümler:

### 2.1 DNS, TCP ve TLS Doğrulaması (`LIVE-HTTP-01-DNS`, `LIVE-HTTP-02-TCP-TLS`)
- **Çözümlenen IPv4 Adresi:** `185.33.130.138` (`23.01 ms`)
- **TCP El Sıkışma Süresi (`:443`):** `27.37 ms`
- **TLS El Sıkışma Süresi:** `30.733 ms`
- **TLS Sürümü ve Şifreleme Kümesi:** `TLSv1.3` — `TLS_AES_256_GCM_SHA384` (`256-bit`)
- **Sertifika Konusu (Subject) ve SAN:** `CN = *.okeymuhabbet.com` (`SAN: *.okeymuhabbet.com, okeymuhabbet.com`)
- **Sertifika Makamı (Issuer):** `Go Daddy Secure Certificate Authority - G2` (`GoDaddy.com, Inc.`)
- **Geçerlilik Aralığı:** `Jan 16 13:26:18 2026 GMT` – `Feb 4 17:14:20 2027 GMT` (`verified: true`)
- **CDN / WAF Gözlemi (`KANITLANDI`):** Sunucu Cloudflare/Turnstile veya benzeri bir ters vekil bot duvarı arkasında değildir; doğrudan `185.33.130.138` üzerinde `nginx/1.21.5` yanıt vermektedir. İstemci tarafında özel sertifika sabitleme (certificate pinning) zorunluluğu olmadan standart Android/시스템 CA deposu ile doğrulanabilmektedir.

### 2.2 Salt Okunur `HEAD /` ve `GET /` Yanıt Analizi (`LIVE-HTTP-03-SAFE-GET`)
- **`HEAD /`:** `HTTP 200 OK` (`79.405 ms`)
- **`GET /`:** `HTTP 200 OK` (`48.896 ms`)
- **Yanıt Başlıkları (Maskelenmiş):**
  - `server: nginx/1.21.5`
  - `content-type: text/html; charset=UTF-8`
  - `transfer-encoding: chunked`
  - `connection: close`
  - `set-cookie: [REDACTED]` *(otomatik maskelendi)*
  - `expires: Thu, 19 Nov 1981 08:52:00 GMT`
  - `cache-control: no-store, no-cache, must-revalidate`
  - `pragma: no-cache`
  - `access-control-allow-origin: *`
- **Yanıt Gövdesi Yapısı:** `0 byte` (`empty_body`, SHA-256: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`).
- **Teknik Çıkarım (`GÜÇLÜ İPUCU`):** `expires: Thu, 19 Nov 1981 08:52:00 GMT` başlığı ve parametresiz istekte `Set-Cookie` üretip `0 byte` gövdeyle `HTTP 200` dönmesi, Nginx arkasında çalışan klasik bir PHP ön denetleyicisine (front-controller) işaret eder; betik `$_GET['h']` ve `$_GET['d']` parametreleri yokken boş çıktı üretip sonlanmaktadır.

---

## 3. Uygulama Katmanı HTTP Komut Mimarisi (Statik İkili Kanıt + Yerel Mock Doğrulaması)

### 3.1 İkili Kod Kanıtı (`libil2cpp.so` + `level1` — `KANITLANDI`)
1. **Yapılandırma Kaynağı:** `level1+0x7DBC` içindeki `SuWebRequest` MonoBehaviour bileşeni `URL = "https://sistem.okeymuhabbet.com/"` değerini taşır.
2. **Çift Gönderim Koruması (`SuWebRequest::Emit @ RVA 0x019C2C64`):** Gönderilecek JSON dizgesinin `MD5` özetini hesaplar; son gönderilen özetle aynıysa ve `lastTime + 1 < now` koşulu sağlanmıyorsa isteği yerel olarak düşürür (`test_envelope_builder_and_duplicate_guard` ile doğrulandı).
3. **Oturum Ekleme ve İmzalama (`SuWebRequest::<Send>d__27::MoveNext @ RVA 0x019C6374`):**
   - Oturum öncesi (`pre-auth`) çağrılar `_e` anahtarını kullanır (örn. `{"token_id":"","device_id":"...","machash":"...","_e":"giris-misafir"}`).
   - Oturum içi (`in-session`) çağrılar `_i` komut adını ve `PlayerPrefs["session_id"]` değerinden okunan `"_t"` alanını içerir.
   - İmza formülü: `h = MD5(d_json + <REDACTED_16_CHAR_STATIC_SALT>)` (`StringLiteral #1429`, depoda açık metin olarak tutulmaz).
   - İstek biçimi: `UnityWebRequest.Get("https://sistem.okeymuhabbet.com/?h=" + h + "&d=" + d_json)`.
4. **Yanıt Kuyruğu (`SuWebRequest::Receive @ RVA 0x019C5614`):** HTTP yanıt gövdesindeki `\` kaçış karakterlerini temizler, `{"s": [{"i": "<OlayAdi>", "d": {...}}]}` zarfını ayrıştırır ve `SuKuyrukPool` (`this+0x38`) üzerinden `SuNetwork` olay işleyicilerine dağıtır.

### 3.2 Yerel Mock Doğrulaması (`MOCK-HTTP-05-SIGNING` — `KANITLANDI`)
- Üretim sunucusuna yetkisiz imzalı komut göndermek yerine (`LIVE-HTTP-04-APP-CMD-GATE` -> `ENGELLENDİ`), `LocalMockHttpServer` üzerinde sentetik tuz (`SYNTHETIC_HTTP_16`) kullanılarak tam zarf ve imza döngüsü çalıştırılmıştır:
  - Geçerli MD5 imzalı `?h=...&d=...` isteği -> `HTTP 200 OK` ve `{"s":[{"i":"VersiyonOnay","d":{"durum":1,"versiyon":"3.1.33"}}]}` (`30.818 ms`).
  - Bozulmuş/hatalı tuzla imzalanmış istek -> `HTTP 403 Forbidden` (`invalid_signature`).
  - `probe.py::send_signed_command()` fonksiyonu `allow_non_local=False` güvenlik kilidi ile korunmakta olup yerel olmayan (`127.0.0.1`/`localhost` dışı) hedeflere imzalı komut gönderimini `PermissionError` ile engeller.

---

## 4. Kısıtlar ve Bilinmeyenler

- **Sunucu Tarafı Canlı Doğrulama (`ENGELLENDİ` / `BİLİNMİYOR`):** Yazılı test yetkisi bulunmadığından `sistem.okeymuhabbet.com` üzerindeki PHP arka ucunun hız sınırlama (rate-limit), IP/ASN filtreleme, `Versiyon` alt sınırı veya ek sunucu tarafı doğrulama davranışları canlı ortamda test edilmemiştir. Taşıma katmanı (`DNS + TCP + TLSv1.3 + HTTP 200`) **`KANITLANDI`**, canlı uygulama komutu kabulü ise **`ENGELLENDİ`** statüsündedir.
