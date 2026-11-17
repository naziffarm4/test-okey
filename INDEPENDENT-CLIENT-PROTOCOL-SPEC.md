# INDEPENDENT CLIENT PROTOCOL SPECIFICATION — OKEY MUHABBET (`v3.1.33`)

- **Tarih:** 2026-11-17
- **Başlangıç `main` Commit SHA:** `d0687710adf4fd669ebbfc7f2d7d553a73a345b5`
- **Kapsam:** Bağımsız Android istemcisinin Okey Muhabbet sunucusuyla konuşabilmesi için gereken çift kanallı protokol şartnamesi.
- **Gizlilik ve Yetki İlkesi:** Uygulamaya özel sabit tuz/el sıkışma değerleri bu şartnamede açık metin olarak **yayınlanmamıştır** (`<REDACTED_...>`). Bu değerlerin bağımsız bir istemcide üretim sunucusuna karşı kullanılabilmesi için **geliştirici / sunucu sahibi (`ADNC` / `Manc Games`) yazılı izni ZORUNLUDUR**. Eksik veya canlıda görülmemiş hiçbir JSON alanı tahminle doldurulmamıştır.

---

## 1. HTTPS Komut Kanalı İstek Oluşturma ve JSON Zarf Yapısı

### 1.1 Taşıma ve Uç Nokta (`KANITLANDI`)
- **Temel URL:** `https://sistem.okeymuhabbet.com/` (`SuWebRequest.url @ level1+0x7DBC`)
- **HTTP Metodu:** `GET` (`<Send>d__27.MoveNext @ RVA 0x019C6374` -> `UnityWebRequest.Get`). `SendPost` (`RVA 0x019C5F34`) kodda bulunsa da `0` çağrıcıya sahiptir.
- **Sorgu Yapısı:** `GET /?h=<32_hex_kucuk_harf_md5>&d=<url_encoded_json>`

### 1.2 İstek Zarf Alanları ve Sınıflandırması

| Alan Adı | Konum | Tür | Açıklama ve İkili Kanıt | Sınıflandırma |
|---|---|---|---|---|
| `h` | URL Query | `string` (32 hex) | `MD5(d_raw_json + <APP_STATIC_16CHAR_SALT>)` (`RVA 0x019C6374`, `OyunMotoru.MD5Hash @ RVA 0x01996CA8`). | **`KANITLANDI`** |
| `d` | URL Query | `string` (JSON) | Komut parametrelerini ve yönlendirme anahtarını taşıyan JSON nesnesi. | **`KANITLANDI`** |
| `_e` | `d` JSON içi | `string` | Oturum açma öncesi kimlik doğrulama komutu yönlendiricisi (örn. `"giris-misafir"`, `"giris-GirisYap"`). | **`KANITLANDI`** |
| `_i` | `d` JSON içi | `string` | Oturum içi modül-eylem yönlendiricisi (`"<modul>-<eylem>"`, örn. `"masatascek-tascek"`). | **`KANITLANDI`** |
| `_t` | `d` JSON içi | `string` | `PlayerPrefs["session_id"]` mevcutsa `<Send>d__27.MoveNext` tarafından otomatik eklenen aktif oturum bileti. | **`KANITLANDI`** |
| *(Sunucu HTTP Başlık Kontrolleri)* | HTTP Header | — | Sunucunun `User-Agent` veya özel bir HTTP başlığı bekleyip beklemediği (istemci ek özel başlık set etmez). | İstemci: **`KANITLANDI`** / Sunucu WAF: **`BİLİNMİYOR`** |

### 1.3 Mükerrer İstek Engeli ve İmzalama Gereksinimleri (`KANITLANDI`)
1. **Mükerrer Gönderim Kilidi (`SuWebRequest::Emit @ RVA 0x019C2C64`):** Son gönderilen JSON metninin `MD5` özeti aynıysa ve `lastTime + 1 < utcNowSeconds` koşulu sağlanmıyorsa istek gönderilmez (`live-test/src/http/probe.py::DuplicateGuard`).
2. **İmza Tuzu Yetki Gereksinimi:** `<Send>d__27.MoveNext` içinde kullanılan 16 karakterlik sabit tuz (`lit#1429`) uygulamaya özel paylaşımlı sırdır. **Bağımsız istemcide bu tuzun kullanılması veya alternatif bir istemci anahtarı tanımlanması için geliştirici izni şarttır.**

---

## 2. Yanıt Ayrıştırma ve Sunucu Olay Yönlendirmesi

### 2.1 Birleşik Sunucu Zarfı (`SuWebRequest::Receive @ RVA 0x019C5614` — `KANITLANDI`)
Hem HTTPS GET yanıt gövdesi hem de Socket.IO `'i'` olayı aynı ayrıştırıcıya girer:
1. Gelen dizgedeki ters eğik çizgiler temizlenir (`raw.replace("\\", "")`).
2. Kök JSON nesnesindeki `"s"` dizisi okunur; her eleman `{"i": "<OlayAdi>", "d": <JSONObject>}` biçimindedir:

| Zarf Alanı | Tür | Açıklama | Sınıflandırma |
|---|---|---|---|
| `s` | `Array<Object>` | Sunucunun tek yanıtta sıralı gönderdiği olay paketi listesi (`lit#15180`). | **`KANITLANDI`** |
| `s[].i` | `string` | `SuNetwork.Start @ RVA 0x019ABDB0` içindeki `120+` olay tablosuyla eşleşen olay anahtarı (`lit#13546`). | **`KANITLANDI`** |
| `s[].d` | `Object` | İlgili `On<OlayAdi>(JSONObject data)` işleyicisine aktarılan olay verisi (`lit#12483`). | **`KANITLANDI`** |

3. Öğeler FIFO kuyruğuna (`SuKuyrukPool @ RVA 0x019C5BD4`, `this+0x38`) alınır ve ana iş parçacığında sırayla çalıştırılır.

---

## 3. Socket.IO Bağlantı Yaşam Döngüsü ve Oturum İlişkilendirmesi

### 3.1 Bağlantı ve El Sıkışma Akışı (`KANITLANDI`)
1. **URI:** `ws://sistem.okeymuhabbet.com:4082/socket.io/?EIO=4&transport=websocket` (`Tranceiver.Connect @ RVA 0x01ACF57C`, `SocketIOClient.Awake @ RVA 0x01AC8848`). Açık metin (`ws://`) olduğu için Android 9+ cihazlarda `network_security_config.xml` içinde `sistem.okeymuhabbet.com` için `cleartextTrafficPermitted="true"` tanımlanmalıdır.
2. **Engine.IO v4 Açılışı:** Sunucudan `0{"sid":"...","upgrades":[],"pingInterval":...,"pingTimeout":...}` alınır (üretim sunucusunun canlı `pingInterval`/`pingTimeout` sayısal değerleri **`ENGELLENDİ` / `BİLİNMİYOR`**).
3. **Oturum–Soket İlişkilendirmesi (`SuWebRequest::Callback @ RVA 0x019C5090`):**
   - HTTPS girişinden (`OnMisafirGirisi` / `OnGirisYapildi`) alınan oyuncu `"id"` değeri ve 10 karakterlik sabit el sıkışma dizgisi (`lit#399`, geliştirici izni gerektirir) varsayılan `/` ad alanında `40{"id":"<player_id>", ...}` paketiyle gönderilir (**`KANITLANDI`**).
   - Sunucu `40{"sid":"<namespace_sid>"}` döndürmek zorundadır; `"sid"` yoksa `SocketIONamespace.Submit @ RVA 0x01ACA854` protokol ihlali üretir (**`KANITLANDI`**).
   - `OnConnect` (`RVA 0x019C51B8`) tetiklendiğinde istemci HTTPS üzerinden `_i: "giriskontrol-UyeGirisKontrol"` gönderir ve sunucudan gelen `'VersiyonKontrol'` olayına `{"Versiyon":"3.1.33","os":"ANDROID","_i":"versiyonkontrol-versiyonkontrol","_t":"<session_id>"}` ile yanıt verir (**`KANITLANDI`**).
4. **Canlılık (Keep-Alive):**
   - Engine.IO katmanı: Sunucu `"2"` gönderir -> istemci `"3"` yanıtlar (**`KANITLANDI`**).
   - Socket.IO katmanı: Sunucu `42["ping"]` gönderir -> istemci `OnPing @ RVA 0x019C5444` ile `42["pong"]` yanıtlar (**`KANITLANDI`**).

### 3.2 Bağlantı Kopması ve Yeniden Bağlanma (`KANITLANDI`)
- Sahne parametreleri (`level1+0x7879`): `volatileOperationMode = 1`, `maxConnectAttempts = 10`, `raisingReconnectDelay = 1`.
- Bağlantı koptuğunda `OnClose` (`RVA 0x019C5400`) çalışır; istemci her denemede gecikmeyi artırarak en fazla 10 kez yeniden bağlanır, `OnConnect` sonrası `giriskontrol-UyeGirisKontrol` ve aktif masadaysa `masakontrol-masakontrol` ile masa durumunu tazeler (`GÜÇLÜ İPUCU` masa kurtarma sırası / `KANITLANDI` yeniden bağlanma parametreleri).

---

## 4. Sıra, Masa ve Oyun Hamlelerinin Senkronizasyonu

### 4.1 İstemci -> Sunucu Oyun Komutları (`KANITLANDI`)

| Eylem | `_i` Komut Değeri | Zorunlu Alanlar (`d` JSON) | İkili Kanıt (RVA) | Sınıflandırma |
|---|---|---|---|---|
| Taş Çekme | `"masatascek-tascek"` | `"tip"` (`"o"` orta / `"m"` yan), `"dc"` (`"0"` / `"1"`), `"_t"` | `0x019B8DD0` | **`KANITLANDI`** |
| Taş Atma | `"masatasat-tasat"` | `"tas"` (`TasAdi`), `"gon"` (`"1"`), `"_t"` | `0x019B8B6C` | **`KANITLANDI`** |
| Sunucu Istaka Diz | `"masaseridiz-perdiz"` | `"tip"` (`"Per"` / `"Cift"`), `"_t"` | `0x019B8A50` | **`KANITLANDI`** |
| Çifte Git | `"masacift-ciftegit"` | `"_t"` | `0x019C1D4C` | **`KANITLANDI`** |
| El Bitir / Okey ile Bit | `"masaoyunbitir-oyunbitirbeta"` | `"taslar"` (`"-<Slot1>..-<Slot28>"`), `"bitentas"` (`TasID`), `"_t"` | `0x019FF938` -> `0x019B7BEC` | **`KANITLANDI`** |

### 4.2 Sunucu -> İstemci Masa ve Sıra Olayları (`KANITLANDI` İstemci İşleyicisi / `ENGELLENDİ` Canlı Örnek)

| `s[].i` Olay Adı | İşleyici RVA | İstemcinin Okuduğu Alanlar (`s[].d`) | Sıra / Durum Etkisi | Sınıflandırma |
|---|---|---|---|---|
| `"IstakayiGuncelle"` | `0x019B94AC` | `t` (ıstaka taş dizgesi) | Oyuncu ıstakasını oluşturur/yeniler (`0x01A08EC0`). | İstemci: **`KANITLANDI`** / Canlı tel ayracı: **`GÜÇLÜ İPUCU`** |
| `"MasaTaslariGuncelle"` | `0x019B9590` -> `0x01A08224` | `mid`, `kt`, `ot`, `ok`, `ms`, `yt`, `el`, `es`, `pn`, `rx`, `rxm`, `mk`, `bb`, `mp`, `cn`, `tc`, `cl`, `ob`, `sa`, `y`, `max`, `is_tournament`, `current_round` | Gösterge (`ot`), aktif Okey (`ok`), kalan taş (`kt`), masa sırası (`ms`) ve yetki yönünü (`yt`) senkronize eder. | İstemci: **`KANITLANDI`** / Opsiyonel alt alanlar: **`ENGELLENDİ`** |
| `"TasCek"` | `0x019B8F9C` -> `0x01A02C7C` | `tas`, `yon`, `tip`, `kt`, `tc`, `dc`, `cl`, `m` | Çekilen taşı (`tas`) ilgili yöne ekler, `kt` düşürür, yerel `SiraGeldi` + `SureBaslat` çağırır. | **`KANITLANDI`** (İstemci) |
| `"TasAt"` | `0x019B8D18` -> `0x01A02728` | `tas`, `yon`, `ms`, `tc`, `cl` | Atılan taşı (`tas`) atık alanına yazar, yeni sıra yönü (`ms`) için yerel `SiraGeldi` (`0x01A0E0A4`) + `SureBaslat` çağırır. | **`KANITLANDI`** (İstemci) |
| `"OyunBitir"` | `0x019BA3B0` -> `0x019FA048` | `Baslik`, `BitenTas`, `CanakKirildi`, `Kazananlar[{id,i,p,a,v}]`, `Taslar[]` | El sonu özetini ve kazanan puanlarını gösterir. | **`KANITLANDI`** (İstemci) |
| `"OyunBitirHata"` | `0x019BA8D4` -> `0x01A159DC` | `hata[{Per, Tip, Taslar[]}]` | Geçersiz bitiş denemesinde hatalı perleri vurgular, oyun devam eder. | **`KANITLANDI`** (İstemci) |

---

## 5. Hatalı veya Eksik Yanıtların Yönetimi (`KANITLANDI`)

1. **Boş HTTP Gövdesi (`0 byte`):** Salt okunur kök testinde (`LIVE-HTTP-03-SAFE-GET`) görüldüğü üzere sunucu geçersiz/parametresiz çağrıda `HTTP 200` + `0 byte` dönebilir; `SuWebRequest.Receive` boş dizgeyi sessizce yok sayar, bağımsız istemci de boş gövdede istisna fırlatmamalı ve zaman aşımı sayacını işletmelidir.
2. **Geçersiz Oturum (`GirisYapilamadi`):** `OnGirisYapilamadi @ RVA 0x019B1AB4` tetiklendiğinde `id`, `kullanici`, `token_id`, `session_id` anahtarları silinir ve giriş ekranına dönülür.
3. **Eksik `sid` veya Bozuk JSON:** `SocketIONamespace.Submit` `sid` içermeyen `40` paketini reddeder; `validate_server_envelope` `"s"` dizisi olmayan veya `"i"`/`"d"` eksik paketleri düşürüp tanı günlüğüne yazar.

---

## 6. Kanıt Ayrımı ve Çözülmemiş Riskler Özeti

- **Statik Kod Kanıtı:** Tüm RVA adresleri, zarf anahtarları (`_e`, `_i`, `_t`, `h`, `d`, `s`, `i`, `d`) ve Socket.IO v4 çerçeveleme kuralları `libil2cpp.so` üzerinde kesinleştirilmiştir.
- **Yerel Mock Test Kanıtı:** `live-test/tests/` altındaki testlerde HTTP imzalama, `DuplicateGuard`, `EIO=4`/`SIO=4` el sıkışma, yeniden bağlanma ve 7 olay şeması doğrulanmıştır.
- **Canlı Sunucu Kanıtı:** Yalnızca `:443` HTTPS ve `:4082` pasif TCP erişilebilirliği test edilmiştir.
- **Yetki Nedeniyle Yapılamayan Testler:** Üretim sunucusundan gerçek `IstakayiGuncelle` / `MasaTaslariGuncelle` / `TasCek` JSON yükü yakalanmamıştır (`ENGELLENDİ`).
- **Çözülmemiş Risk:** `IstakayiGuncelle.d.t` dizgesinin çoklu taş ayırıcısı (virgül `,` vs tire `-`) ve opsiyonel masa alanlarının canlı veri tipleri yetkili test kaydı olmadan %100 kesinleştirilemez.
