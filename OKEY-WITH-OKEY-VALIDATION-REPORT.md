# OKEY WITH OKEY (`OKEY İLE BİT`) VALIDATION REPORT

- **Tarih:** 2026-11-17
- **Başlangıç `main` Commit SHA:** `d0687710adf4fd669ebbfc7f2d7d553a73a345b5`
- **Doğrulanan Modüller:** `live-test/src/protocol/schemas.py` (`OkeyRackEngine.build_okey_ile_bit_command`), `live-test/src/http/probe.py` (`LocalMockHttpServer` `masaoyunbitir-oyunbitirbeta` doğrulayıcısı)
- **Test ve Kanıt Dosyaları:** `live-test/tests/test_schemas_and_okey_engine.py`, `live-test/reports/faz4_5_protocol_and_engine.json`

---

## 1. İkili Kod Mekanizması ve Ölü Kod Ayrımı (`KANITLANDI`)

Ghidra `12.1.4` (`libil2cpp.so`) analizi, Okey ile bitme işleminin ayrı bir ağ komutu kullanmadığını kesin olarak kanıtlamıştır:

1. **Ölü Kod (`0` Çağrıcı):** `SuNetwork::OyunBitir` (`RVA 0x019B7A9C`, `_i: "masaoyunbitir-oyunbitir"`) oyunda hiçbir metottan çağrılmaz.
2. **Aktif Bitiş Zinciri:** Oyuncu 15. taşını sahnedeki `'OkeyBitis'` (`GameObject.Find("OkeyBitis")` @ `RVA 0x01A08F78`, `RVA 0x01A02C7C`) gösterge bırakma alanına sürüklediğinde `Masa::TasHareketleri` (`RVA 0x019FEEB8`) -> `Masa::OyunBitir` (`RVA 0x019FF938`) -> `SuNetwork::OyunBitirBeta` (`RVA 0x019B7BEC`, `_i: "masaoyunbitir-oyunbitirbeta"`) zinciri çalışır.
3. **28 Yuva Serileştirme Kuralı (`Masa::OyunBitir @ RVA 0x019FF938`):**
   - Metot ıstaka kapsayıcısının (`param_3 + 0x58`) altındaki 28 yuvayı sırayla dolaşır.
   - `slotTransform.childCount > 0` ise `GetChild(0).GetComponent<Tas_Object>()->Tas (+0x20)->TasID (+0x18)` dizgisini alır; yuva boşsa `"Bos"` (`lit#2666`) sabitini alır.
   - Her yuva için `String.Concat3(TasListe, "-", slotValue)` çağrılır; böylece üretilen dizge `"-"` ile başlar ve tam **28 adet** `"-"` ayrımlı belirteçten oluşur.

---

## 2. Altı Doğrulama Kaleminin İncelemesi (Bölüm 6B)

| # | İncelenen Kriter | Uygulama ve İkili Uyum (`schemas.py`) | Yerel / Mock Test Sonucu | Durum |
|---|---|---|---|---|
| 1 | **14 taşlık elin geçerli bitiş kontrolü** | Aday Okey taşı çıkarıldıktan sonra kalan **14 taşın** ya (a) `mode="per"` altında `kalan_toplam == 0` ve `leftover == []` olacak şekilde tam perler oluşturduğu ya da (b) `mode="cift"` altında `cift_sayisi == 7` ve `leftover == []` oluşturduğu doğrulanır. | Hem 4 perlik (14 taş) el hem de sahte Okey çifti (`53`+`106`) içeren 7 çiftlik el doğrulandı. | **`KANITLANDI`** (Yerel) |
| 2 | **15. taşın Okey taşı olması** | El tam `15` taş olmalı ve atılacak taş `candidate.is_okey_joker() == True` koşulunu sağlamalıdır. Sahte Okey (`"53-o-0"`, `"106-o-0"`) aktif Okey jokeri **olmadığından** Okey ile bitiş taşı olarak seçilmesi reddedilir (`returns None`). | `fake_okey_finish_rejected = true` (`Case C` birim testi). | **`KANITLANDI`** (Yerel) |
| 3 | **28 yuvalık taş dizisinin oluşturulması** | Kalan 14 taşın oluşturduğu perler/çiftler 28 yuvalık ıstakaya (`0..13`, `14..27`) satır sınırı korunarak yerleştirilir (`14` dolu `TasID` + `14` `"Bos"` = `28` yuva). | `len(slots) == 28`, `slots.count("Bos") == 14`. | **`KANITLANDI`** (Yerel) |
| 4 | **Boş yuva ve `'-'` / `'Bos'` ayrımları** | `taslar` alanı `Masa::OyunBitir` ile birebir aynı şekilde `"-"` önekiyle başlar ve boş yuvalarda `"Bos"` dizgesini kullanır: `"-1-2-3-Bos-14-15-16-Bos-27-40-66-20-Bos-Bos-30-31-32-33-Bos-Bos-Bos-Bos-Bos-Bos-Bos-Bos-Bos-Bos"`. | Başlangıç `"-"` ve 28 belirteç `test_akilli_diz_and_okey_ile_bit_...` içinde doğrulandı. | **`KANITLANDI`** (Yerel) |
| 5 | **`bitentas` alanının oluşturulması** | Atılan 15. aktif Okey taşının fiziksel `TasID` değeri (`"5"` veya `"58"`) `"bitentas"` alanına yazılır ve bu `TasID`'nin 28 yuvalık `"taslar"` dizgesinde yer **almadığı** doğrulanır. | `bitentas == "5"`, `"5" not in slots`. | **`KANITLANDI`** (Yerel) |
| 6 | **Sunucuya gönderilecek bitiş verisinin doğruluğu** | Gönderilen JSON: `{"taslar": "<28_slot>", "bitentas": "<okey_tas_id>", "_i": "masaoyunbitir-oyunbitirbeta", "_t": "<session_id>"}`. `LocalMockHttpServer` geçerli 28 yuvalı yükte `"OyunBitir"`, bozuk yuva sayısında `"OyunBitirHata"` döndürür. | `mock_server_finish_event = "OyunBitir"`, bozuk yük -> `"OyunBitirHata"`. | Mock: **`KANITLANDI`** / Canlı Sunucu: **`ENGELLENDİ`** |

---

## 3. Zorunlu Kanıt Katmanı Ayrımı

- **Statik Kod Kanıtı:** `Masa::OyunBitir @ RVA 0x019FF938`, `SuNetwork::OyunBitirBeta @ RVA 0x019B7BEC`, `OnOyunBitir @ RVA 0x019BA3B0`, `OnOyunBitirHata @ RVA 0x019BA8D4` ve `IsOkeyTile @ RVA 0x01A0A210` metotları Ghidra C çıktısı üzerinden doğrulanmıştır.
- **Yerel Mock Test Kanıtı:** `test_akilli_diz_and_okey_ile_bit_per_and_7_pairs_and_mock_submit` testi hem normal per hem 7-çift elinde `Okey ile Bit` komutunu üretip yerel imzalı HTTP mock sunucusunda `"OyunBitir"` yanıtını ve hatalı dizilimde `"OyunBitirHata"` reddini doğrulamıştır.
- **Canlı Sunucu Kanıtı:** **YOKTUR (`ENGELLENDİ`).** Gerçek Okey Muhabbet üretim sunucusunun bu komutu canlı bir oyun masasında kabul ettiği **iddia edilmemektedir**; çünkü sunucu sahibinin yazılı izni olmadan canlı masada oyun bitirme komutu gönderilmemiştir.
- **Yetki Nedeniyle Yapılamayan Testler:** Gerçek üretim veya yetkili staging sunucusunda canlı el oynayıp `masaoyunbitir-oyunbitirbeta` göndererek `OnOyunBitir` (`CanakKirildi` / puan çarpanı) yanıtını alma testi.
- **Çözülmemiş Riskler:**
  1. Çifte gitme ilanı (`masacift-ciftegit`) yapılmamış bir masada sunucunun 7 çift + Okey ile bitişi kabul edip etmediği (yoksa öncesinde `masacift-ciftegit` zorunluluğu arayıp aramadığı) yalnızca yetkili canlı testte doğrulanabilir (`BİLİNMİYOR`).
  2. Sunucunun `"taslar"` içindeki perler arasında en az bir `"Bos"` boşluk bekleyip beklemediği (mevcut motorumuz her per arasına `"Bos"` koyarak güvenli biçimi üretmektedir).
