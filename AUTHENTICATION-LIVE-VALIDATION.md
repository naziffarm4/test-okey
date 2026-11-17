# AUTHENTICATION LIVE VALIDATION — OKEY MUHABBET

- **Tarih:** 2026-11-17
- **Uygulama:** `com.adnc.okeymuhabbet` `v3.1.33` (`versionCode: 118`)
- **Kanıt Dosyaları:** `AUTHENTICATION-FLOW-TRACE.md`, `live-test/reports/faz4_5_protocol_and_engine.json`, `live-test/reports/test_execution_ledger.json`

---

## 1. Beş Kimlik Doğrulama Akışının Teknik Durumu

Ghidra `12.1.4` (`libil2cpp.so`) ve Unity varlık (`resources.assets`, `level1`) analizleriyle doğrulanan 5 giriş akışı ve bağımsız istemci uyumluluğu:

| Akış (`_e` / Komut) | İkili Kod Konumu (RVA) | Gönderilen Parametreler | Bağımsız İstemcide Durum | Kanıt Etiketi |
|---|---|---|---|---|
| `giris-misafir` | `SuNetwork::MisafirGirisi @ 0x019B2B0C` (`resources.assets+0x70315C` aktif UI butonu) | `token_id`, `device_id`, `machash`, `_e: "giris-misafir"` | **Birincil Aday:** Harici OAuth veya APK sertifikası gerektirmez; ancak canlı sunucu kabulü yazılı izin olmadan test edilmedi. | İstemci: **`KANITLANDI`** / Canlı Sunucu: **`ENGELLENDİ`** |
| `giris-GirisYap` | `SuNetwork::Giris @ 0x019B1940` | `machash`, `token_id`, `_e: "giris-GirisYap"` | Kayıtlı `token_id` + `machash` ile oturum yenileme/otomatik giriş akışı. | İstemci: **`KANITLANDI`** / Canlı Sunucu: **`ENGELLENDİ`** |
| `giris-googlegirisyeni` | `Login::OnGoogleLogin @ 0x0197F264` | `user_id`, `user_name`, `user_mail`, `foto`, `device_id`, `token_id`, `_e` | **Uyumsuz:** Google Play Games Services (`APP_ID` + orijinal APK imzalama sertifikası SHA-1 kilidi). | **`KANITLANDI`** (Kilitli) |
| `giris-facebookgiris` | `<>c::<FacebookGirisOk>b__2_0 @ 0x0197EB6C` | `user_id`, `user_name`, `device_id`, `token_id`, `_e` | **Uyumsuz:** Meta App ID (`1479949552201495`) Android Key Hash kilidi. | **`KANITLANDI`** (Kilitli) |
| `giris-applegiris` | `AppleLogin::<LoginToApple>b__11_0 @ 0x0197DD04` | `user_id`, `user_name`, `user_mail`, `aid`, `aid_md5`, `device_id`, `token_id`, `_e` | Android'de birincil değil; Apple kimlik belirteci gerektirir. | **`KANITLANDI`** |

---

## 2. Oturum Yaşam Döngüsü ve Maskelenmiş Parametreler (`KANITLANDI`)

1. **Cihaz Özeti (`machash` / `device_id`):**
   - `GameUniqueID::get_id @ RVA 0x019BB8E8`, `SystemInfo.deviceUniqueIdentifier` değerini okur (`Android Settings.Secure.ANDROID_ID` türevi) ve `machash = MD5(device_id + <REDACTED_SALT>)` özetini üretir. Fiziksel MAC adresi Android 11+ / Android 16'da işletim sistemi tarafından kısıtlandığından gerçek donanım MAC adresi okunmamaktadır.
2. **Başarılı Giriş Yanıt İşleyicileri (`OnMisafirGirisi @ RVA 0x019B2CE8` & `OnGirisYapildi @ RVA 0x019B1C24`):**
   - Sunucu `{"s": [{"i": "MisafirGirisi" | "GirisYapildi", "d": {...}}]}` zarfıyla döndüğünde istemci şu alanları `PlayerPrefs` içine kaydeder (tüm test kayıtlarında `"[REDACTED]"` olarak maskelenir):
     - `id`: Sayısal oyuncu kimliği (Socket.IO `40{"id": ...}` el sıkışmasında kullanılır).
     - `kullanici`: Oyuncu görünen adı.
     - `token_id`: Sonraki açılışta `giris-GirisYap` ile oturumu sürdürmek için saklanan kalıcı anahtar.
     - `session_id`: Aktif oturum anahtarı; sonraki tüm HTTP komutlarına `"_t": "[REDACTED]"` olarak eklenir.
3. **Sürüm ve Paket Kontrolleri (`KANITLANDI`):**
   - `SuNetwork::VersiyonKontrol @ RVA 0x019B2FA4`: `level1+0x8420` içinden `AppVersiyon = "3.1.33"` ve `os = "ANDROID"` gönderir (`_i: "versiyonkontrol-versiyonkontrol"`).
   - `PackNameFinder` (`RVA 0x0197FB50`): Tüm `libil2cpp.so` çapraz referans (xref) taramasında **sıfır çağrıcıya (`0` caller)** sahiptir; giriş veya oyun komutlarına paket adı (`Application.identifier`) eklenmez.
   - APK bağımlılıklarında **Google Play Integrity API** veya **SafetyNet Attestation** bulunmamaktadır (`KANITLANDI`).

---

## 3. PAIRIP, Frida ve Bağımsız İstemci Ayrımı (`KANITLANDI`)

- **Orijinal APK Üzerindeki Engel:** Xiaomi 17T Pro (Android 16) testlerinde orijinal APK'nın `libpairipcore.so` (`com.pairip.licensecheck`) korumasını içerdiği; ADB kurulumunda `responseCode = 2 (NOT_LICENSED)` dönerek kapandığı ve APK yeniden paketlendiğinde (`frida-gadget` enjeksiyonu vb.) imza/CRC bütünlük kontrolüne takıldığı kanıtlanmıştır.
- **Bağımsız İstemciye Etkisi:** Geliştirilecek **bağımsız Android istemcisi** orijinal APK'yı değiştirmez ve `libpairipcore.so` içermez. Dolayısıyla PAIRIP, bağımsız istemcinin kendi çalışmasını engellemez; yalnızca yetkisiz kullanıcıların orijinal üretim APK'sına çalışma zamanı kancası (Frida hook) atmasını engeller.
- **Yetkili Test / QA Seçeneği:** Sunucu sahibinden yazılı test izni veya PAIRIP içermeyen bir QA/staging derlemesi sağlandığında canlı protokol doğrulaması hiçbir güvenlik mekanizmasını atlatmadan yasal ve temiz biçimde tamamlanabilir.

---

## 4. Canlı Doğrulama Durumu Özeti

- **Yerel Mock Doğrulaması (`MOCK-SIO4-06-DUAL-CHANNEL`):** `giris-misafir` zarf üretimi, MD5 imzalama, `session_id` / `token_id` maskeli saklama ve ardından oyuncu `id` değeriyle Socket.IO `40` ad alanı bağlama akışı yerel mock yığınında eksiksiz doğrulanmıştır (`passed = true`).
- **Canlı Sunucu Kabulü (`LIVE-HTTP-04-APP-CMD-GATE`):** Sunucu sahibinin yazılı izni bulunmadığından üretim `https://sistem.okeymuhabbet.com/` adresine sahte veya gerçek `giris-misafir` isteği gönderilmemiştir (**`ENGELLENDİ`**). Sunucunun yeni misafir kaydını açık tutup tutmadığı canlı ortamda henüz doğrulanmamıştır (**`BİLİNMİYOR`**).
