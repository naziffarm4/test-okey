# SMART SORT (`AKILLI DİZ`) VALIDATION REPORT

- **Tarih:** 2026-11-17
- **Başlangıç `main` Commit SHA:** `d0687710adf4fd669ebbfc7f2d7d553a73a345b5`
- **Doğrulanan Modüller:** `live-test/src/protocol/schemas.py` (`Tas`, `Rack28Model`, `OkeyRackEngine.akilli_diz`, `OkeyRackEngine.akilli_diz_cift`, `OkeyRackEngine.suggest_alternatives`)
- **Birim Test Kanıtı:** `live-test/tests/test_schemas_and_okey_engine.py`, `live-test/reports/faz4_5_protocol_and_engine.json`

---

## 1. Yönetici Özeti

4 kişilik Düz Okey'de oyuncu tur boyunca ıstakasındaki taşları tamamen yerel olarak dizer; sunucuya ara dizilim gönderme zorunluluğu yoktur. Bu nedenle **Akıllı Diz** özelliği sunucu yetkisine bağımlı olmayan, %100 yerel bir modül olarak gerçek APK'nın `MasaPerHesaplayici` (`RVA 0x01A09D98..0x01A0C170`) kurallarıyla birebir uyumlu şekilde geliştirilmiş ve doğrulanmıştır (**`KANITLANDI`**).

---

## 2. Altı Teknik Gereksinimin Doğrulama Sonuçları (Bölüm 6A)

| # | Gereksinim | Uygulanan Çözüm (`schemas.py`) | Doğrulama Testi | Sonuç |
|---|---|---|---|---|
| 1 | **28 taş yuvasını doğru yönetme** | `Rack28Model`: `0..13` üst satır, `14..27` alt satır olmak üzere tam `28` yuva; boş yuvalar `"Bos"`, dolu yuvalar fiziksel `TasID` tutar; perlerin `13 -> 14` satır sınırında bölünmesini engeller ve aralarına `"Bos"` ayırıcı koyar. | `test_rack28_model_and_non_destructive_alternatives_and_no_duplicate_reuse` | **`KANITLANDI`** |
| 2 | **Seri ve çift kombinasyonlarını hesaplama** | `mode="per"`: Aynı renk ardışık seriler (`3..13` taş, geçerli `12-13-1` dahil) ve `3..4` farklı renk aynı sayı perleri + aktif Okey joker ikamesi. `mode="cift"`: Aynı `(renk, sayı)` çiftleri, iki sahte Okey (`53`+`106`) çifti ve en yüksek puanlı tek taşları aktif Okey jokeriyle eşleştirme. | `test_rack28_model_...` & `test_akilli_diz_and_okey_ile_bit_per_and_7_pairs_...` | **`KANITLANDI`** |
| 3 | **Geçerli dizilimleri bulma (Kural Sınırları)** | Düz Okey kuralına uygun olarak `12-13-1` kabul edilirken geçersiz `13-1-2` döngüsü reddedilir (`wrap_trap` testi: `0` per, `16` kalan puan). Sahte Okeyler (`TasID` `"53"` ve `"106"`, `IsOkeyTile @ RVA 0x01A0A210`) joker sayılmaz, gösterge+1 (`okey_key`) değerini alır. | `test_tile_wire_parsing_and_okey_rules`, `test_rack28_model_...` | **`KANITLANDI`** |
| 4 | **Kalan taşları değerlendirme** | Per dışı kalan taşların sayısal değer toplamı (`kalan_toplam`) dal-sınır / belleklemeli (`memoized`) tam arama ile minimuma indirilir ve artan taşlar alt satırın sağ ucundan (`slot 27` geriye doğru) yerleştirilir. | `SIM-ENGINE-08-AKILLI-DIZ-OKEY-BIT` (`kalan_toplam = 0`) | **`KANITLANDI`** |
| 5 | **Kullanıcının mevcut dizilimini bozmadan alternatif dizilim sunma** | `OkeyRackEngine.suggest_alternatives(rack, okey_key)` ıstakanın klonlanmış kopyası (`rack.clone()`) üzerinde çalışır; orijinal `rack.to_slot_ids()` diziliminin değişmediğini `assert` ile garanti eder ve hem `per_alternative` hem `cift_alternative` önerisini döner. | `test_rack28_model_...` (`rack.to_slot_ids() == before_snapshot`) | **`KANITLANDI`** |
| 6 | **Aynı taşın birden fazla kombinasyonda kullanılması hatasını önleme** | Bitmask ayrıklığı (`used_mask & m == 0`) + `Rack28Model` ve `assert_disjoint_tile_usage` fiziksel `TasID` tekillik denetimi: aynı fiziksel `TasID` iki kez girilirse veya iki kombinasyonda kullanılırsa anında `ValueError` fırlatılır. | `test_rack28_model_...` (`assertRaises(ValueError)`) | **`KANITLANDI`** |

---

## 3. Zorunlu Kanıt Katmanı Ayrımı

1. **Statik Kod Kanıtı (`libil2cpp.so`):**
   - `Tas::TasOlustur @ RVA 0x01A1265C`: `<TasID>-<TasRenk>-<TasSayi>` tel biçimi ve `"Bos"` sabiti.
   - `MasaPerHesaplayici::IsOkeyTile @ RVA 0x01A0A210`: `Okeymi` bayrağı ve `"53"` / `"106"` sahte Okey istisnası.
   - `MasaPerHesaplayici::HesaplaKalanToplam @ RVA 0x01A09D98`, `PerOkeyKontrol @ RVA 0x01A0A308`, `PerSeriTasSorgula @ RVA 0x01A0BCC0`, `PerRenkTasSorgula @ RVA 0x01A0C170`.
2. **Yerel Test Kanıtı:**
   - `python -W error -m unittest live-test/tests/test_schemas_and_okey_engine.py -v` -> **`4/4 OK` (`0` uyarı)**.
   - `faz4_5_protocol_and_engine.json` içinde `non_destructive_preview_verified: true`, 15 taşlık seri elinde `kalan_toplam: 0` ve 14 taşlık çift elinde `cift_sayisi: 7, kalan_toplam: 0` çıktıları kaydedilmiştir.
3. **Canlı Sunucu Kanıtı:**
   - Akıllı Diz yerel bir ıstaka düzenleme algoritması olduğundan çalışması için canlı sunucu çağrısı gerekmez (isteğe bağlı sunucu destekli `masaseridiz-perdiz` komutu ise canlıda çalıştırılmamıştır).
4. **Yetki Nedeniyle Yapılamayan Testler:**
   - Canlı sunucudan gelen gerçek `IstakayiGuncelle` mesajıyla beslenen uçtan uca masa içi dizilim testi ve `masaseridiz-perdiz` (`OnPerDiz`) sunucu dizilim karşılaştırması yazılı izin yokluğunda yapılmamıştır (`ENGELLENDİ`).
5. **Çözülmemiş Riskler:**
   - Canlı sunucunun bazı özel turnuva veya varyant odalarda sahte Okey ya da gösterge taşını farklı bir ön ekle gönderip göndermediği, ilk yetkili canlı masa kaydında teyit edilmelidir.
