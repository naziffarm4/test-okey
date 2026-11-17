# LIVE PROTOCOL EVIDENCE — OKEY MUHABBET

- **Tarih:** 2026-11-17
- **Kanıt Defteri:** `live-test/reports/test_execution_ledger.json`
- **Ham Ölçüm ve Simülasyon Çıktıları:**
  - `live-test/reports/faz2_live_http_probe.json`
  - `live-test/reports/faz3_websocket_validation.json`
  - `live-test/reports/faz4_5_protocol_and_engine.json`

---

## 1. Yapılandırılmış Test Çalıştırma Defteri (10 Zorunlu Alan Özeti)

Tüm kayıtlar `2026-11-17T09:29:03Z–09:29:04Z` aralığında otomatik üretilmiş ve hassas alanlar `"[REDACTED]"` olarak maskelenmiştir:

| Test ID | Ortam | İstek Türü | Yanıt Kodu | Süre (ms) | Beklenen Sonuç | Gerçek Sonuç | Kanıt Dosyası | Başarı |
|---|---|---|---|---:|---|---|---|---|
| `LIVE-HTTP-01-DNS` | `PRODUCTION_SAFE_READONLY` | `DNS_A_AAAA_LOOKUP` | `RESOLVED` | `23.010` | `>=1` IP çözümü | `['185.33.130.138']` | `faz2_live_http_probe.json` | Başarılı |
| `LIVE-HTTP-02-TCP-TLS` | `PRODUCTION_SAFE_READONLY` | `TCP_443_AND_TLS_HANDSHAKE` | `TLSv1.3` | `58.103` | TCP 443 + geçerli CA sertifikası | `TLSv1.3` (`27.37ms` TCP + `30.733ms` TLS) | `faz2_live_http_probe.json` | Başarılı |
| `LIVE-HTTP-03-SAFE-GET` | `PRODUCTION_SAFE_READONLY` | `HTTPS_READONLY_ROOT_GET` | `200` | `48.896` | Salt okunur durum ve başlıklar | `HTTP 200`, `nginx/1.21.5`, `0 byte` gövde | `faz2_live_http_probe.json` | Başarılı |
| `LIVE-HTTP-04-APP-CMD-GATE` | `PRODUCTION_SAFE_READONLY` | `SIGNED_APP_COMMAND_AUTHORIZATION_CHECK` | `ENGELLENDİ` | `0.000` | Yazılı izinsiz komut göndermeme | `0` imzalı komut gönderildi | `faz2_live_http_probe.json` | Başarılı |
| `LIVE-WS-01-TCP4082` | `PRODUCTION_SAFE_READONLY` | `TCP_4082_CONNECT_ZERO_BYTES` | `OPEN` | `14.592` | `0` bayt ile `:4082` erişimi | `185.33.130.138:4082` açık (`0` bayt) | `faz3_websocket_validation.json` | Başarılı |
| `LIVE-WS-02-PROD-APP-GATE` | `PRODUCTION_SAFE_READONLY` | `WS_UPGRADE_EIO4_AUTHORIZATION_CHECK` | `ENGELLENDİ` | `0.000` | Yazılı izinsiz WS oturumu açmama | `ENGELLENDİ` (Bölüm 4 kuralı) | `faz3_websocket_validation.json` | Başarılı |
| `MOCK-WS-03-EIO4-HANDSHAKE-PING` | `LOCAL_MOCK` | `WS_101_UPGRADE_AND_EIO4_PING_PONG` | `101` | `22.635` | `HTTP 101` + `0{sid}` + `2/3` RTT | `HTTP 101`, `pong=True` (`0.459 ms` RTT) | `faz3_websocket_validation.json` | Başarılı |
| `MOCK-WS-04-RECONNECT` | `LOCAL_MOCK` | `WS_DROP_AND_RECONNECT_RECOVERY` | `101` | `69.117` | Kopma sonrası yeniden bağlanma | 2. denemede bağlandı (`69.117 ms`) | `faz3_websocket_validation.json` | Başarılı |
| `MOCK-HTTP-05-SIGNING` | `LOCAL_MOCK` | `SIGNED_GET_MD5_VERIFICATION` | `200/403` | `30.818` | Geçerli `200`, bozuk tuz `403` | `Valid=200`, `Tampered=403` | `faz4_5_protocol_and_engine.json` | Başarılı |
| `MOCK-SIO4-06-DUAL-CHANNEL` | `LOCAL_MOCK` | `DUAL_CHANNEL_HTTP_AND_SOCKETIO_V4` | `ALL_OK` | `45.705` | HTTP giriş + WS `40` + `'i'` olay + `41` | `6/6` aşama başarılı (`ping_rtt=1.562ms`) | `faz4_5_protocol_and_engine.json` | Başarılı |
| `SIM-SCHEMA-07-ALL-EVENTS` | `LOCAL_SIMULATION` | `JSON_SCHEMA_VALIDATION_7_EVENTS` | `7/7_VALID` | `0.043` | 7 olay ve 3 zarf şema doğrulaması | `all_schemas_ok=True` | `faz4_5_protocol_and_engine.json` | Başarılı |
| `SIM-ENGINE-08-AKILLI-DIZ-OKEY-BIT` | `LOCAL_SIMULATION` | `AKILLI_DIZ_AND_OKEY_ILE_BIT_28_SLOT` | `OK` | `17.396` | `kalan_toplam=0` ve 28 yuva bitiş komutu | `kalan_toplam=0`, `bitentas="5"`, 28 yuva | `faz4_5_protocol_and_engine.json` | Başarılı |

---

## 2. Tel Üstü Taş Biçimi ve Olay Şemaları Kanıt Matrisi (`libil2cpp.so` Ghidra `12.1.4`)

### 2.1 Taş Kodlaması (`Tas::TasOlustur @ RVA 0x01A1265C` & `IsOkeyTile @ RVA 0x01A0A210` — `KANITLANDI`)
- **Dolu Yuva Tel Dizgesi (`TasAdi`):** `<TasID>-<TasRenk>-<TasSayi>` (ayırıcı `'-'`):
  - `TasID` (`parts[0]`): `"1"`..`"106"` benzersiz fiziksel taş kimliği.
  - `TasRenk` (`parts[1]`): `"k"` (kırmızı), `"m"` (mavi), `"s"` (sarı/siyah), `"y"` (yeşil), `"o"` (sahte okey).
  - `TasSayi` / `TasRakam` (`parts[2]`): `1..13` (sahte okey için `0`).
  - `TasKey`: `"{TasRenk}-{TasSayi}"` (örn. `"k-5"`).
- **Boş Istaka Yuvası:** `"Bos"` (`StringLiteral #2666`).
- **Aktif Okey (Joker) vs Sahte Okey Kuralı (`RVA 0x01A0A210`):**
  - Masa nesnesindeki `ok` alanı (örn. gösterge `"4-k-4"` iken `ok = "k-5"`) aktif Okey anahtarını belirler; `TasKey == ok` olan iki taş **gerçek Okey jokeridir** (`Okeymi == true`).
  - `TasID == "53"` ve `TasID == "106"` olan taşlar **Sahte Okeydir**; joker olarak **kullanılmazlar**, yalnızca aktif Okey'in nominal renk ve sayı değerini (`"k-5"`) temsil ederler.

### 2.2 Yedi Hedef Olay Şemasının Kanıt Durumu (`SIM-SCHEMA-07-ALL-EVENTS`)

| İşleyici / Metot | RVA (`libil2cpp.so`) | Okunan JSON Alanları | İstemci Şeması | Canlı Sunucu Yükü |
|---|---|---|---|---|
| `OnIstakayiGuncelle` | `0x019B94AC` -> `0x01A08EC0` | `t` (ıstaka taş listesi) | **`KANITLANDI`** | **`ENGELLENDİ`** |
| `OnMasaTaslariGuncelle` | `0x019B9590` -> `0x01A08224` | `mid`, `kt`, `ot`, `ok`, `ms`, `yt`, `el`, `es`, `pn`, `rx`, `rxm`, `mk`, `bb`, `mp`, `cn`, `tc`, `cl`, `ob`, `sa`, `y`, `max`, `is_tournament`, `current_round` | **`KANITLANDI`** | **`ENGELLENDİ`** |
| `OnTasCek` | `0x019B8F9C` -> `0x01A02C7C` | `tas`, `yon`, `tip`, `kt`, `tc`, `dc`, `cl`, `m` | **`KANITLANDI`** | **`ENGELLENDİ`** |
| `OnTasAt` | `0x019B8D18` -> `0x01A02728` | `tas`, `yon`, `ms`, `tc`, `cl` | **`KANITLANDI`** | **`ENGELLENDİ`** |
| `Masa_Object::SiraGeldi` | `0x01A0E0A4` *(Yerel türetilmiş çağrı)* | Ağ olayı değildir; `TasCek`/`TasAt` sonunda `(int Sira, float sure)` argümanlarıyla yerel çağrılır | **`KANITLANDI`** | Geçersiz (Yerel Metot) |
| `OnOyunBitir` | `0x019BA3B0` -> `0x019FA048` | `Baslik`, `BitenTas`, `CanakKirildi`, `Kazananlar[{id,i,p,a,v}]`, `Taslar[]` | **`KANITLANDI`** | **`ENGELLENDİ`** |
| `OnOyunBitirHata` | `0x019BA8D4` -> `0x01A159DC` | `hata[{Per, Tip, Taslar[]}]` | **`KANITLANDI`** | **`ENGELLENDİ`** |

---

## 3. `Akıllı Diz` ve `Okey ile Bit` Protokol Simülasyonu (`SIM-ENGINE-08-AKILLI-DIZ-OKEY-BIT` — `KANITLANDI`)

- **`Akıllı Diz` (`MasaPerHesaplayici::HesaplaKalanToplam @ RVA 0x01A09D98` Eşdeğeri):**
  - Gösterge `"4-k-4"`, aktif Okey `"k-5"` iken 15 taşlık örnek elde 4 tam per (`1-2-3 k`, `1-2-3 m`, `7-7-7-7 s/y/k/m`, `10-11-12-13 s`) bulunmuş (`kalan_toplam = 0`) ve 15. taş olan aktif Okey (`"5-k-5"`) boşa çıkarılmıştır.
  - Tamamen yerel (client-side) çalışır; sunucuya ağ isteği göndermez (**`KANITLANDI`**).
- **`Okey ile Bit` (`Masa::OyunBitir @ RVA 0x019FF938` -> `SuNetwork::OyunBitirBeta @ RVA 0x019B7BEC`):**
  - 28 ıstaka yuvası soldan sağa taranarak dolu yuvalarda `TasID`, boş yuvalarda `"Bos"` birleştirilir ve başına `"-"` eklenir:
    - `taslar`: `"-1-2-3-Bos-14-15-16-Bos-27-40-66-20-Bos-Bos-30-31-32-33-Bos-Bos-Bos-Bos-Bos-Bos-Bos-Bos-Bos-Bos"` (`28` yuva, biten taş `"5"` ıstaka dizgesinde yer almaz).
    - `bitentas`: `"5"` (aktif Okey taşının `TasID` değeri).
    - `_i`: `"masaoyunbitir-oyunbitirbeta"`, `_t`: `"[REDACTED]"`.
  - Sunucu nihai per geçerliliğini doğrular; hatalı dizilimde `OnOyunBitirHata`, geçerli bitişte `OnOyunBitir` (`CanakKirildi` dahil) yayınlar (**`KANITLANDI`**).
