# OKEY MUHABBET — ALTERNATİF İSTEMCİ GERÇEKLİK TESTİ (`v3.1.33`)

> **Belge Türü:** Komut Düzeyi (ARM64 + Ghidra 12.1.4 Decompile + IL2CPP Metadata v106 + UnityFS Sahne Serileştirmesi) Gerçeklik Testi Ana Raporu  
> **Hedef Paket:** `com.adnc.okeymuhabbet` (`versionName: 3.1.33`, `versionCode: 118`, Unity `6000.5.0f1`)  
> **İncelenen İkili Kaynaklar:**  
> - `config.arm64_v8a.apk!/lib/arm64-v8a/libil2cpp.so` (`65.456.416` bayt, `SHA-256: 12549b7aa4bc2f17eb8b437124a418be05a142aa738a213c6ff71f19cd10235b`)  
> - `config.arm64_v8a.apk!/lib/arm64-v8a/libpairipcore.so` (`609.256` bayt)  
> - `com.adnc.okeymuhabbet.apk!/assets/bin/Data/Managed/Metadata/global-metadata.dat` (`10.128.084` bayt, `magic=0xFAB11BAF`, `version=106`)  
> - `com.adnc.okeymuhabbet.apk!/assets/bin/Data/data.unity3d` (`61.809.385` bayt sıkıştırılmış `UnityFS` v8 -> `244.994.501` bayt açılmış akış)  
> **Analiz Sağlayıcısı:** `rea` MCP + Normal Ghidra `12.1.4_PUBLIC` (`analyzeHeadless.bat -noanalysis`, `ImageBase = 0x00100000`)

---

## 1. Yönetici Özeti ve Önceki Raporlardaki Hatalı Varsayımların Düzeltilmesi

Depodaki önceki beş rapor (`SERVER-PROTOCOL-FINDINGS.md`, `AUTHENTICATION-ANALYSIS.md`, `ALTERNATIVE-CLIENT-FEASIBILITY.md`, `CLIENT-ARCHITECTURE-PROPOSAL.md`, `BLOCKERS-AND-REQUIREMENTS.md`) `global-metadata.dat` v106 formatı henüz çözülmediği için **yalnızca ham metin tablosu (string table) taramasına** dayanıyordu. Bu gerçeklik testinde Unity `6000.5.0f1` IL2CPP metadata v106 ikili tabloları (`81.948` metot sembolü, `393.220` `R_AARCH64_RELATIVE` relokasyon kaydı ve bit-kaydırmalı `(val & 0x1FFFFFFF) >> 1` `s_MetadataUsages` dizgi sabitleri) tam olarak çözülmüş ve 38 hedef fonksiyon Normal Ghidra `12.1.4` ile C sözde koduna decompile edilmiştir.

Önceki raporlarda yer alan **5 büyük yanılgı** bu çalışmada kanıtlarıyla düzeltilmiştir:

| # | Önceki Raporlardaki İddia / Varsayım | Gerçeklik Testi Bulgusu (`libil2cpp.so` + `data.unity3d`) | Kanıt Durumu |
|---|---|---|---|
| 1 | *"İstemci tüm oyun komutlarını Socket.IO üzerinden gönderir."* | **YANLIŞ.** `SuWebRequest.Emit(Data)` (`RVA 0x019C2C64`) isminde `Emit` geçmesine rağmen Socket.IO kullanmaz; `SuWebRequest.Send` (`RVA 0x019C5D88` -> `<Send>d__27.MoveNext @ RVA 0x019C6374`) üzerinden tüm komutları **`https://sistem.okeymuhabbet.com/?h=<MD5>&d=<JSON>` adresine HTTPS GET** olarak gönderir. Socket.IO (`ws://sistem.okeymuhabbet.com:4082`) yalnızca **sunucudan istemciye gerçek zamanlı olay itme (`'i'` olayı)** ve canlılık (`ping`/`pong`) için kullanılır. | `KANITLANDI` |
| 2 | *"`OyunMotoru.PackNameFinder` girişte Android paket adını (`com.adnc.okeymuhabbet`) doğrular."* | **YANLIŞ.** `OyunMotoru.PackNameFinder(key, sys)` (`RVA 0x01997F3C`, GhidraVA `0x01A97F3C`) `this->PackNames` listesindeki `key-sys-urun` dizgilerini `'-'` ile bölen bir mağaza paket arayıcısıdır ve `Assembly-CSharp.dll` içinde **hiçbir metottan çağrılmamaktadır (`0 caller`)**. | `KANITLANDI` |
| 3 | *"`MD5Hash` yalnızca MAC adresi özetlemek için kullanılır; istek imzalama yoktur."* | **YANLIŞ.** `OyunMotoru.MD5Hash` (`RVA 0x01996CA8`) toplam **17 çağrı noktasında** kullanılır. Bunların en kritiği `<Send>d__27.MoveNext` (`RVA 0x019C6374`) olup her HTTPS GET isteğinde `MD5(JSON + <16_KARAKTER_SABİT_TUZ>)` (`lit#1429`) hesaplayarak `?h=` parametresine yazar. Ayrıca `SuWebRequest.Emit` (`RVA 0x019C2C64`) istemci tarafında mükerrer tıklamayı engellemek için `MD5(JSON)` + `DateTime.UtcNow` kontrolü yapar. | `KANITLANDI` |
| 4 | *"Oturum anahtarları `UID` ve `TokenID` alanlarında tutulur; `AppVersiyon` ağ alanıdır."* | **YANLIŞ.** `AppVersiyon` bir ağ alanı değil, `Application.get_version()` değerini ekrana yazan bir UI sınıfıdır (`TypeDefinition[7392]`, `Start @ RVA 0x019DD10C`). `TokenID` yalnızca `SuNetwork.FireBaseToken(string TokenID)` (`Method[60166]`) parametre adıdır; `UID` ise `<ResimCek>d__299` coroutine alanıdır (`Field[29902]`). Gerçek oturum verileri `PlayerPrefs` içinde **`"id"`, `"kullanici"`, `"token_id"` ve `"session_id"`** (isteklerde `"_t"`) anahtarlarıyla saklanır. | `KANITLANDI` |
| 5 | *"`PerDiz` 101 Okey'deki gibi masaya seri açma komutudur; `OyunBitir` aktiftir."* | **YANLIŞ.** Oyun klasik 4 kişilik **Düz Okey**'dir (`stage4_live_game_screen/screen.png`, 28 yuvalı ıstaka). `SuNetwork.PerDiz(Tip)` (`RVA 0x019B8A50`, `masaseridiz-perdiz`) masaya el açmaz; sunucudan oyuncunun kendi ıstakasını `"Per"` veya `"Cift"` dizmesini ister (`resources.assets+0x6BC68C` ve `+0x75134C`). Eski `SuNetwork.OyunBitir` (`RVA 0x019B7A9C`) ölü koddur (`0 caller`); aktif bitirme metodu **`SuNetwork.OyunBitirBeta`** (`RVA 0x019B7BEC`, `masaoyunbitir-oyunbitirbeta`) olup hem normal bitişi hem **Okey ile bitmeyi** yürütür. | `KANITLANDI` |

---

## 2. Kanıt Sınıflandırma Standardı

Bu rapordaki ve bağlı üç teknik kanıt belgesindeki tüm iddialar aşağıdaki beş etiketle sınıflandırılmıştır:

- **`KANITLANDI`**: Doğrudan ikili kod (`libil2cpp.so` RVA / Ghidra C çıktısı), `global-metadata.dat` tablosu, `data.unity3d` sahne serileştirmesi veya `rea` MCP kanıt kimliğiyle kesin olarak doğrulandı.
- **`GÜÇLÜ İPUCU`**: İstemci tarafı kod/veri akışıyla yüksek tutarlılıkta doğrulandı ancak sunucu tarafı kaynak kodu görülmeden tek yönlü kanıta dayanıyor.
- **`TAHMİN`**: Sınırlı dolaylı veriye dayalı olasılık değerlendirmesi.
- **`BİLİNMİYOR`**: Statik analizle bilinemeyen, yalnızca canlı sunucu yanıtıyla görülebilecek davranış.
- **`ENGELLENDİ`**: Etik/yetki sınırları (üretim sunucusuna izinsiz istek göndermeme kuralı) veya fiziksel cihaz/PAIRIP kısıtları nedeniyle canlı olarak test edilemedi.

---

## 3. Bölüm Bazlı Teknik Araştırma Bulguları

### A. İletişim Protokolü Özeti (Detaylar: `SERVER-CONNECTION-EVIDENCE.md`)

1. **Asimetrik Çift Kanal Mimarisi (`KANITLANDI`):**
   - **İstemci -> Sunucu (Komut Kanalı):** Tüm oyun ve oturum komutları `SuWebRequest.Emit(JSONObject Data)` (`RVA 0x019C2C64`) üzerinden `SuWebRequest.Send` (`RVA 0x019C5D88`) -> `<Send>d__27.MoveNext` (`RVA 0x019C6374`) coroutine'ine aktarılır ve `UnityEngine.Networking.UnityWebRequest.Get` (`RVA 0x037BF180`) ile **HTTPS GET** olarak gönderilir.
   - **Sunucu -> İstemci (Gerçek Zamanlı İtme Kanalı):** `Firesplash.GameDevAssets.SocketIOPlus.dll` (`Il2CppCodeGenModule @ VA 0x37F5758`, `228` metot) üzerinden **Socket.IO v4 / Engine.IO v4** bağlantısı kurulur; sunucu anlık masa/oyun olaylarını `'i'` olay adıyla iter (`SuWebRequest.Start @ RVA 0x019C4BE0` -> `OnSocketGelen @ RVA 0x019C54AC`).
2. **Socket.IO ve Engine.IO Sürümleri (`KANITLANDI`):**
   - `EngineIO.Tranceiver.Connect` (`RVA 0x01ACF57C`, GhidraVA `0x01BCF57C`) sorgu parametrelerine sabit olarak `'EIO'` = `'4'` (`lit @ 0x3ABC998`, `0x3AB7738`) ve `'transport'` = `'websocket'` (`0x3AD3AA8`, `0x3AD4788`) ekler.
   - `SocketIONamespace.Submit` (`RVA 0x01ACA854`) ad alanı `CONNECT` (`40`) paketinde `'sid'` alanı bekler (`'Received connect packet without sid payload. This is a server-side protocol violation.'`), bu da **Socket.IO Protokol v5 (Socket.IO v4.x istemci/sunucu)** standardıdır.
3. **Taşıma Yöntemi (`KANITLANDI`):**
   - Gerçek zamanlı kanalda **yalnızca WebSocket** kullanılır (`NativeImplementation` / `Tranceiver` içinde HTTP long-polling taşıyıcısı yoktur). Komut kanalında ise **HTTPS GET** (`<Send>d__27.MoveNext`) aktiftir; `SuWebRequest.SendPost` (`RVA 0x019C5F34`, `WWWForm` ile `'d'` alanı) tanımlı olsa da `Assembly-CSharp.dll` içinde `0` çağrıcıya sahiptir.
4. **Sunucu Adresi ve Portlar (`KANITLANDI`):**
   - `data.unity3d` -> `level1` sahnesi ofset `0x504340` (`level1+0x7879`): `ws://sistem.okeymuhabbet.com:4082` (`SocketIOClient.serverAddress`, yol `/socket.io/` -> tam WS adresi: `ws://sistem.okeymuhabbet.com:4082/socket.io/?EIO=4&transport=websocket`).
   - `data.unity3d` -> `level1` sahnesi ofset `0x504880` (`level1+0x7DBC`): `https://sistem.okeymuhabbet.com/` (`SuWebRequest.url`).
5. **Gerçek JSON Zarf Yapısı (`KANITLANDI`):**
   - **Giden (HTTPS GET `?h=<md5>&d=<json>`):**
     - Giriş öncesi komutlar: `{"_e": "<modul>-<komut>", ...alanlar, "_t": "<varsa_session_id>"}`
     - Oturum içi komutlar: `{"_i": "<modul>-<komut>", ...alanlar, "_t": "<session_id>"}`
   - **Gelen (hem HTTPS yanıt gövdesi hem Socket.IO `'i'` olayı -> `SuWebRequest.Receive @ RVA 0x019C5614`):**
     - `{"s": [ {"i": "<OlayAdi>", "d": { ...veri... }} ]}` (`SuKuyrukPool @ RVA 0x019C5BD4` her karede `"s"` kuyruğundan `"i"` olay adını çekip `"d"` nesnesini ilgili `SuNetwork.On...` metoduna iletir).

---

### B. Misafir Oturumu Özeti (Detaylar: `AUTHENTICATION-FLOW-TRACE.md`)

1. **`giris-misafir` Akışının Durumu (`KANITLANDI` statik / `BİLİNMİYOR` canlı kabul):**
   - `SuNetwork.MisafirGirisi()` (`RVA 0x019B2B0C`) C# kodundan doğrudan `BL` ile çağrılmaz; ancak `data.unity3d` -> `resources.assets+0x70315C` (akış ofseti `0xC0951D`) konumunda bir Unity `Button` bileşenine (`m_Interactable = 1`, `m_CallState = 2 [RuntimeOnly]`, `m_MethodName = "MisafirGirisi"`) bağlıdır (`KANITLANDI`).
   - Buna karşılık üretim sunucusunun `v3.1.33` sürümünde `giris-misafir` isteğine aktif oturum verip vermediği ya da `MisafirGirisBildirim` / `GirisYapilamadi` ile kapatıp kapatmadığı canlı istek atılmadığı için doğrulanmamıştır (`ENGELLENDİ` / `BİLİNMİYOR`).
   - *Önemli Ayrım:* Kod tabanındaki `MisafirIcerik` (`RVA 0x01991984`) ve `MisafirKonusma` (`RVA 0x01991E7C`) sınıfları misafir girişiyle ilgili **değildir**; masadaki izleyicilerin Vivox sesli sohbet izinlerini (`'Allowed Guests'`, `'SesiAc'`, `'SesiKapat'`) yönetir (`KANITLANDI`).
2. **Gönderilen Parametreler ve Beklenen Yanıt (`KANITLANDI`):**
   - `SuNetwork.MisafirGirisi()` (`RVA 0x019B2B0C`): `'LoadingMini'` panelini açar ve `{"token_id": PlayerPrefs["token_id"], "device_id": Login.Instance.GameUniqueID, "machash": MD5Hash(MacAddressBul()), "_e": "giris-misafir"}` nesnesini `SuWebRequest.Emit` ile gönderir.
   - `SuNetwork.OnMisafirGirisi(data)` (`RVA 0x019B2CE8`) ve `SuNetwork.OnGirisYapildi(data)` (`RVA 0x019B1C24`): Sunucudan gelen `data` içinden `"id"`, `"kullanici"`, `"token_id"` ve `"session_id"` alanlarını okuyup `PlayerPrefs.SetString` + `PlayerPrefs.Save` ile kalıcı olarak kaydeder.
3. **`GameUniqueID` ve MAC Adresi Kullanımı (`KANITLANDI`):**
   - `Login.Instance.GameUniqueID` (`Field[29220]`): `Login.Awake` (`RVA 0x0197F0D4`) içinde `SystemInfo.deviceUniqueIdentifier` (`RVA 0x034F8488`) ile doldurulur.
   - `SuNetwork.MacAddressBul()` (`RVA 0x019B1158`): `NetworkInterface.GetAllNetworkInterfaces()` (`RVA 0x02FED3A0`) üzerinden ağ arayüzü fiziksel adresini alır, `MD5Hash` ile özetlenerek `"machash"` alanı olarak çoklu hesap tespiti (`LoginDetectAccount @ RVA 0x019B0FE4`) ve cihaz eşleştirmesi için gönderilir. (Not: Modern Android 11+ / SDK 36'da `GetAllNetworkInterfaces` donanım MAC adresini kısıtladığından boş/sabit değer dönebilir — `GÜÇLÜ İPUCU`.)

---

### C. Sunucu Kontrolleri Özeti (Detaylar: `AUTHENTICATION-FLOW-TRACE.md`)

1. **`PackNameFinder` (`KANITLANDI`):** Giriş akışında **kullanılmaz** (`0 caller`); mağaza paket adı ayrıştırıcısıdır (`RVA 0x01997F3C`).
2. **Sürüm Kontrolü (`KANITLANDI`):** Sunucu `'VersiyonKontrol'` olayı gönderdiğinde `SuNetwork.OnVersiyonKontrol` (`RVA 0x019B0E70`) yanıt olarak `{"Versiyon": Application.version, "os": "ANDROID", "_i": "versiyonkontrol-versiyonkontrol"}` gönderir (`3.1.33`). Uyumsuz sürümde sunucu `'OyunuGuncelle'` veya `'VersiyonMesaj'` (`OnVersiyonMesaj @ RVA 0x019BEB74`) tetikleyebilir (`GÜÇLÜ İPUCU`).
3. **İstek İmzası ve El Sıkışma Kontrolü (`KANITLANDI`):**
   - **HTTPS GET İmzası:** `<Send>d__27.MoveNext` (`RVA 0x019C6374`) her giden JSON dizgisinin sonuna APK içine gömülü **16 karakterlik sabit tuzu (`lit#1429`, güvenlik gereği `<REDACTED_16CHAR_STATIC_SALT>`)** ekleyip `OyunMotoru.MD5Hash` alır ve `?h=<md5>&d=<json>` olarak gönderir.
   - **Socket.IO Ad Alanı Kimlik Doğrulaması:** `SuWebRequest.Callback` (`RVA 0x019C5090`) Socket.IO `/` ad alanına bağlanırken oyuncu `"id"` değerini ve **10 karakterlik sabit el sıkışma dizgisini (`lit#399`, `<REDACTED_10CHAR_HANDSHAKE_SECRET>`)** gönderir.
   - **Play Integrity / APK Sertifika Kontrolü Yokluğu:** DEX (`ev_bce20d9021b7e540...`), `ScriptingAssemblies.json` ve `libil2cpp.so` ağ metotlarında Play Integrity, SafetyNet, Firebase App Check veya APK imza özeti gönderimi **yoktur** (`KANITLANDI`). PAIRIP (`libpairipcore.so`) tamamen yerel APK başlatma kilididir; oyun sunucusuyla konuşmaz (`KANITLANDI`).

---

### D. Oyun İşlemleri ve Doğrulama Sınırları

Aşağıdaki tablo altı temel oyun işleminin istemci-sunucu akışını ve doğrulama sınırlarını özetler:

| İşlem | İstemci Metodu & RVA | İstemcinin Gönderdiği Veri (`HTTPS GET ?h=...&d=...`) | Sunucu Yanıt / İtme Olayı (`"i"`) | İstemci vs Sunucu Doğrulama Ayrımı | Kanıt |
|---|---|---|---|---|---|
| **1. Taş Çekme** | `SuNetwork.TasCek` (`0x019B8DD0`) <- `Masa.TasHareketleri` (`0x019FE61C`) | `{"tip": "o" \| "m", "dc": "1" \| "0", "_i": "masatascek-tascek", "_t": session_id}` (`"o"`=orta deste, `"m"`=yandan atılan taş) | `"TasCek"` -> `OnTasCek` (`0x019B8F9C`) -> `Masa.TasCek` (`0x01A02C7C`): `tas`, `yon`, `tip`, `kt`, `tc`, `dc`, `cl` | İstemci yalnızca nereden çekmek istediğini (`o`/`m`) bildirir; **hangi taşın çekildiğini (`tas`), sıra uygunluğunu ve kalan taş sayısını (`kt`) sunucu belirler ve doğrular.** | `KANITLANDI` |
| **2. Taş Atma** | `SuNetwork.TasAt` (`0x019B8B6C`) <- `Masa.TasHareketleri` (`0x019FE61C`) | `{"tas": TasAdi, "gon": "1", "_i": "masatasat-tasat", "_t": session_id}` | `"TasAt"` -> `OnTasAt` (`0x019B8D18`) -> `Masa.TasAt` (`0x01A02728`): `tas`, `yon`, `ms`, `tc`, `cl` + `SiraGeldi` | İstemci atılan taşın kimliğini (`tas`) gönderir; **oyuncunun elinde bu taşın gerçekten bulunup bulunmadığını ve sıranın o oyuncuda olduğunu sunucu doğrular** (`GÜÇLÜ İPUCU` sunucu kontrolü, `KANITLANDI` istemci yükü). | `KANITLANDI` |
| **3. Seri Açma / Istaka Dizme** | `SuNetwork.PerDiz` (`0x019B8A50`) (`resources.assets` `"Per"` / `"Cift"` butonları) | `{"tip": Tip, "_i": "masaseridiz-perdiz", "_t": session_id}` | `"PerDiz"` -> `OnPerDiz` (`0x019B9648`) -> `Masa.PerDiz` (`0x01A03B4C`): `"Taslar"` sözlüğü (`IstakaSlot` eşlemesi) | Oyun klasik **Düz Okey** olduğundan 101 Okey tarzı masaya seri açma yoktur (`KANITLANDI`). Oyuncu tur içinde ıstakasını tamamen yerel olarak dizebildiği gibi (`MasaPerHesaplayici`), `masaseridiz-perdiz` ile sunucudan da otomatik seri/çift dizilim isteyebilir. | `KANITLANDI` |
| **4. Çift Açma / Çifte Gitme** | `SuNetwork.CifteGit` (`0x019C1D4C`) (`resources.assets+0x72BCC8`) | `{"_i": "masacift-ciftegit", "_t": session_id}` | `"CifteGit"` (`OnCifteGit @ 0x019C1E20`) ve `"CiftAc"` (`OnCiftAc @ 0x019B910C` -> `Masa.TaslarYerine`) | Klasik Okey'de "Çifte Git" ilanı (`masacift-ciftegit`) hiç taş dizisi göndermeden yalnızca niyet bildirir; uygun tur/zaman penceresini sunucu kontrol eder (`GÜÇLÜ İPUCU`). | `KANITLANDI` |
| **5. Oyun Bitirme** | `Masa.OyunBitir` (`0x019FF938`) -> `SuNetwork.OyunBitirBeta` (`0x019B7BEC`) | `{"taslar": TasListe, "bitentas": tas, "_i": "masaoyunbitir-oyunbitirbeta", "_t": session_id}` (`TasListe`: 28 ıstaka yuvasının `'-'` ve `'Bos'` ile birleştirilmiş tam dizilimi) | Başarılıysa `"OyunBitir"` (`0x019BA3B0`) / `"OyunBitirTurnuva"` (`0x019BA6AC`); geçersizse `"OyunBitirHata"` (`0x019BA8D4`, `data["hata"]`) | İstemci 28 yuvalık ıstaka dizilimini ve atılan bitiş taşını gönderir; **dizilimin geçerli per/çift oluşturup oluşturmadığını sunucu doğrular ve hatalıysa `"OyunBitirHata"` döndürür (`KANITLANDI`).** (Not: Eski `SuNetwork.OyunBitir @ 0x019B7A9C` çağrılmaz.) | `KANITLANDI` |
| **6. Okey ile Bitme** | `Masa.TasHareketleri` (`0x019FEEB8` -> `OkeyBitis` bırakma alanı) -> `Masa.OyunBitir` (`0x019FF938`) -> `SuNetwork.OyunBitirBeta` (`0x019B7BEC`) | Ayrı bir komut adı yoktur; aynı `masaoyunbitir-oyunbitirbeta` komutunda `"bitentas"` olarak aktif Okey taşının kimliği ve `"taslar"` olarak kalan 14 taşın geçerli ıstaka dizilimi gönderilir. | `"OyunBitir"` / `"OyunBitirTurnuva"` veya `"OyunBitirHata"` | `'OkeyBitis'` (`GameObject.Find("OkeyBitis")` @ `0x01A08F78`, `0x01A02C7C`) sahnedeki gösterge bırakma nesnesidir. Bitişin "Okey ile bitiş" çarpanı taşıyıp taşımadığını `bitentas == OkeyTas` kontrolüyle **sunucu hesaplar** (`KANITLANDI` istemci akışı / `GÜÇLÜ İPUCU` sunucu puanlaması). | `KANITLANDI` |

---

## 4. Gözlem, Çıkarım ve Bilinmeyenlerin Kesin Ayrımı

### Doğrulanmış Gözlemler (Observations — `KANITLANDI`)
1. `libil2cpp.so` içindeki tüm ağ istemcisi `https://sistem.okeymuhabbet.com/` (HTTPS GET, MD5 tuz imzalı) ve `ws://sistem.okeymuhabbet.com:4082/socket.io/?EIO=4&transport=websocket` (Socket.IO v4 anlık olay kanalı) uç noktaları üzerinden JSON zarflarıyla çalışmaktadır.
2. Ağ katmanında Google Play Integrity, SafetyNet, Firebase App Check, mTLS istemci sertifikası veya Android paket/imza doğrulaması bulunmamaktadır; PAIRIP (`libpairipcore.so`) yalnızca orijinal APK ikilisinin yerel açılış kontrolüdür.
3. **Akıllı Diz** (yerel `MasaPerHesaplayici` mantığı + 28 yuvalı ıstaka yönetimi) ve **Okey ile Bit** (`masaoyunbitir-oyunbitirbeta` içinde Okey taşını `bitentas` olarak gönderip kalan 14 taşı `taslar` diziliminde sunma) mevcut sunucu protokolüyle %100 uyumludur.

### Teknik Çıkarımlar (Inferences — `GÜÇLÜ İPUCU`)
1. Sunucu taş dağıtımı, taş çekme sonucu (`tas`) ve el bitirme doğrulaması (`OyunBitir` vs `OyunBitirHata`) konularında tam otoriterdir (server-authoritative); dolayısıyla alternatif istemci hile/kural dışı taş üretemez, ancak kullanıcının elindeki gerçek taşları optimal dizip (`Akıllı Diz`) geçerli el oluştuğunda tek dokunuşla bitirebilir (`Okey ile Bit`).
2. İstek imzalama tuzu (`lit#1429`) ve Socket.IO el sıkışma dizgisi (`lit#399`) APK içinde sabit olduğundan teknik olarak bir protokol engeli oluşturmaz; ancak sunucu sahibinin (ADNC / Manc Games) izni olmadan üçüncü taraf istemcide kullanılması kullanım koşulları (ToS) ve yetkilendirme sorunu doğurur.

### Bilinmeyenler ve Canlı Doğrulama Engelleri (`BİLİNMİYOR` / `ENGELLENDİ`)
1. Üretim sunucusunun `giris-misafir` (`_e: "giris-misafir"`) isteğini şu an aktif olarak kabul edip etmediği (`ENGELLENDİ` — canlı sunucuya izinsiz istek gönderilmedi).
2. Sosyal girişlerin (Google Play Games `LoginGoogle @ RVA 0x0197F168`, Facebook `FacebookGiris @ RVA 0x0197E6BC`) paket adı / SHA-1 sertifika kısıtı nedeniyle resmi imza olmadan bağımsız bir Android paketinden (`com.alternatif...`) OAuth token alıp alamayacağı (`GÜÇLÜ İPUCU`: Google/Facebook OAuth sağlayıcıları paket adı + imza SHA-1 eşleşmesi zorunlu tutar).
3. Canlı oyunda taş kimliklerinin (`TasAdi`, örn. `IstakayiGuncelle` içindeki `"t"` dizisi ve `MasaPerHesaplayici.IsOkeyTile` içindeki `'106'`, `'53'`, `'o'` referansları) tam tel (wire) formatı (`1..106` sayısal dizgi formatı `GÜÇLÜ İPUCU`, ancak tüm renk/sahte okey/aktif okey varyasyonlarının canlı paket kaydı `BİLİNMİYOR`).

---

## 5. Bağlı Raporlar

- Sunucu bağlantı kanıtları, çerçeveleme ve tam protokol şemaları: [`SERVER-CONNECTION-EVIDENCE.md`](./SERVER-CONNECTION-EVIDENCE.md)
- Kimlik doğrulama, misafir girişi ve sunucu kontrolleri izi: [`AUTHENTICATION-FLOW-TRACE.md`](./AUTHENTICATION-FLOW-TRACE.md)
- Nihai karar ve eksik canlı kanıtları kapatma planı: [`GO-NO-GO-DECISION.md`](./GO-NO-GO-DECISION.md)
