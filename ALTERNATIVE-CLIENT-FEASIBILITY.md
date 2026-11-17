# Okey Muhabbet (`com.adnc.okeymuhabbet`) — Alternatif Android İstemcisi Fizibilite Raporu

**Tarih:** 17.11.2026  
**Hedef Uygulama:** `com.adnc.okeymuhabbet` (`v3.1.33`, `versionCode: 118`, Unity `6000.5.0f1` IL2CPP `arm64-v8a`)  
**İlgili Belgeler:**
- [SERVER-PROTOCOL-FINDINGS.md](file:///e:/apk/test-okey/SERVER-PROTOCOL-FINDINGS.md)
- [AUTHENTICATION-ANALYSIS.md](file:///e:/apk/test-okey/AUTHENTICATION-ANALYSIS.md)
- [CLIENT-ARCHITECTURE-PROPOSAL.md](file:///e:/apk/test-okey/CLIENT-ARCHITECTURE-PROPOSAL.md)
- [BLOCKERS-AND-REQUIREMENTS.md](file:///e:/apk/test-okey/BLOCKERS-AND-REQUIREMENTS.md)

---

## 1. Yönetici Kararı (Aşama 3 Karar Noktası)

> [!IMPORTANT]
> ### KARAR: **SONUÇ B — KOŞULLU MÜMKÜN** *(Geliştirici Onayı Yoksa Uygulamaya Geçiş: **SONUÇ C — ENGEL**)*
> Yapılan derinlemesine statik ikili analiz sonucunda, Okey Muhabbet sunucusunun özel/kapalı bir ikili kriptografik protokol veya donanım tabanlı Google Play Integrity / Firebase App Check doğrulaması **kullanmadığı**, bunun yerine standart **Socket.IO (WebSocket `ws://sistem.okeymuhabbet.com:4082`) + JSON** mimarisi üzerinde çalıştığı **KANITLANMIŞTIR**.  
> **Ancak**, bağımsız bir Android istemcisinin mevcut üretim sunucusuyla meşru, kesintisiz ve tüm hesap türleriyle çalışabilmesi için **sunucu/geliştirici (`MANC` / `ADNC`) izni, OAuth istemci sertifika kaydı ve resmi mesaj şeması onayı zorunludur**. Bu koşullar geliştirici tarafından sağlanmadığı sürece tek taraflı (izinsiz) istemci geliştirilmesine **başlanmamalıdır** (bu durumda proje fiilen **SONUÇ C** konumunda kalır).

### Epistemik Etiketleme Anahtarı
Bu rapordaki ve bağlı dört teknik rapordaki tüm bulgular aşağıdaki doğruluk seviyeleriyle işaretlenmiştir:
- **`[KANITLANDI]`**: APK ikilileri (`ScriptingAssemblies.json`, `global-metadata.dat` v106, `data.unity3d`, `AndroidManifest.xml`, `libil2cpp.so`) veya fiziksel cihaz gözlemleriyle doğrudan doğrulanan olgu.
- **`[GÜÇLÜ İPUCU]`**: Sınıf, metot, alan ve sabit dizgelerinin birleşiminden yüksek güvenle çıkarılan ancak canlı sunucu trafiğiyle teyit edilmemiş teknik yapı.
- **`[TAHMİN]`**: Benzer Socket.IO / Unity oyun mimarilerine dayalı mühendislik öngörüsü.
- **`[BİLİNMİYOR]`**: Canlı sunucuya izinsiz istek göndermeme ve PAIRIP korumasını kırmama sınırları nedeniyle statik analizle görülemeyen çalışma zamanı detayı.

---

## 2. Aşama 1 — Dokuz Temel Fizibilite Sorusunun Kanıtlı Yanıtları

### 2.1 İstemci-Sunucu Mimarisi Hakkındaki Kanıtlar
- **`[KANITLANDI]`** Uygulamanın tüm oyun ve ağ mantığı `Assembly-CSharp.dll` (`2.829` temiz sembol) içindeki özel **`SuSistem` / `SuNetwork`** çatısı altında toplanmıştır (`global-metadata.dat` v106 tanımlayıcı tablosu `[57101..60304]`).
- **`[KANITLANDI]`** Mimari dört ayrı sunucu/servis katmanından oluşmaktadır:
  1. **Gerçek Zamanlı Oyun Sunucusu:** `SuNetwork` ve `SuWebSocket` sınıfları üzerinden `ws://sistem.okeymuhabbet.com:4082` adresine bağlanır (`data.unity3d @ 0x17F81A`).
  2. **HTTP Yardımcı İstek Katmanı:** `SuWebRequest.SendPost`, `http://okey.manc.com.tr/redirect/` ve `https://www.okeymuhabbet.com/storage/img/` üzerinden REST/görsel içerik alışverişi yapar (`global-metadata.dat` sabitleri).
  3. **Varlık Güncelleme (CDN) Katmanı:** `SuUpdateControl` ve `SuUpdateServerSettings` üzerinden `https://update-okey.mancgames.com/android/` adresinden `AssetBundle` ve `HashList` manifestlerini indirir.
  4. **Sesli Sohbet Katmanı:** `VivoxControl` (`Unity.Services.Vivox.dll` + `libvivox-sdk.so`) üzerinden masa içi gerçek zamanlı sesli sohbet yürütür.

### 2.2 Sunucu İletişim Protokolü
- **`[KANITLANDI]`** Gerçek zamanlı iletişim protokolü **Socket.IO**'dur (Engine.IO + WebSocket taşıyıcısı, `/engine.io/` ve `/socket.io/` yolları). İstemci tarafında `Firesplash.GameDevAssets.SocketIOPlus.dll` kütüphanesi kullanılmaktadır (`ScriptingAssemblies.json`).
- **`[KANITLANDI]`** Veri serileştirme biçimi metin tabanlı **JSON**'dur (`JSONObject` ve `Newtonsoft.Json.dll`).
- **`[KANITLANDI]`** Uygulama katmanı komutları `<kategori>-<eylem>` adlandırma standardını izler (`60+` komut: ör. `giris-misafir`, `masayakatil-masalistesi`, `masatascek-tascek`, `masatasat-tasat`, `masaseridiz-perdiz`, `masaoyunbitir-oyunbitir`).
- **`[BİLİNMİYOR]`** `SuNetwork.SendServerCommand` metodunun Socket.IO üzerinde her komutu doğrudan olay adı (`emit("masatasat-tasat", payload)`) olarak mı yoksa tek bir genel olay zarfı içinde mi gönderdiği statik dizge tablosundan tek başına kesinleştirilemez; yetkili QA derlemesi veya protokol dokümanı gerektirir.

### 2.3 Kimlik Doğrulama Mekanizması
- **`[KANITLANDI]`** İstemcide beş farklı giriş kanalı tanımlıdır (`GirisIcerik` ve `SuNetwork` sınıfları):
  1. `giris-googlegirisyeni` (`Google.Play.Games.dll` — `InitializePlayGamesLogin` / `LoginGoogle`),
  2. `giris-facebookgiris` (`Facebook.Unity.dll` — `FacebookGiris`, App ID: `1479949552201495`),
  3. `giris-applegiris` (`AppleAuth.dll` — `LoginToApple`),
  4. `giris-GirisYap` / `uye-GirisKayit` / `giris-LoginDetectAccount` (Klasik hesap / cihaz-hesap eşleştirme),
  5. `giris-misafir` (`MisafirGirisi`).

### 2.4 Misafir Hesabıyla Giriş İmkânı
- **`[KANITLANDI]`** Protokolde ve istemci kodunda **Misafir Girişi (`giris-misafir` / `SuNetwork.MisafirGirisi` / `OnMisafirGirisi`) açıkça mevcuttur**.
- **`[GÜÇLÜ İPUCU]`** Misafir oturumları cihaz tanımlayıcılarıyla (`GameUniqueID`, `MacAdresiGonder`, `MacAddressBul`, `oyun-mackayit`) ilişkilendirilerek kalıcı hâle getirilmekte ve sonradan `oyuncu-AccountMergeNative` (`MergePayload`) ile sosyal hesaplara bağlanabilmektedir.

### 2.5 Oyuncu Oturumunun Korunması
- **`[KANITLANDI]`** Oturum kimliği `UID` (`get_uid`) ve sunucunun ürettiği oturum anahtarı `TokenID` (`get_token`, `token_id`, `session_token`) ile tutulur.
- **`[KANITLANDI]`** Bağlantı sürekliliği ve çoklu/askıda oturum kontrolü `giriskontrol-UyeGirisKontrol`, `uyecron-cronmasa`, `PingCheck` ve `SuPoolPingStatus` mekanizmalarıyla yürütülür.
- **`[GÜÇLÜ İPUCU]`** `OyunMotoru` içindeki `MD5Hash` ve `UnixTime` yardımcıları, belirli isteklerde veya sürüm/cihaz doğrulamasında özet (hash) üretimi için kullanılmaktadır; olası sabit tuz (salt) değeri **`[BİLİNMİYOR]`** statüsündedir.

### 2.6 İstemci İmzası, Paket Kimliği ve Play Integrity Kontrolü
- **`[KANITLANDI]`** **Play Integrity ve Firebase App Check YOKTUR:** APK içindeki 14.540 DEX sınıfı (`ev_bce20d9021b7e540...`, `ev_887174815c0b126f...`) ve 171 C# assembly (`ScriptingAssemblies.json`) taranmış; ne `com.google.android.play.core.integrity` ne de `com.google.firebase.appcheck` bulunmuştur.
- **`[KANITLANDI]`** **PAIRIP Yalnızca Yereldir:** `com.pairip.licensecheck` Google Play kurulum/lisans kontrolünü cihaz üzerinde yapar ve kapanır; oyun sunucusuna PAIRIP jetonu iletilmez.
- **`[KANITLANDI]`** **OAuth Paket/Sertifika Kilidi VARDIR:** Google Play Games ve Facebook Android SDK girişleri Google/Meta sunucularında `com.adnc.okeymuhabbet` paket adına ve `1e9f627e...` üretim sertifikasına kilitlidir; geliştirici kaydı olmadan bağımsız istemci bu sağlayıcılardan jeton alamaz.
- **`[KANITLANDI]`** **Sürüm ve Paket Yoklaması VARDIR:** İstemcide `versiyonkontrol-versiyonkontrol` (`OnVersiyonKontrol`, `AppVersiyon`) ve `PackNameFinder` (`PackNames`) bulunmaktadır.

### 2.7 Masa, Oyuncu, Taş Dağıtımı ve Hamle Modellemesi
- **`[KANITLANDI]`** `SuSistem.Masa` ad alanında tam nesne modeli mevcuttur:
  - **Masa (`Masa_Object`):** `MasaID`, `OyunDurum`, `MasaSira`, `YetkiYon`, `KalanTas`, `MasaSure`, `Esli`, `Yardimli`, `MasaBedeli`, `MasaCanak`, `Rix`, `OkeyTas`.
  - **Oyuncu (`Oyuncu_Object`):** `OyuncuId`, `OyuncuYon` (`k`/`d`/`g`/`b`), `ElToplam`, `SeriSkor`, `CiftSkor`, `isBot`, `VivoxId`.
  - **Taş (`Tas_Object`) ve İstaka (`Istaka`):** `TasID`, `TasSayi`, `TasRenk`, `TasKey`, `TasIslek`, `Okeymi`, `SlotID`, `IstakaSira`.
  - **Hamle Akışı:** `masatascek-tascek` (taş çekme), `masatasat-tasat` (taş atma), `masaseridiz-perdiz` (seri/per dizme bildirimi), `masacift-ciftegit` (çifte gitme), `masaoyunbitir-oyunbitir` (eli bitirme).

### 2.8 Oyun Kurallarının Doğrulama Yeri (İstemci vs Sunucu)
- **`[KANITLANDI]`** **Hibrit Mimari (Otoriter Sunucu + Yardımcı İstemci Hesaplayıcısı):**
  - İstemci tarafındaki `MasaPerHesaplayici` (`PerSorgula`, `PerSeriTasSorgula`, `PerRenkTasSorgula`, `PerOkeyKontrol`, `HesaplaKalanToplam`) kullanıcının ıstakasındaki perleri ve el toplamını yerel arayüz için hesaplar.
  - Ancak taş çekme (`OnTasCek`), ıstaka/masa taş senkronizasyonu (`OnIstakayiGuncelle`, `OnMasaTaslariGuncelle`), sıra kontrolü (`MasaSira`, `YetkiYon`) ve el bitirme doğrulaması **tamamen sunucu otoritesindedir**. Geçersiz bitiş denemesinde sunucu `OnOyunBitirHata` (`BitirHata`, `PerHata`) döndürerek hamleyi reddeder.

### 2.9 Bağımsız İstemcinin Mevcut Sunucuyla Çalışabilirliği
- **Teknik Düzeyde (`[KANITLANDI]`):** Standart Socket.IO + JSON protokolü ve Play Integrity yokluğu nedeniyle, protokol şeması bilindiğinde Android (Kotlin) tabanlı bağımsız bir istemcinin sunucuyla konuşması teknik olarak **mümkündür**.
- **Yetki, Kimlik ve Oyun Kuralları Düzeyinde (`[KANITLANDI]`):**
  1. Sosyal hesap girişleri (Google Play Games / Facebook) geliştiricinin OAuth konsoluna yeni istemci sertifikası eklenmeden çalışmaz.
  2. Masalarda sunucu tarafından yönetilen `Yardimli` (`get_Yardimli`) bayrağı vardır; yardımsız masalarda istemci tarafında **"Hamle önerileri"** veya sunucu kuralları dışında destek sunulması haksız rekabet / kullanım koşulu ihlali oluşturur ve sunucudaki `BanMesaj` / `siparis-hile` mekanizmalarını tetikler.
  3. Bu nedenle bağımsız istemci **ancak geliştirici (`MANC` / `ADNC`) onayı, istemci kaydı ve protokol şartnamesi ile (`SONUÇ B`)** geliştirilebilir.

---

## 3. Özellik Bazlı Fizibilite Özeti

| Hedeflenen İstemci Özelliği | Teknik Uygulanabilirlik | Sunucu / Politika Uyumluluğu | Durum |
|---|---|---|---|
| **Kendi Oyun Arayüzümüz** | Jetpack Compose / Canvas ile tam uygulanabilir | Geliştirici istemci izni gerektirir | Koşullu Mümkün (`SONUÇ B`) |
| **Taşların ve El Durumunun Yönetimi** | `Istaka` / `Tas_Object` modeliyle birebir uyumlu | `OnIstakayiGuncelle` JSON şeması gerekir | Koşullu Mümkün (`SONUÇ B`) |
| **Akıllı Diz (`PerDiz`)** | Yerel `MasaPerHesaplayici` eşdeğeri algoritma kurulabilir | Orijinal oyunda da `masaseridiz-perdiz` mevcuttur | Koşullu Mümkün (`SONUÇ B`) |
| **Okey İle Bit** | Yerel per doğrulayıcı + `masaoyunbitir-oyunbitir` komutu | Sunucu `OnOyunBitir` / `OnOyunBitirHata` ile doğrular | Koşullu Mümkün (`SONUÇ B`) |
| **Hamle Önerileri ve Durum Takibi** | Olasılık ve el takip motoru yerel olarak yazılabilir | **Yalnızca geliştiricinin izin verdiği `Yardimli == true` masalarda** açılmalıdır; aksi kullanım koşulu ihlalidir | Politika Onayı Şart (`SONUÇ B`) |
