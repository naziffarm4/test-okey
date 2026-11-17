# FINAL GO / NO-GO DECISION — OKEY MUHABBET BAĞIMSIZ İSTEMCİ

- **Tarih:** 2026-11-17
- **Başlangıç `main` Commit SHA:** `d0687710adf4fd669ebbfc7f2d7d553a73a345b5`
- **Hedef Uygulama:** `com.adnc.okeymuhabbet` `v3.1.33` (`versionCode: 118`, 4 Kişilik Düz Okey)
- **Nihai Karar:** **`BLOCKED`** *(Gerekli sunucu sahibi yazılı yetkisi ve yetkili test ortamı bulunmadığı için canlı oturum ve oyun doğrulaması yapılamadı; canlı oturum doğrulanmadan tam Android istemcisi geliştirmeye başlanamaz.)*

---

## 1. Dördüncü Öncelik: Bağımsız İstemci Geliştirme Karar Tablosu (Bölüm 7)

| Gereksinim | Kanıt | Durum |
|---|---|---|
| **Sunucuya ağ erişimi** | DNS (`185.33.130.138`), TCP `:443` (`26.165 ms`), `TLSv1.3` GoDaddy G2 (`20.681 ms`), salt okunur `GET /` -> `HTTP 200` (`nginx/1.21.5`), pasif TCP `:4082` (`14.174 ms`) (`faz2_live_http_probe.json`, `faz3_websocket_validation.json`) | **`KANITLANDI` (Doğrulandı)** |
| **Misafir oturumu** | İstemci UI butonu (`resources.assets+0x70315C`) ve `MisafirGirisi @ RVA 0x019B2B0C` + yerel mock doğrulandı; ancak yazılı sunucu izni olmadığından **yetkili canlı test yapılamadı** (`FINAL-SERVER-ACCESS-REPORT.md`) | **`ENGELLENDİ` (Yetkili Canlı Test Yok)** |
| **Socket.IO bağlantısı** | `EIO=4` + Socket.IO v4 `40{id}` -> `40{sid}` ikili kodda (`RVA 0x01ACF57C`, `0x01ACA854`) ve yerel mock yığınında doğrulandı; üretim `:4082` üzerinde **yetkili canlı test yapılamadı** | **`ENGELLENDİ` (Yetkili Canlı Test Yok)** |
| **Oyun olayları** | 7 olay işleyicisinin JSON şemaları (`SIM-SCHEMA-07-ALL-EVENTS`) ve `'i'` zarfı ikili kodda/mock'ta doğrulandı; üretim sunucusundan **yetkili canlı olay yakalanmadı** | **`ENGELLENDİ` (Yetkili Canlı Test Yok)** |
| **Taş kimlikleri** | `Tas::TasOlustur @ RVA 0x01A1265C` (`<TasID>-<TasRenk>-<TasSayi>`, `"Bos"`, sahte Okey `"53"`/`"106"`) statik olarak kanıtlandı; **canlı sunucu örneği veya resmi şema mevcut değil** | **Statik: `KANITLANDI` / Canlı Örnek: `ENGELLENDİ`** |
| **Taş çekme/atma** | `masatascek-tascek` (`0x019B8DD0`) ve `masatasat-tasat` (`0x019B8B6C`) şemaları kanıtlandı; üretim sunucusunda **yetkili canlı test yapılamadı** | **`ENGELLENDİ` (Yetkili Canlı Test Yok)** |
| **Akıllı Diz** | 28 yuva (`Rack28Model`), seri/renk (`per`) + çift (`cift`), `12-13-1` / `13-1-2` kuralı, mevcut dizilimi bozmayan alternatif önizleme ve mükerrer taş kilidi yerel birim testleriyle doğrulandı (`SMART-SORT-VALIDATION-REPORT.md`) | **`KANITLANDI` (Yerel Test Başarılı)** |
| **Okey ile Bit** | 14 taş per/7-çift + 15. aktif Okey + 28 yuva `"-<id_veya_Bos>"` + `bitentas` yerel ve mock testlerle doğrulandı; **yetkili canlı sunucu kabul doğrulaması yapılamadı** (`OKEY-WITH-OKEY-VALIDATION-REPORT.md`) | **Yerel/Mock: `KANITLANDI` / Sunucu Kabulü: `ENGELLENDİ`** |
| **Bağımsız APK mimarisi** | Çift kanallı ağ katmanı (`HTTPS GET` + `ws://:4082` açık metin yapılandırması), 28 yuvalı ıstaka ve yerel çözücü mimarisi hazır (`CLIENT-ARCHITECTURE-PROPOSAL.md`, `INDEPENDENT-CLIENT-PROTOCOL-SPEC.md`) | **`KANITLANDI` (Teknik Tasarım Hazır)** |

---

## 2. Karar Gerekçesi (`GO` / `CONDITIONAL GO` / `NO-GO` / `BLOCKED` Değerlendirmesi)

- **Neden `GO` Verilmedi?** Gerçek sunucu oturumu, misafir girişi kabulü, canlı Socket.IO olay akışı ve gerçek masada `Okey ile Bit` kabulü yetkili biçimde doğrulanmamıştır. Kullanıcı için gerçek sunucuya bağlanamayan bir APK başarı sayılmaz.
- **Neden `NO-GO` Verilmedi?** İstemci ikili kodunda bağımsız istemciyi teknik olarak imkânsız kılan bir donanım/kriptografik engel (Google Play Integrity, SafetyNet, Firebase App Check, mTLS istemci sertifikası veya `PackNameFinder` paket adı doğrulaması) **bulunmadığı kanıtlanmıştır**.
- **Neden `BLOCKED` Seçildi (`CONDITIONAL GO` ile İlişkisi)?** Bölüm 7 tanımına göre *"Gerekli yetki veya test ortamı bulunmadığı için canlı doğrulama yapılamadı"* durumu doğrudan **`BLOCKED`** kategorisidir ve Bölüm 8 kuralı (*"Canlı sunucu oturumu doğrulanmadan tam Android istemcisi geliştirmeye başlama"*) tam APK geliştirmesini bu yetki kapısına bağlamaktadır. Geliştirici (`ADNC` / `Manc Games`) yazılı test izni veya staging ortamı sağladığında proje `BLOCKED` durumundan çıkar; 3 adımlı yetkili canlı doğrulama geçtiği anda doğrudan **`GO`** durumuna yükselir.

---

## 3. Uygulama Geliştirme Sınırı ve Hazır Bağımsız Modüller (Bölüm 8)

Tam Android istemcisi (UI / APK) kodlamasına **başlanmamıştır**. Buna karşılık gerçek sunucuya bağlanmış gibi sunulmadan, `live-test/` altında aşağıdaki **8 bağımsız çekirdek modül** geliştirilmiş ve otomatik birim testleriyle (`11/11 OK`) doğrulanmıştır:

1. **Akıllı Diz Algoritması:** `OkeyRackEngine.akilli_diz`, `akilli_diz_cift`, `suggest_alternatives` (`live-test/src/protocol/schemas.py`)
2. **Okey ile Bit Doğrulama Algoritması:** `OkeyRackEngine.build_okey_ile_bit_command` (`live-test/src/protocol/schemas.py`)
3. **Taş Modeli:** `Tas` (`from_wire`, `is_okey_joker`, `effective_key`) (`live-test/src/protocol/schemas.py`)
4. **28 Yuvalık İstaka Modeli:** `Rack28Model` (`live-test/src/protocol/schemas.py`)
5. **Protokol JSON Ayrıştırıcısı ve Şema Doğrulayıcı:** `validate_http_command_envelope`, `validate_server_envelope`, `validate_event_payload` (`live-test/src/protocol/schemas.py`)
6. **Socket.IO v4 / Engine.IO v4 İstemci Adaptörü:** `WebSocketClient` (`live-test/src/websocket/handshake.py`) + `EngineIOPacket` / `SocketIOPacket` (`live-test/src/socketio/parser.py`)
7. **Çift Kanallı Mock Sunucu Yığını:** `LocalMockHttpServer` + `LocalEngineIOWebSocketServer` + `LocalOkeyProtocolMockStack`
8. **Otomatik Birim Testleri ve Maskeli Kanıt Kaydedici:** `live-test/tests/*.py` + `EvidenceRecorder` (`live-test/src/diagnostics/recorder.py`)

---

## 4. Zorunlu Kanıt Katmanı Ayrımı

1. **Statik Kod Kanıtı:** `libil2cpp.so` (Ghidra `12.1.4` RVA ve C çıktıları), `global-metadata.dat` (v106) ve `data.unity3d` (`level1`, `resources.assets`).
2. **Yerel Mock Test Kanıtı:** `live-test/reports/faz3_websocket_validation.json`, `faz4_5_protocol_and_engine.json` ve `11/11` geçen birim testi.
3. **Canlı Sunucu Kanıtı:** Yalnızca `faz2_live_http_probe.json` (`:443` DNS/TCP/TLSv1.3 + salt okunur `HEAD/GET /` -> `HTTP 200`) ve `:4082` `0` bayt pasif TCP erişilebilirliği (`14.174 ms`).
4. **Yetki Nedeniyle Yapılamayan Testler:** Üretim sunucusunda `giris-misafir`, Socket.IO `40{id}` oturumu, masa katılma, taş çekme/atma ve `masaoyunbitir-oyunbitirbeta` canlı kabul testleri.
5. **Çözülmemiş Riskler:** Sunucu sahibinin üçüncü taraf istemciye izin vermemesi (ToS / paylaşımlı tuz kullanımı), üretimde misafir girişinin kapalı/kısıtlı olma olasılığı, Google/Facebook OAuth SHA-1 sertifika kilidi ve canlı `IstakayiGuncelle` tel formatı varyasyonları.

---

## 5. Son Rapor Formatı — 10 Sorunun Kesin Cevapları (Bölüm 12)

1. **Gerçek üretim sunucusuna bağımsız istemciyle bağlanabildin mi?**
   - **HAYIR** (Yalnızca `:443` HTTPS ve `:4082` TCP taşıma erişilebilirliği doğrulandı; uygulama/oturum bağlantısı yazılı izin olmadığı için açılmadı — Kanıt: `FINAL-SERVER-ACCESS-REPORT.md`, `live-test/reports/faz2_live_http_probe.json`).
2. **Misafir oturumu açılabildi mi?**
   - **HAYIR** (Üretimde yetkisiz `giris-misafir` isteği gönderilmedi; sunucunun canlı kabul durumu `BİLİNMİYOR` / `ENGELLENDİ`, yalnızca yerel mock üzerinde doğrulandı — Kanıt: `AUTHENTICATION-FLOW-TRACE.md`, `FINAL-SERVER-ACCESS-REPORT.md`).
3. **Socket.IO bağlantısı kuruldu mu?**
   - **HAYIR** (Gerçek üretim `:4082` sunucusunda kurulmadı; yalnızca yerel `LocalOkeyProtocolMockStack` üzerinde `EIO=4` + Socket.IO v4 `40{sid}` el sıkışması doğrulandı — Kanıt: `live-test/reports/faz3_websocket_validation.json`, `SOCKETIO-PROTOCOL-VALIDATION.md`).
4. **Gerçek oyun olayları alındı mı?**
   - **HAYIR** (Canlı sunucudan olay alınmadı; 7 olay şeması ikili koddan çıkarılıp yerel simülasyonda doğrulandı — Kanıt: `INDEPENDENT-CLIENT-PROTOCOL-SPEC.md`, `live-test/reports/faz4_5_protocol_and_engine.json`).
5. **Taş çekme ve atma doğrulandı mı?**
   - **HAYIR** (Canlı sunucuda doğrulanmadı; `masatascek-tascek` ve `masatasat-tasat` komut/yanıt şemaları statik ikili kod ve yerel şema testleriyle doğrulandı — Kanıt: `INDEPENDENT-CLIENT-PROTOCOL-SPEC.md`, `SERVER-CONNECTION-EVIDENCE.md`).
6. **Akıllı Diz algoritması çalışıyor mu?**
   - **EVET** (28 yuva modeli, seri/renk ve çift kombinasyonları, `12-13-1` / `13-1-2` sınırları, mevcut dizilimi bozmayan alternatif önizleme ve mükerrer taş engeli yerel birim testleriyle kanıtlandı — Kanıt: `SMART-SORT-VALIDATION-REPORT.md`, `live-test/tests/test_schemas_and_okey_engine.py`).
7. **Okey ile Bit algoritması çalışıyor mu?**
   - **EVET** (Yerel algoritma ve mock doğrulaması düzeyinde çalışıyor: 14 taş seri/7-çift kontrolü, 15. aktif Okey kontrolü, sahte Okey reddi ve 28 yuvalı `masaoyunbitir-oyunbitirbeta` üretimi doğrulandı — Kanıt: `OKEY-WITH-OKEY-VALIDATION-REPORT.md`, `live-test/tests/test_schemas_and_okey_engine.py`).
8. **Gerçek sunucuda Okey ile Bit kabul edildi mi?**
   - **BİLİNMİYOR** (Yetkili canlı oyun testi yapılamadığı için gerçek sunucuda denenmedi; yalnızca yerel mock sunucuda doğrulandı — Kanıt: `OKEY-WITH-OKEY-VALIDATION-REPORT.md`).
9. **Android istemci geliştirmeye başlanabilir mi?**
   - **HAYIR** (Bölüm 8 kuralı gereği canlı sunucu oturumu yetkili olarak doğrulanmadan tam Android istemcisi geliştirmeye başlanamaz; yalnızca çevrimdışı çekirdek/algoritma modülleri hazırdır — Kanıt: `FINAL-GO-NO-GO-DECISION.md` Bölüm 3).
10. **Şu an en büyük engel nedir?**
    - **Sunucu sahibi (`ADNC` / `Manc Games`) yazılı izni ve yetkili test/staging ortamının bulunmaması** (bu izin olmadan uygulamaya gömülü MD5/WS el sıkışma sabitleri meşru olarak kullanılamaz, Google/Facebook OAuth sertifikası tanımlanamaz ve `giris-misafir` + canlı masa protokol kabulü doğrulanamaz — Kanıt: `FINAL-SERVER-ACCESS-REPORT.md`, `BLOCKERS-AND-REQUIREMENTS.md`).

---

**TEK NİHAİ KARAR:** **`BLOCKED`**
